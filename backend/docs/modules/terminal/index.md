# Terminal 模块

## 模块职责

`terminal` 提供远程终端会话与会话存储能力。

## 核心目录

- `api/routes.py`
- `service/terminal_service.py`
- `service/session_store.py`
- `domain/session.py`
- `schemas/terminal.py`

## 关键职责拆分

- `terminal_service.py`
  管理终端会话生命周期
- `session_store.py`
  管理会话状态存储

## 常见修改场景

- 改终端接口参数：看 `schemas/terminal.py`
- 改会话管理：看 `terminal_service.py`
- 改存储策略：看 `session_store.py`
