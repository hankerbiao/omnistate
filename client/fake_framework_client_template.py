#!/usr/bin/env python3
import json
import socket
from contextlib import asynccontextmanager
from typing import Any

import requests
from fastapi import FastAPI


PLATFORM_URL = "http://10.2.50.167:8000"
AGENT_ID = "fake-framework-agent"
HOST = "127.0.0.1"
PORT = 19090
REGION = "default"
HEARTBEAT_INTERVAL = 30
HEARTBEAT_TTL = 90


def detect_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class JsonHttpClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def post(self, url: str, payload: dict) -> dict:
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


class FrameworkClient:
    def __init__(self) -> None:
        self.platform_url = PLATFORM_URL
        self.agent_id = AGENT_ID
        self.host = HOST
        self.port = PORT
        self.region = REGION
        self.heartbeat_interval = HEARTBEAT_INTERVAL
        self.heartbeat_ttl_seconds = HEARTBEAT_TTL
        self.base_url = f"http://{HOST}:{PORT}"
        self.http = JsonHttpClient()

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

    def send_heartbeat(self) -> dict[str, Any]:
        url = f"{self.platform_url}/api/v1/execution/agents/{self.agent_id}/heartbeat"
        payload = {"status": "ONLINE"}
        response = self.http.post(url, payload)
        print(f"[heartbeat] {json.dumps(response, ensure_ascii=False)}")
        return response


client = FrameworkClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    client.register_agent()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/heartbeat")
async def heartbeat():
    return client.send_heartbeat()


@app.get("/health")
async def health():
    return {"ok": True, "agent_id": client.agent_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)