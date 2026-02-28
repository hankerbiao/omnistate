# 登录 API 快速使用指南

## 🎯 快速开始

### 1. 启动后端服务

```bash
# 进入后端目录
cd backend

# 启动服务（默认端口 8000）
python -m app.main

# 或者使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

验证后端是否启动：
```bash
curl http://localhost:8000/health
```

### 2. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖（如果还没安装）
npm install

# 启动开发服务器
npm run dev
```

浏览器访问：http://localhost:3000

### 3. 测试登录

#### 方式一：手动登录

1. 在用户ID输入框输入：`admin`
2. 在密码输入框输入：`123456`
3. 点击「立即登录」按钮
4. 验证登录成功并跳转到主页

#### 方式二：快速登录

点击快速登录按钮（如「管理员」），表单会自动填充并登录。

#### 方式三：浏览器控制台测试

1. 打开浏览器开发者工具 (F12)
2. 切换到 Console 标签
3. 粘贴运行 `test-login.js` 文件中的内容
4. 查看测试结果

## 📝 实现的核心功能

### ✅ 已完成的登录功能

1. **真实后端登录**
   - POST `/auth/login` 接口调用
   - JWT 令牌获取和存储
   - 用户信息返回

2. **令牌自动管理**
   - 自动添加到所有 API 请求
   - `Authorization: Bearer ${token}` 头
   - 登录/登出时自动更新

3. **登录状态持久化**
   - 记住登录：存储到 `localStorage`
   - 会话登录：存储到 `sessionStorage`
   - 页面刷新后自动恢复

4. **错误处理**
   - 网络错误提示
   - 认证失败提示
   - 自动降级到模拟数据

### 🔄 数据流向

```
用户输入 → 前端验证 → 后端认证 → JWT 生成 → 令牌存储 → 状态更新
    ↓           ↓         ↓         ↓         ↓         ↓
 user_id   前端表单   验证密码   access_token  本地存储   登录成功
 password   检查
```

## 📚 重要文件说明

### 后端文件

| 文件 | 说明 |
|------|------|
| `backend/app/modules/auth/api/routes.py` | 登录接口定义 |
| `backend/app/modules/auth/service/rbac_service.py` | 认证服务逻辑 |
| `backend/app/modules/auth/schemas/rbac.py` | 请求/响应模型 |
| `backend/app/shared/auth/jwt_auth.py` | JWT 工具 |

### 前端文件

| 文件 | 说明 |
|------|------|
| `frontend/src/services/api/TestDesignerApi.ts` | 所有 API 方法 |
| `frontend/src/services/api/ApiClient.ts` | HTTP 客户端 |
| `frontend/src/services/api/index.ts` | 令牌管理 |
| `frontend/src/App.tsx` | 登录逻辑 |
| `frontend/.env` | 环境变量配置 |

## 🔧 配置说明

### 环境变量 (`.env`)

```bash
# 必须配置：后端 API 地址
VITE_BACKEND_API_BASE_URL=http://localhost:8000

# 可选配置：API 超时时间（毫秒）
VITE_API_TIMEOUT_MS=15000
```

### 更改配置

如果后端在其他端口或地址，修改 `frontend/.env`：

```bash
# 生产环境示例
VITE_BACKEND_API_BASE_URL=https://api.yourdomain.com

# 其他端口示例
VITE_BACKEND_API_BASE_URL=http://localhost:3001
```

## 🧪 测试账户

### 默认测试账户

| user_id | password | username | 角色 |
|---------|----------|----------|------|
| `admin` | `123456` | 管理员 | ADMIN |
| `alice` | `123456` | Alice | ROLE_TPM |
| `bob` | `123456` | Bob | ROLE_ENGINEER |

### 创建新用户

如果需要创建新用户，可以通过后端 API：

```bash
curl -X POST http://localhost:8000/api/v1/auth/users \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "username": "测试用户",
    "password": "123456",
    "email": "test@example.com",
    "role_ids": ["ROLE_TESTER"]
  }'
```

## 🚨 常见问题

### Q: 登录一直失败？

**A**: 检查以下几点：
1. 后端服务是否启动：`curl http://localhost:8000/health`
2. `.env` 文件中的 `VITE_BACKEND_API_BASE_URL` 是否正确
3. 浏览器控制台是否有错误信息
4. 测试账户是否存在

### Q: 如何查看网络请求？

**A**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签
3. 执行登录操作
4. 查看 `auth/login` 请求的请求和响应

### Q: 如何调试登录问题？

**A**:
1. 查看浏览器控制台错误信息
2. 检查后端日志
3. 手动测试 API：`curl -X POST http://localhost:8000/api/v1/auth/login`
4. 运行 `test-login.js` 脚本测试

### Q: 如何切换到生产环境？

**A**: 修改 `frontend/.env`：

```bash
VITE_BACKEND_API_BASE_URL=https://your-production-api.com
```

然后重新构建前端：
```bash
npm run build
```

## 🔐 安全注意事项

### ⚠️ 开发环境

- ✅ 可以使用 HTTP
- ✅ 密码可以简单（如 `123456`）
- ✅ 使用 `localStorage` 记住登录

### ⚠️ 生产环境

- ❌ **必须使用 HTTPS**
- ❌ 密码必须复杂
- ❌ 使用 `sessionStorage`（关闭浏览器后清除）
- ❌ 启用 CORS 白名单
- ❌ 配置 JWT 密钥

## 📖 API 文档

### 登录接口

**请求**:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "user_id": "admin",
  "password": "123456"
}
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGci...",
    "token_type": "Bearer",
    "user": {
      "user_id": "admin",
      "username": "管理员",
      "status": "ACTIVE"
    }
  }
}
```

### 获取当前用户

**请求**:
```http
GET /api/v1/auth/users/me
Authorization: Bearer eyJhbGci...
```

**响应**:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "admin",
    "username": "管理员",
    "status": "ACTIVE"
  }
}
```

## 🎉 成功标志

当你看到以下现象时，说明登录 API 工作正常：

1. ✅ 输入正确凭据后登录成功
2. ✅ 页面跳转到主页
3. ✅ Network 面板显示 `POST /auth/login` 返回 200 状态码
4. ✅ 后续 API 请求自动添加 `Authorization` 头
5. ✅ 刷新页面后自动恢复登录状态

## 📞 获取帮助

如果遇到问题：

1. 查看文档：
   - `docs/登录API实现完成说明.md`
   - `docs/前端API集成状态检查报告.md`

2. 检查日志：
   - 浏览器控制台
   - 后端服务日志

3. 运行测试：
   - 浏览器控制台执行 `test-login.js`

---

**祝您使用愉快！** 🎉