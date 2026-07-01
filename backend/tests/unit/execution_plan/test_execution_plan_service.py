"""execution_plan 服务层单元测试。

测试策略：
- 使用 FakeDoc 模拟 MongoDB Document，避免真实数据库依赖
- 使用 unittest.mock.patch 替换 Beanie 查询方法
- 每个测试方法只测一个业务逻辑分支
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService  # noqa: E402
from app.modules.execution_plan.application.plan_command_service import PlanCommandService  # noqa: E402
from app.modules.execution_plan.domain.constants import PlanItemStatus  # noqa: E402
from app.modules.execution_plan.domain.exceptions import ItemNotFoundError, PlanNotFoundError, ResultNotFoundError  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  Fake Field expressions (must be before _FakeDoc)
# ═══════════════════════════════════════════════════════════════════════

class _FakeField:
    def __init__(self, name):
        self._name = name

    def __eq__(self, other):
        return _FakeExpr(self._name, other)

    def __bool__(self):
        return False


class _FakeExpr:
    def __init__(self, field, value):
        self._field = field
        self._value = value


class _Awaitable:
    """Synchronous awaitable wrapper — allows `await obj` without async def."""
    def __init__(self, value):
        self._value = value
    def __await__(self):
        return self._await_impl().__await__()
    async def _await_impl(self):
        return self._value


# ═══════════════════════════════════════════════════════════════════════
#  Fake Document helpers
# ═══════════════════════════════════════════════════════════════════════

class _FakeDoc:
    """Minimal fake Beanie document — stores dict and supports find_one/find/save."""

    store: dict[str, "_FakeDoc"] = {}
    id_field = "item_id"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for field_name in ("plan_id", "item_id", "case_id", "result_id", "assignee_id",
                           "status", "ref_type", "execution_task_id",
                           "is_deleted", "order_no", "title", "component", "priority",
                           "case_title", "archived_at"):
            if not hasattr(cls, field_name):
                setattr(cls, field_name, _FakeField(field_name))

    def __init__(self, **payload):
        for k, v in payload.items():
            setattr(self, k, v)
        for field in ("is_deleted", "created_at", "updated_at", "archived_at"):
            if not hasattr(self, field):
                setattr(self, field, None)
        self.__class__.store[getattr(self, self.__class__.id_field)] = self

    def save(self):
        self.__class__.store[getattr(self, self.__class__.id_field)] = self
        return _Awaitable(self)

    def insert(self):
        self.__class__.store[getattr(self, self.__class__.id_field)] = self
        return _Awaitable(self)

    @classmethod
    def reset(cls):
        cls.store = {}

    @classmethod
    def find_one(cls, *args, **kwargs):
        async def _coro():
            for doc in cls.store.values():
                if getattr(doc, "is_deleted", False):
                    continue
                # match by positional Field expressions (beanie style)
                for arg in args:
                    if hasattr(arg, "_field") and hasattr(arg, "_value"):
                        if getattr(doc, arg._field, None) != arg._value:
                            break
                else:
                    return doc
                # match by dict filter
                if args and isinstance(args[0], dict):
                    cond = args[0]
                    if all(getattr(doc, k, None) == v for k, v in cond.items() if k != "is_deleted"):
                        return doc
            return None
        return _coro()

    @classmethod
    def find(cls, *args, **kwargs):
        class _Query:
            def __init__(self, docs):
                self._docs = list(docs)
            def sort(self, *args, **kwargs):
                return self
            def skip(self, n):
                return self
            def limit(self, n):
                return self
            async def to_list(self):
                return self._docs
            async def count(self):
                return len(self._docs)
            def update(self, *args, **kwargs):
                class _Result:
                    modified_count = len(self._docs)
                    def __await__(self):
                        return self._await_impl().__await__()
                    async def _await_impl(self):
                        return self
                return _Result()
            def find(self, _expr):
                return self

        docs = [d for d in cls.store.values() if not getattr(d, "is_deleted", False)]
        for arg in args:
            if hasattr(arg, "_field") and hasattr(arg, "_value"):
                docs = [d for d in docs if getattr(d, arg._field, None) == arg._value]
            elif hasattr(arg, "field") and hasattr(arg, "other"):
                # Handle InOp: filter by field in values
                field_name = arg.field._name if hasattr(arg.field, '_name') else str(arg.field)
                values = arg.other
                docs = [d for d in docs if getattr(d, field_name, None) in values]
        return _Query(docs)

    @classmethod
    def aggregate(cls, pipeline):
        """简化版 aggregation pipeline 执行器，支持 $match + $group($sum/$cond)。

        覆盖 get_overview 的状态计数 pipeline 语义；其他复杂 stage 暂不支持。
        """
        class _AggResult:
            def __init__(self, rows):
                self._rows = rows
            def to_list(self):
                async def _coro():
                    return self._rows
                return _coro()

        docs = list(cls.store.values())
        rows: list = []
        for stage in pipeline:
            if "$match" in stage:
                cond = stage["$match"]
                docs = [d for d in docs
                        if all(getattr(d, k, None) == v for k, v in cond.items())]
            elif "$group" in stage:
                group_spec = stage["$group"]
                id_expr = group_spec["_id"]
                id_field = id_expr.lstrip("$") if isinstance(id_expr, str) else None
                groups: dict = {}
                for d in docs:
                    key = getattr(d, id_field, None) if id_field else None
                    groups.setdefault(key, []).append(d)
                rows = []
                for key, group_docs in groups.items():
                    row: dict = {"_id": key}
                    for field, acc in group_spec.items():
                        if field == "_id":
                            continue
                        row[field] = cls._eval_accumulator(acc, group_docs)
                    rows.append(row)
                # $group 后续 stage 基于行（dict）而非 doc，当前 pipeline 到此结束
                return _AggResult(rows)
        return _AggResult(rows if rows else docs)

    @staticmethod
    def _eval_accumulator(acc, group_docs):
        """计算 $group 累加器（支持 $sum: 1 与 $sum: {$cond: [...]}）。"""
        if isinstance(acc, dict) and "$sum" in acc:
            operand = acc["$sum"]
            if operand == 1:
                return len(group_docs)
            if isinstance(operand, dict) and "$cond" in operand:
                cond_args = operand["$cond"]
                # 形如 [{"$eq": ["$status", "VALUE"]}, then_val, else_val]
                cond_match, then_val, else_val = cond_args
                if isinstance(cond_match, dict) and "$eq" in cond_match:
                    field_expr, expected = cond_match["$eq"]
                    fname = field_expr.lstrip("$") if isinstance(field_expr, str) else field_expr
                    return sum(
                        then_val if getattr(gd, fname, None) == expected else else_val
                        for gd in group_docs
                    )
            return 0
        return acc


class _FakePlanDoc(_FakeDoc):
    store: dict[str, "_FakePlanDoc"] = {}
    id_field = "plan_id"


class _FakeItemDoc(_FakeDoc):
    store: dict[str, "_FakeItemDoc"] = {}
    id_field = "item_id"

    def __init__(self, **payload):
        payload.setdefault("component", "")
        payload.setdefault("priority", "")
        payload.setdefault("case_title", "")
        payload.setdefault("dispatch_config", None)
        super().__init__(**payload)


class _FakeResultDoc(_FakeDoc):
    store: dict[str, "_FakeResultDoc"] = {}
    id_field = "result_id"


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_stores():
    _FakePlanDoc.reset()
    _FakeItemDoc.reset()
    _FakeResultDoc.reset()
    yield
    _FakePlanDoc.reset()
    _FakeItemDoc.reset()
    _FakeResultDoc.reset()


@pytest.fixture
def service():
    return ExecutionPlanService()


@pytest.fixture
def command_service(service):
    return PlanCommandService(
        plan_service=service,
        dispatch_port=AsyncMock(),
        notification_port=AsyncMock(),
    )


@pytest.fixture
def plan():
    doc = _FakePlanDoc(
        plan_id="EP-2026-000001",
        title="测试计划",
        status="active",
        item_count=0,
        done_count=0,
        progress_percent=0,
        is_deleted=False,
    )
    doc.save()
    return doc


@pytest.fixture
def auto_item(plan):
    doc = _FakeItemDoc(
        item_id="EPI-2026-000001",
        plan_id=plan.plan_id,
        ref_type="auto",
        case_id="AUTO-001",
        case_title="自动用例",
        component="bios",
        priority="P1",
        status=PlanItemStatus.FAIL.value,
        assignee_id="user1",
        execution_task_id=None,
        is_deleted=False,
    )
    return doc


@pytest.fixture
def manual_item(plan):
    doc = _FakeItemDoc(
        item_id="EPI-2026-000002",
        plan_id=plan.plan_id,
        ref_type="manual",
        case_id="MANUAL-001",
        case_title="手工用例",
        component="bios",
        priority="P2",
        status=PlanItemStatus.DONE.value,
        assignee_id="user2",
        execution_task_id=None,
        is_deleted=False,
    )
    return doc


# ═══════════════════════════════════════════════════════════════════════
#  Helper: patch the service's model references
# ═══════════════════════════════════════════════════════════════════════

SERVICE_PATH = "app.modules.execution_plan.service.execution_plan_service"


def patch_service(service, target_model: str, fake_cls):
    """Patch a model reference on the service's module."""
    patcher = patch.object(service, target_model, fake_cls)
    patcher.start()
    return patcher


@pytest.fixture(autouse=True)
def auto_patch_models(service):
    """Auto-patch all model references on the service instance."""
    patches = []
    for attr, fake in [
        ("ExecutionPlanDoc", _FakePlanDoc),
        ("ExecutionPlanItemDoc", _FakeItemDoc),
        ("ManualExecutionResultDoc", _FakeResultDoc),
    ]:
        p = patch(f"{SERVICE_PATH}.{attr}", fake)
        p.start()
        patches.append(p)
    # Also patch SequenceIdService to return predictable IDs
    seq_patcher = patch(f"{SERVICE_PATH}.SequenceIdService")
    mock_seq_cls = seq_patcher.start()
    mock_seq = MagicMock()
    mock_seq.next = AsyncMock(side_effect=[1, 2, 3])
    mock_seq_cls.return_value = mock_seq
    patches.append(seq_patcher)
    yield
    for p in patches:
        p.stop()


# ═══════════════════════════════════════════════════════════════════════
#  Tests — rerun_item
# ═══════════════════════════════════════════════════════════════════════

class TestRerunItem:
    async def test_rerun_fail_auto_item_resets_to_pending(self, command_service, auto_item):
        result = await command_service.rerun_item(
            item_id=auto_item.item_id,
            request=MagicMock(assignee_id=None),
            actor_id="actor1",
        )
        assert result["status"] == "pending"
        assert result["execution_task_id"] is None

    async def test_rerun_done_manual_item_resets_to_pending(self, command_service, manual_item):
        result = await command_service.rerun_item(
            item_id=manual_item.item_id,
            request=MagicMock(assignee_id=None),
            actor_id="actor1",
        )
        assert result["status"] == "pending"

    async def test_rerun_updates_assignee_when_provided(self, command_service, auto_item):
        result = await command_service.rerun_item(
            item_id=auto_item.item_id,
            request=MagicMock(assignee_id="new_user"),
            actor_id="actor1",
        )
        assert result["assignee_id"] == "new_user"

    async def test_rerun_keeps_assignee_when_not_provided(self, command_service, auto_item):
        result = await command_service.rerun_item(
            item_id=auto_item.item_id,
            request=MagicMock(assignee_id=None),
            actor_id="actor1",
        )
        assert result["assignee_id"] == "user1"

    async def test_rerun_rejects_non_fail_done_status(self, command_service, plan):
        pending_item = _FakeItemDoc(
            item_id="EPI-PENDING", plan_id=plan.plan_id,
            ref_type="auto", case_id="C", status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        )
        pending_item.save()
        with pytest.raises(ValueError, match="仅 fail/done"):
            await command_service.rerun_item(
                item_id="EPI-PENDING",
                request=MagicMock(assignee_id=None),
                actor_id="actor1",
            )

    async def test_rerun_rejects_running_status(self, command_service, plan):
        running_item = _FakeItemDoc(
            item_id="EPI-RUNNING", plan_id=plan.plan_id,
            ref_type="auto", case_id="C", status=PlanItemStatus.RUNNING.value,
            execution_task_id="task-1", is_deleted=False,
        )
        running_item.save()
        with pytest.raises(ValueError, match="仅 fail/done"):
            await command_service.rerun_item(
                item_id="EPI-RUNNING",
                request=MagicMock(assignee_id=None),
                actor_id="actor1",
            )

    async def test_rerun_item_not_found_raises(self, command_service):
        with pytest.raises(ItemNotFoundError):
            await command_service.rerun_item(
                item_id="NONEXISTENT",
                request=MagicMock(assignee_id=None),
                actor_id="actor1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — dispatch_item
# ═══════════════════════════════════════════════════════════════════════

class TestDispatchItem:
    # 成功下发需要真实 DispatchTaskRequest 集成，此处跳过
    async def test_dispatch_pending_auto_success(self):
        pytest.skip("需要真实 DispatchTaskRequest 集成")

    async def test_dispatch_rejects_non_auto(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-MANUAL", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅自动化条目"):
            await command_service.dispatch_item(
                item_id="EPI-MANUAL",
                request=MagicMock(),
                actor_id="actor1",
            )

    async def test_dispatch_rejects_non_pending_status(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-RUNNING", plan_id=plan.plan_id,
            ref_type="auto", case_id="A",
            status=PlanItemStatus.RUNNING.value,
            execution_task_id="task-old", is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅 pending"):
            await command_service.dispatch_item(
                item_id="EPI-RUNNING",
                request=MagicMock(),
                actor_id="actor1",
            )

    async def test_dispatch_item_not_found(self, command_service):
        with pytest.raises(ItemNotFoundError):
            await command_service.dispatch_item(
                item_id="NONEXISTENT",
                request=MagicMock(),
                actor_id="actor1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — cancel_execution
# ═══════════════════════════════════════════════════════════════════════

class TestCancelExecution:
    async def test_cancel_auto_item_resets_to_pending(self):
        pytest.skip("需要真实 ExecutionTaskDoc 集成")

    async def test_cancel_rejects_manual_item(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-MANUAL", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            status=PlanItemStatus.RUNNING.value,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅自动化"):
            await command_service.cancel_execution(
                item_id="EPI-MANUAL",
                actor_id="actor1",
            )

    async def test_cancel_rejects_item_without_execution_task(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-NO-TASK", plan_id=plan.plan_id,
            ref_type="auto", case_id="A",
            status=PlanItemStatus.PENDING.value,
            execution_task_id=None, is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="无需取消"):
            await command_service.cancel_execution(
                item_id="EPI-NO-TASK",
                actor_id="actor1",
            )

    async def test_cancel_item_not_found(self, command_service):
        with pytest.raises(ItemNotFoundError):
            await command_service.cancel_execution(
                item_id="NONEXISTENT",
                actor_id="actor1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — submit_result / get_result
# ═══════════════════════════════════════════════════════════════════════

class TestSubmitResult:
    async def test_submit_result_manual_item_passed(self):
        pytest.skip("需要真实 ManualExecutionResultDoc 和 SequenceIdService 集成")

    async def test_submit_result_manual_item_failed(self):
        pytest.skip("需要真实 ManualExecutionResultDoc 集成")

    async def test_submit_result_rejects_auto_item(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-AUTO", plan_id=plan.plan_id,
            ref_type="auto", case_id="A",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅手工"):
            await command_service.submit_result(
                item_id="EPI-AUTO",
                request=MagicMock(),
                actor_id="actor1",
            )

    async def test_submit_result_replaces_previous_result(self):
        pytest.skip("需要真实 ManualExecutionResultDoc 集成")

    async def test_get_result_returns_result(self):
        pytest.skip("需要真实 ManualExecutionResultDoc 集成")

    async def test_get_result_not_found(self, service, plan):
        item = _FakeItemDoc(
            item_id="EPI-NO-RESULT", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            result_id=None, is_deleted=False,
        )
        item.save()
        with pytest.raises(ResultNotFoundError):
            await service.get_result(item_id="EPI-NO-RESULT")


# ═══════════════════════════════════════════════════════════════════════
#  Tests — batch operations
# ═══════════════════════════════════════════════════════════════════════

class TestBatchDispatch:
    async def test_batch_dispatch_empty_raises(self, command_service):
        from app.modules.execution_plan.schemas.execution_plan import BatchDispatchRequest
        with pytest.raises(ValueError, match="不能为空"):
            await command_service.batch_dispatch(
                request=BatchDispatchRequest(item_ids=[]),
                actor_id="actor1",
            )


class TestBatchUpdateAssignee:
    async def test_batch_update_assignee(self, command_service, plan):
        pytest.skip("需要真实 Beanie InOp 查询集成")

    async def test_batch_update_assignee_empty_raises(self, command_service, plan):
        with pytest.raises(ValueError, match="不能为空"):
            await command_service.batch_update_assignee(
                plan_id=plan.plan_id,
                item_ids=[],
                assignee_id="user1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — archive / unarchive
# ═══════════════════════════════════════════════════════════════════════

class TestArchiveItem:
    async def test_archive_item_sets_archived_at(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-ARCHIVE", plan_id=plan.plan_id,
            ref_type="auto", case_id="A",
            status=PlanItemStatus.DONE.value,
            is_deleted=False, archived_at=None,
        )
        item.save()
        await command_service.archive_item(item_id="EPI-ARCHIVE", actor_id="actor1")
        updated = _FakeItemDoc.store["EPI-ARCHIVE"]
        assert updated.archived_at is not None

    async def test_unarchive_item_clears_archived_at(self, command_service, plan):
        from datetime import datetime, timezone
        item = _FakeItemDoc(
            item_id="EPI-UNARCHIVE", plan_id=plan.plan_id,
            ref_type="auto", case_id="A",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
            archived_at=datetime.now(timezone.utc),
        )
        item.save()
        await command_service.unarchive_item(item_id="EPI-UNARCHIVE", actor_id="actor1")
        updated = _FakeItemDoc.store["EPI-UNARCHIVE"]
        assert updated.archived_at is None


# ═══════════════════════════════════════════════════════════════════════
#  Tests — list / overview
# ═══════════════════════════════════════════════════════════════════════

class TestListMyItems:
    async def test_list_my_items_returns_assigned_items(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-MY", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            status=PlanItemStatus.PENDING.value,
            assignee_id="my_user", is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-OTHER", plan_id=plan.plan_id,
            ref_type="manual", case_id="M2",
            status=PlanItemStatus.PENDING.value,
            assignee_id="other_user", is_deleted=False,
        ).save()
        # patch _sync_auto_item_status to no-op
        with patch.object(service, "_sync_auto_item_status", AsyncMock()):
            results = await service.list_my_items(assignee_id="my_user")
        assert len(results) == 1
        assert results[0]["item_id"] == "EPI-MY"

    async def test_list_my_items_empty(self, service):
        results = await service.list_my_items(assignee_id="no_one")
        assert results == []


class TestListItems:
    async def test_list_items_filters_by_status(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-D", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            status=PlanItemStatus.DONE.value, is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-P", plan_id=plan.plan_id,
            ref_type="manual", case_id="M2",
            status=PlanItemStatus.PENDING.value, is_deleted=False,
        ).save()
        with patch.object(service, "_sync_auto_item_status", AsyncMock()):
            results = await service.list_items(status="done")
        assert len(results) == 1
        assert results[0]["item_id"] == "EPI-D"

    async def test_list_items_invalid_status_raises(self, service):
        with pytest.raises(ValueError, match="status 无效"):
            await service.list_items(status="invalid_status")


class TestListArchivedItems:
    async def test_list_archived_items(self, service, plan):
        from datetime import datetime, timezone
        _FakeItemDoc(
            item_id="EPI-ARCH", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            status=PlanItemStatus.DONE.value,
            assignee_id="my_user",
            archived_at=datetime.now(timezone.utc), is_deleted=False,
        ).save()
        with patch.object(service, "_sync_auto_item_status", AsyncMock()):
            results = await service.list_archived_items(assignee_id="my_user")
        assert len(results) == 1
        assert results[0]["item_id"] == "EPI-ARCH"


class TestGetOverview:
    async def test_get_overview_aggregates_counts(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-O1", plan_id=plan.plan_id,
            ref_type="manual", case_id="M",
            status=PlanItemStatus.DONE.value, is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-O2", plan_id=plan.plan_id,
            ref_type="auto", case_id="A",
            status=PlanItemStatus.PENDING.value, is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-O3", plan_id=plan.plan_id,
            ref_type="auto", case_id="A2",
            status=PlanItemStatus.FAIL.value, is_deleted=False,
        ).save()
        with patch.object(service, "_sync_auto_item_status", AsyncMock()):
            overview = await service.get_overview()
        assert overview["total_items"] == 3
        assert overview["done_count"] == 1
        assert overview["fail_count"] == 1
        assert overview["pending_count"] == 1
        assert len(overview["plans"]) == 1


# ═══════════════════════════════════════════════════════════════════════
#  Tests — progress recalculation
# ═══════════════════════════════════════════════════════════════════════

class TestRecalculateProgress:
    async def test_progress_all_done_marks_plan_done(self, service, plan):
        for i in range(3):
            _FakeItemDoc(
                item_id=f"EPI-PROG-{i}", plan_id=plan.plan_id,
                ref_type="manual", case_id=f"M-{i}",
                status=PlanItemStatus.DONE.value, is_deleted=False,
            ).save()
        await service.recalculate_plan_progress(plan.plan_id)
        updated = _FakePlanDoc.store[plan.plan_id]
        assert updated.progress_percent == 100
        assert updated.status == "done"

    async def test_progress_partial(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-P1", plan_id=plan.plan_id,
            ref_type="manual", case_id="M1",
            status=PlanItemStatus.DONE.value, is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-P2", plan_id=plan.plan_id,
            ref_type="manual", case_id="M2",
            status=PlanItemStatus.PENDING.value, is_deleted=False,
        ).save()
        await service.recalculate_plan_progress(plan.plan_id)
        updated = _FakePlanDoc.store[plan.plan_id]
        assert updated.progress_percent == 50

    async def test_progress_fail_and_done_counts_separately(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-PD", plan_id=plan.plan_id,
            ref_type="manual", case_id="M1",
            status=PlanItemStatus.DONE.value, is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-PF", plan_id=plan.plan_id,
            ref_type="manual", case_id="M2",
            status=PlanItemStatus.FAIL.value, is_deleted=False,
        ).save()
        await service.recalculate_plan_progress(plan.plan_id)
        updated = _FakePlanDoc.store[plan.plan_id]
        assert updated.done_count == 1  # only DONE, not FAIL
        assert updated.progress_percent == 100  # both DONE+FAIL = completed
