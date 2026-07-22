# Terminal 模块

> 历史说明：当前 `backend/app/modules` 下已没有 `terminal` 模块，本页不再作为当前实现入口。保留此页仅用于追溯早期远程终端能力的设计意图；新增或排查当前后端能力时不要按本页路径寻找代码。

## 历史职责

早期 `terminal` 设计目标是提供远程终端会话与会话存储能力。

## 历史目录

- `api/routes.py`
- `service/terminal_service.py`
- `service/session_store.py`
- `domain/session.py`
- `schemas/terminal.py`

## 历史职责拆分

- `terminal_service.py`
  管理终端会话生命周期
- `session_store.py`
  管理会话状态存储

## 当前维护建议

如果后续重新引入远程终端能力，应重新建模当前 API、鉴权、审计和会话存储设计，再恢复为正式模块文档。
