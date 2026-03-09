class FakeQuery:
    def __init__(self, docs):
        # 保存预置数据，模拟查询结果集
        self.docs = docs
        # 记录排序表达式，便于断言
        self.sort_expr = None
        # 记录跳过条数，便于断言
        self.skipped = None
        # 记录限制条数，便于断言
        self.limited = None

    def sort(self, sort_expr):
        # 记录排序参数，返回 self 以模拟链式调用
        self.sort_expr = sort_expr
        return self

    def skip(self, offset):
        # 记录分页偏移，返回 self 以模拟链式调用
        self.skipped = offset
        return self

    def limit(self, limit):
        # 记录分页大小，返回 self 以模拟链式调用
        self.limited = limit
        return self

    async def to_list(self):
        # 异步返回数据列表，模拟 Beanie 的 to_list 行为
        return self.docs


class FakeWorkItemDoc:
    def __init__(self, **kwargs):
        # 允许动态注入字段，模拟 Document 实例
        self.__dict__.update(kwargs)
        # 用于测试保存行为
        self.saved = False

    async def save(self):
        # 标记保存成功，便于断言
        self.saved = True

    def model_dump(self):
        # 仅返回测试所需字段的字典
        return {
            "id": self.id,
            "type_code": self.type_code,
            "title": self.title,
            "content": self.content,
            "parent_item_id": self.parent_item_id,
            "current_state": self.current_state,
            "current_owner_id": self.current_owner_id,
            "creator_id": self.creator_id,
        }


class FakeConfigDoc:
    def __init__(self, **kwargs):
        # 允许动态注入字段，模拟配置文档
        self.__dict__.update(kwargs)


class FakeFlowLog:
    # 用于记录插入行为与 payload，便于断言
    inserted = False
    payload = None

    def __init__(self, **kwargs):
        # 允许动态注入字段，模拟日志文档
        self.__dict__.update(kwargs)

    async def insert(self):
        # 标记插入成功并记录 payload
        FakeFlowLog.inserted = True
        FakeFlowLog.payload = self.payload


class FakeWorkflowService:
    async def get_work_types(self):
        # 返回固定的类型数据，供接口测试使用
        return [
            {
                "code": "REQ",
                "name": "Requirement",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
        ]

    async def get_item_by_id(self, item_id: str):
        # 默认返回 None，便于测试 404 场景
        return None

    async def create_item(self, type_code, title, content, creator_id, parent_item_id=None):
        # 返回固定结构，模拟创建成功后的业务对象
        return {
            "id": "507f1f77bcf86cd799439011",
            "item_id": "507f1f77bcf86cd799439011",
            "type_code": type_code,
            "title": title,
            "content": content,
            "parent_item_id": parent_item_id,
            "current_state": "DRAFT",
            "current_owner_id": creator_id,
            "creator_id": creator_id,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

    async def batch_get_logs(self, item_ids, limit=20):
        invalid = [item_id for item_id in item_ids if "invalid" in item_id]
        if invalid:
            raise ValueError(f"invalid item_ids: {invalid}")
        return {item_id: [] for item_id in item_ids}
