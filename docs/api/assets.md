# 资产管理 API

## 概述

资产管理模块提供硬件部件库和DUT（Device Under Test）设备的管理功能，支持部件信息维护、设备资产跟踪和测试计划关联。

**基础路径**: `/api/v1/assets`

## 注意事项

- 所有接口需要 `assets:read` 或 `assets:write` 权限
- 使用JWT Token进行身份认证

## 部件库管理

### 数据模型

```typescript
interface ComponentLibraryDoc {
  part_number: string;         // 部件型号（主键）
  name: string;               // 部件名称
  description: string;        // 部件描述
  category: string;           // 部件类别
  subcategory: string;        // 部件子类别
  vendor: string;             // 厂商
  model: string;              // 型号
  specifications: object;     // 技术规格
  lifecycle_status: string;   // 生命周期状态
  support_level: string;      // 支持等级
  compatibility_notes: string; // 兼容性说明
  created_at: string;         // 创建时间
  updated_at: string;         // 更新时间
  created_by: string;         // 创建人
  updated_by: string;         // 更新人
  is_deleted: boolean;        // 是否删除
}
```

### 创建部件字典项

创建一个新的硬件部件。

```http
POST /api/v1/assets/components
```

**权限要求**: `assets:write`

**请求体**:
```json
{
  "part_number": "DDR5-16GB-3200",
  "name": "DDR5 16GB 3200MHz 内存条",
  "description": "三星DDR5内存条，容量16GB，频率3200MHz",
  "category": "Memory",
  "subcategory": "DDR5",
  "vendor": "Samsung",
  "model": "M323R2GA3BB0-CWM",
  "specifications": {
    "capacity": "16GB",
    "speed": "3200MHz",
    "voltage": "1.1V",
    "timing": "22-22-22-52",
    "form_factor": "DIMM"
  },
  "lifecycle_status": "ACTIVE",
  "support_level": "Standard",
  "compatibility_notes": "兼容Intel 12代及以上处理器"
}
```

**字段说明**:
- `part_number` (string, required): 部件型号，全局唯一
- `name` (string, required): 部件名称
- `description` (string, required): 部件描述
- `category` (string, required): 部件类别
- `subcategory` (string, required): 部件子类别
- `vendor` (string, required): 厂商
- `model` (string, required): 型号
- `specifications` (object, required): 技术规格，JSON格式
- `lifecycle_status` (string, optional): 生命周期状态，默认ACTIVE
- `support_level` (string, optional): 支持等级
- `compatibility_notes` (string, optional): 兼容性说明

**响应示例**:
```json
{
  "code": 201,
  "message": "Success",
  "data": {
    "part_number": "DDR5-16GB-3200",
    "name": "DDR5 16GB 3200MHz 内存条",
    "category": "Memory",
    "vendor": "Samsung",
    "lifecycle_status": "ACTIVE",
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z",
    "created_by": "current_user_id",
    "updated_by": "current_user_id",
    "is_deleted": false
  }
}
```

### 获取部件详情

根据部件型号查询部件详细信息。

```http
GET /api/v1/assets/components/{part_number}
```

**权限要求**: `assets:read`

**路径参数**:
- `part_number` (string, required): 部件型号

### 查询部件列表

分页查询部件列表，支持多种筛选条件。

```http
GET /api/v1/assets/components
```

**权限要求**: `assets:read`

**查询参数**:
- `category` (string, optional): 按部件类别筛选
- `subcategory` (string, optional): 按部件子类别筛选
- `vendor` (string, optional): 按厂商筛选
- `model` (string, optional): 按型号筛选
- `lifecycle_status` (string, optional): 按生命周期状态筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

**生命周期状态值**:
- ACTIVE, EOL, NRND (Not Recommended for New Designs), OBSOLETE

### 更新部件信息

更新部件的基本信息和技术规格。

```http
PUT /api/v1/assets/components/{part_number}
```

**权限要求**: `assets:write`

**路径参数**:
- `part_number` (string, required): 部件型号

### 删除部件

删除部件（逻辑删除）。

```http
DELETE /api/v1/assets/components/{part_number}
```

**权限要求**: `assets:write`

**路径参数**:
- `part_number` (string, required): 部件型号

## DUT设备管理

### 数据模型

```typescript
interface DutDoc {
  asset_id: string;            // 资产ID（主键）
  device_name: string;         // 设备名称
  device_type: string;         // 设备类型
  model: string;               // 设备型号
  serial_number: string;       // 序列号
  mac_address: string;         // MAC地址
  ip_address: string;          // IP地址
  location: string;            // 物理位置
  rack_location: string;       // 机架位置
  owner_team: string;          // 负责团队
  status: string;              // 设备状态
  health_status: string;       // 健康状态
  last_maintenance: string;    // 最后维护时间
  next_maintenance: string;    // 下次维护时间
  specifications: object;      // 设备规格
  installed_components: string[]; // 已安装部件
  test_capabilities: string[]; // 测试能力
  availability_schedule: object; // 可用时间表
  created_at: string;          // 创建时间
  updated_at: string;          // 更新时间
  created_by: string;          // 创建人
  updated_by: string;          // 更新人
  is_deleted: boolean;         // 是否删除
}
```

### 创建设备资产

创建一个新的DUT设备资产。

```http
POST /api/v1/assets/duts
```

**权限要求**: `assets:write`

**请求体**:
```json
{
  "device_name": "DDR5_Test_Platform_01",
  "device_type": "Test_Platform",
  "model": "TPM-2024-X1",
  "serial_number": "SN-TPM-2024-001",
  "mac_address": "00:1B:44:11:3A:B7",
  "ip_address": "192.168.1.100",
  "location": "Test_Lab_A",
  "rack_location": "Rack-A-Unit-15",
  "owner_team": "Hardware_Test_Team",
  "status": "AVAILABLE",
  "health_status": "HEALTHY",
  "specifications": {
    "cpu": "Intel Core i9-13900K",
    "memory_slots": 4,
    "max_memory": "128GB",
    "pcie_slots": 7,
    "usb_ports": 8,
    "network_ports": 2
  },
  "installed_components": ["DDR5-16GB-3200", "DDR5-32GB-4800"],
  "test_capabilities": ["Memory_Test", "Compatibility_Test", "Performance_Test"],
  "availability_schedule": {
    "weekdays": "09:00-18:00",
    "weekends": "10:00-16:00",
    "timezone": "UTC+8"
  }
}
```

**字段说明**:
- `device_name` (string, required): 设备名称
- `device_type` (string, required): 设备类型
- `model` (string, required): 设备型号
- `serial_number` (string, required): 序列号，全局唯一
- `mac_address` (string, required): MAC地址
- `ip_address` (string, required): IP地址
- `location` (string, required): 物理位置
- `rack_location` (string, optional): 机架位置
- `owner_team` (string, required): 负责团队
- `status` (string, optional): 设备状态，默认AVAILABLE
- `health_status` (string, optional): 健康状态，默认HEALTHY
- `specifications` (object, required): 设备规格
- `installed_components` (string[], optional): 已安装部件列表
- `test_capabilities` (string[], optional): 测试能力列表
- `availability_schedule` (object, optional): 可用时间表

**响应示例**:
```json
{
  "code": 201,
  "message": "Success",
  "data": {
    "asset_id": "DUT-20260303-001",
    "device_name": "DDR5_Test_Platform_01",
    "device_type": "Test_Platform",
    "status": "AVAILABLE",
    "health_status": "HEALTHY",
    "owner_team": "Hardware_Test_Team",
    "created_at": "2026-03-03T11:42:00Z",
    "updated_at": "2026-03-03T11:42:00Z",
    "created_by": "current_user_id",
    "updated_by": "current_user_id",
    "is_deleted": false
  }
}
```

### 获取设备资产详情

根据资产ID查询设备详细信息。

```http
GET /api/v1/assets/duts/{asset_id}
```

**权限要求**: `assets:read`

**路径参数**:
- `asset_id` (string, required): 设备资产ID

### 查询设备资产列表

分页查询设备资产列表，支持多种筛选条件。

```http
GET /api/v1/assets/duts
```

**权限要求**: `assets:read`

**查询参数**:
- `status` (string, optional): 按设备状态筛选
- `owner_team` (string, optional): 按负责团队筛选
- `rack_location` (string, optional): 按机架位置筛选
- `health_status` (string, optional): 按健康状态筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认20)
- `offset` (integer, optional): 分页偏移 (默认0)

**设备状态值**:
- AVAILABLE, IN_USE, MAINTENANCE, OUT_OF_SERVICE, RETIRED

**健康状态值**:
- HEALTHY, WARNING, CRITICAL, UNKNOWN

### 更新设备资产

更新设备的基本信息和状态。

```http
PUT /api/v1/assets/duts/{asset_id}
```

**权限要求**: `assets:write`

**路径参数**:
- `asset_id` (string, required): 设备资产ID

### 删除设备资产

删除设备资产（逻辑删除）。

```http
DELETE /api/v1/assets/duts/{asset_id}
```

**权限要求**: `assets:write`

**路径参数**:
- `asset_id` (string, required): 设备资产ID

## 测试计划关联部件

### 数据模型

```typescript
interface TestPlanComponentDoc {
  id: string;                  // 记录ID
  plan_id: string;             // 测试计划ID
  part_number: string;         // 部件型号
  quantity: number;            // 数量
  priority: string;            // 优先级
  notes: string;               // 备注
  created_at: string;          // 创建时间
  updated_at: string;          // 更新时间
  is_deleted: boolean;         // 是否删除
}
```

### 创建测试计划关联部件

将部件添加到测试计划中。

```http
POST /api/v1/assets/plan-components
```

**权限要求**: `assets:write`

**请求体**:
```json
{
  "plan_id": "TEST-PLAN-20260303-001",
  "part_number": "DDR5-16GB-3200",
  "quantity": 5,
  "priority": "HIGH",
  "notes": "主要用于兼容性测试"
}
```

**字段说明**:
- `plan_id` (string, required): 测试计划ID
- `part_number` (string, required): 部件型号
- `quantity` (integer, required): 所需数量
- `priority` (string, optional): 优先级，默认MEDIUM
- `notes` (string, optional): 备注信息

### 查询测试计划关联部件

查询测试计划下的部件列表。

```http
GET /api/v1/assets/plan-components
```

**权限要求**: `assets:read`

**查询参数**:
- `plan_id` (string, optional): 按测试计划筛选
- `part_number` (string, optional): 按部件型号筛选
- `limit` (integer, optional): 返回数量限制 (1-200, 默认50)
- `offset` (integer, optional): 分页偏移 (默认0)

### 删除测试计划关联部件

从测试计划中移除部件关联。

```http
DELETE /api/v1/assets/plan-components?plan_id={plan_id}&part_number={part_number}
```

**权限要求**: `assets:write`

**查询参数**:
- `plan_id` (string, required): 测试计划ID
- `part_number` (string, required): 部件型号

## 枚举值参考

### 部件类别
| 类别 | 说明 |
|------|------|
| Memory | 内存 |
| CPU | 处理器 |
| Motherboard | 主板 |
| Storage | 存储 |
| Graphics_Card | 显卡 |
| Network_Card | 网卡 |
| Power_Supply | 电源 |
| Cooling | 散热 |

### 设备类型
| 类型 | 说明 |
|------|------|
| Test_Platform | 测试平台 |
| DUT | 被测设备 |
| Measurement_Equipment | 测量设备 |
| Environmental_Chamber | 环境舱 |

### 生命周期状态
| 状态 | 说明 |
|------|------|
| ACTIVE | 活跃 |
| EOL | 停产 |
| NRND | 不建议新设计 |
| OBSOLETE | 已废弃 |

## 使用示例

### 部件管理

```bash
# 1. 创建部件
curl -X POST "http://localhost:8000/api/v1/assets/components" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "part_number": "DDR5-32GB-4800",
    "name": "DDR5 32GB 4800MHz 内存条",
    "category": "Memory",
    "vendor": "Kingston",
    "specifications": {
      "capacity": "32GB",
      "speed": "4800MHz"
    }
  }'

# 2. 查询部件列表
curl -X GET "http://localhost:8000/api/v1/assets/components?category=Memory&vendor=Kingston" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 获取部件详情
curl -X GET "http://localhost:8000/api/v1/assets/components/DDR5-32GB-4800" \
  -H "Authorization: Bearer your_jwt_token"
```

### 设备管理

```bash
# 1. 创建设备
curl -X POST "http://localhost:8000/api/v1/assets/duts" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "device_name": "Memory_Test_Platform_02",
    "device_type": "Test_Platform",
    "serial_number": "SN-2024-002",
    "owner_team": "Test_Team_A",
    "specifications": {
      "cpu": "AMD Ryzen 9 7950X",
      "memory_slots": 4
    }
  }'

# 2. 查询设备列表
curl -X GET "http://localhost:8000/api/v1/assets/duts?status=AVAILABLE&owner_team=Test_Team_A" \
  -H "Authorization: Bearer your_jwt_token"

# 3. 更新设备状态
curl -X PUT "http://localhost:8000/api/v1/assets/duts/DUT-20260303-001" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_USE",
    "health_status": "WARNING"
  }'
```

### 测试计划关联

```bash
# 1. 添加部件到测试计划
curl -X POST "http://localhost:8000/api/v1/assets/plan-components" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "TEST-PLAN-DDR5-001",
    "part_number": "DDR5-16GB-3200",
    "quantity": 3,
    "priority": "HIGH"
  }'

# 2. 查询计划部件
curl -X GET "http://localhost:8000/api/v1/assets/plan-components?plan_id=TEST-PLAN-DDR5-001" \
  -H "Authorization: Bearer your_jwt_token"
```

## 最佳实践

### 部件管理
1. 使用有意义的部件型号命名规范
2. 详细填写技术规格信息
3. 及时更新生命周期状态
4. 记录兼容性信息

### 设备管理
1. 保持设备信息实时更新
2. 定期检查设备健康状态
3. 合理安排维护计划
4. 跟踪设备使用情况

### 关联管理
1. 合理规划测试计划部件需求
2. 及时更新部件数量需求
3. 维护部件与测试计划的关联关系

### 安全考虑
1. 敏感设备信息访问控制
2. 设备操作日志记录
3. 定期备份资产数据