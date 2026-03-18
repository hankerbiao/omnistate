#!/usr/bin/env python3
"""极简 Fake 测试框架客户端。

用途：
- 模拟执行框架接收后端 HTTP 下发的任务
- 自动回传消费确认、事件、case 进度和最终结果
- 默认逻辑尽量简单，方便按需直接修改

运行方式：
    python client/fake_framework_client.py

默认会：
1. 启动本地 HTTP 服务，监听 /api/v1/execution/tasks/dispatch
2. 向平台注册自己为一个 execution agent
3. 周期性发送心跳
4. 收到任务后，按预设步骤自动回调平台
"""
from __future__ import annotations

import argparse
import json
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from typing import Any


# 这部分故意写成简单常量，方便直接改。
DEFAULT_PLATFORM_URL = "http://127.0.0.1:8000"
DEFAULT_AGENT_ID = "fake-framework-agent"
DEFAULT_AGENT_HOST = "127.0.0.1"
DEFAULT_AGENT_PORT = 19090
DEFAULT_REGION = "default"
DEFAULT_HEARTBEAT_INTERVAL = 30
DEFAULT_HEARTBEAT_TTL = 90
DEFAULT_STEP_DELAY_SECONDS = 1.0

# 模拟每个 case 的进度步骤；需要改流程时直接改这里。
DEFAULT_CASE_STEPS = [
    {"progress": 10, "status": "RUNNING", "step_passed": 0, "step_failed": 0, "step_skipped": 0},
    {"progress": 50, "status": "RUNNING", "step_passed": 1, "step_failed": 0, "step_skipped": 0},
    {"progress": 100, "status": "PASSED", "step_passed": 2, "step_failed": 0, "step_skipped": 0},
]

# 结果模板；按 case_id 覆盖时可参考这个形状。
DEFAULT_CASE_RESULT = {
    "status": "PASSED",
    "message": "fake execution finished",
    "artifacts": ["report/fake-report.html"],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def detect_local_ip() -> str:
    """尽量获取本机可访问 IP，失败时回退为 127.0.0.1。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class JsonHttpClient:
    """极简 JSON HTTP 客户端，仅覆盖当前脚本需要的能力。"""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {url}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"request failed for {url}: {exc}") from exc


class FakeFrameworkClient:
    """假执行框架客户端。"""

    def __init__(
        self,
        *,
        platform_url: str,
        agent_id: str,
        host: str,
        port: int,
        region: str,
        heartbeat_interval: int,
        heartbeat_ttl_seconds: int,
        step_delay_seconds: float,
    ) -> None:
        self.platform_url = platform_url.rstrip("/")
        self.agent_id = agent_id
        self.host = host
        self.port = port
        self.region = region
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_ttl_seconds = heartbeat_ttl_seconds
        self.step_delay_seconds = step_delay_seconds
        self.base_url = f"http://{host}:{port}"
        self.http = JsonHttpClient()
        self.event_seq = count(start=1)
        self.stop_event = threading.Event()
        self.case_results: dict[str, dict[str, Any]] = {}

    def register_agent(self) -> None:
        payload = {
            "agent_id": self.agent_id,
            "hostname": socket.gethostname(),
            "ip": detect_local_ip(),
            "port": self.port,
            "base_url": self.base_url,
            "region": self.region,
            "status": "ONLINE",
            "heartbeat_ttl_seconds": self.heartbeat_ttl_seconds,
        }
        url = f"{self.platform_url}/api/v1/execution/agents/register"
        response = self.http.post(url, payload)
        print(f"[register] {json.dumps(response, ensure_ascii=False)}")

    def heartbeat_forever(self) -> None:
        url = f"{self.platform_url}/api/v1/execution/agents/{self.agent_id}/heartbeat"
        payload = {"status": "ONLINE"}
        while not self.stop_event.is_set():
            try:
                response = self.http.post(url, payload)
                print(f"[heartbeat] {json.dumps(response, ensure_ascii=False)}")
            except Exception as exc:  # noqa: BLE001
                print(f"[heartbeat] failed: {exc}")
            self.stop_event.wait(self.heartbeat_interval)

    def handle_task(self, task_payload: dict[str, Any]) -> None:
        thread = threading.Thread(
            target=self._run_task,
            args=(task_payload,),
            daemon=True,
        )
        thread.start()

    def _run_task(self, task_payload: dict[str, Any]) -> None:
        task_id = task_payload["task_id"]
        cases = task_payload.get("cases") or []
        if not cases:
            print(f"[task:{task_id}] skipped: cases is empty")
            return

        case_id = cases[0]["case_id"]
        print(f"[task:{task_id}] start case={case_id}")

        try:
            self._ack_consume(task_id)
            self._report_event(
                task_id,
                event_type="TASK_ACCEPTED",
                payload={"agent_id": self.agent_id, "case_id": case_id},
            )
            self._simulate_case(task_id, case_id)
            self._complete_task(task_id, case_id)
            print(f"[task:{task_id}] completed")
        except Exception as exc:  # noqa: BLE001
            print(f"[task:{task_id}] failed: {exc}")
            self._safe_complete_as_failed(task_id, case_id, str(exc))

    def _ack_consume(self, task_id: str) -> None:
        url = f"{self.platform_url}/api/v1/execution/tasks/{task_id}/consume-ack"
        payload = {"consumer_id": self.agent_id}
        response = self.http.post(url, payload)
        print(f"[consume-ack] task={task_id} response={json.dumps(response, ensure_ascii=False)}")

    def _report_event(self, task_id: str, event_type: str, payload: dict[str, Any]) -> None:
        seq = next(self.event_seq)
        event_payload = {
            "event_id": f"{task_id}-evt-{seq}",
            "event_type": event_type,
            "seq": seq,
            "source_time": utc_now_iso(),
            "payload": payload,
        }
        url = f"{self.platform_url}/api/v1/execution/tasks/{task_id}/events"
        response = self.http.post(url, event_payload)
        print(f"[event] task={task_id} type={event_type} response={json.dumps(response, ensure_ascii=False)}")

    def _simulate_case(self, task_id: str, case_id: str) -> None:
        started_at = utc_now_iso()
        total_steps = max(len(DEFAULT_CASE_STEPS), 1)

        for index, step in enumerate(DEFAULT_CASE_STEPS, start=1):
            seq = next(self.event_seq)
            is_final_step = index == total_steps
            payload = {
                "status": step["status"],
                "event_id": f"{task_id}-{case_id}-status-{seq}",
                "seq": seq,
                "progress_percent": float(step["progress"]),
                "step_total": total_steps,
                "step_passed": int(step["step_passed"]),
                "step_failed": int(step["step_failed"]),
                "step_skipped": int(step["step_skipped"]),
                "started_at": started_at,
                "finished_at": utc_now_iso() if is_final_step else None,
                "result_data": self._build_case_result(case_id, step["status"], index, total_steps),
            }
            url = (
                f"{self.platform_url}/api/v1/execution/tasks/{task_id}/cases/"
                f"{case_id}/status"
            )
            response = self.http.post(url, payload)
            print(
                "[case-status] "
                f"task={task_id} case={case_id} step={index}/{total_steps} "
                f"response={json.dumps(response, ensure_ascii=False)}"
            )
            if not is_final_step:
                time.sleep(self.step_delay_seconds)

    def _build_case_result(
        self,
        case_id: str,
        status: str,
        step_index: int,
        total_steps: int,
    ) -> dict[str, Any]:
        result = dict(DEFAULT_CASE_RESULT)
        result.update(self.case_results.get(case_id, {}))
        result.update(
            {
                "case_id": case_id,
                "status": status,
                "current_step": step_index,
                "total_steps": total_steps,
                "updated_at": utc_now_iso(),
            }
        )
        return result

    def _complete_task(self, task_id: str, case_id: str) -> None:
        seq = next(self.event_seq)
        final_case_result = dict(DEFAULT_CASE_RESULT)
        final_case_result.update(self.case_results.get(case_id, {}))
        final_status = final_case_result.get("status", "PASSED")
        summary = {
            "agent_id": self.agent_id,
            "case_id": case_id,
            "case_status": final_status,
            "passed": 1 if final_status == "PASSED" else 0,
            "failed": 1 if final_status == "FAILED" else 0,
            "skipped": 1 if final_status == "SKIPPED" else 0,
        }
        payload = {
            "status": "PASSED" if final_status == "PASSED" else "FAILED",
            "event_id": f"{task_id}-complete-{seq}",
            "seq": seq,
            "finished_at": utc_now_iso(),
            "summary": summary,
            "error_message": None if final_status == "PASSED" else final_case_result.get("message"),
            "executor": self.agent_id,
        }
        url = f"{self.platform_url}/api/v1/execution/tasks/{task_id}/complete"
        response = self.http.post(url, payload)
        print(f"[complete] task={task_id} response={json.dumps(response, ensure_ascii=False)}")

    def _safe_complete_as_failed(self, task_id: str, case_id: str, error_message: str) -> None:
        try:
            seq = next(self.event_seq)
            payload = {
                "status": "FAILED",
                "event_id": f"{task_id}-complete-{seq}",
                "seq": seq,
                "finished_at": utc_now_iso(),
                "summary": {
                    "agent_id": self.agent_id,
                    "case_id": case_id,
                    "passed": 0,
                    "failed": 1,
                    "skipped": 0,
                },
                "error_message": error_message,
                "executor": self.agent_id,
            }
            url = f"{self.platform_url}/api/v1/execution/tasks/{task_id}/complete"
            response = self.http.post(url, payload)
            print(f"[complete-failed] task={task_id} response={json.dumps(response, ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001
            print(f"[complete-failed] task={task_id} failed again: {exc}")


def build_handler(client: FakeFrameworkClient) -> type[BaseHTTPRequestHandler]:
    class TaskDispatchHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/v1/execution/tasks/dispatch":
                self.send_error(404, "not found")
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                payload = json.loads(body or "{}")
            except json.JSONDecodeError:
                self._write_json(400, {"accepted": False, "message": "invalid json"})
                return

            print(f"[dispatch] received={json.dumps(payload, ensure_ascii=False)}")
            client.handle_task(payload)
            self._write_json(
                202,
                {
                    "accepted": True,
                    "message": "fake framework accepted task",
                    "agent_id": client.agent_id,
                    "task_id": payload.get("task_id"),
                },
            )

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._write_json(200, {"ok": True, "agent_id": client.agent_id})
                return
            self.send_error(404, "not found")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return TaskDispatchHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fake execution framework client")
    parser.add_argument("--platform-url", default=DEFAULT_PLATFORM_URL, help="后端平台地址")
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID, help="执行代理 ID")
    parser.add_argument("--host", default=DEFAULT_AGENT_HOST, help="本地监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_AGENT_PORT, help="本地监听端口")
    parser.add_argument("--region", default=DEFAULT_REGION, help="代理区域")
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=DEFAULT_HEARTBEAT_INTERVAL,
        help="心跳间隔秒数",
    )
    parser.add_argument(
        "--heartbeat-ttl",
        type=int,
        default=DEFAULT_HEARTBEAT_TTL,
        help="注册时上报的心跳租约秒数",
    )
    parser.add_argument(
        "--step-delay",
        type=float,
        default=DEFAULT_STEP_DELAY_SECONDS,
        help="每个 fake 进度步骤之间的等待秒数",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = FakeFrameworkClient(
        platform_url=args.platform_url,
        agent_id=args.agent_id,
        host=args.host,
        port=args.port,
        region=args.region,
        heartbeat_interval=args.heartbeat_interval,
        heartbeat_ttl_seconds=args.heartbeat_ttl,
        step_delay_seconds=args.step_delay,
    )

    client.register_agent()

    heartbeat_thread = threading.Thread(target=client.heartbeat_forever, daemon=True)
    heartbeat_thread.start()

    server = ThreadingHTTPServer((args.host, args.port), build_handler(client))
    print(
        f"[server] listening on {client.base_url}, "
        f"dispatch path=/api/v1/execution/tasks/dispatch, "
        f"platform={client.platform_url}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] shutting down")
    finally:
        client.stop_event.set()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
