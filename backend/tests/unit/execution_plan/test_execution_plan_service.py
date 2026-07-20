"""execution_plan 服务层单元测试。

测试策略：
- 使用 FakeDoc 模拟 MongoDB Document，避免真实数据库依赖
- 使用 unittest.mock.patch 替换 Beanie 查询方法
- 每个测试方法只测一个业务逻辑分支
"""

from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.execution_plan.service.execution_plan_service import ExecutionPlanService  # noqa: E402
from app.modules.execution_plan.application.plan_command_service import PlanCommandService  # noqa: E402
from app.modules.execution_plan.domain.constants import PlanItemStatus  # noqa: E402
from app.modules.execution_plan.domain.exceptions import ItemNotFoundError, ResultNotFoundError  # noqa: E402
from app.shared.domain.exceptions import PermissionDeniedError  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  Fake Field expressions (must be before _FakeDoc)
# ═══════════════════════════════════════════════════════════════════════


class _FakeField:
    def __init__(self, name):
        self._name = name

    def __eq__(self, other):
        return _FakeExpr(self._name, other)

    def __ne__(self, other):
        return _FakeExpr(self._name, other, op="ne")

    def is_in(self, values):
        return _FakeExpr(self._name, values, op="in")

    def __bool__(self):
        return False


class _FakeExpr:
    def __init__(self, field, value, op="eq"):
        self._field = field
        self._value = value
        self._op = op


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
        for field_name in (
            "plan_id",
            "item_id",
            "case_id",
            "result_id",
            "assignee_id",
            "status",
            "ref_type",
            "execution_task_id",
            "is_deleted",
            "order_no",
            "title",
            "component",
            "priority",
            "case_title",
            "archived_at",
            "created_by",
        ):
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
                        if not cls._matches_expr(doc, arg):
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

    @staticmethod
    def _matches_expr(doc, expr):
        current = getattr(doc, expr._field, None)
        if expr._op == "ne":
            return current != expr._value
        if expr._op == "in":
            return current in expr._value
        return current == expr._value

    @classmethod
    def find(cls, *args, **kwargs):  # noqa: C901
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

                payload = args[0] if args else {}
                for doc in self._docs:
                    for key, value in payload.get("$set", {}).items():
                        setattr(doc, key, value)
                    doc.save()
                return _Result()

            def find(self, _expr):
                return self

        docs = [d for d in cls.store.values() if not getattr(d, "is_deleted", False)]
        for arg in args:
            if hasattr(arg, "_field") and hasattr(arg, "_value"):
                docs = [d for d in docs if cls._matches_expr(d, arg)]
            elif hasattr(arg, "field") and hasattr(arg, "other"):
                # Handle InOp: filter by field in values
                field_name = arg.field._name if hasattr(arg.field, "_name") else str(arg.field)
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
                docs = [d for d in docs if all(getattr(d, k, None) == v for k, v in cond.items())]
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
                        then_val if getattr(gd, fname, None) == expected else else_val for gd in group_docs
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
        payload.setdefault("manual_case_id", None)
        payload.setdefault("result_id", None)
        payload.setdefault("execution_task_id", None)
        payload.setdefault("result_source", None)
        payload.setdefault("order_no", 0)
        super().__init__(**payload)


class _FakeResultDoc(_FakeDoc):
    store: dict[str, "_FakeResultDoc"] = {}
    id_field = "result_id"

    def __init__(self, **payload):
        payload.setdefault("attachments", [])
        payload.setdefault("executed_at", datetime.now(timezone.utc))
        payload.setdefault("result_source", "manual")
        super().__init__(**payload)


class _FakeChangeLogDoc(_FakeDoc):
    store: dict[str, "_FakeChangeLogDoc"] = {}
    id_field = "log_id"
    _seq = 0

    def __init__(self, **payload):
        self.__class__._seq += 1
        payload.setdefault("log_id", f"LOG-{self.__class__._seq}")
        super().__init__(**payload)


# ═══════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_stores():
    _FakePlanDoc.reset()
    _FakeItemDoc.reset()
    _FakeResultDoc.reset()
    _FakeChangeLogDoc.reset()
    yield
    _FakePlanDoc.reset()
    _FakeItemDoc.reset()
    _FakeResultDoc.reset()
    _FakeChangeLogDoc.reset()


@pytest.fixture
def service():
    svc = ExecutionPlanService(user_query=AsyncMock())
    svc._user_query.is_admin.return_value = False
    return svc


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
        created_by="owner1",
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
COMMAND_PATH = "app.modules.execution_plan.application.plan_command_service"


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
        for path in (SERVICE_PATH, COMMAND_PATH):
            p = patch(f"{path}.{attr}", fake)
            p.start()
            patches.append(p)
    p = patch(f"{COMMAND_PATH}.ExecutionPlanChangeLogDoc", _FakeChangeLogDoc)
    p.start()
    patches.append(p)
    for path in (SERVICE_PATH, COMMAND_PATH):
        seq_patcher = patch(f"{path}.SequenceIdService")
        mock_seq_cls = seq_patcher.start()
        mock_seq = MagicMock()
        mock_seq.next = AsyncMock(side_effect=[1, 2, 3, 4, 5])
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
            actor_id="owner1",
        )
        assert result["status"] == "pending"
        assert result["execution_task_id"] is None

    async def test_rerun_rejects_non_assignee_or_manager(self, command_service, auto_item):
        with pytest.raises(PermissionDeniedError):
            await command_service.rerun_item(
                item_id=auto_item.item_id,
                request=MagicMock(assignee_id=None),
                actor_id="stranger",
            )

    async def test_rerun_done_manual_item_resets_to_pending(self, command_service, manual_item):
        result = await command_service.rerun_item(
            item_id=manual_item.item_id,
            request=MagicMock(assignee_id=None),
            actor_id="owner1",
        )
        assert result["status"] == "pending"

    async def test_rerun_updates_assignee_when_provided(self, command_service, auto_item):
        result = await command_service.rerun_item(
            item_id=auto_item.item_id,
            request=MagicMock(assignee_id="new_user"),
            actor_id="owner1",
        )
        assert result["assignee_id"] == "new_user"

    async def test_rerun_keeps_assignee_when_not_provided(self, command_service, auto_item):
        result = await command_service.rerun_item(
            item_id=auto_item.item_id,
            request=MagicMock(assignee_id=None),
            actor_id="owner1",
        )
        assert result["assignee_id"] == "user1"

    async def test_rerun_rejects_non_fail_done_status(self, command_service, plan):
        pending_item = _FakeItemDoc(
            item_id="EPI-PENDING",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="C",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        )
        pending_item.save()
        with pytest.raises(ValueError, match="仅 fail/done"):
            await command_service.rerun_item(
                item_id="EPI-PENDING",
                request=MagicMock(assignee_id=None),
                actor_id="owner1",
            )

    async def test_rerun_rejects_running_status(self, command_service, plan):
        running_item = _FakeItemDoc(
            item_id="EPI-RUNNING",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="C",
            status=PlanItemStatus.RUNNING.value,
            execution_task_id="task-1",
            is_deleted=False,
        )
        running_item.save()
        with pytest.raises(ValueError, match="仅 fail/done"):
            await command_service.rerun_item(
                item_id="EPI-RUNNING",
                request=MagicMock(assignee_id=None),
                actor_id="owner1",
            )

    async def test_rerun_item_not_found_raises(self, command_service):
        with pytest.raises(ItemNotFoundError):
            await command_service.rerun_item(
                item_id="NONEXISTENT",
                request=MagicMock(assignee_id=None),
                actor_id="owner1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — dispatch_plan_item
# ═══════════════════════════════════════════════════════════════════════


class TestDispatchItem:
    async def test_dispatch_plan_item_marks_auto_item_running(self, command_service, plan):
        from app.modules.execution_plan.schemas.execution_plan import PlanItemDispatchRequest

        item = _FakeItemDoc(
            item_id="EPI-DISPATCH",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.PENDING.value,
            result_source="auto",
            is_deleted=False,
        )
        item.save()
        command_service._dispatch_port.dispatch_task = AsyncMock(return_value={"task_id": "task-1"})

        result = await command_service.dispatch_plan_item(
            item_id="EPI-DISPATCH",
            request=PlanItemDispatchRequest(parameters={"k": "v"}),
            actor_id="owner1",
        )

        updated = _FakeItemDoc.store["EPI-DISPATCH"]
        assert result["task_id"] == "task-1"
        assert updated.status == PlanItemStatus.RUNNING.value
        assert updated.execution_task_id == "task-1"
        assert updated.result_source is None
        assert updated.dispatch_config.parameters == {"k": "v"}
        command_service._dispatch_port.dispatch_task.assert_awaited_once()

    async def test_dispatch_rejects_non_auto(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-MANUAL",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅自动化条目"):
            await command_service.dispatch_plan_item(
                item_id="EPI-MANUAL",
                request=MagicMock(),
                actor_id="owner1",
            )

    async def test_dispatch_rejects_non_pending_status(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-RUNNING",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.RUNNING.value,
            execution_task_id="task-old",
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅 pending"):
            await command_service.dispatch_plan_item(
                item_id="EPI-RUNNING",
                request=MagicMock(),
                actor_id="owner1",
            )

    async def test_dispatch_plan_item_not_found(self, command_service):
        with pytest.raises(ItemNotFoundError):
            await command_service.dispatch_plan_item(
                item_id="NONEXISTENT",
                request=MagicMock(),
                actor_id="owner1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — cancel_execution
# ═══════════════════════════════════════════════════════════════════════


class TestCancelExecution:
    async def test_cancel_auto_item_resets_to_pending(self):
        pytest.skip("需要真实 ExecutionTaskDoc 集成")

    async def test_cancel_rejects_manual_item(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-MANUAL",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            status=PlanItemStatus.RUNNING.value,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅自动化"):
            await command_service.cancel_execution(
                item_id="EPI-MANUAL",
                actor_id="owner1",
            )

    async def test_cancel_rejects_item_without_execution_task(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-NO-TASK",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.PENDING.value,
            execution_task_id=None,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="无需取消"):
            await command_service.cancel_execution(
                item_id="EPI-NO-TASK",
                actor_id="owner1",
            )

    async def test_cancel_item_not_found(self, command_service):
        with pytest.raises(ItemNotFoundError):
            await command_service.cancel_execution(
                item_id="NONEXISTENT",
                actor_id="owner1",
            )


# ═══════════════════════════════════════════════════════════════════════
#  Tests — submit_manual_result / get_result
# ═══════════════════════════════════════════════════════════════════════


class TestSubmitResult:
    async def test_submit_manual_result_manual_item_passed(self, command_service, manual_item):
        result = await command_service.submit_manual_result(
            item_id=manual_item.item_id,
            request=MagicMock(
                passed=True,
                notes="ok",
                severity="normal",
                actual="actual",
                expected="expected",
                env="dev",
                test_data="data",
                bug_id="",
                actual_duration="3m",
                attachments=[],
                executed_at=None,
            ),
            actor_id="user2",
        )
        updated = _FakeItemDoc.store[manual_item.item_id]
        assert result["result_id"] == updated.result_id
        assert updated.status == PlanItemStatus.DONE.value
        assert updated.result_source == "manual"
        assert result["result_source"] == "manual"

    async def test_submit_manual_result_manual_item_failed(self, command_service, manual_item):
        await command_service.submit_manual_result(
            item_id=manual_item.item_id,
            request=MagicMock(
                passed=False,
                notes="fail",
                severity="major",
                actual="bad",
                expected="good",
                env="dev",
                test_data="data",
                bug_id="BUG-1",
                actual_duration="5m",
                attachments=[],
                executed_at=None,
            ),
            actor_id="user2",
        )
        assert _FakeItemDoc.store[manual_item.item_id].status == PlanItemStatus.FAIL.value
        assert _FakeItemDoc.store[manual_item.item_id].result_source == "manual"

    async def test_submit_manual_result_rejects_auto_item(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-AUTO",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ValueError, match="仅手工"):
            await command_service.submit_manual_result(
                item_id="EPI-AUTO",
                request=MagicMock(),
                actor_id="owner1",
            )

    async def test_submit_manual_result_replaces_previous_result(self, command_service, manual_item):
        old_result = _FakeResultDoc(
            result_id="MER-OLD",
            item_id=manual_item.item_id,
            plan_id=manual_item.plan_id,
            case_id=manual_item.case_id,
            passed=True,
            notes="old",
            severity="normal",
            actual="",
            expected="",
            env="",
            test_data="",
            bug_id="",
            actual_duration="",
            attachments=[],
            executed_by="user2",
            is_deleted=False,
        )
        manual_item.result_id = old_result.result_id
        manual_item.save()

        result = await command_service.submit_manual_result(
            item_id=manual_item.item_id,
            request=MagicMock(
                passed=True,
                notes="new",
                severity="normal",
                actual="",
                expected="",
                env="",
                test_data="",
                bug_id="",
                actual_duration="",
                attachments=[],
                executed_at=None,
            ),
            actor_id="user2",
        )

        assert _FakeItemDoc.store[manual_item.item_id].result_id == result["result_id"]
        assert _FakeResultDoc.store["MER-OLD"].is_deleted is True
        active_results = [doc for doc in _FakeResultDoc.store.values() if not doc.is_deleted]
        assert [doc.result_id for doc in active_results] == [result["result_id"]]

    async def test_submit_manual_result_insert_failure_keeps_previous_result(self, command_service, manual_item):
        old_result = _FakeResultDoc(
            result_id="MER-OLD",
            item_id=manual_item.item_id,
            plan_id=manual_item.plan_id,
            case_id=manual_item.case_id,
            passed=True,
            notes="old",
            severity="normal",
            actual="",
            expected="",
            env="",
            test_data="",
            bug_id="",
            actual_duration="",
            attachments=[],
            executed_by="user2",
            is_deleted=False,
        )
        manual_item.result_id = old_result.result_id
        manual_item.save()

        async def fail_insert(_self):
            raise RuntimeError("insert failed")

        with patch.object(_FakeResultDoc, "insert", fail_insert):
            with pytest.raises(RuntimeError, match="insert failed"):
                await command_service.submit_manual_result(
                    item_id=manual_item.item_id,
                    request=MagicMock(
                        passed=False,
                        notes="new",
                        severity="normal",
                        actual="",
                        expected="",
                        env="",
                        test_data="",
                        bug_id="",
                        actual_duration="",
                        attachments=[],
                        executed_at=None,
                    ),
                    actor_id="user2",
                )

        assert _FakeItemDoc.store[manual_item.item_id].result_id == "MER-OLD"
        assert _FakeResultDoc.store["MER-OLD"].is_deleted is False

    async def test_submit_manual_result_rejects_non_assignee(self, command_service, manual_item):
        with pytest.raises(PermissionDeniedError):
            await command_service.submit_manual_result(
                item_id=manual_item.item_id,
                request=MagicMock(),
                actor_id="stranger",
            )

    async def test_get_result_returns_result(self, service, manual_item):
        result_doc = _FakeResultDoc(
            result_id="MER-1",
            item_id=manual_item.item_id,
            plan_id=manual_item.plan_id,
            case_id=manual_item.case_id,
            passed=True,
            notes="ok",
            severity="normal",
            actual="",
            expected="",
            env="",
            test_data="",
            bug_id="",
            actual_duration="",
            attachments=[],
            executed_by="user2",
            is_deleted=False,
        )
        manual_item.result_id = result_doc.result_id
        manual_item.save()
        result = await service.get_result(item_id=manual_item.item_id)
        assert result["result_id"] == "MER-1"

    async def test_get_result_not_found(self, service, plan):
        item = _FakeItemDoc(
            item_id="EPI-NO-RESULT",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            result_id=None,
            is_deleted=False,
        )
        item.save()
        with pytest.raises(ResultNotFoundError):
            await service.get_result(item_id="EPI-NO-RESULT")


# ═══════════════════════════════════════════════════════════════════════
#  Tests — batch operations
# ═══════════════════════════════════════════════════════════════════════


class TestResourceAuthorization:
    async def test_plan_owner_can_reassign_item(self, command_service, auto_item):
        result = await command_service.reassign_item(
            item_id=auto_item.item_id,
            assignee_id="new_user",
            operator_id="owner1",
        )
        assert result["assignee_id"] == "new_user"

    async def test_non_manager_cannot_reassign_item(self, command_service, auto_item):
        with pytest.raises(PermissionDeniedError):
            await command_service.reassign_item(
                item_id=auto_item.item_id,
                assignee_id="new_user",
                operator_id="stranger",
            )

    async def test_non_manager_cannot_delete_item(self, command_service, auto_item):
        with pytest.raises(PermissionDeniedError):
            await command_service.delete_item(
                plan_id=auto_item.plan_id,
                item_id=auto_item.item_id,
                actor_id="stranger",
            )
        assert _FakeItemDoc.store[auto_item.item_id].is_deleted is False

    async def test_assignee_can_archive_own_item(self, command_service, auto_item):
        await command_service.archive_item(item_id=auto_item.item_id, actor_id="user1")
        assert _FakeItemDoc.store[auto_item.item_id].archived_at is not None


class TestBatchDispatch:
    async def test_batch_dispatch_empty_raises(self, command_service):
        from app.modules.execution_plan.schemas.execution_plan import BatchDispatchRequest

        with pytest.raises(ValueError, match="不能为空"):
            await command_service.batch_dispatch(
                request=BatchDispatchRequest(item_ids=[]),
                actor_id="owner1",
            )


class TestUpdateItemBoundaries:
    async def test_update_item_allows_metadata_fields_only(self, command_service, auto_item):
        result = await command_service.update_item(
            plan_id=auto_item.plan_id,
            item_id=auto_item.item_id,
            data={"component": "wifi", "order_no": 9},
            actor_id="owner1",
        )

        assert result["component"] == "wifi"
        assert result["order_no"] == 9
        assert _FakeItemDoc.store[auto_item.item_id].status == PlanItemStatus.FAIL.value

    @pytest.mark.parametrize("field", ["status", "execution_task_id", "result_id", "result_source"])
    async def test_update_item_rejects_process_fields(self, command_service, auto_item, field):
        before_status = auto_item.status
        before_task_id = auto_item.execution_task_id
        before_result_id = auto_item.result_id

        with pytest.raises(ValueError, match="流程字段"):
            await command_service.update_item(
                plan_id=auto_item.plan_id,
                item_id=auto_item.item_id,
                data={field: "illegal"},
                actor_id="owner1",
            )

        updated = _FakeItemDoc.store[auto_item.item_id]
        assert updated.status == before_status
        assert updated.execution_task_id == before_task_id
        assert updated.result_id == before_result_id


class TestBatchUpdateAssignee:
    async def test_batch_update_assignee(self, command_service, plan):
        _FakeItemDoc(
            item_id="EPI-B1",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.PENDING.value,
            assignee_id="old",
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-B2",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M2",
            status=PlanItemStatus.PENDING.value,
            assignee_id="old",
            is_deleted=False,
        ).save()
        result = await command_service.batch_update_assignee(
            plan_id=plan.plan_id,
            item_ids=["EPI-B1", "EPI-B2", "EPI-B1"],
            assignee_id="new_user",
            actor_id="owner1",
        )
        assert result["updated_count"] == 2
        assert _FakeItemDoc.store["EPI-B1"].assignee_id == "new_user"
        assert _FakeItemDoc.store["EPI-B2"].assignee_id == "new_user"

    async def test_batch_update_assignee_empty_raises(self, command_service, plan):
        with pytest.raises(ValueError, match="不能为空"):
            await command_service.batch_update_assignee(
                plan_id=plan.plan_id,
                item_ids=[],
                assignee_id="user1",
                actor_id="owner1",
            )

    async def test_batch_update_assignee_invalid_id_rolls_back(self, command_service, plan):
        _FakeItemDoc(
            item_id="EPI-B1",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.PENDING.value,
            assignee_id="old",
            is_deleted=False,
        ).save()
        with pytest.raises(ValueError, match="不存在"):
            await command_service.batch_update_assignee(
                plan_id=plan.plan_id,
                item_ids=["EPI-B1", "MISSING"],
                assignee_id="new_user",
                actor_id="owner1",
            )
        assert _FakeItemDoc.store["EPI-B1"].assignee_id == "old"

    async def test_batch_update_assignee_cross_plan_rolls_back(self, command_service, plan):
        other_plan = _FakePlanDoc(
            plan_id="EP-OTHER",
            title="其他计划",
            status="active",
            created_by="owner1",
            is_deleted=False,
        )
        other_plan.save()
        _FakeItemDoc(
            item_id="EPI-B1",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.PENDING.value,
            assignee_id="old",
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-X",
            plan_id=other_plan.plan_id,
            ref_type="manual",
            case_id="M2",
            status=PlanItemStatus.PENDING.value,
            assignee_id="old",
            is_deleted=False,
        ).save()
        with pytest.raises(ValueError, match="不属于该计划"):
            await command_service.batch_update_assignee(
                plan_id=plan.plan_id,
                item_ids=["EPI-B1", "EPI-X"],
                assignee_id="new_user",
                actor_id="owner1",
            )
        assert _FakeItemDoc.store["EPI-B1"].assignee_id == "old"
        assert _FakeItemDoc.store["EPI-X"].assignee_id == "old"


# ═══════════════════════════════════════════════════════════════════════
#  Tests — archive / unarchive
# ═══════════════════════════════════════════════════════════════════════


class TestArchiveItem:
    async def test_archive_item_sets_archived_at(self, command_service, plan):
        item = _FakeItemDoc(
            item_id="EPI-ARCHIVE",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
            archived_at=None,
        )
        item.save()
        await command_service.archive_item(item_id="EPI-ARCHIVE", actor_id="owner1")
        updated = _FakeItemDoc.store["EPI-ARCHIVE"]
        assert updated.archived_at is not None

    async def test_unarchive_item_clears_archived_at(self, command_service, plan):
        from datetime import datetime, timezone

        item = _FakeItemDoc(
            item_id="EPI-UNARCHIVE",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
            archived_at=datetime.now(timezone.utc),
        )
        item.save()
        await command_service.unarchive_item(item_id="EPI-UNARCHIVE", actor_id="owner1")
        updated = _FakeItemDoc.store["EPI-UNARCHIVE"]
        assert updated.archived_at is None


# ═══════════════════════════════════════════════════════════════════════
#  Tests — list / overview
# ═══════════════════════════════════════════════════════════════════════


class TestListMyItems:
    async def test_list_my_items_returns_assigned_items(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-MY",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            status=PlanItemStatus.PENDING.value,
            assignee_id="my_user",
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-OTHER",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M2",
            status=PlanItemStatus.PENDING.value,
            assignee_id="other_user",
            is_deleted=False,
        ).save()
        results = await service.list_my_items(assignee_id="my_user")
        assert len(results) == 1
        assert results[0]["item_id"] == "EPI-MY"

    async def test_list_my_items_empty(self, service):
        results = await service.list_my_items(assignee_id="no_one")
        assert results == []


class TestListItems:
    async def test_list_items_filters_by_status(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-D",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-P",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M2",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        ).save()
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
            item_id="EPI-ARCH",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            status=PlanItemStatus.DONE.value,
            assignee_id="my_user",
            archived_at=datetime.now(timezone.utc),
            is_deleted=False,
        ).save()
        results = await service.list_archived_items(assignee_id="my_user")
        assert len(results) == 1
        assert results[0]["item_id"] == "EPI-ARCH"


class TestGetOverview:
    async def test_get_overview_aggregates_counts(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-O1",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-O2",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-O3",
            plan_id=plan.plan_id,
            ref_type="auto",
            case_id="A2",
            status=PlanItemStatus.FAIL.value,
            is_deleted=False,
        ).save()
        overview = await service.get_overview()
        assert overview["total_items"] == 3
        assert overview["done_count"] == 1
        assert overview["fail_count"] == 1
        assert overview["pending_count"] == 1
        assert len(overview["plans"]) == 1


# ═══════════════════════════════════════════════════════════════════════
#  Tests — progress recalculation
# ═══════════════════════════════════════════════════════════════════════


class TestRefreshPlanStatus:
    async def test_all_done_marks_plan_done(self, service, plan):
        for i in range(3):
            _FakeItemDoc(
                item_id=f"EPI-PROG-{i}",
                plan_id=plan.plan_id,
                ref_type="manual",
                case_id=f"M-{i}",
                status=PlanItemStatus.DONE.value,
                is_deleted=False,
            ).save()
        await service.refresh_plan_status(plan.plan_id)
        updated = _FakePlanDoc.store[plan.plan_id]
        assert updated.status == "done"

    async def test_partial_plan_stays_active(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-P1",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-P2",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M2",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        ).save()
        await service.refresh_plan_status(plan.plan_id)
        assert _FakePlanDoc.store[plan.plan_id].status == "active"

    async def test_done_plan_returns_active_when_unfinished_items_exist(self, service, plan):
        plan.status = "done"
        plan.save()
        _FakeItemDoc(
            item_id="EPI-P1",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.PENDING.value,
            is_deleted=False,
        ).save()
        await service.refresh_plan_status(plan.plan_id)
        updated = _FakePlanDoc.store[plan.plan_id]
        assert updated.status == "active"

    async def test_draft_plan_status_is_not_recalculated_to_active_or_done(self, service, plan):
        plan.status = "draft"
        plan.save()
        _FakeItemDoc(
            item_id="EPI-PD",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
        ).save()
        await service.refresh_plan_status(plan.plan_id)
        assert _FakePlanDoc.store[plan.plan_id].status == "draft"

    async def test_done_and_fail_items_mark_plan_done(self, service, plan):
        _FakeItemDoc(
            item_id="EPI-PD",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M1",
            status=PlanItemStatus.DONE.value,
            is_deleted=False,
        ).save()
        _FakeItemDoc(
            item_id="EPI-PF",
            plan_id=plan.plan_id,
            ref_type="manual",
            case_id="M2",
            status=PlanItemStatus.FAIL.value,
            is_deleted=False,
        ).save()
        await service.refresh_plan_status(plan.plan_id)
        updated = _FakePlanDoc.store[plan.plan_id]
        assert updated.status == "done"

class TestPlanStats:
    def test_plan_stats_are_derived_from_items(self):
        items = [
            _FakeItemDoc(
                item_id="EPI-S1", plan_id="EP-1", ref_type="manual", case_id="M1",
                status=PlanItemStatus.DONE.value, is_deleted=False,
            ),
            _FakeItemDoc(
                item_id="EPI-S2", plan_id="EP-1", ref_type="manual", case_id="M2",
                status=PlanItemStatus.FAIL.value, is_deleted=False,
            ),
            _FakeItemDoc(
                item_id="EPI-S3", plan_id="EP-1", ref_type="manual", case_id="M3",
                status=PlanItemStatus.PENDING.value, is_deleted=False,
            ),
        ]

        stats = ExecutionPlanService._plan_stats_from_items(items)

        assert stats == {
            "item_count": 3,
            "done_count": 1,
            "progress_percent": 67,
        }
