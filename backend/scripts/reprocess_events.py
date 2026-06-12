"""
重新处理已归档但未更新到 case 的执行事件。

背景：Kafka 上报的 case_id（如 "test_firmware_inventory_list"）与系统
execution_task_cases 中的 case_id（如 "suite-redfish-001"）不一致，
导致 ingest_event 找不到 case，case 的 result_data / status 全部为空。

修复后在 ingest 中增加了兜底逻辑（按 task_id 取第一条 case），
但这个脚本用来修复已有的旧事件。
"""

import asyncio
import sys
from datetime import timezone
from pathlib import Path

# 确保可以 import app 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymongo import MongoClient
from app.shared.config import get_settings


def main():
    settings = get_settings()
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 找到所有 processed=true 但 case 状态还是 QUEUED 的事件所属 task
    # （即事件被归档了但 case 没被更新的 task）
    case_task_ids = set(
        doc["task_id"]
        for doc in db["execution_task_cases"].find(
            {"status": "QUEUED", "event_count": 0},
            {"task_id": 1},
        )
    )

    # 找到这些 task 相关的 events
    events = list(
        db["execution_events"].find(
            {"task_id": {"$in": list(case_task_ids)}, "processed": True},
        ).sort("_id", 1)
    )

    if not events:
        print("没有需要重新处理的事件")
        return

    print(f"找到 {len(events)} 条待重新处理的事件（涉及 {len(case_task_ids)} 个 task）")

    updated_case_count = 0
    for e in events:
        task_id = e["task_id"]
        event_case_id = e.get("case_id")

        # 1. 尝试按 event.case_id 匹配
        case = db["execution_task_cases"].find_one({
            "task_id": task_id,
            "case_id": event_case_id,
            "is_deleted": False,
        })

        # 2. 兜底：取 task 第一条 case
        if case is None:
            case = db["execution_task_cases"].find_one(
                {"task_id": task_id, "is_deleted": False},
                sort=[("order_no", 1)],
            )

        if case is None:
            continue  # 该 task 没有任何 case，跳过

        # 更新 case 状态
        phase = e.get("phase")
        event_type = e.get("event_type")
        event_status = e.get("event_status")
        event_time = e.get("event_timestamp")

        # 累积计数
        inc_fields = {}
        if event_type == "assert":
            inc_fields["step_total"] = 1
            status_norm = (event_status or "").strip().lower()
            if status_norm == "ok":
                inc_fields["step_passed"] = 1
            elif status_norm == "failed":
                inc_fields["step_failed"] = 1
            elif status_norm == "skipped":
                inc_fields["step_skipped"] = 1

        set_fields = {
            "last_event_id": e["event_id"],
            "last_event_at": event_time,
        }

        # 时间戳
        if phase == "case_start" and case.get("started_at") is None:
            set_fields["started_at"] = event_time
        if phase == "case_finish":
            if case.get("started_at") is None:
                set_fields["started_at"] = event_time
            set_fields["finished_at"] = event_time
            set_fields["status"] = "done"

        # 如果还没设置过 status，根据 phase 设置
        if case.get("status") == "QUEUED":
            if phase in ("case_start",):
                set_fields["status"] = "RUNNING"
            if phase in ("collection_start",):
                set_fields["status"] = "RUNNING"

        # result_data
        result_data = dict(case.get("result_data") or {})
        result_data["event_type"] = event_type
        result_data["phase"] = phase
        result_data["status"] = event_status
        if e.get("payload", {}).get("data"):
            result_data["data"] = e["payload"]["data"]
        if e.get("payload", {}).get("error"):
            result_data["error"] = e["payload"]["error"]

        set_fields["result_data"] = result_data

        if inc_fields:
            db["execution_task_cases"].update_one(
                {"_id": case["_id"]},
                {"$set": set_fields, "$inc": {**inc_fields, "event_count": 1}},
            )
        else:
            db["execution_task_cases"].update_one(
                {"_id": case["_id"]},
                {"$set": set_fields, "$inc": {"event_count": 1}},
            )
        updated_case_count += 1

    # 更新 task 聚合状态
    for task_id in case_task_ids:
        task_cases = list(db["execution_task_cases"].find(
            {"task_id": task_id, "is_deleted": False}
        ))
        finished = sum(1 for c in task_cases if c.get("finished_at"))
        failed = sum(1 for c in task_cases if c.get("status") == "FAILED")
        passed = finished - failed
        total = len(task_cases)

        db["execution_tasks"].update_one(
            {"task_id": task_id},
            {"$set": {
                "consume_status": "CONSUMED",
                "consumed_at": events[-1]["event_timestamp"],
                "finished_case_count": finished,
                "failed_case_count": failed,
                "passed_case_count": max(passed, 0),
                "progress_percent": round((finished / total) * 100, 2) if total else 0,
                "overall_status": "FAILED" if failed > 0 else ("PASSED" if finished == total else "RUNNING"),
            }},
        )
        print(f"  Task {task_id}: {total} cases, {finished} finished")

    print(f"\n完成！已更新 {updated_case_count} 条 case 记录")
    client.close()


if __name__ == "__main__":
    main()
