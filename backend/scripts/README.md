# Backend Scripts 索引

## 脚本列表

### 1. 初始化脚本

#### `init_rbac.py`
- **用途**: 初始化 RBAC 权限与角色
- **功能**: 创建默认权限和角色（ADMIN、TPM、TESTER、AUTOMATION）
- **用法**:
  ```bash
  python scripts/init_rbac.py
  ```
- **输出**: 在数据库中创建 permissions 和 roles 集合

#### `seed_test_data.py` ⭐
- **用途**: 创建模拟测试数据
- **功能**: 生成测试需求和测试用例数据
- **用法**:
  ```bash
  python scripts/seed_test_data.py
  ```
- **输出**: 在数据库中创建 6 个需求和 6 个用例
- **特点**: 幂等操作，可重复执行

#### `verify_test_data.py` ⭐
- **用途**: 验证测试数据
- **功能**: 查看已创建的测试需求和用例详情
- **用法**:
  ```bash
  python scripts/verify_test_data.py
  ```
- **输出**: 详细的数据统计和内容展示

### 2. 用户管理脚本

#### `create_user.py`
- **用途**: 创建用户账号
- **功能**: 创建具有指定角色的用户
- **用法**:
  ```bash
  python scripts/create_user.py \
    --user-id admin001 \
    --username 系统管理员 \
    --password 'Admin@123' \
    --roles ADMIN \
    --email admin@example.com
  ```
- **参数**:
  - `--user-id`: 用户唯一ID
  - `--username`: 用户名
  - `--password`: 密码
  - `--roles`: 角色列表（逗号分隔）
  - `--email`: 邮箱（可选）
  - `--upsert`: 是否覆盖更新

---

## 使用流程

### 首次部署
```bash
# 1. 初始化 RBAC
python scripts/init_rbac.py

# 2. 创建用户
python scripts/create_user.py --user-id admin001 --username 管理员 --password 'Admin@123' --roles ADMIN
python scripts/create_user.py --user-id tpm001 --username TPM --password 'TPM@123' --roles TPM
python scripts/create_user.py --user-id tester001 --username 测试工程师 --password 'Test@123' --roles TESTER
python scripts/create_user.py --user-id auto001 --username 自动化工程师 --password 'Auto@123' --roles AUTOMATION

# 3. 创建测试数据
python scripts/seed_test_data.py

# 4. 验证数据
python scripts/verify_test_data.py
```

### 日常维护
```bash
# 重新生成测试数据（幂等）
python scripts/seed_test_data.py

# 查看数据状态
python scripts/verify_test_data.py
```

---

## 脚本特性

### 幂等性
- ✅ `seed_test_data.py`: 支持重复执行，自动更新现有数据
- ✅ `init_rbac.py`: 支持重复执行，幂等创建
- ⚠️ `create_user.py`: 默认不允许重复创建，需加 `--upsert` 覆盖

### 依赖关系
```
init_rbac.py (必须先执行)
    ↓
create_user.py (需要 RBAC 已初始化)
    ↓
seed_test_data.py (需要用户已创建)
    ↓
verify_test_data.py (可选，随时执行)
```

### 数据库集合
- **permissions**: 权限定义
- **roles**: 角色定义
- **users**: 用户信息
- **test_requirements**: 测试需求
- **test_cases**: 测试用例

---

## 故障排除

### 问题 1: 导入错误
**错误**: `ImportError: cannot import name '...'`
**解决**: 确保在 `backend` 目录下运行脚本

### 问题 2: 数据库连接失败
**错误**: `pymongo.errors.ServerSelectionTimeoutError`
**解决**: 检查 MongoDB 服务是否启动，连接地址是否正确

### 问题 3: 用户已存在
**错误**: `RuntimeError: 用户已存在`
**解决**: 加 `--upsert` 参数覆盖，或删除现有用户

### 问题 4: 角色不存在
**错误**: `RuntimeError: 角色不存在，无法创建用户`
**解决**: 先运行 `init_rbac.py` 初始化角色

---

## 脚本源码位置

所有脚本位于：
```
/Users/libiao/Desktop/github/dmlv4/backend/scripts/
```

详细文档参考：
- [模拟数据说明](../../模拟测试数据说明.md)
- [用户账号说明](../../测试用户账号.md)
- [项目架构规范](../../docs/项目架构规范.md)