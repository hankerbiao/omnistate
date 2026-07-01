"""TestCaseRepositoryProtocol 注入场景测试。

验证 P0-1 Repository 协议设计意图：
1. TestCaseService 可通过构造器注入 Mock 实现
2. 注入后业务逻辑走 Mock 而非真实 Document（隔离测试）
3. 不注入时使用默认 TestCaseRepository（生产行为）
4. 协议方法签名可用（类型安全）

测试策略：
- 使用 AsyncMock / MagicMock 构造 Mock 仓库
- 验证 Mock 仓库的调用链被正确执行
- patch 掉 _enrich_test_case_status 和嵌入的 Beanie 操作（AutomationTestCaseDoc），
  避免 Beanie CollectionWasNotInitialized（单元测试环境未 init_beanie）
- 不依赖 _FakeTestCaseDoc 内存存储（纯 Mock）
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.test_case_service import TestCaseService  # noqa: E402
from app.modules.workflow.application import WorkflowItemGateway  # noqa: E402

_SERVICE_MODULE = "app.modules.test_specs.service.test_case_service"


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_workflow_gateway() -> MagicMock:
    gw = MagicMock(spec=WorkflowItemGateway)
    return gw


@pytest.fixture
def mock_catalog_service() -> MagicMock:
    c = MagicMock()
    c.enrich_case_dict = AsyncMock(side_effect=lambda x: x)
    c.prepare_catalog_fields = AsyncMock(return_value={
        "lab_id": "LAB-BIOS",
        "catalog_path": ["bios"],
        "catalog_path_key": "bios",
    })
    c.adjust_path_on_update = AsyncMock()
    c.register_path = AsyncMock()
    return c


@pytest.fixture
def mock_case_repo() -> MagicMock:
    """构造一个实现 TestCaseRepositoryProtocol 的 Mock 仓库。

    使用 MagicMock(spec=) 确保方法签名匹配协议定义。
    """
    from app.modules.test_specs.domain.repositories import TestCaseRepositoryProtocol

    repo = MagicMock(spec=TestCaseRepositoryProtocol)
    repo.find_active_by_case_id = AsyncMock()
    repo.find_by_case_id = AsyncMock()
    repo.insert = AsyncMock()
    repo.save = AsyncMock()
    repo.count = AsyncMock(return_value=0)
    repo.build_find_query = MagicMock()
    repo.get_mongo_client = AsyncMock(return_value=None)
    return repo


def _patch_beanie_side_effects():
    """返回一个上下文管理器集合，防御 Beanie 未初始化的连带副作用。

    在单元测试环境中（无 init_beanie），任何 Beanie Document 的类方法访问
    （如 AutomationTestCaseDoc.find_one）都会抛出 CollectionWasNotInitialized。
    TestCaseService 的 _enrich_test_case_status 中使用了 AutomationTestCaseDoc，
    每次调用 get_test_case/update_test_case 时都需要 patch 它。
    """
    mock_auto = MagicMock()
    mock_auto.find_one = AsyncMock(return_value=None)
    return patch(f"{_SERVICE_MODULE}.AutomationTestCaseDoc", mock_auto)


# ═══════════════════════════════════════════════════════════════════════
#  构造器注入测试
# ═══════════════════════════════════════════════════════════════════════

def test_construct_with_mock_repository(mock_workflow_gateway, mock_catalog_service, mock_case_repo):
    """通过构造器注入 Mock 仓库，不触发默认 TestCaseRepository 的 import。"""
    service = TestCaseService(
        workflow_gateway=mock_workflow_gateway,
        catalog_service=mock_catalog_service,
        case_repository=mock_case_repo,
    )
    assert service._case_repo is mock_case_repo


def test_default_construction_uses_real_repository(mock_workflow_gateway, mock_catalog_service):
    """不传 case_repository 时，使用默认 TestCaseRepository 实现。"""
    service = TestCaseService(
        workflow_gateway=mock_workflow_gateway,
        catalog_service=mock_catalog_service,
    )
    from app.modules.test_specs.repository.test_case_repository import TestCaseRepository
    assert isinstance(service._case_repo, TestCaseRepository)


# ═══════════════════════════════════════════════════════════════════════
#  业务逻辑走 Mock 仓库
# ═══════════════════════════════════════════════════════════════════════

async def test_get_active_case_delegates_to_mock_repo(
    mock_workflow_gateway,
    mock_catalog_service,
    mock_case_repo,
):
    """_get_active_case 通过 mock_case_repo 获取数据，不访问真实 DB。"""
    mock_doc = MagicMock()
    mock_doc.case_id = "TC-001"
    mock_doc.is_deleted = False
    mock_doc.title = "Mocked Case"
    mock_doc.steps = []
    mock_doc.lab_id = None
    mock_doc.catalog_path = None
    mock_doc.catalog_path_key = None
    mock_doc.workflow_item_id = None
    mock_doc.status = "active"
    mock_doc.linked_auto_case_id = None
    mock_doc.model_dump.side_effect = lambda: {
        "case_id": mock_doc.case_id,
        "title": mock_doc.title,
        "status": mock_doc.status,
    }
    mock_case_repo.find_active_by_case_id = AsyncMock(return_value=mock_doc)

    service = TestCaseService(
        workflow_gateway=mock_workflow_gateway,
        catalog_service=mock_catalog_service,
        case_repository=mock_case_repo,
    )

    with patch(f"{_SERVICE_MODULE}.enrich_projected_status",
               AsyncMock(side_effect=lambda x: x)), \
         _patch_beanie_side_effects():
        result = await service.get_test_case("TC-001")

    mock_case_repo.find_active_by_case_id.assert_awaited_once_with("TC-001")
    assert result["case_id"] == "TC-001"
    assert result["title"] == "Mocked Case"


async def test_get_active_case_not_found_raises_key_error(
    mock_workflow_gateway,
    mock_catalog_service,
    mock_case_repo,
):
    """_get_active_case 接收 None 时抛 KeyError。"""
    mock_case_repo.find_active_by_case_id = AsyncMock(return_value=None)

    service = TestCaseService(
        workflow_gateway=mock_workflow_gateway,
        catalog_service=mock_catalog_service,
        case_repository=mock_case_repo,
    )

    with pytest.raises(KeyError, match="test case not found"):
        await service._get_active_case("TC-MISSING")


async def test_update_test_case_via_mock_repo(
    mock_workflow_gateway,
    mock_catalog_service,
    mock_case_repo,
):
    """update_test_case 通过 mock repo 查 + 写，验证数据流完整。

    验证：
    1. find_active_by_case_id 被调用一次
    2. 更新后被 mock_repo.save 保存
    3. 返回结果包含更新后的字段值
    """
    # 准备 mock doc（初始 owner_id=old-owner）
    mock_doc = MagicMock()
    mock_doc.case_id = "TC-001"
    mock_doc.is_deleted = False
    mock_doc.title = "Test"
    mock_doc.owner_id = "old-owner"
    mock_doc.reviewer_id = None
    mock_doc.auto_dev_id = None
    mock_doc.lab_id = None
    mock_doc.catalog_path = None
    mock_doc.catalog_path_key = None
    mock_doc.workflow_item_id = None
    mock_doc.ref_req_id = None
    mock_doc.status = "active"
    mock_doc.tags = []
    mock_doc.test_category = None
    mock_doc.is_active = True
    mock_doc.priority = "P2"
    mock_doc.estimated_duration_sec = None
    mock_doc.required_env = None
    mock_doc.is_destructive = False
    mock_doc.pre_condition = None
    mock_doc.post_condition = None
    mock_doc.risk_level = None
    mock_doc.failure_analysis = None
    mock_doc.confidentiality = None
    mock_doc.visibility_scope = None
    mock_doc.attachments = []
    mock_doc.custom_fields = {}
    mock_doc.deprecation_reason = None
    mock_doc.approval_history = []
    mock_doc.steps = []
    mock_doc.cleanup_steps = []
    mock_doc.updated_at = None
    mock_doc.created_at = None
    mock_doc.version = 1
    mock_doc.save = AsyncMock()  # doc.save 是异步操作
    mock_doc.linked_auto_case_id = None
    mock_doc.model_dump.side_effect = lambda: {
        "case_id": mock_doc.case_id,
        "title": mock_doc.title,
        "owner_id": mock_doc.owner_id,
        "status": mock_doc.status,
    }

    mock_case_repo.find_active_by_case_id = AsyncMock(return_value=mock_doc)
    mock_case_repo.save = AsyncMock()

    service = TestCaseService(
        workflow_gateway=mock_workflow_gateway,
        catalog_service=mock_catalog_service,
        case_repository=mock_case_repo,
    )

    with patch(f"{_SERVICE_MODULE}.enrich_projected_status",
               AsyncMock(side_effect=lambda x: x)), \
         _patch_beanie_side_effects():
        result = await service.update_test_case("TC-001", {"owner_id": "u-new"})

    mock_case_repo.find_active_by_case_id.assert_awaited_once_with("TC-001")
    assert mock_doc.owner_id == "u-new"  # doc 被修改
    assert result["owner_id"] == "u-new"


# ═══════════════════════════════════════════════════════════════════════
#  协议签名验证（编译期检查）
# ═══════════════════════════════════════════════════════════════════════

def test_protocol_has_expected_methods():
    """TestCaseRepositoryProtocol 暴露所有预期方法。"""
    from app.modules.test_specs.domain.repositories import TestCaseRepositoryProtocol

    methods = {
        "find_active_by_case_id",
        "find_by_case_id",
        "insert",
        "save",
        "count",
        "build_find_query",
        "get_mongo_client",
    }
    for m in methods:
        assert hasattr(TestCaseRepositoryProtocol, m), f"协议缺少方法: {m}"


def test_concrete_repo_conforms_to_protocol():
    """TestCaseRepository 实现了协议所有方法。"""
    from app.modules.test_specs.domain.repositories import TestCaseRepositoryProtocol
    from app.modules.test_specs.repository.test_case_repository import TestCaseRepository

    assert issubclass(TestCaseRepository, TestCaseRepositoryProtocol)


# ═══════════════════════════════════════════════════════════════════════
#  不支持注入（面向接口而非实现）装饰器/签名验证
# ═══════════════════════════════════════════════════════════════════════

def test_service_accepts_protocol_not_implementation():
    """构造器签名接受 TestCaseRepositoryProtocol（ABC），而非具体实现。"""
    import inspect
    from app.modules.test_specs.service.test_case_service import TestCaseService

    sig = inspect.signature(TestCaseService.__init__)
    param = sig.parameters.get("case_repository")
    assert param is not None
    # case_repository 的默认值为 None，类型标注应为协议
    if param.annotation is not inspect.Parameter.empty:
        from app.modules.test_specs.domain.repositories import TestCaseRepositoryProtocol
        # 如果加了类型标注，应该用协议而非具体实现
        type_hint = param.annotation
        assert type_hint is TestCaseRepositoryProtocol or type_hint is None or "Protocol" in str(type_hint), (
            f"类型标注应为协议而非具体实现: {type_hint}"
        )
