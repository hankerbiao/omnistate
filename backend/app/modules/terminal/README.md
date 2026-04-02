# Terminal 模块

当前 terminal 能力采用单进程内存会话模型。

约束：

- 仅支持单实例部署
- 会话状态默认保存在进程内存
- 进程重启后会话会丢失
- 会话上限按单进程维度计算

实现说明：

- `api/routes.py` 只负责 websocket 生命周期和鉴权
- `service/terminal_service.py` 负责 SSH 会话生命周期
- `service/session_store.py` 提供会话存储抽象，默认实现为 `InMemoryTerminalSessionStore`

后续如果要支持多实例部署，应替换为共享 session store，而不是继续扩展模块级内存单例
