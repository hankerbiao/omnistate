# Plan: 添加 AI 分析端点到 TestCaseCollection 模块

## 概述
基于对 `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/` 目录的探索，本文档提供添加新 AI 分析端点的详细指南。

## 1. 模块结构分析

### 1.1 目录结构
```
test_case_collection/
├── api/
│   ├── __init__.py
│   ├── dependencies.py      # 依赖注入定义
│   └── router.py            # API 路由定义 (核心文件)
├── models/
│   └── collection.py        # Beanie Document 模型
├── schemas/
│   └── collection.py        # Pydantic 请求/响应 Schema
├── service/
│   └── __init__.py          # TestCaseCollectionService 实现
└── __init__.py
```

### 1.2 关键文件详情

#### API 路由文件
**文件路径**: `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/api/router.py`

**路由器定义**:
```python
router = APIRouter(
    prefix="/api/v1/test-case-collections",
    tags=["用例集合"],
    dependencies=[Depends(get_current_user)]
)
```

**现有端点**:
1. `POST /` - 创建集合
2. `GET /` - 列表查询（分页、搜索、标签筛选）
3. `GET /{collection_id}` - 获取详情
4. `PUT /{collection_id}` - 更新集合
5. `DELETE /{collection_id}` - 删除集合
6. `POST /{collection_id}/cases` - 添加用例
7. `DELETE /{collection_id}/cases` - 移除用例
8. `GET /{collection_id}/cases` - 获取用例列表（分页、搜索）

#### 数据模型
**文件路径**: `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/models/collection.py`

**核心字段**:
- `collection_id`: str - 业务ID（格式: COLL-YYYYMMDD-XXX）
- `name`: str - 集合名称
- `description`: Optional[str] - 描述
- `tags`: List[str] - 标签列表
- `case_ids`: List[str] - 手工用例ID列表
- `auto_case_ids`: List[str] - 自动化用例ID列表
- `created_by`: str - 创建人
- `created_at`, `updated_at`: datetime
- `is_deleted`: bool - 软删除标志

**Settings 类配置**:
```python
class Settings:
    name = "test_case_collections"
    indexes = [
        IndexModel([("collection_id", 1)], unique=True),
        IndexModel([("name", 1)]),
        IndexModel([("tags", 1)]),
        IndexModel([("created_by", 1)]),
        IndexModel([("is_deleted", 1), ("created_at", -1)]),
    ]
```

#### Service 层
**文件路径**: `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/service/__init__.py`

**TestCaseCollectionService 类** - 所有业务逻辑的入口

**关键方法**:
1. `create_collection(request, user)` - 创建集合
2. `get_collections(page, page_size, search, tags)` - 分页查询
3. `get_collection_detail(collection_id)` - 获取详情
4. `update_collection(collection_id, request)` - 更新
5. `delete_collection(collection_id)` - 删除（软删除）
6. `add_cases(collection_id, request)` - 添加用例
7. `remove_cases(collection_id, request)` - 移除用例
8. `get_collection_cases(collection_id, page, page_size, search)` - 获取用例列表

**设计模式**:
- 纯领域服务（无继承）
- 直接使用 Beanie Document 进行数据库操作
- 统一的错误处理和日志记录
- 支持批量操作的事务性保证

## 2. 添加 AI 分析端点的实现方案

### 2.1 推荐的实现路径

#### 方案 A: 在现有 router.py 中添加端点（推荐）
**优点**: 
- 保持代码组织的一致性
- 利用现有的依赖注入和服务层
- 便于维护和测试

**实现步骤**:
1. 在 `schemas/collection.py` 中定义请求/响应 Schema
2. 在 `service/__init__.py` 中添加分析方法
3. 在 `api/router.py` 中添加 API 端点

#### 方案 B: 创建独立的 AI 分析模块
**适用场景**: AI 功能较为复杂，需要独立的配置和管理

### 2.2 具体实现示例

#### Step 1: 定义 Schema
**文件**: `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/schemas/collection.py`

```python
class AIAnalysisRequest(BaseModel):
    """AI 分析请求"""
    analysis_type: str = Field(..., description="分析类型: similarity, coverage, optimization")
    options: Optional[Dict[str, Any]] = Field(None, description="分析选项")

class AIAnalysisResponse(BaseModel):
    """AI 分析响应"""
    collection_id: str
    analysis_type: str
    result: Dict[str, Any]
    created_at: datetime
    
    model_config = {"from_attributes": True}
```

#### Step 2: 实现 Service 方法
**文件**: `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/service/__init__.py`

```python
async def analyze_collection_with_ai(
    self, 
    collection_id: str, 
    analysis_type: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    使用 AI 分析用例集合。
    
    Args:
        collection_id: 集合 ID
        analysis_type: 分析类型
        options: 分析选项
        
    Returns:
        分析结果字典
        
    Raises:
        CollectionNotFoundError: 集合不存在
    """
    # 1. 获取集合详情（包含用例列表）
    doc = await TestCaseCollectionDoc.find_one(
        TestCaseCollectionDoc.collection_id == collection_id,
        TestCaseCollectionDoc.is_deleted == False
    )
    if not doc:
        raise CollectionNotFoundError(f"集合不存在: {collection_id}")
    
    # 2. 获取用例详情（需要调用 test_specs 模块）
    case_details = await self._fetch_case_details(doc.case_ids)
    
    # 3. 调用 AI 分析（需要实现 AI 服务客户端）
    analysis_result = await self._call_ai_service(
        analysis_type=analysis_type,
        cases=case_details,
        options=options
    )
    
    # 4. 保存分析结果（可选：创建新的 CollectionAnalysisResultDoc）
    logger.info(
        "AI 分析完成",
        extra={"collection_id": collection_id, "analysis_type": analysis_type}
    )
    
    return {
        "collection_id": collection_id,
        "analysis_type": analysis_type,
        "result": analysis_result,
        "case_count": len(doc.case_ids)
    }

async def _fetch_case_details(self, case_ids: List[str]) -> List[Dict[str, Any]]:
    """获取用例详情列表"""
    # 需要导入 test_specs 模块的 service
    # 这里需要根据实际的 test_specs service 接口实现
    pass

async def _call_ai_service(
    self, 
    analysis_type: str, 
    cases: List[Dict[str, Any]],
    options: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """调用 AI 服务进行分析"""
    # 实现 AI 服务调用逻辑
    # 可以使用 OpenAI API、本地 LLM 或其他 AI 服务
    pass
```

#### Step 3: 添加 API 端点
**文件**: `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/api/router.py`

```python
@router.post(
    "/{collection_id}/analyze",
    response_model=ApiResponse[AIAnalysisResponse],
    summary="AI 分析用例集合"
)
async def analyze_collection(
    collection_id: str = Path(..., description="集合 ID"),
    request: AIAnalysisRequest = Body(...),
    service: CollectionServiceDep = Depends(),
    user: UserDep = Depends(get_current_user)
):
    """
    使用 AI 分析用例集合。
    
    支持的分析类型：
    - similarity: 用例相似度分析
    - coverage: 测试覆盖率分析
    - optimization: 用例优化建议
    """
    result = await service.analyze_collection_with_ai(
        collection_id=collection_id,
        analysis_type=request.analysis_type,
        options=request.options
    )
    return ApiResponse(data=result)
```

### 2.3 前端集成

#### 更新 API 服务
**文件**: `/Users/libiao/Desktop/github/dmlv4/frontend/src/services/api.ts`

```typescript
// 在 testCaseCollectionApi 对象中添加
analyzeCollection: (collectionId: string, request: AIAnalysisRequest) =>
  api.post<ApiResponse<AIAnalysisResponse>>(
    `/test-case-collections/${collectionId}/analyze`,
    request
  ),
```

#### 更新类型定义
**文件**: `/Users/libiao/Desktop/github/dmlv4/frontend/src/types/index.ts`

```typescript
export interface AIAnalysisRequest {
  analysis_type: string;
  options?: Record<string, any>;
}

export interface AIAnalysisResponse {
  collection_id: string;
  analysis_type: string;
  result: Record<string, any>;
  created_at: string;
}
```

## 3. 关键技术要点

### 3.1 依赖注入模式
- 使用 `Annotated` + `Depends` 定义依赖类型
- `CollectionServiceDep` 是标准的依赖类型定义
- 在路由函数中直接使用 `service: CollectionServiceDep`

### 3.2 响应格式
- 所有 API 使用统一的 `ApiResponse` 包装
- `ApiResponse(data=result)` 自动序列化为 `{"code": 0, "message": "ok", "data": {...}}`

### 3.3 错误处理
- Service 层抛出领域异常（如 `CollectionNotFoundError`）
- API 层捕获异常并转换为适当的 HTTP 响应
- 使用 `app.shared.core.logger` 进行结构化日志记录

### 3.4 数据库操作
- 使用 Beanie ODM 进行 MongoDB 操作
- 所有查询都包含 `is_deleted == False` 条件
- 使用 `PydanticObjectId` 处理文档 ID

## 4. 参考文件清单

### 后端文件
1. `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/api/router.py` - API 路由
2. `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/models/collection.py` - 数据模型
3. `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/schemas/collection.py` - Pydantic Schema
4. `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/service/__init__.py` - Service 层
5. `/Users/libiao/Desktop/github/dmlv4/backend/app/modules/test_case_collection/api/dependencies.py` - 依赖注入

### 前端文件
1. `/Users/libiao/Desktop/github/dmlv4/frontend/src/services/api.ts` - API 服务
2. `/Users/libiao/Desktop/github/dmlv4/frontend/src/types/index.ts` - 类型定义

### 共享模块
1. `/Users/libiao/Desktop/github/dmlv4/backend/app/shared/core/logger.py` - 日志工具
2. `/Users/libiao/Desktop/github/dmlv4/backend/app/shared/core/security.py` - 安全工具（JWT 认证）

## 5. 下一步行动

1. **确定 AI 服务集成方式** - 选择 OpenAI API、本地 LLM 或其他服务
2. **设计分析结果存储方案** - 是否需要创建新的 Document 模型
3. **实现核心分析方法** - 在 Service 层实现 AI 调用逻辑
4. **添加单元测试** - 为新的端点和方法编写测试
5. **更新前端界面** - 添加 AI 分析功能的 UI 组件

## 6. 注意事项

1. **异步模式** - 所有数据库操作和 AI 调用都应该是异步的
2. **错误处理** - AI 服务调用可能失败，需要妥善处理
3. **性能考虑** - AI 分析可能耗时较长，考虑使用后台任务或 WebSocket
4. **权限控制** - 确保 AI 分析端点有适当的权限检查
5. **配置管理** - AI 服务的相关配置（API key、endpoint 等）应通过环境变量管理
