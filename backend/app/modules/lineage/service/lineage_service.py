"""测试血缘图谱服务 —— 遍历外键链构造 DAG。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from app.modules.execution.repository.models import (
    ExecutionAgentDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.lineage.schemas.lineage import (
    LineageEdge,
    LineageGraphResponse,
    LineageNode,
    NodeType,
)
from app.modules.test_specs.repository.models import (
    AutomationTestCaseDoc,
    TestCaseDoc,
    TestRequirementDoc,
)


class LineageService:
    """血缘图谱构造服务。

    外键链（正序）:
        Requirement -> TestCase -> AutomationTestCase -> ExecutionTask -> CaseResult -> Agent

    该服务接受任意一个 entity_id + entity_type，
    自动判断其在链中的位置，同时向上下游遍历，收集所有关联节点。
    """

    # 每层向"上游"（朝 Requirement 方向）走一步的解析器映射。
    # 键为当前节点类型，值为 (lambda 名, 解析函数)。
    # 解析函数返回 (nodes, edges) 元组。
    UPSTREAM_RESOLVERS: Dict[str, str] = {
        "task": "_resolve_task_upstream",
        "case_result": "_resolve_case_result_upstream",
        "automation_case": "_resolve_auto_case_upstream",
        "test_case": "_resolve_test_case_upstream",
    }

    DOWNSTREAM_RESOLVERS: Dict[str, str] = {
        "requirement": "_resolve_requirement_downstream",
        "test_case": "_resolve_test_case_downstream",
        "automation_case": "_resolve_auto_case_downstream",
        "task": "_resolve_task_downstream",
    }

    async def get_lineage_graph(
        self,
        entity_type: str,
        entity_id: str,
        max_nodes: int = 50,
    ) -> LineageGraphResponse:
        """获取完整血缘图谱。

        1. 根据 entity_type 找到入口实体并作为根节点
        2. 朝上游（Requirement 方向）遍历
        3. 朝下游（Agent 方向）遍历
        4. 去重节点和边
        5. 返回 LineageGraphResponse

        Args:
            entity_type: 入口实体类型
            entity_id: 入口实体 ID
            max_nodes: 最大节点数限制，防止大扇出场景

        Returns:
            血缘图谱响应

        Raises:
            KeyError: 入口实体不存在时抛出
            ValueError: 不支持的实体类型时抛出
        """
        # 1. 验证入口实体存在，并获取根节点
        root_node = await self._resolve_entry_node(entity_type, entity_id)
        if root_node is None:
            raise KeyError(f"Entity not found: type={entity_type}, id={entity_id}")

        all_nodes: Dict[str, LineageNode] = {root_node.id: root_node}
        all_edges: List[LineageEdge] = []
        visited: Set[Tuple[str, str]] = {(entity_type, entity_id)}

        # 2. 上游遍历
        upstream_nodes, upstream_edges = await self._walk_upstream(
            entity_type, entity_id, visited, max_nodes
        )
        for n in upstream_nodes:
            all_nodes[n.id] = n
        all_edges.extend(upstream_edges)

        # 3. 下游遍历
        downstream_nodes, downstream_edges = await self._walk_downstream(
            entity_type, entity_id, visited, max_nodes
        )
        for n in downstream_nodes:
            all_nodes[n.id] = n
        all_edges.extend(downstream_edges)

        return LineageGraphResponse(
            nodes=list(all_nodes.values()),
            edges=all_edges,
            root_id=entity_id,
            root_type=entity_type,  # type: ignore
        )

    # ── 入口节点解析 ──────────────────────────────────────

    async def _resolve_entry_node(
        self, entity_type: str, entity_id: str
    ) -> Optional[LineageNode]:
        """根据类型和 ID 查询入口实体，构造节点。"""
        if entity_type == "requirement":
            doc = await TestRequirementDoc.find_one(
                {"req_id": entity_id, "is_deleted": False}
            )
            if not doc:
                return None
            return LineageNode(
                id=doc.req_id,
                type="requirement",
                label=doc.title,
                status=doc.status,
                subtitle=doc.req_id,
                meta={"category": doc.category, "priority": doc.priority},
            )

        if entity_type == "test_case":
            doc = await TestCaseDoc.find_one(
                {"case_id": entity_id, "is_deleted": False}
            )
            if not doc:
                return None
            return LineageNode(
                id=doc.case_id,
                type="test_case",
                label=doc.title,
                status=doc.status,
                subtitle=doc.case_id,
                meta={
                    "priority": doc.priority,
                    "lab_id": doc.lab_id,
                    "ref_req_id": doc.ref_req_id,
                },
            )

        if entity_type == "auto_case":
            doc = await AutomationTestCaseDoc.find_one(
                {"auto_case_id": entity_id, "is_deleted": False}
            )
            if not doc:
                return None
            return LineageNode(
                id=doc.auto_case_id,
                type="automation_case",
                label=doc.name,
                status=doc.status,
                subtitle=doc.auto_case_id,
                meta={
                    "framework": doc.framework,
                    "script_path": doc.script_path,
                    "dml_manual_case_id": doc.dml_manual_case_id,
                },
            )

        if entity_type == "task":
            doc = await ExecutionTaskDoc.find_one(
                {"task_id": entity_id, "is_deleted": False}
            )
            if not doc:
                return None
            return LineageNode(
                id=doc.task_id,
                type="task",
                label=f"Task {doc.task_id}",
                status=doc.overall_status,
                subtitle=f"{doc.schedule_type} | {doc.case_count} cases",
                meta={
                    "agent_id": doc.agent_id,
                    "overall_status": doc.overall_status,
                    "case_count": doc.case_count,
                },
            )

        if entity_type == "case_result":
            doc = await ExecutionTaskCaseDoc.find_one({"case_id": entity_id})
            if not doc:
                return None
            return LineageNode(
                id=doc.case_id,
                type="case_result",
                label=doc.case_snapshot.get("title") or doc.case_id,
                status=doc.status,
                subtitle=f"Task: {doc.task_id}",
                meta={
                    "task_id": doc.task_id,
                    "failure_message": doc.failure_message,
                    "started_at": str(doc.started_at) if doc.started_at else None,
                    "finished_at": str(doc.finished_at) if doc.finished_at else None,
                },
            )

        return None

    # ── 上游遍历 ──────────────────────────────────────────

    async def _walk_upstream(
        self,
        entity_type: str,
        entity_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """从入口节点朝 Requirement 方向遍历。"""
        all_nodes: List[LineageNode] = []
        all_edges: List[LineageEdge] = []
        resolver_name = self.UPSTREAM_RESOLVERS.get(entity_type)

        if resolver_name is None:
            return all_nodes, all_edges

        resolver = getattr(self, resolver_name)
        nodes, edges = await resolver(entity_id, visited, max_nodes)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

        # 如果上游还有节点，继续递归向上
        for node in nodes:
            key = (node.type, node.id)
            if key in visited:
                continue
            visited.add(key)
            sub_nodes, sub_edges = await self._walk_upstream(
                node.type, node.id, visited, max_nodes
            )
            all_nodes.extend(sub_nodes)
            all_edges.extend(sub_edges)

        return all_nodes, all_edges

    async def _resolve_task_upstream(
        self, task_id: str, visited: Set[Tuple[str, str]], max_nodes: int
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """Task -> AutoCase(s): 从 task 的 request_payload 中提取 auto_case_id。"""
        task_doc = await ExecutionTaskDoc.find_one(
            {"task_id": task_id, "is_deleted": False}
        )
        if not task_doc:
            return [], []

        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        payload = task_doc.request_payload or {}
        case_items = [
            c for c in payload.get("cases", []) if isinstance(c, dict) and c.get("auto_case_id")
        ]
        for item in case_items:
            auto_case_id = item["auto_case_id"]
            if (("automation_case", auto_case_id)) in visited:
                continue
            auto_doc = await AutomationTestCaseDoc.find_one(
                {"auto_case_id": auto_case_id, "is_deleted": False}
            )
            if auto_doc:
                nodes.append(
                    LineageNode(
                        id=auto_doc.auto_case_id,
                        type="automation_case",
                        label=auto_doc.name,
                        status=auto_doc.status,
                        subtitle=auto_doc.auto_case_id,
                        meta={"framework": auto_doc.framework},
                    )
                )
                edges.append(
                    LineageEdge(
                        source=auto_doc.auto_case_id,
                        target=task_id,
                        label="executed_as",
                    )
                )

        return nodes, edges

    async def _resolve_case_result_upstream(
        self, case_id: str, visited: Set[Tuple[str, str]], max_nodes: int
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """CaseResult -> Task: 查找执行该 case 的任务。"""
        case_doc = await ExecutionTaskCaseDoc.find_one({"case_id": case_id})
        if not case_doc:
            return [], []

        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        if ("task", case_doc.task_id) not in visited:
            task_doc = await ExecutionTaskDoc.find_one(
                {"task_id": case_doc.task_id, "is_deleted": False}
            )
            if task_doc:
                nodes.append(
                    LineageNode(
                        id=task_doc.task_id,
                        type="task",
                        label=f"Task {task_doc.task_id}",
                        status=task_doc.overall_status,
                        subtitle=f"{task_doc.case_count} cases",
                        meta={"agent_id": task_doc.agent_id},
                    )
                )
                edges.append(
                    LineageEdge(
                        source=case_id,
                        target=task_doc.task_id,
                        label="belongs_to",
                    )
                )

        return nodes, edges

    async def _resolve_auto_case_upstream(
        self,
        auto_case_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """AutoCase -> TestCase (via dml_manual_case_id) -> Requirement (via ref_req_id)。"""
        auto_doc = await AutomationTestCaseDoc.find_one(
            {"auto_case_id": auto_case_id, "is_deleted": False}
        )
        if not auto_doc:
            return [], []

        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        # AutoCase -> TestCase
        if ("test_case", auto_doc.dml_manual_case_id) not in visited:
            tc_doc = await TestCaseDoc.find_one(
                {"case_id": auto_doc.dml_manual_case_id, "is_deleted": False}
            )
            if tc_doc:
                nodes.append(
                    LineageNode(
                        id=tc_doc.case_id,
                        type="test_case",
                        label=tc_doc.title,
                        status=tc_doc.status,
                        subtitle=tc_doc.case_id,
                        meta={"ref_req_id": tc_doc.ref_req_id},
                    )
                )
                edges.append(
                    LineageEdge(
                        source=auto_case_id,
                        target=tc_doc.case_id,
                        label="links_to",
                    )
                )

        return nodes, edges

    async def _resolve_test_case_upstream(
        self,
        case_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """TestCase -> Requirement (via ref_req_id)。"""
        tc_doc = await TestCaseDoc.find_one(
            {"case_id": case_id, "is_deleted": False}
        )
        if not tc_doc:
            return [], []

        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        if tc_doc.ref_req_id and ("requirement", tc_doc.ref_req_id) not in visited:
            req_doc = await TestRequirementDoc.find_one(
                {"req_id": tc_doc.ref_req_id, "is_deleted": False}
            )
            if req_doc:
                nodes.append(
                    LineageNode(
                        id=req_doc.req_id,
                        type="requirement",
                        label=req_doc.title,
                        status=req_doc.status,
                        subtitle=req_doc.req_id,
                        meta={"category": req_doc.category, "priority": req_doc.priority},
                    )
                )
                edges.append(
                    LineageEdge(
                        source=req_doc.req_id,
                        target=tc_doc.case_id,
                        label="contains",
                    )
                )

        return nodes, edges

    # ── 下游遍历 ──────────────────────────────────────────

    async def _walk_downstream(
        self,
        entity_type: str,
        entity_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """从入口节点朝 Agent 方向遍历。"""
        all_nodes: List[LineageNode] = []
        all_edges: List[LineageEdge] = []
        resolver_name = self.DOWNSTREAM_RESOLVERS.get(entity_type)

        if resolver_name is None:
            return all_nodes, all_edges

        resolver = getattr(self, resolver_name)
        nodes, edges = await resolver(entity_id, visited, max_nodes)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

        for node in nodes:
            key = (node.type, node.id)
            if key in visited:
                continue
            visited.add(key)
            sub_nodes, sub_edges = await self._walk_downstream(
                node.type, node.id, visited, max_nodes
            )
            all_nodes.extend(sub_nodes)
            all_edges.extend(sub_edges)

        return all_nodes, all_edges

    async def _resolve_requirement_downstream(
        self,
        req_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """Requirement -> TestCase(s): 查找所有关联的测试用例。"""
        tc_docs = await (
            TestCaseDoc.find(
                {"ref_req_id": req_id, "is_deleted": False, "is_active": True}
            )
            .limit(max_nodes)
            .to_list()
        )

        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        for tc in tc_docs:
            if ("test_case", tc.case_id) in visited:
                continue
            nodes.append(
                LineageNode(
                    id=tc.case_id,
                    type="test_case",
                    label=tc.title,
                    status=tc.status,
                    subtitle=tc.case_id,
                    meta={"priority": tc.priority, "lab_id": tc.lab_id},
                )
            )
            edges.append(
                LineageEdge(
                    source=req_id,
                    target=tc.case_id,
                    label="contains",
                )
            )

        return nodes, edges

    async def _resolve_test_case_downstream(
        self,
        case_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """TestCase -> AutoCase(s), -> Task(s), -> CaseResult(s), -> Agent。"""
        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        # TestCase -> AutoCase
        auto_doc = await AutomationTestCaseDoc.find_one(
            {"dml_manual_case_id": case_id, "is_deleted": False}
        )
        if auto_doc and ("automation_case", auto_doc.auto_case_id) not in visited:
            nodes.append(
                LineageNode(
                    id=auto_doc.auto_case_id,
                    type="automation_case",
                    label=auto_doc.name,
                    status=auto_doc.status,
                    subtitle=auto_doc.auto_case_id,
                    meta={"framework": auto_doc.framework},
                )
            )
            edges.append(
                LineageEdge(
                    source=case_id,
                    target=auto_doc.auto_case_id,
                    label="automated_by",
                )
            )

        return nodes, edges

    async def _resolve_auto_case_downstream(
        self,
        auto_case_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """AutoCase -> Task(s) -> CaseResult(s) -> Agent。"""
        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        # AutoCase -> Task: 在所有未删除任务的 request_payload 中查找
        task_docs = await (
            ExecutionTaskDoc.find({"is_deleted": False})
            .sort("-created_at")
            .limit(max_nodes)
            .to_list()
        )
        for task_doc in task_docs:
            if ("task", task_doc.task_id) in visited:
                continue
            payload = task_doc.request_payload or {}
            case_items = payload.get("cases", [])
            matched = any(
                isinstance(c, dict) and c.get("auto_case_id") == auto_case_id
                for c in case_items
            )
            if not matched:
                continue

            nodes.append(
                LineageNode(
                    id=task_doc.task_id,
                    type="task",
                    label=f"Task {task_doc.task_id}",
                    status=task_doc.overall_status,
                    subtitle=f"{task_doc.case_count} cases",
                    meta={"agent_id": task_doc.agent_id},
                )
            )
            edges.append(
                LineageEdge(
                    source=auto_case_id,
                    target=task_doc.task_id,
                    label="executed_in",
                )
            )

        return nodes, edges

    async def _resolve_task_downstream(
        self,
        task_id: str,
        visited: Set[Tuple[str, str]],
        max_nodes: int,
    ) -> Tuple[List[LineageNode], List[LineageEdge]]:
        """Task -> CaseResult(s) -> Agent。"""
        nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        # Task -> CaseResult(s)
        case_docs = await (
            ExecutionTaskCaseDoc.find({"task_id": task_id})
            .sort("order_no")
            .limit(max_nodes)
            .to_list()
        )
        for case_doc in case_docs:
            if ("case_result", case_doc.case_id) in visited:
                continue
            nodes.append(
                LineageNode(
                    id=case_doc.case_id,
                    type="case_result",
                    label=case_doc.case_snapshot.get("title") or case_doc.case_id,
                    status=case_doc.status,
                    subtitle=f"#{case_doc.order_no}",
                    meta={
                        "failure_message": case_doc.failure_message,
                        "started_at": str(case_doc.started_at) if case_doc.started_at else None,
                        "finished_at": str(case_doc.finished_at) if case_doc.finished_at else None,
                    },
                )
            )
            edges.append(
                LineageEdge(
                    source=task_id,
                    target=case_doc.case_id,
                    label="has_result",
                )
            )

        # Task -> Agent
        task_doc = await ExecutionTaskDoc.find_one(
            {"task_id": task_id, "is_deleted": False}
        )
        if task_doc and task_doc.agent_id:
            if ("agent", task_doc.agent_id) not in visited:
                agent_doc = await ExecutionAgentDoc.find_one(
                    {"agent_id": task_doc.agent_id, "is_deleted": False}
                )
                if agent_doc:
                    nodes.append(
                        LineageNode(
                            id=agent_doc.agent_id,
                            type="agent",
                            label=agent_doc.hostname,
                            status=agent_doc.status,
                            subtitle=f"{agent_doc.ip} | {agent_doc.region}",
                            meta={
                                "ip": agent_doc.ip,
                                "region": agent_doc.region,
                                "is_online": agent_doc.is_online,
                            },
                        )
                    )
                    edges.append(
                        LineageEdge(
                            source=task_id,
                            target=agent_doc.agent_id,
                            label="runs_on",
                        )
                    )

        return nodes, edges
