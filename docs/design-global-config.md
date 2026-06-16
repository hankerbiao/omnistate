# 全局配置系统设计文档

> **注意**: 本文档为早期设计稿，包含 SQL schema 描述。实际实现使用 MongoDB + Beanie ODM，
> 文档模型见 `app/modules/system_config/repository/models/__init__.py`。
> 设计思路已落地，具体实现以代码为准。

## 1. 系统概述

### 1.1 目标
设计一个全局配置管理系统，支持动态配置LLM服务、系统参数等，无需修改代码即可切换AI分析引擎。

### 1.2 核心功能
- LLM服务配置（Ollama/OpenAI/自定义）
- 配置热加载（无需重启服务）
- 配置验证（测试连接）
- 配置历史记录

---

## 2. 数据库设计

### 2.1 配置表 (system_configs)

```sql
CREATE TABLE system_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    config_type VARCHAR(50) NOT NULL DEFAULT 'string',
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    description TEXT,
    is_encrypted BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    INDEX idx_category (category),
    INDEX idx_active (is_active)
);
```

### 2.2 配置历史表 (system_config_history)

```sql
CREATE TABLE system_config_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(50),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remark TEXT
);
```

### 2.3 预置配置项

```sql
-- LLM配置
INSERT INTO system_configs (config_key, config_value, config_type, category, description) VALUES
('ai.base_url', 'http://localhost:11434/v1', 'string', 'ai', 'LLM API基础URL'),
('ai.model', 'qwen2.5:latest', 'string', 'ai', 'LLM模型名称'),
('ai.api_key', '', 'string', 'ai', 'API密钥（如需要）', 1),
('ai.enabled', 'true', 'boolean', 'ai', '是否启用AI分析'),
('ai.temperature', '0.7', 'float', 'ai', '生成温度参数'),
('ai.max_tokens', '4096', 'integer', 'ai', '最大生成token数'),
('ai.timeout', '60', 'integer', 'ai', '请求超时时间(秒)');

-- 系统配置
INSERT INTO system_configs (config_key, config_value, config_type, category, description) VALUES
('system.site_name', 'DML测试平台', 'string', 'system', '站点名称'),
('system.max_upload_size', '10485760', 'integer', 'system', '最大上传文件大小(字节)'),
('system.allowed_file_types', '.pdf,.txt,.json', 'string', 'system', '允许上传的文件类型');
```

---

## 3. 后端设计

### 3.1 模块结构

```
backend/app/modules/system_config/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── routes.py              # API路由
├── models/
│   ├── __init__.py
│   └── config.py              # 数据库模型
├── schemas/
│   ├── __init__.py
│   └── config.py              # Pydantic Schema
└── services/
    ├── __init__.py
    └── config_service.py      # 业务逻辑
```

### 3.2 核心API设计

#### 3.2.1 获取配置列表
```
GET /api/v1/system-configs
Query参数:
  - category: 配置分类（ai/system/general）
  - active_only: 是否只返回激活的配置
  - search: 搜索关键词

响应:
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "config_key": "ai.base_url",
        "config_value": "http://localhost:11434/v1",
        "config_type": "string",
        "category": "ai",
        "description": "LLM API基础URL",
        "is_encrypted": false,
        "is_active": true,
        "updated_at": "2026-06-09T10:00:00"
      }
    ],
    "total": 10
  }
}
```

#### 3.2.2 获取单个配置
```
GET /api/v1/system-configs/{config_key}

响应:
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "config_key": "ai.base_url",
    "config_value": "http://localhost:11434/v1",
    "config_type": "string",
    "category": "ai",
    "description": "LLM API基础URL",
    "is_encrypted": false,
    "is_active": true
  }
}
```

#### 3.2.3 更新配置
```
PUT /api/v1/system-configs/{config_key}
Content-Type: application/json

请求体:
{
  "config_value": "http://localhost:11434/v1",
  "remark": "切换到本地Ollama"
}

响应:
{
  "code": 0,
  "message": "配置更新成功",
  "data": {...}
}
```

#### 3.2.4 批量更新配置
```
PUT /api/v1/system-configs/batch
Content-Type: application/json

请求体:
{
  "items": [
    {"config_key": "ai.base_url", "config_value": "http://localhost:11434/v1"},
    {"config_key": "ai.model", "config_value": "deepseek-r1:latest"}
  ],
  "remark": "批量更新LLM配置"
}

响应:
{
  "code": 0,
  "message": "批量更新成功",
  "data": {"updated_count": 2}
}
```

#### 3.2.5 测试LLM连接
```
POST /api/v1/system-configs/ai/test-connection
Content-Type: application/json

请求体:
{
  "base_url": "http://localhost:11434/v1",
  "model": "qwen2.5:latest",
  "api_key": ""
}

响应:
{
  "code": 0,
  "message": "连接成功",
  "data": {
    "success": true,
    "model": "qwen2.5:latest",
    "response_time_ms": 1234
  }
}
```

#### 3.2.6 获取配置分类
```
GET /api/v1/system-configs/categories

响应:
{
  "code": 0,
  "message": "ok",
  "data": ["ai", "system", "general"]
}
```

### 3.3 配置服务层设计

#### 3.3.1 ConfigService 核心方法

```python
class ConfigService:
    """系统配置服务"""
    
    @staticmethod
    def get_config(key: str, default: Any = None) -> Any:
        """获取配置值（带缓存）"""
        pass
    
    @staticmethod
    def set_config(key: str, value: Any, changed_by: str = None, remark: str = None):
        """设置配置值（自动记录历史）"""
        pass
    
    @staticmethod
    def get_ai_config() -> dict:
        """获取AI相关配置（用于LLM调用）"""
        pass
    
    @staticmethod
    def test_ai_connection(base_url: str, model: str, api_key: str = None) -> dict:
        """测试AI服务连接"""
        pass
    
    @staticmethod
    def reload_config():
        """热加载配置（清除缓存）"""
        pass
```

#### 3.3.2 配置缓存机制

```python
from functools import lru_cache

class ConfigCache:
    """配置缓存管理器"""
    
    _cache = {}
    _cache_ttl = 300  # 5分钟缓存
    
    @classmethod
    def get(cls, key: str) -> Any:
        """从缓存获取配置"""
        pass
    
    @classmethod
    def set(cls, key: str, value: Any):
        """设置缓存"""
        pass
    
    @classmethod
    def invalidate(cls, key: str = None):
        """清除缓存（key为None时清除所有）"""
        pass
```

### 3.4 AI服务集成

#### 3.4.1 使用配置的LLM

```python
# backend/app/modules/ai_analysis/service/ai_service.py

from app.modules.system_config.services.config_service import ConfigService
from openai import OpenAI

class AIService:
    """AI分析服务（使用系统配置的LLM）"""
    
    @staticmethod
    def _get_client() -> OpenAI:
        """根据系统配置创建LLM客户端"""
        config = ConfigService.get_ai_config()
        
        return OpenAI(
            base_url=config['base_url'],
            api_key=config['api_key'] or 'ollama',  # Ollama不需要真实key
            timeout=config['timeout']
        )
    
    @staticmethod
    def analyze_collection(collection_id: str, analysis_types: list) -> dict:
        """分析用例集"""
        client = AIService._get_client()
        config = ConfigService.get_ai_config()
        
        # 构建Prompt
        prompt = AIService._build_prompt(collection_id, analysis_types)
        
        # 调用LLM
        response = client.chat.completions.create(
            model=config['model'],
            messages=[{"role": "user", "content": prompt}],
            temperature=config['temperature'],
            max_tokens=config['max_tokens']
        )
        
        # 解析结果
        return AIService._parse_response(response)
```

---

## 4. 前端设计

### 4.1 页面结构

```
frontend/src/pages/SystemConfig/
├── index.tsx                  # 主页面
├── components/
│   ├── ConfigList.tsx         # 配置列表
│   ├── ConfigForm.tsx         # 配置编辑表单
│   ├── AICOnfigPanel.tsx      # LLM配置面板
│   ├── TestConnection.tsx     # 测试连接组件
│   └── ConfigHistory.tsx      # 配置历史
└── styles/
    └── index.css              # 样式
```

### 4.2 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  系统配置                          [@/system-config]       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [分类标签页: 全部 | AI配置 | 系统配置 | 通用配置]          │
│                                                             │
│  ┌─ AI配置 ───────────────────────────────────────────┐    │
│  │                                                     │    │
│  │  LLM服务配置                                        │    │
│  │  ┌─────────────────────────────────────────────┐   │    │
│  │  │ 基础URL: [http://localhost:11434/v1    ]    │   │    │
│  │  │ 模型名称: [qwen2.5:latest          ▼]    │   │    │
│  │  │ API密钥: [••••••••••••••••        ] (可选) │   │    │
│  │  │ 温度参数: [0.7                            ] │   │    │
│  │  │ 最大Token: [4096                   ]      │   │    │
│  │  │ 超时时间: [60秒                    ]      │   │    │
│  │  │ 启用AI分析: [✓]                            │   │    │
│  │  └─────────────────────────────────────────────┘   │    │
│  │                                                     │    │
│  │  [测试连接]  [重置默认]  [保存配置]                 │    │
│  │                                                     │    │
│  │  连接状态: ✅ 已连接 (qwen2.5:latest, 响应时间123ms)│   │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─ 系统配置 ─────────────────────────────────────────┐    │
│  │  站点名称: [DML测试平台              ]               │    │
│  │  最大上传: [10MB                       ]            │    │
│  │  允许文件: [.pdf,.txt,.json          ]             │    │
│  │  [保存]                                              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─ 配置历史 ─────────────────────────────────────────┐    │
│  │  时间                | 配置项       | 操作人 | 备注  │    │
│  │  2026-06-09 10:00  | ai.model    | admin  | 切换  │    │
│  │  2026-06-08 15:30  | ai.base_url | admin  | 更新  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 主要组件设计

#### 4.3.1 AICOnfigPanel (LLM配置面板)

```typescript
// frontend/src/pages/SystemConfig/components/AICOnfigPanel.tsx

interface AIConfigPanelProps {
  onSave?: (values: AIConfig) => void;
  onTest?: (values: AIConfig) => Promise<TestResult>;
}

interface AIConfig {
  base_url: string;
  model: string;
  api_key: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  enabled: boolean;
}

const AICOnfigPanel: React.FC<AIConfigPanelProps> = ({ onSave, onTest }) => {
  const [config, setConfig] = useState<AIConfig>({...});
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  
  // 测试连接
  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await api.testAIConnection(config);
      setTestResult(result.data);
    } finally {
      setTesting(false);
    }
  };
  
  // 保存配置
  const handleSave = async () => {
    await api.batchUpdateConfigs([
      { config_key: 'ai.base_url', config_value: config.base_url },
      { config_key: 'ai.model', config_value: config.model },
      // ...
    ]);
    onSave?.(config);
  };
  
  return (
    <div className="ai-config-panel">
      <h3>LLM服务配置</h3>
      
      <div className="form-field">
        <label>基础URL</label>
        <input value={config.base_url} onChange={...} />
        <span className="hint">Ollama示例: http://localhost:11434/v1</span>
      </div>
      
      <div className="form-field">
        <label>模型名称</label>
        <input value={config.model} onChange={...} />
        <span className="hint">Ollama: qwen2.5:latest, deepseek-r1:latest</span>
      </div>
      
      {/* 更多字段... */}
      
      <div className="actions">
        <button onClick={handleTest} disabled={testing}>
          {testing ? '测试中...' : '测试连接'}
        </button>
        <button onClick={handleSave} className="btn-primary">
          保存配置
        </button>
      </div>
      
      {testResult && (
        <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
          {testResult.success ? '✅ 连接成功' : '❌ 连接失败'}
          {testResult.response_time_ms && ` (${testResult.response_time_ms}ms)`}
        </div>
      )}
    </div>
  );
};
```

#### 4.3.2 ConfigList (配置列表)

```typescript
// frontend/src/pages/SystemConfig/components/ConfigList.tsx

const ConfigList: React.FC = () => {
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [category, setCategory] = useState<string>('all');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  
  const fetchConfigs = async () => {
    const res = await api.getSystemConfigs({ 
      category: category === 'all' ? undefined : category 
    });
    setConfigs(res.data.items);
  };
  
  const handleEdit = (config: SystemConfig) => {
    setEditingKey(config.config_key);
  };
  
  const handleSave = async (config: SystemConfig, value: string) => {
    await api.updateSystemConfig(config.config_key, { 
      config_value: value 
    });
    setEditingKey(null);
    fetchConfigs();
  };
  
  return (
    <div className="config-list">
      <div className="category-tabs">
        {['all', 'ai', 'system', 'general'].map(cat => (
          <button 
            key={cat}
            className={category === cat ? 'active' : ''}
            onClick={() => setCategory(cat)}
          >
            {cat === 'all' ? '全部' : cat === 'ai' ? 'AI配置' : cat === 'system' ? '系统配置' : '通用'}
          </button>
        ))}
      </div>
      
      <table className="config-table">
        <thead>
          <tr>
            <th>配置项</th>
            <th>值</th>
            <th>类型</th>
            <th>描述</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {configs.map(config => (
            <tr key={config.config_key}>
              <td><code>{config.config_key}</code></td>
              <td>
                {editingKey === config.config_key ? (
                  <input 
                    type={config.is_encrypted ? 'password' : 'text'}
                    defaultValue={config.config_value}
                    onBlur={(e) => handleSave(config, e.target.value)}
                  />
                ) : (
                  <span>
                    {config.is_encrypted ? '••••••' : config.config_value}
                  </span>
                )}
              </td>
              <td><span className="badge">{config.config_type}</span></td>
              <td>{config.description}</td>
              <td>
                <button onClick={() => handleEdit(config)}>编辑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

### 4.4 路由配置

```typescript
// frontend/src/App.tsx 或路由配置文件

<Route path="/system-config" element={<SystemConfigPage />} />
```

### 4.5 导航集成

在侧边栏或顶部导航中添加"系统配置"入口（仅管理员可见）：

```typescript
// frontend/src/components/Layout/Sidebar.tsx

{navigationPermissions.includes('system:config') && (
  <NavItem icon={<SettingsIcon />} label="系统配置" to="/system-config" />
)}
```

---

## 5. 实现步骤

### 阶段1: 数据库和模型 (1小时)
- [ ] 创建 `system_configs` 表迁移脚本
- [ ] 实现 `Config` 和 `ConfigHistory` 模型
- [ ] 插入默认配置数据

### 阶段2: 后端API (2小时)
- [ ] 创建 `system_config` 模块
- [ ] 实现 `ConfigService` 服务类
- [ ] 实现6个API端点
- [ ] 实现配置缓存机制
- [ ] 实现AI连接测试

### 阶段3: AI服务集成 (1小时)
- [ ] 修改 `AIService` 使用 `ConfigService`
- [ ] 移除硬编码的LLM配置
- [ ] 添加配置热加载支持

### 阶段4: 前端页面 (2小时)
- [ ] 创建 `SystemConfig` 页面
- [ ] 实现 `AICOnfigPanel` 组件
- [ ] 实现 `ConfigList` 组件
- [ ] 实现 `TestConnection` 组件
- [ ] 添加API调用方法

### 阶段5: 测试和文档 (1小时)
- [ ] 后端单元测试
- [ ] 前端手动测试
- [ ] 更新API文档
- [ ] 更新README

---

## 6. 技术要点

### 6.1 配置加密
对于敏感配置（如API密钥），使用AES加密存储：

```python
# backend/app/core/security.py

from cryptography.fernet import Fernet

def encrypt_value(value: str) -> str:
    """加密配置值"""
    key = os.getenv('CONFIG_ENCRYPTION_KEY', Fernet.generate_key())
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """解密配置值"""
    key = os.getenv('CONFIG_ENCRYPTION_KEY')
    f = Fernet(key)
    return f.decrypt(encrypted_value.encode()).decode()
```

### 6.2 配置验证
在保存配置前进行验证：

```python
# backend/app/modules/system_config/services/config_service.py

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate(config_key: str, config_value: str) -> tuple[bool, str]:
        """验证配置值，返回 (是否有效, 错误信息)"""
        
        if config_key == 'ai.base_url':
            # 验证URL格式
            if not config_value.startswith(('http://', 'https://')):
                return False, 'URL必须以http://或https://开头'
        
        elif config_key == 'ai.temperature':
            # 验证温度参数范围
            try:
                val = float(config_value)
                if not 0 <= val <= 2:
                    return False, '温度参数必须在0-2之间'
            except ValueError:
                return False, '必须是有效的数字'
        
        elif config_key == 'ai.max_tokens':
            # 验证token数量
            try:
                val = int(config_value)
                if val < 1 or val > 100000:
                    return False, 'Token数量必须在1-100000之间'
            except ValueError:
                return False, '必须是有效的整数'
        
        return True, ''
```

### 6.3 前端表单验证

```typescript
// frontend/src/pages/SystemConfig/components/AICOnfigPanel.tsx

const validateConfig = (config: AIConfig): string[] => {
  const errors: string[] = [];
  
  if (!config.base_url) {
    errors.push('基础URL不能为空');
  } else if (!config.base_url.startsWith('http://') && !config.base_url.startsWith('https://')) {
    errors.push('URL必须以http://或https://开头');
  }
  
  if (!config.model) {
    errors.push('模型名称不能为空');
  }
  
  if (config.temperature < 0 || config.temperature > 2) {
    errors.push('温度参数必须在0-2之间');
  }
  
  if (config.max_tokens < 1 || config.max_tokens > 100000) {
    errors.push('最大Token必须在1-100000之间');
  }
  
  return errors;
};
```

---

## 7. 使用示例

### 7.1 切换LLM服务

1. 进入"系统配置"页面
2. 在"AI配置"面板修改：
   - 基础URL: `https://api.openai.com/v1`
   - 模型名称: `gpt-4`
   - API密钥: `sk-xxx...`
3. 点击"测试连接"验证
4. 点击"保存配置"

### 7.2 使用本地Ollama

1. 确保Ollama已安装并运行：`ollama serve`
2. 拉取模型：`ollama pull qwen2.5`
3. 在配置页面设置：
   - 基础URL: `http://localhost:11434/v1`
   - 模型名称: `qwen2.5:latest`
   - API密钥: （留空）
4. 测试连接并保存

### 7.3 在代码中使用配置

```python
# 任何需要获取AI配置的地方

from app.modules.system_config.services.config_service import ConfigService

# 获取单个配置
base_url = ConfigService.get_config('ai.base_url')
model = ConfigService.get_config('ai.model')

# 获取所有AI配置
ai_config = ConfigService.get_ai_config()
# 返回: {'base_url': '...', 'model': '...', 'api_key': '...', ...}

# 更新配置
ConfigService.set_config('ai.model', 'deepseek-r1:latest', 
                        changed_by='admin', remark='切换到DeepSeek')
```

---

## 8. 文件变更清单

| 文件/目录 | 操作 | 说明 |
|----------|------|------|
| `backend/migrations/versions/xxx_add_system_configs.py` | 新增 | 数据库迁移脚本 |
| `backend/app/modules/system_config/` | 新增 | 系统配置模块 |
| `backend/app/modules/ai_analysis/service/ai_service.py` | 修改 | 使用ConfigService |
| `frontend/src/pages/SystemConfig/` | 新增 | 系统配置页面 |
| `frontend/src/services/api.ts` | 修改 | 添加配置API调用 |
| `frontend/src/types/index.ts` | 修改 | 添加配置类型定义 |
| `docs/design-global-config.md` | 新增 | 本设计文档 |

---

## 9. 后续扩展

### 9.1 配置模板
支持导入/导出配置模板，方便环境迁移。

### 9.2 配置版本控制
配置变更时自动创建Git提交，支持回滚到任意版本。

### 9.3 配置同步
多实例部署时，支持配置自动同步（Redis Pub/Sub）。

### 9.4 配置权限
细粒度的配置权限控制（如：某些配置只有超级管理员可修改）。

---

## 附录A: 完整类型定义

```typescript
// frontend/src/types/system-config.ts

export interface SystemConfig {
  id: number;
  config_key: string;
  config_value: string;
  config_type: 'string' | 'integer' | 'float' | 'boolean' | 'json';
  category: 'ai' | 'system' | 'general';
  description: string;
  is_encrypted: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  updated_by: string;
}

export interface AIConfig {
  base_url: string;
  model: string;
  api_key: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  enabled: boolean;
}

export interface TestConnectionRequest {
  base_url: string;
  model: string;
  api_key?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  model?: string;
  response_time_ms?: number;
  error?: string;
}

export interface BatchUpdateConfigRequest {
  items: Array<{
    config_key: string;
    config_value: string;
  }>;
  remark?: string;
}

export interface ConfigHistory {
  id: number;
  config_key: string;
  old_value: string;
  new_value: string;
  changed_by: string;
  changed_at: string;
  remark: string;
}
```

---

## 附录B: API调用示例

### B.1 前端API封装

```typescript
// frontend/src/services/api.ts

export const systemConfigApi = {
  // 获取配置列表
  getConfigs: (params?: {
    category?: string;
    active_only?: boolean;
    search?: string;
  }): Promise<ApiResponse<{ items: SystemConfig[]; total: number }>> =>
    api.get('/system-configs', { params }),
  
  // 获取单个配置
  getConfig: (key: string): Promise<ApiResponse<SystemConfig>> =>
    api.get(`/system-configs/${key}`),
  
  // 更新配置
  updateConfig: (key: string, data: { config_value: string; remark?: string }): Promise<ApiResponse<SystemConfig>> =>
    api.put(`/system-configs/${key}`, data),
  
  // 批量更新
  batchUpdate: (data: BatchUpdateConfigRequest): Promise<ApiResponse<{ updated_count: number }>> =>
    api.put('/system-configs/batch', data),
  
  // 测试AI连接
  testAIConnection: (data: TestConnectionRequest): Promise<ApiResponse<TestConnectionResponse>> =>
    api.post('/system-configs/ai/test-connection', data),
  
  // 获取配置分类
  getCategories: (): Promise<ApiResponse<string[]>> =>
    api.get('/system-configs/categories'),
  
  // 获取配置历史
  getHistory: (config_key?: string): Promise<ApiResponse<ConfigHistory[]>> =>
    api.get('/system-configs/history', { params: { config_key } }),
};
```

---

**文档版本**: v1.0  
**创建时间**: 2026-06-09  
**作者**: CodeBuddy Code  
**审核状态**: 待审核
