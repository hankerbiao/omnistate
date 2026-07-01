"""审计日志查询服务。"""
from __future__ import annotations

from datetime import datetime
from typing import Any


from app.modules.audit.repository.models.audit_log import AuditLogDoc


class AuditLogService:
    """审计日志查询服务。"""

    @staticmethod
    async def list_logs(
        *,
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        method: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """分页查询审计日志。"""
        query: dict[str, Any] = {}
        if actor_id:
            query["actor_id"] = actor_id
        if resource_type:
            query["resource_type"] = resource_type
        if resource_id:
            query["resource_id"] = resource_id
        if action:
            query["action"] = action
        if method:
            query["method"] = method
        if start_time or end_time:
            query["created_at"] = {}
            if start_time:
                query["created_at"]["$gte"] = start_time
            if end_time:
                query["created_at"]["$lte"] = end_time

        total = await AuditLogDoc.find(query).count()
        skip = (page - 1) * page_size
        docs = (
            await AuditLogDoc.find(query)
            .sort("-created_at")
            .skip(skip)
            .limit(page_size)
            .to_list()
        )

        items = [
            {
                "id": str(doc.id),
                "actor_id": doc.actor_id,
                "username": doc.username,
                "role_ids": doc.role_ids,
                "client_ip": doc.client_ip,
                "request_id": doc.request_id,
                "method": doc.method,
                "path": doc.path,
                "query_params": doc.query_params,
                "action": doc.action,
                "resource_type": doc.resource_type,
                "resource_id": doc.resource_id,
                "request_body": doc.request_body,
                "status_code": doc.status_code,
                "response_summary": doc.response_summary,
                "duration_ms": doc.duration_ms,
                "created_at": doc.created_at,
            }
            for doc in docs
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_stats() -> dict[str, Any]:
        """获取审计日志统计信息。"""
        total = await AuditLogDoc.count()

        # 按 action 分组统计
        pipeline_action = [
            {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        action_results = await AuditLogDoc.aggregate(pipeline_action).to_list()
        by_action = {r["_id"]: r["count"] for r in action_results if r["_id"]}

        # 按 resource_type 分组统计
        pipeline_resource = [
            {"$group": {"_id": "$resource_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        resource_results = await AuditLogDoc.aggregate(pipeline_resource).to_list()
        by_resource = {r["_id"]: r["count"] for r in resource_results if r["_id"]}

        # Top 操作者
        pipeline_actors = [
            {"$group": {
                "_id": {"actor_id": "$actor_id", "username": "$username"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        actor_results = await AuditLogDoc.aggregate(pipeline_actors).to_list()
        top_actors = [
            {
                "actor_id": r["_id"]["actor_id"],
                "username": r["_id"]["username"],
                "count": r["count"],
            }
            for r in actor_results
        ]

        return {
            "total": total,
            "by_action": by_action,
            "by_resource_type": by_resource,
            "top_actors": top_actors,
        }
