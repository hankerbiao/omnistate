# WebSocket 远程终端

本文档描述 DMLV4 当前仓库中“终端调试”页面的真实实现。

这份文档同时面向两类读者：

- 用户：想知道如何在页面中连接远程服务器并使用终端
- 开发者：想了解前端、WebSocket、后端 SSH 桥接、协议字段和安全边界

当前能力基于：

- 前端 `xterm.js`
- 后端 FastAPI WebSocket
- 后端 `paramiko` SSH 连接

当前实现不是浏览器直接 SSH 到远程主机，而是：

1. 浏览器通过 WebSocket 连接 DMLV4 后端
2. 后端收到连接参数后，使用 SSH 连接远程服务器
3. 后端把远程 shell 输入输出转发给前端终端页面

## 1. 适用范围

本文档只描述当前仓库中已经实现的终端能力：

- 前端页面：`frontend/src/components/TerminalPage.tsx`
- WebSocket 路由：`backend/app/modules/terminal/api/routes.py`
- 终端服务：`backend/app/modules/terminal/service/terminal_service.py`
- 协议模型：`backend/app/modules/terminal/schemas/terminal.py`

当前范围内的真实行为：

- 用户登录后可进入“终端调试”页面
- 页面可填写 `host`、`port`、`username`、`password`
- 连接参数保存在浏览器本地 `localStorage`
- 前端通过 WebSocket 与后端建立会话
- 后端通过 SSH 连接远程主机并打开交互式 shell
- xterm 输入会被转发到远程 shell
- 远程 shell 输出会实时显示在页面中

当前未实现的能力：

- 私钥登录
- 跳板机
- 多主机收藏管理
- 后端持久化保存密码
- 主机指纹校验界面
- 审计回放

## 2. 用户指南

## 2.1 使用前提

使用终端页前，需要满足以下条件：

- 已登录 DMLV4 前端
- 当前用户具备访问终端页的权限
- DMLV4 后端可以访问目标 SSH 主机
- 目标主机开放 SSH 端口，通常是 `22`
- 目标主机用户名和密码正确

补充说明：

- 浏览器不直接连接远程主机
- 真正发起 SSH 连接的是 DMLV4 后端所在机器
- 如果浏览器能访问目标主机，但后端机器不能访问，连接仍然会失败

## 2.2 页面输入项

终端页当前提供 4 个连接字段：

| 字段 | 说明 |
|------|------|
| `Host` | 目标服务器地址，可以是 IP 或域名 |
| `Port` | SSH 端口，默认 `22` |
| `Username` | 登录用户名 |
| `Password` | 登录密码 |

页面会自动把这些值保存到浏览器本地 `localStorage`，下次打开页面时自动回填。

## 2.3 连接步骤

1. 打开“终端调试”页面
2. 填写 `Host`、`Port`、`Username`、`Password`
3. 点击“连接终端”
4. 等待页面显示连接状态和会话信息
5. 在终端区域直接输入命令

连接成功后，页面通常会显示：

- 状态：`已连接`
- 目标主机：`username@host:port`
- 会话 ID

## 2.4 断开连接

点击“断开”会关闭当前 WebSocket 会话，后端会同步关闭 SSH channel 和 SSH client。

这意味着：

- 当前远程 shell 会话结束
- 未保存的交互式状态会丢失
- 再次连接会重新创建一个新的远程 shell

## 2.5 清空凭据

点击“清空凭据”会清理浏览器本地保存的连接信息，包括：

- `host`
- `port`
- `username`
- `password`

此操作只影响当前浏览器，不影响后端，也不会影响其他用户。

## 2.6 常见错误

### `[error] missing SSH connection fields`

含义：

- `host`
- `port`
- `username`
- `password`

中至少有一个为空。

处理方式：

1. 点“清空凭据”
2. 重新填写全部字段
3. 再次连接

### `WebSocket 连接失败`

含义：

- 前端无法成功连接 DMLV4 后端的 `/api/v1/terminal/ws`

常见原因：

- 后端服务未启动
- 前端配置的 `VITE_API_BASE_URL` 不正确
- 登录 token 无效
- 反向代理未放通 WebSocket

### 页面显示连接异常，但 SSH 主机本身没问题

这通常说明问题不在目标主机，而在中间链路，例如：

- 后端无法访问目标主机
- 后端未安装 `paramiko`
- 用户认证通过了，但 SSH 认证失败

## 3. 开发者视角的整体架构

终端链路当前是一个“双跳模型”：

```text
Browser (xterm.js)
  <-> WebSocket
DMLV4 Backend (FastAPI + TerminalService)
  <-> SSH
Remote Host Shell
```

职责划分如下：

- 前端：负责终端 UI、用户输入、WebSocket 连接和显示输出
- WebSocket 路由：负责 token 鉴权、建立连接、调用终端服务
- 终端服务：负责 SSH 建连、会话管理、I/O 桥接、超时和清理
- 远程主机：负责提供真实 shell 执行环境

## 4. 前端实现说明

前端入口文件：

- `frontend/src/components/TerminalPage.tsx`

## 4.1 页面状态

终端页维护几个核心状态：

- `connectionState`
  - `idle`
  - `connecting`
  - `connected`
  - `closed`
  - `error`
- `sessionMeta`
  - `sessionId`
  - `shell`
  - `cwd`
  - `host`
  - `port`
  - `username`
- `form`
  - `host`
  - `port`
  - `username`
  - `password`

## 4.2 浏览器本地保存

前端通过 `localStorage` 保存 SSH 凭据：

- key：`dml_terminal_ssh_credentials`

当前保存内容包括明文密码。

这意味着：

- 刷新页面后数据仍会保留
- 同一浏览器同一用户下次打开页面会自动回填
- 安全性依赖浏览器和本机环境

因此当前实现只适合受控环境，不适合公网高风险场景。

## 4.3 xterm 生命周期

终端页在挂载时创建 `Terminal` 和 `FitAddon`，并绑定到页面容器。

当前实现特别处理了 `fit()` 的调用时机：

- 不直接在每次尺寸变化时立刻调用
- 通过 `requestAnimationFrame` 延迟到下一帧执行
- 仅在终端已经 `open()` 且容器仍在 DOM 中时执行

这样做的原因是旧版 `xterm` / `xterm-addon-fit` 在 viewport 尚未准备好，或组件已经销毁时，容易报类似错误：

`Cannot read properties of undefined (reading 'dimensions')`

## 4.4 WebSocket 建连流程

前端不会把 SSH 用户名密码放在 WebSocket URL 中。

实际流程是：

1. 从 `localStorage` 取 JWT token
2. 组装 `/api/v1/terminal/ws?token=...&cols=...&rows=...`
3. 建立 WebSocket
4. `onopen` 后发送第一条消息 `connect`
5. 收到后端 `session` 消息后，进入 `connected`
6. 后续键盘输入使用 `input`
7. 终端尺寸变化使用 `resize`

这意味着：

- URL 里只会出现 JWT token 和窗口尺寸
- SSH 密码只出现在 WebSocket 消息体里

## 4.5 前端时序

从前端视角看，一次完整连接通常经历以下顺序：

```text
用户点击“连接终端”
  -> 前端校验 host / port / username / password
  -> 前端读取 jwt_token
  -> 前端创建 WebSocket
  -> WebSocket onopen
  -> 前端发送 connect 消息
  -> 前端等待 session 消息
  -> 收到 session 后切到 connected
  -> 用户键盘输入
  -> 前端持续发送 input 消息
  -> 页面尺寸变化时发送 resize 消息
  -> 用户点击断开或连接中断
  -> WebSocket onclose
```

## 5. 后端实现说明

后端相关文件：

- `backend/app/modules/terminal/api/routes.py`
- `backend/app/modules/terminal/service/terminal_service.py`
- `backend/app/modules/terminal/domain/session.py`
- `backend/app/modules/terminal/schemas/terminal.py`

## 5.1 WebSocket 路由职责

`/api/v1/terminal/ws` 路由负责：

1. 从 query string 提取 `token`
2. 解码 JWT
3. 校验用户是否存在且状态为 `ACTIVE`
4. 接受 WebSocket 连接
5. 读取初始 `cols` 和 `rows`
6. 将连接交给 `TerminalService.handle_websocket`

注意：

- WebSocket 鉴权复用了现有 JWT
- 鉴权失败时会在升级阶段直接拒绝连接
- 路由层不负责 SSH 细节

## 5.2 TerminalService 的职责

`TerminalService` 当前负责以下几类事情：

- 会话配额检查
- 接收首条 `connect` 消息
- 用 `paramiko` 建立 SSH 连接
- 打开远程 shell
- 把远程输出泵送到 WebSocket
- 把前端输入转发到 SSH channel
- 处理终端 resize
- 空闲超时回收
- 会话关闭时释放资源

## 5.3 会话模型

当前终端会话是一个内存态对象，保存在服务进程内。

每个会话至少包含：

- `session_id`
- `user_id`
- `host`
- `port`
- `username`
- `ssh_client`
- `ssh_channel`
- `cols`
- `rows`
- `created_at`
- `last_active_at`

这意味着：

- 服务进程重启后，会话不会保留
- 终端会话目前不支持多实例共享
- 当前设计更适合单实例或黏性会话部署

## 5.4 SSH 建连行为

当前 SSH 建连使用 `paramiko.SSHClient`，关键行为如下：

- `set_missing_host_key_policy(paramiko.AutoAddPolicy())`
- `look_for_keys=False`
- `allow_agent=False`
- 使用密码登录
- `invoke_shell(term="xterm-256color", width=cols, height=rows)`

这代表当前实现：

- 不读取本地私钥
- 不走 ssh-agent
- 遇到未知主机指纹会自动接受
- 使用交互式 shell，而不是单次命令执行

## 5.5 I/O 桥接模型

连接建立后，后端启动 3 个并发协程：

1. 输出泵送协程
   持续从 SSH channel 读取数据，转成 `output` 消息发给前端
2. 输入接收协程
   持续接收前端消息，把 `input` 写入 SSH channel，把 `resize` 同步给远程 PTY
3. 空闲检测协程
   定期检查 `last_active_at`，超时后关闭会话

任意一个协程先结束，都会触发本次会话的整体回收。

## 5.6 端到端时序图

下面这张图把“浏览器 -> DMLV4 后端 -> 远程 SSH 主机”的真实链路串起来。

```text
Browser / xterm.js                DMLV4 WebSocket API                 TerminalService                    Remote SSH Host
       |                                   |                                 |                                   |
       |  ws connect ?token&cols&rows      |                                 |                                   |
       |---------------------------------->|                                 |                                   |
       |                                   |  decode token / load user       |                                   |
       |                                   |-------------------------------->|                                   |
       |                                   |<--------------------------------|                                   |
       |                                   |  websocket accept               |                                   |
       |<----------------------------------|                                 |                                   |
       |                                   |                                 |                                   |
       |  {"type":"connect", ...}          |                                 |                                   |
       |---------------------------------->|  handle_websocket               |                                   |
       |                                   |-------------------------------->|                                   |
       |                                   |                                 |  SSH connect(host, port, user)    |
       |                                   |                                 |---------------------------------->|
       |                                   |                                 |  invoke_shell + allocate PTY      |
       |                                   |                                 |<----------------------------------|
       |                                   |                                 |                                   |
       |                                   |  {"type":"session", ...}        |                                   |
       |<----------------------------------|<--------------------------------|                                   |
       |                                   |                                 |                                   |
       |  {"type":"input","data":"ls\r"}   |                                 |                                   |
       |---------------------------------->|-------------------------------->|  send to ssh channel              |
       |                                   |                                 |---------------------------------->|
       |                                   |                                 |                                   |
       |                                   |                                 |  recv stdout/stderr               |
       |                                   |                                 |<----------------------------------|
       |  {"type":"output","data":"..."}   |                                 |                                   |
       |<----------------------------------|<--------------------------------|                                   |
       |                                   |                                 |                                   |
       |  {"type":"resize",...}            |                                 |                                   |
       |---------------------------------->|-------------------------------->|  resize_pty                       |
       |                                   |                                 |---------------------------------->|
       |                                   |                                 |                                   |
       |  websocket close / idle timeout   |                                 |                                   |
       |<--------------------------------->|-------------------------------->|  close channel + client           |
```

## 6. WebSocket 协议

协议模型定义在：

- `backend/app/modules/terminal/schemas/terminal.py`

## 6.1 客户端到服务端

### `connect`

首条消息必须是 `connect`。

示例：

```json
{
  "type": "connect",
  "host": "10.10.10.8",
  "port": 22,
  "username": "root",
  "password": "secret"
}
```

约束：

- `host` 必填
- `port` 必填，范围 `1-65535`
- `username` 必填
- `password` 必填

如果首条消息不是 `connect`，后端会拒绝本次终端初始化。

### `input`

用于发送终端键盘输入。

示例：

```json
{
  "type": "input",
  "data": "ls -la\r"
}
```

### `resize`

用于同步终端尺寸。

示例：

```json
{
  "type": "resize",
  "cols": 132,
  "rows": 40
}
```

### `ping`

用于活跃探测。

示例：

```json
{
  "type": "ping"
}
```

## 6.2 服务端到客户端

### `session`

表示 SSH 会话已经成功建立。

示例：

```json
{
  "type": "session",
  "session_id": "1c2d3e4f",
  "shell": "ssh",
  "cwd": "root@10.10.10.8",
  "host": "10.10.10.8",
  "port": 22,
  "username": "root"
}
```

### `output`

表示远程 shell 输出。

示例：

```json
{
  "type": "output",
  "data": "Linux server 5.15.0 ...\r\n"
}
```

### `error`

表示会话错误。

示例：

```json
{
  "type": "error",
  "message": "Authentication failed."
}
```

### `exit`

表示远程 shell 已退出。

示例：

```json
{
  "type": "exit",
  "code": 0
}
```

### `pong`

表示对 `ping` 的响应。

## 6.3 一次成功会话的完整消息示例

下面的示例展示了一个典型成功链路。

### 1. 浏览器建立 WebSocket

```text
ws://localhost:8000/api/v1/terminal/ws?token=<jwt_token>&cols=170&rows=39
```

### 2. 浏览器发送首条 `connect`

```json
{
  "type": "connect",
  "host": "10.17.154.252",
  "port": 22,
  "username": "root",
  "password": "secret"
}
```

### 3. 服务端返回 `session`

```json
{
  "type": "session",
  "session_id": "6f769355f5d345d88f4684e5f8e784aa",
  "shell": "ssh",
  "cwd": "root@10.17.154.252",
  "host": "10.17.154.252",
  "port": 22,
  "username": "root"
}
```

### 4. 服务端持续返回远端输出

```json
{
  "type": "output",
  "data": "Last login: Tue Apr  1 10:22:08 2026 from 10.17.55.10\r\n[root@host ~]# "
}
```

### 5. 浏览器发送命令输入

```json
{
  "type": "input",
  "data": "uname -a\r"
}
```

### 6. 服务端返回命令输出

```json
{
  "type": "output",
  "data": "Linux host 5.15.0-102.el9.x86_64 #1 SMP ...\r\n[root@host ~]# "
}
```

### 7. 浏览器调整终端尺寸

```json
{
  "type": "resize",
  "cols": 180,
  "rows": 42
}
```

### 8. 浏览器主动断开

此时通常不会再收到新的业务消息，而是进入 WebSocket `onclose`，后端同步执行 SSH 资源清理。

## 7. 鉴权与权限

当前终端链路有两层访问控制：

### 7.1 WebSocket 建连鉴权

前端在 WebSocket URL 中携带 JWT token。

后端会：

- 解码 token
- 读取 `sub`
- 查询 `UserDoc`
- 确认用户状态为 `ACTIVE`

若失败，则 WebSocket 不会进入正常会话阶段。

### 7.2 页面入口权限

终端页是否对某个用户开放，仍应由现有导航权限和 RBAC 体系控制。

文档层建议：

- 只向可信用户开放
- 不要给普通业务用户默认开通
- 生产环境需要更严格的权限模型

## 8. 安全边界与风险

当前实现可以工作，但安全边界比较宽，必须明确。

## 8.1 当前风险

### 前端明文保存密码

密码保存在浏览器 `localStorage` 中。

风险包括：

- 同机其他人可读取浏览器本地数据
- 被恶意脚本利用时可能泄漏
- 浏览器配置同步时可能带出数据

### URL 中仍包含 JWT token

WebSocket URL query 中包含业务登录 token。

风险包括：

- 某些代理或日志可能记录 URL
- 排障截图中可能泄漏 token

### 自动接受 SSH 主机指纹

后端当前使用 `AutoAddPolicy()`。

这会降低首次连接门槛，但也降低主机真实性校验强度。

### 会话不持久化

当前会话只保存在内存中。

如果服务重启：

- 会话立即断开
- 用户无法恢复原终端状态

## 8.2 生产环境建议

如果要把此功能用于更严格环境，建议后续按优先级补强：

1. 不在前端保存明文密码
2. 改为后端加密保存或临时会话态保存
3. 支持 SSH 私钥登录
4. 做主机指纹确认与白名单
5. 记录安全审计日志
6. 对危险命令或目标主机做权限限制
7. 把 token 从 query string 迁移到更稳妥的握手方案

## 8.3 生产环境加固清单

如果这个终端能力要进入测试生产环境或正式生产环境，建议至少做到以下几点。

### 账号与凭据

- 不要在前端 `localStorage` 保存明文密码
- 优先改成后端短期会话态保存，或后端加密存储
- 更推荐支持 SSH 私钥或一次性凭据，而不是长期静态密码
- 明确密码轮换机制，避免长期共用 root 密码

### 用户与权限

- 只给少数受信管理员开放终端入口
- 单独定义终端访问权限，不要和普通读权限混用
- 对不同角色限制可访问的主机范围
- 最好将“能登录页面”和“能连接生产主机”拆成两层授权

### 主机与网络

- 后端只允许连接白名单主机和白名单端口
- 如果可以，限制只允许 `22` 或少量固定 SSH 端口
- 建议把后端部署在受控网络，不让它自由访问任意内外网地址
- 对高风险环境建议通过堡垒机或跳板机统一接入

### 协议与鉴权

- 不建议长期把 JWT 放在 WebSocket query string
- 如果后续演进，建议改成更短生命周期 token 或专用 websocket token
- 对终端会话增加服务端 TTL、用户级并发限制和强制断开策略
- 对异常频繁连接、重复失败认证等行为做限流或告警

### SSH 主机真实性

- 不建议生产环境继续使用 `AutoAddPolicy()`
- 建议改成已知主机指纹校验
- 首次接入主机时应有明确的指纹确认流程
- 对关键资产建议只允许连接已登记主机

### 审计与留痕

- 至少记录连接人、连接时间、目标主机、断开时间、失败原因
- 对高风险环境建议记录命令审计或会话审计
- 日志中不要记录密码、token、完整敏感输出
- 排障日志建议做脱敏

### 部署与可用性

- 终端会话当前是进程内内存态，建议生产上使用单实例或黏性会话
- 如果走多实例负载均衡，必须保证同一 websocket 不会漂移到其他实例
- 为 WebSocket 和 SSH 会话分别设置合理的超时
- 服务重启策略要考虑正在进行中的终端会话会被中断

## 8.4 最低可接受生产基线

如果你现在就要把这个能力放进一个相对严肃的环境，最低建议至少做这 6 项：

1. 去掉前端明文密码保存
2. 限制只有管理员角色能访问终端页
3. 限制只允许连接白名单主机
4. 改掉 `AutoAddPolicy()`，启用主机指纹校验
5. 增加连接审计日志
6. 通过反向代理正确配置 WebSocket 超时和 Upgrade 头

## 8.5 不建议直接上线的现状项

以下现状如果不调整，不建议直接用于公网或核心生产环境：

- 浏览器本地保存明文 SSH 密码
- WebSocket URL 携带长期 JWT
- 自动接受未知 SSH 主机指纹
- 没有主机白名单
- 没有命令审计
- 没有更细粒度的 RBAC 限制

## 9. 反向代理 WebSocket 配置

终端页依赖长连接 WebSocket。

如果你的前端或后端前面有 Nginx、Ingress、Traefik、HAProxy 等反向代理，必须显式支持：

- `Upgrade`
- `Connection: upgrade`
- 较长的读写超时
- 不要把 WebSocket 当普通短 HTTP 请求处理

否则常见现象会是：

- 页面刚连上就断开
- 一段时间不操作后被代理切断
- 握手返回 400 / 426 / 502
- 前端只看到 `WebSocket 连接失败`

## 9.1 Nginx 示例

如果前端通过 Nginx 反代到后端 FastAPI，可参考下面的最小配置：

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name your-domain.example.com;

    location /api/v1/terminal/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_connect_timeout 60s;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

关键点：

- `proxy_http_version 1.1`
- `Upgrade` 头
- `Connection` 头
- `proxy_read_timeout` 不能太短

对于终端这种长时间交互链路，如果 `proxy_read_timeout` 只有几十秒，用户在空闲时很容易被代理直接切断。

## 9.2 常见代理注意事项

### Nginx

- 必须开启 `proxy_http_version 1.1`
- 必须设置 `Upgrade` 和 `Connection`
- 注意 `proxy_read_timeout`
- 如果前面还有 WAF/CDN，也要确认它们支持 WebSocket

### Kubernetes Ingress

- 需要确认你使用的 Ingress Controller 支持 WebSocket
- 常见 Nginx Ingress 通常默认支持，但仍要关注超时配置
- 若使用注解控制超时，需要显式拉长 read/send timeout

### Traefik / HAProxy

- 通常原生支持 WebSocket
- 重点仍然是长连接超时与转发头
- 要确认路由规则没有把 `/api/v1/terminal/ws` 当普通 HTTP 静态接口处理

## 9.3 反向代理排查要点

如果 WebSocket 看起来有问题，可以按以下顺序排查：

1. 浏览器开发者工具看握手请求是否到达 `/api/v1/terminal/ws`
2. 看响应码是否是 `101 Switching Protocols`
3. 如果不是 `101`，优先看反向代理日志
4. 如果是 `101` 但很快断开，优先看代理超时
5. 如果代理层正常，再看后端应用日志和 SSH 连接日志

## 9.4 生产环境代理建议

生产上建议把 `/api/v1/terminal/ws` 单独视为高敏感长连接接口，和普通 REST API 分开考虑：

- 单独的访问日志策略
- 单独的超时策略
- 单独的限流策略
- 单独的权限控制和监控指标
- 单独的告警阈值
## 10. 故障排查

## 10.1 页面没法连接

先检查：

- 是否已登录
- JWT 是否存在
- 后端服务是否正常
- 反向代理是否支持 WebSocket

## 10.2 WebSocket 已连接，但 SSH 建连失败

先检查：

- `host` 是否正确
- `port` 是否正确
- 用户名密码是否正确
- 后端机器是否能访问目标主机
- 后端环境是否安装 `paramiko`

典型排查命令：

```bash
cd backend
python -c "import paramiko; print(paramiko.__version__)"
nc -vz 10.17.154.252 22
```

如果 `nc` 不通，问题通常是网络或目标主机防火墙，而不是 WebSocket 协议。

### 常见失败示例 1：用户名或密码错误

前端通常会看到：

```json
{
  "type": "error",
  "message": "Authentication failed."
}
```

服务端含义：

- WebSocket 已成功
- JWT 已通过
- 后端已尝试 SSH 连接
- 但远端拒绝了账号认证

### 常见失败示例 2：目标主机不可达

前端通常会看到：

```json
{
  "type": "error",
  "message": "[Errno 60] Operation timed out"
}
```

或：

```json
{
  "type": "error",
  "message": "[Errno 61] Connection refused"
}
```

服务端含义：

- 前端到 DMLV4 正常
- DMLV4 到远程主机失败
- 需要检查目标 IP、端口、防火墙和网络连通性

### 常见失败示例 3：第一条消息不是 `connect`

如果前端协议实现错了，或者手工调试时先发了 `input`，后端会拒绝初始化：

```json
{
  "type": "error",
  "message": "first terminal message must be connect"
}
```

这表示协议层顺序错误，而不是 SSH 失败。

## 10.3 终端打开后没有输出

先检查：

- 远程 shell 是否已真正启动
- SSH channel 是否被远端策略限制
- 前端是否已收到 `session`
- 后端输出泵送协程是否仍在运行

## 10.4 页面切换时报 xterm viewport 异常

这类错误通常与前端生命周期有关，而不是 SSH 本身有问题。

当前实现已经通过延迟 `fit()` 和安全检查规避常见问题。

如果仍然出现，可以优先检查：

- 组件是否重复挂载/卸载
- `ResizeObserver` 是否在销毁后仍触发
- xterm 版本是否需要升级到新的包名体系

## 10.5 建议的联调顺序

开发联调时，不要一上来就盯着页面。建议按链路分层验证：

1. 先验证后端服务本身可访问

```bash
curl http://localhost:8000/health
```

2. 再验证后端机器能访问目标 SSH 主机

```bash
nc -vz <host> <port>
```

3. 再验证 Python 环境里已有 `paramiko`

```bash
cd backend
python -c "import paramiko; print(paramiko.__version__)"
```

4. 最后再打开前端页面做完整联调

这样能更快区分问题到底在：

- 前端页面
- WebSocket 握手
- 后端应用
- SSH 网络
- 远端认证

## 11. 后续演进建议

如果要继续扩展终端能力，建议按以下顺序推进：

1. 支持收藏常用主机
2. 增加连接历史
3. 增加私钥登录
4. 支持跳板机
5. 增加主机指纹管理
6. 增加后端审计和命令留痕
7. 增加更细粒度 RBAC

## 12. 相关文档

- [快速开始](/guide/getting-started)
- [认证与登录](/guide/authentication)
- [测试执行下发](/guide/test-execution)
- [后端架构](/architecture)
