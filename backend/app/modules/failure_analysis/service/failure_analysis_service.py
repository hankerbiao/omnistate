"""失效分析聚合查询服务。

聚合执行任务用例数据，生成失败模式分布、按代理统计、每日趋势、
不稳定测试检测和高频失败列表等分析结果。
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Counter, Dict, List, Optional

from app.modules.execution.repository.models.execution import (
    ExecutionAgentDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.failure_analysis.schemas.failure_analysis import (
    FailureAnalysisDashboard,
    FailureByAgent,
    FailureDailyTrend,
    FailurePatternSummary,
    FlakyTestCase,
    HighFrequencyFailure,
)
from app.modules.failure_analysis.service.pattern_classifier import FailurePatternClassifier
from app.shared.core.logger import log


class FailureAnalysisService:
    """失效分析服务，聚合执行数据生成分析结果。"""

    def _compute_cutoff(self, time_range: str) -> datetime:
        """根据时间范围字符串计算截止时间。"""
        days = int(time_range.rstrip("d"))
        return datetime.now(timezone.utc) - timedelta(days=days)

    def _build_case_id_set(self, failed_cases: List[ExecutionTaskCaseDoc]) -> List[str]:
        """从失败 case 列表中收集唯一的 case_id。"""
        seen: set[str] = set()
        result: list[str] = []
        for c in failed_cases:
            if c.case_id not in seen:
                seen.add(c.case_id)
                result.append(c.case_id)
        return result

    def _get_auto_case_id(self, case: ExecutionTaskCaseDoc) -> str:
        """从 case_snapshot 中提取 auto_case_id，兜底用 case_id。"""
        return case.case_snapshot.get("auto_case_id", case.case_id)

    async def get_dashboard(
        self,
        time_range: str = "30d",
        limit_flaky: int = 20,
        limit_high_freq: int = 20,
    ) -> FailureAnalysisDashboard:
        """查询失效分析仪表盘聚合数据。

        Args:
            time_range: 时间范围，如 "7d", "30d", "90d"。
            limit_flaky: 不稳定测试返回条数上限。
            limit_high_freq: 高频失败返回条数上限。

        Returns:
            FailureAnalysisDashboard 包含所有分析结果。
        """
        cutoff = self._compute_cutoff(time_range)

        # 1. 查询失败 case
        failed_cases = await self._query_failed_cases(cutoff)

        if not failed_cases:
            return FailureAnalysisDashboard(
                time_range=time_range,
                total_failures=0,
            )

        # 2. 模式分布
        pattern_distribution = await self._compute_pattern_distribution(failed_cases)

        # 3. 按代理统计
        by_agent = await self._compute_failure_by_agent(failed_cases)

        # 4. 每日趋势
        daily_trend = await self._compute_daily_trend(failed_cases, cutoff)

        # 5. 不稳定测试检测
        case_ids = self._build_case_id_set(failed_cases)
        flaky_tests = await self._detect_flaky_tests(case_ids, cutoff, limit_flaky)

        # 6. 高频失败
        high_frequency = await self._find_high_frequency_failures(
            failed_cases, limit_high_freq
        )

        return FailureAnalysisDashboard(
            time_range=time_range,
            total_failures=len(failed_cases),
            pattern_distribution=pattern_distribution,
            by_agent=by_agent,
            daily_trend=daily_trend,
            flaky_tests=flaky_tests,
            high_frequency_failures=high_frequency,
        )

    async def _query_failed_cases(
        self, cutoff: datetime
    ) -> List[ExecutionTaskCaseDoc]:
        """查询时间范围内所有失败/错误的用例。"""
        return await ExecutionTaskCaseDoc.find(
            {
                "status": {"$in": ["FAILED", "ERROR"]},
                "finished_at": {"$gte": cutoff},
            }
        ).sort(("-finished_at")).to_list()

    async def _compute_pattern_distribution(
        self, failed_cases: List[ExecutionTaskCaseDoc]
    ) -> List[FailurePatternSummary]:
        """对每个失败分类并统计模式分布。"""
        counter: Counter[str] = Counter()
        for case in failed_cases:
            pattern = FailurePatternClassifier.classify(case.failure_message)
            counter[pattern] += 1

        total = len(failed_cases) or 1
        return [
            FailurePatternSummary(
                pattern=p, count=c, percentage=round(c / total * 100, 1)
            )
            for p, c in counter.most_common()
        ]

    async def _compute_failure_by_agent(
        self, failed_cases: List[ExecutionTaskCaseDoc]
    ) -> List[FailureByAgent]:
        """按代理分组统计失败分布。"""
        # 收集所有关联的 task_id
        task_ids = list({c.task_id for c in failed_cases})
        tasks = await ExecutionTaskDoc.find(
            {"task_id": {"$in": task_ids}}
        ).to_list()
        task_map: Dict[str, ExecutionTaskDoc] = {t.task_id: t for t in tasks}

        # 收集所有 agent_id 并查询代理信息
        agent_ids = list({t.agent_id for t in tasks if t.agent_id})
        agents = await ExecutionAgentDoc.find(
            {"agent_id": {"$in": agent_ids}}
        ).to_list()
        agent_map: Dict[str, ExecutionAgentDoc] = {a.agent_id: a for a in agents}

        # 按 agent_id 分组统计失败模式
        from collections import defaultdict

        agent_groups: Dict[str, Counter[str]] = defaultdict(Counter)
        for case in failed_cases:
            task = task_map.get(case.task_id)
            agent_id = task.agent_id if task else None
            if not agent_id:
                continue
            pattern = FailurePatternClassifier.classify(case.failure_message)
            agent_groups[agent_id][pattern] += 1

        return [
            FailureByAgent(
                agent_id=agent_id,
                hostname=agent_map[agent_id].hostname if agent_id in agent_map else agent_id,
                failure_count=sum(groups.values()),
                pattern_breakdown=dict(groups.most_common()),
            )
            for agent_id, groups in agent_groups.items()
        ]

    async def _compute_daily_trend(
        self, failed_cases: List[ExecutionTaskCaseDoc], cutoff: datetime
    ) -> List[FailureDailyTrend]:
        """按日期分组统计每日失败趋势。"""
        from collections import defaultdict

        daily: Dict[str, Counter[str]] = defaultdict(Counter)
        for case in failed_cases:
            if not case.finished_at:
                continue
            date_key = case.finished_at.strftime("%Y-%m-%d")
            pattern = FailurePatternClassifier.classify(case.failure_message)
            daily[date_key][pattern] += 1

        # 补全天数（包含无失败数据的日期）
        current = cutoff.replace(tzinfo=timezone.utc) if cutoff.tzinfo else cutoff
        end = datetime.now(timezone.utc)
        result: list[FailureDailyTrend] = []
        while current <= end:
            date_key = current.strftime("%Y-%m-%d")
            if date_key in daily:
                result.append(
                    FailureDailyTrend(
                        date=date_key,
                        failure_count=sum(daily[date_key].values()),
                        patterns=dict(daily[date_key].most_common()),
                    )
                )
            else:
                result.append(
                    FailureDailyTrend(
                        date=date_key,
                        failure_count=0,
                        patterns={},
                    )
                )
            current += timedelta(days=1)

        return result

    async def _detect_flaky_tests(
        self, case_ids: List[str], cutoff: datetime, limit: int = 20
    ) -> List[FlakyTestCase]:
        """检测不稳定测试。

        算法：对每个 case，查询其在时间窗口内的全部执行记录，
        如果同时有 PASSED 和 FAILED 记录则视为不稳定，
        不稳定度 = min(通过次数, 失败次数) / 总次数。
        """
        pipeline = [
            {"$match": {
                "case_id": {"$in": case_ids},
                "finished_at": {"$gte": cutoff},
            }},
            {"$sort": {"finished_at": -1}},
            {"$group": {
                "_id": "$case_id",
                "statuses": {"$push": "$status"},
                "total": {"$sum": 1},
                "passed_count": {"$sum": {"$cond": [{"$eq": ["$status", "PASSED"]}, 1, 0]}},
                "failed_count": {"$sum": {"$cond": [{"$eq": ["$status", "FAILED"]}, 1, 0]}},
            }},
            {"$match": {"passed_count": {"$gt": 0}, "failed_count": {"$gt": 0}}},
            {"$sort": {"total": -1}},
            {"$limit": limit},
        ]

        rows = await ExecutionTaskCaseDoc.aggregate(
            pipeline=pipeline,
        ).to_list()

        if not rows:
            return []

        # resolve case names from the first matching case snapshot
        case_ids_found = [r["_id"] for r in rows]
        name_map: Dict[str, str] = {}
        auto_case_id_map: Dict[str, str] = {}
        if case_ids_found:
            samples = await ExecutionTaskCaseDoc.find(
                {"case_id": {"$in": case_ids_found}},
            ).limit(len(case_ids_found)).to_list()
            for s in samples:
                name_map[s.case_id] = s.case_snapshot.get(
                    "title", s.case_title_snapshot or s.case_id
                )
                auto_case_id_map[s.case_id] = s.case_snapshot.get(
                    "auto_case_id", s.case_id
                )

        flaky_tests: list[FlakyTestCase] = []
        for row in rows:
            cid = row["_id"]
            passed = row["passed_count"]
            failed = row["failed_count"]
            flaky_ratio = min(passed, failed) / max(row["total"], 1)
            # recent results: last 10
            recent = [
                {"status": s} for s in row["statuses"][:10]
            ]
            flaky_tests.append(FlakyTestCase(
                auto_case_id=auto_case_id_map.get(cid, cid),
                case_id=cid,
                name=name_map.get(cid, cid),
                total_runs=row["total"],
                flaky_ratio=round(flaky_ratio, 3),
                recent_results=recent,
            ))

        flaky_tests.sort(key=lambda x: x.flaky_ratio, reverse=True)
        return flaky_tests

    async def _find_high_frequency_failures(
        self, failed_cases: List[ExecutionTaskCaseDoc], limit: int = 20
    ) -> List[HighFrequencyFailure]:
        """找出高频失败用例。

        统计时间窗口内失败次数最多的用例，按次数降序排列。
        """
        from collections import Counter, defaultdict

        # auto_case_id → fail count, latest time, pattern counter
        counter: Counter[str] = Counter()
        latest: Dict[str, datetime] = {}
        pattern_counter: Dict[str, Counter[str]] = defaultdict(Counter)

        for case in failed_cases:
            auto_id = self._get_auto_case_id(case)
            counter[auto_id] += 1
            pattern = FailurePatternClassifier.classify(case.failure_message)
            pattern_counter[auto_id][pattern] += 1
            if case.finished_at:
                key = auto_id
                if key not in latest or case.finished_at > latest[key]:
                    latest[key] = case.finished_at

        # 取 top N
        top_ids = [acid for acid, _ in counter.most_common(limit)]
        if not top_ids:
            return []

        # resolve names from task_case snapshots
        name_map: Dict[str, str] = {}
        auto_id_samples = await ExecutionTaskCaseDoc.find(
            {"case_snapshot.auto_case_id": {"$in": top_ids}},
        ).limit(len(top_ids)).to_list()
        for s in auto_id_samples:
            acid = s.case_snapshot.get("auto_case_id", s.case_id)
            if acid not in name_map:
                name_map[acid] = s.case_snapshot.get(
                    "title", s.case_title_snapshot or acid
                )

        result: list[HighFrequencyFailure] = []
        for auto_id in top_ids:
            pc = pattern_counter[auto_id]
            dominant = pc.most_common(1)[0][0] if pc else "UNKNOWN"
            result.append(HighFrequencyFailure(
                auto_case_id=auto_id,
                case_id="",  # 从 auto_id 反向查 manual case_id 需要额外查询
                name=name_map.get(auto_id, auto_id),
                failure_count=counter[auto_id],
                dominant_pattern=dominant,
                latest_failure_at=latest.get(auto_id),
                avg_duration_sec=None,
            ))

        return result

    # ─────────────────────────────────────────────────────────────────
    #  AI 根因分析辅助：跨模块查询测试用例
    # ─────────────────────────────────────────────────────────────────

    async def fetch_case_for_ai_analysis(self, case_id: str) -> Optional[Dict[str, Any]]:
        """按 case_id 查询测试用例的标题与步骤，供 AI 根因分析使用。

        将对 test_specs.repository 的跨模块访问收敛在 service 层，
        避免 API 层直接穿透到其他模块的 repository。
        """
        if not case_id:
            return None
        try:
            from app.modules.test_specs.repository.models.test_case import TestCaseDoc
            doc = await TestCaseDoc.find_one(
                TestCaseDoc.case_id == case_id,
                TestCaseDoc.is_deleted == False,  # noqa: E712
            )
            if not doc:
                return None
            steps = []
            if doc.steps:
                for s in doc.steps:
                    steps.append({
                        "step_id": s.step_id,
                        "name": s.name,
                        "action": s.action,
                        "expected": s.expected,
                    })
            return {
                "case_title": doc.title or "",
                "steps_json": json.dumps(steps, ensure_ascii=False, indent=2),
            }
        except Exception as e:
            log.warning("Failed to fetch test case {}: {}", case_id, e)
            return None
