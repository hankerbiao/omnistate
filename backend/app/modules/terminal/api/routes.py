"""Terminal websocket routes."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.modules.auth.repository.models import UserDoc
from app.modules.terminal.service import TerminalService
from app.shared.auth.jwt_auth import decode_token
from app.shared.core.logger import log as logger

router = APIRouter(prefix="/terminal", tags=["Terminal"])


def extract_token_from_query(token: str | None) -> str:
    """Extract the JWT token from the websocket query string."""
    # 前端 websocket 不方便复用现有 HTTP Bearer 依赖，这里改为从 query string 取 token。
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    value = token.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    return value


async def get_ws_current_user(token: str) -> dict:
    """Resolve websocket user from JWT token."""
    # websocket 连接建立前先完成用户校验，后续会话只保留 user_id。
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    user = await UserDoc.find_one(UserDoc.user_id == user_id)
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user disabled")

    data = user.model_dump()
    data["id"] = str(user.id)
    return data


@lru_cache(maxsize=1)
def get_terminal_service() -> TerminalService:
    """提供默认的 terminal service。

    当前仍是单进程内存会话模型，不支持多实例共享。
    """
    return TerminalService()


TerminalServiceDep = Annotated[TerminalService, Depends(get_terminal_service)]


@router.websocket("/ws")
async def terminal_ws(
    websocket: WebSocket,
    terminal_service: TerminalServiceDep,
) -> None:
    """Interactive terminal websocket endpoint."""
    try:
        token = extract_token_from_query(websocket.query_params.get("token"))
        current_user = await get_ws_current_user(token)
    except HTTPException as exc:
        # 认证失败直接拒绝升级，避免进入 PTY 创建阶段。
        await websocket.close(code=1008, reason=exc.detail)
        return

    await websocket.accept()

    cols = int(websocket.query_params.get("cols", "120"))
    rows = int(websocket.query_params.get("rows", "32"))

    logger.info(
        "terminal websocket accepted: "
        f"user_id={current_user['user_id']}, cols={cols}, rows={rows}"
    )

    try:
        await terminal_service.handle_websocket(
            websocket=websocket,
            user_id=current_user["user_id"],
            cols=cols,
            rows=rows,
        )
    except ValueError as exc:
        # 这里主要承接会话上限等业务性拒绝。
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close(code=1013, reason=str(exc))
    except WebSocketDisconnect:
        logger.info(f"terminal websocket disconnected: user_id={current_user['user_id']}")
    except Exception:
        logger.exception(f"terminal websocket failed unexpectedly: user_id={current_user['user_id']}")
        await websocket.close(code=1011, reason="terminal session error")
