# Scripts 目录说明

本目录包含 dmlv4 项目中常用的脚本工具，按功能分为以下几类：

---

## 初始化脚本

### `init_rbac.py` - RBAC 初始化
初始化系统权限(Permission)和角色(Role)。

**使用方法：**
```bash
# 默认执行，创建所有默认角色和权限
python scripts/init_rbac.py
```

**功能说明：**
- 创建 `Permission` 集合：所有业务权限（work_items、users、requirements、test_cases 等）
- 创建 `Role` 集合：ADMIN（全量权限）、TPM、REVIEWER、MANUAL_DEV、QA、TESTER、AUTO_DEV、AUTOMATION
- 幂等操作，可重复执行

---

### `seed_test_users.py` - 测试用户创建
一键创建多个测试账号，方便开发和演示使用。

**使用方法：**
```bash
# 创建所有测试用户（默认密码: Test@123）
python scripts/seed_test_users.py

# 覆盖已存在的用户
python scripts/seed_test_users.py --reset

# 自定义统一密码
python scripts/seed_test_users.py --password MyPass@456
```

**创建的测试用户：**

| user_id | username | roles   |
|---------|----------|---------|
| admin   | 管理员   | ADMIN   |
| tpm     | 项目经理 | TPM     |
| reviewer| 审核人   | REVIEWER|
| dev     | 开发人员 | MANUAL_DEV |
| qa      | 质量保证 | QA      |
| tester  | 测试人员 | TESTER  |

---

### `create_user.py` - 单个用户创建
创建单个 RBAC 用户账号。

**使用方法：**
```bash
# 基本用法
python scripts/create_user.py \
  --user-id admin \
  --username 管理员 \
  --password 'admin123' \
  --roles ADMIN \
  --email admin@example.com

# 覆盖已存在的用户
python scripts/create_user.py \
  --user-id admin \
  --username 新管理员 \
  --password 'newpass' \
  --roles ADMIN \
  --upsert

# 多角色分配
python scripts/create_user.py \
  --user-id developer \
  --username 测试开发 \
  --password 'dev123' \
  --roles MANUAL_DEV,TESTER
```

**参数说明：**
| 参数 | 必填 | 说明 |
|------|------|------|
| `--user-id` | 是 | 用户唯一 ID |
| `--username` | 是 | 用户显示名 |
| `--password` | 是 | 登录密码（明文，脚本内加密） |
| `--roles` | 否 | 角色列表，逗号分隔 |
| `--email` | 否 | 邮箱 |
| `--status` | 否 | 用户状态（ACTIVE/DISABLED） |
| `--upsert` | 否 | 若用户存在则更新 |

---

## Token 相关

### `create_token.py` - 生成 JWT Token
为指定用户生成访问令牌。

**使用方法：**
```bash
# 基本用法（默认 8 小时有效期）
python scripts/create_token.py --user-id admin

# 自定义有效期（2 小时）
python scripts/create_token.py --user-id admin --expire-minutes 120

# 保存到文件
python scripts/create_token.py --user-id admin --save-to-file /tmp/token.txt

# 打印 token payload 内容
python scripts/create_token.py --user-id admin --print-payload
```

**参数说明：**
| 参数 | 必填 | 说明 |
|------|------|------|
| `--user-id` | 是 | 用户 ID（会校验用户存在且状态为 ACTIVE） |
| `--expire-minutes` | 否 | Token 有效期分钟数（默认 480，即 8 小时） |
| `--save-to-file` | 否 | 将 token 保存到指定文件 |
| `--print-payload` | 否 | 打印 JWT payload 内容 |

---

## 测试数据生成

### `generate_mock_test_cases.py` - 生成模拟测试用例
通过 API 批量创建测试用例，用于演示或测试数据准备。

**使用方法：**
```bash
# 默认参数创建全部模板用例
python scripts/generate_mock_test_cases.py

# 只创建 5 条
python scripts/generate_mock_test_cases.py --count 5

# 指定后端地址
python scripts/generate_mock_test_cases.py --url http://10.17.154.252:8000

# 指定登录用户
python scripts/generate_mock_test_cases.py --user admin --password 'Admin@123'

# 免 token 模式（需后端开启 dev_bypass_auth）
python scripts/generate_mock_test_cases.py --no-auth

# 关联到指定需求
python scripts/generate_mock_test_cases.py --req-id TR-2026-00001

# 预览模式（不实际创建）
python scripts/generate_mock_test_cases.py --dry-run
```

**参数说明：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--url` | http://localhost:8000 | 后端 API 地址 |
| `--user` | test_admin | 登录用户 ID |
| `--password` | Admin@123 | 登录密码 |
| `--count` | 全部 | 创建条数 |
| `--req-id` | 第一个需求 | 关联的需求 ID |
| `--dry-run` | False | 只预览不创建 |
| `--no-auth` | False | 免 token 模式 |

---

## 代理相关

### `register_agent.py` - 注册执行代理
将测试执行代理注册到平台。

**使用方法：**
```bash
# 默认注册（自动检测本机信息）
python scripts/register_agent.py

# 指定平台地址
export AGENT_PLATFORM_URL=http://10.17.154.252:8000
python scripts/register_agent.py

# 指定代理端口（自动拼接 base_url）
export AGENT_PORT=19091
python scripts/register_agent.py

# 指定区域
export AGENT_REGION=beijing
python scripts/register_agent.py
```

**环境变量：**
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_PLATFORM_URL` | http://127.0.0.1:8000 | 平台地址 |
| `AGENT_PORT` | 无 | 代理服务端口 |
| `AGENT_REGION` | default | 代理区域 |

---

### `mock_rabbitmq_consumer.py` - RabbitMQ 消费模拟
消费 RabbitMQ 任务队列中的消息，模拟执行后回写结果到 Kafka。

**使用方法：**
```bash
# 启动消费（自动从 config.yaml 读取配置）
python scripts/mock_rabbitmq_consumer.py
```

**功能说明：**
- 从 RabbitMQ 消费任务消息
- 模拟执行测试用例
- 向 Kafka 发送测试事件和执行结果
- 向平台发送代理心跳

---

## 维护脚本

### `remove_test_specs_status_projection.py` - 清理废弃字段
移除 test_specs 集合中遗留的 status 字段和索引。

**使用方法：**
```bash
# 只查看不修改（预览模式）
python scripts/remove_test_specs_status_projection.py

# 确认后执行清理
python scripts/remove_test_specs_status_projection.py --apply
```

**参数说明：**
| 参数 | 说明 |
|------|------|
| `--apply` | 执行清理操作，不带此参数只预览 |

---

## 快速开始

首次部署时按以下顺序执行：

```bash
# 1. 初始化 RBAC（角色和权限）
python scripts/init_rbac.py

# 2. 创建管理员账号
python scripts/create_user.py \
  --user-id admin \
  --username 管理员 \
  --password 'Admin@123' \
  --roles ADMIN

# 3. 生成管理员 token
python scripts/create_token.py --user-id admin --save-to-file /tmp/admin_token.txt

# 4. 或者使用一键脚本创建测试用户（方便演示）
python scripts/seed_test_users.py
```

后续开发调试可直接使用 `seed_test_users.py` 快速创建多个测试账号。