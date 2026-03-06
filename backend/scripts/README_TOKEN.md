# Token 生成脚本使用说明

本目录提供了两个用于生成 JWT Token 的脚本，适用于不同的使用场景。

## 📦 脚本列表

### 1. `create_token.py` - 完整版（推荐）

**功能**：完整的 token 生成脚本，会验证用户存在性和状态。

**特点**：
- ✅ 验证用户是否存在于数据库中
- ✅ 检查用户状态是否为 ACTIVE
- ✅ 自动初始化默认权限（当用户角色为 ADMIN 时）
- ✅ 生成包含完整用户信息的 JWT Token

**使用场景**：
- 生产环境
- 需要严格验证用户身份的场景
- 管理员创建用户 token

**示例**：
```bash
# 基本使用
python scripts/create_token.py --user-id admin

# 自定义过期时间（2小时）
python scripts/create_token.py --user-id admin --expire-minutes 120

# 保存到文件并打印 payload
python scripts/create_token.py --user-id admin \
  --expire-minutes 480 \
  --save-to-file /tmp/token.txt \
  --print-payload
```

**输出示例**：
```
✓ 用户校验通过: admin (管理员)

正在生成 token...
  用户ID: admin
  有效期: 480 分钟

================================================================================
Token 生成成功:
================================================================================
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImlhdCI6MTY5...
================================================================================
```

### 2. `create_token_simple.py` - 简化版

**功能**：轻量级 token 生成脚本，无需数据库连接。

**特点**：
- ⚡ 无需连接 MongoDB
- ⚡ 快速生成 token
- ⚡ 支持自定义密钥
- ⚡ 适用于自动化场景

**使用场景**：
- CI/CD 流水线
- 自动化测试
- 临时 token 生成
- 开发调试

**示例**：
```bash
# 基本使用
python scripts/create_token_simple.py --user-id test_user

# 自定义过期时间（24小时）
python scripts/create_token_simple.py --user-id test_user --expire-minutes 1440

# 使用自定义密钥
python scripts/create_token_simple.py \
  --user-id test_user \
  --secret-key "my-secret-key" \
  --save-to-file token.json \
  --print-payload
```

**输出示例**：
```
✓ 使用配置密钥: CHANGE_ME_...
正在生成 token...
  用户ID: test_user
  有效期: 480 分钟

================================================================================
JWT Token 生成成功
================================================================================
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJpYXQi...
================================================================================
```

## 🔑 认证头格式

生成的 token 可用于 API 请求的 Authorization 头：

```bash
# curl 示例
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/tasks

# JavaScript 示例
fetch('/api/v1/tasks', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

## 📋 参数说明

| 参数 | 说明 | 适用脚本 | 必需 |
|------|------|----------|------|
| `--user-id` | 用户唯一 ID | 全部 | ✅ |
| `--expire-minutes` | Token 有效期（分钟） | 全部 | ❌ (默认480) |
| `--save-to-file` | 保存 token 到文件 | 全部 | ❌ |
| `--print-payload` | 打印 payload 内容 | 全部 | ❌ |
| `--secret-key` | 自定义 JWT 密钥 | 简化版 | ❌ |
| `--upsert` | 覆盖已存在用户 | 完整版 | ❌ |
| `--roles` | 用户角色 | 完整版 | ❌ |

## ⚠️ 注意事项

1. **密钥安全**：
   - 生产环境请使用强密钥（建议 32+ 位随机字符串）
   - 不要在命令行中明文传递密钥
   - 可以通过 `.env` 文件配置 `JWT_SECRET_KEY`

2. **Token 过期**：
   - 默认有效期为 8 小时（480 分钟）
   - 过期后需要重新生成 token
   - 可根据需要调整过期时间

3. **用户验证**（完整版）：
   - 确保用户在数据库中存在
   - 确保用户状态为 ACTIVE
   - 如需覆盖已存在用户，使用 `--upsert` 参数

4. **文件权限**：
   - 保存 token 到文件时，注意文件权限设置
   - 避免 token 文件被未授权访问

## 🔧 环境变量配置

可以在 `.env` 文件中配置以下变量：

```bash
# .env
JWT_SECRET_KEY=your-super-secret-key-here
JWT_EXPIRE_MINUTES=480
JWT_ISSUER=tcm-backend
JWT_AUDIENCE=tcm-frontend
```

## 🎯 使用建议

- **开发调试**：使用简化版 `create_token_simple.py`
- **生产环境**：使用完整版 `create_token.py`
- **CI/CD**：使用简化版，无需数据库依赖
- **批量生成**：结合脚本和配置文件使用

## 🐛 常见问题

**Q: 提示 "用户不存在" 怎么办？**
A: 使用 `create_user.py` 先创建用户，或使用简化版脚本。

**Q: Token 验证失败？**
A: 检查 JWT_SECRET_KEY 是否一致，确保前后端使用相同的密钥。

**Q: 如何批量生成 token？**
A: 可以编写循环脚本调用生成接口，或使用 shell 脚本批量执行。

**Q: Token 过期了怎么办？**
A: 重新运行脚本生成新的 token，或延长过期时间。

---

更多问题请参考项目文档或联系管理员。