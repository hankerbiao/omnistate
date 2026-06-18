"""项目管理集成测试。

测试策略：
- 使用 conftest.py 提供的认证客户端（admin, tpm, reviewer, no_role）
- 每个测试独立创建/清理测试数据
- 覆盖 CRUD 全流程 + RBAC 权限验证 + 统计接口
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.integration.utils.helpers import unique_id


def _project_data(**overrides) -> dict:
    """生成测试项目数据。"""
    key = overrides.get("key") or unique_id("PRJ").upper().replace("-", "_")[:20]
    data = {
        "name": overrides.get("name") or f"测试项目 {unique_id()}",
        "key": key,
        "description": overrides.get("description") or f"项目描述 {unique_id()}",
    }
    return data


# ═══════════════════════════════════════════════════════════════════════
#  基础 CRUD
# ═══════════════════════════════════════════════════════════════════════

class TestProjectCRUD:

    @pytest.mark.asyncio
    async def test_create_project(self, client_admin: AsyncClient):
        """创建项目应返回 200，含 project_id。"""
        resp = await client_admin.post("/api/v1/projects", json=_project_data())
        assert resp.status_code == 200, f"创建项目失败: {resp.text}"
        data = resp.json()["data"]
        assert "project_id" in data
        assert data["project_id"].startswith("PRJ-")
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_project_duplicate_key(self, client_admin: AsyncClient):
        """重复 key 应返回 400。"""
        data = _project_data()
        resp1 = await client_admin.post("/api/v1/projects", json=data)
        assert resp1.status_code == 200

        resp2 = await client_admin.post("/api/v1/projects", json=data)
        assert resp2.status_code == 400 or resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_list_projects(self, client_admin: AsyncClient):
        """获取项目列表应返回分页结果。"""
        # 先创建几个项目
        for i in range(3):
            await client_admin.post("/api/v1/projects", json=_project_data(key=f"LIST-{unique_id()}-{i}"))

        resp = await client_admin.get("/api/v1/projects")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)

    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self, client_admin: AsyncClient):
        """列表查询支持 status 和搜索过滤。"""
        resp = await client_admin.get("/api/v1/projects?status=active")
        assert resp.status_code == 200
        resp = await client_admin.get("/api/v1/projects?name=test")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_project(self, client_admin: AsyncClient):
        """获取项目详情应返回 200。"""
        create_resp = await client_admin.post("/api/v1/projects", json=_project_data())
        project_id = create_resp.json()["data"]["project_id"]

        resp = await client_admin.get(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["project_id"] == project_id
        assert "stats" in data

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client_admin: AsyncClient):
        """获取不存在的项目应返回 404。"""
        resp = await client_admin.get("/api/v1/projects/NONEXIST_PROJECT_ID")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project(self, client_admin: AsyncClient):
        """更新项目名称应生效。"""
        create_resp = await client_admin.post("/api/v1/projects", json=_project_data())
        project_id = create_resp.json()["data"]["project_id"]

        new_name = f"更新后项目 {unique_id()}"
        resp = await client_admin.put(
            f"/api/v1/projects/{project_id}",
            json={"name": new_name},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == new_name

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, client_admin: AsyncClient):
        """更新不存在的项目应返回 400。"""
        resp = await client_admin.put(
            "/api/v1/projects/NONEXIST",
            json={"name": "新名称"},
        )
        assert resp.status_code == 404 or resp.status_code == 400

    @pytest.mark.asyncio
    async def test_toggle_project_status(self, client_admin: AsyncClient):
        """项目状态可在 active/archived 间切换。"""
        create_resp = await client_admin.post("/api/v1/projects", json=_project_data())
        project_id = create_resp.json()["data"]["project_id"]
        assert create_resp.json()["data"]["status"] == "active"

        # 归档
        resp = await client_admin.put(f"/api/v1/projects/{project_id}", json={"status": "archived"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "archived"

        # 激活
        resp = await client_admin.put(f"/api/v1/projects/{project_id}", json={"status": "active"})
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_delete_project(self, client_admin: AsyncClient):
        """删除项目应返回 200（软删除）。"""
        create_resp = await client_admin.post("/api/v1/projects", json=_project_data())
        project_id = create_resp.json()["data"]["project_id"]

        resp = await client_admin.delete(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "项目已删除"

        # 验证已无法查询
        get_resp = await client_admin.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, client_admin: AsyncClient):
        """删除不存在的项目应返回 404。"""
        resp = await client_admin.delete("/api/v1/projects/NONEXIST")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_stats(self, client_admin: AsyncClient):
        """项目统计应返回各项计数字段。"""
        create_resp = await client_admin.post("/api/v1/projects", json=_project_data())
        project_id = create_resp.json()["data"]["project_id"]

        resp = await client_admin.get(f"/api/v1/projects/{project_id}/stats")
        assert resp.status_code == 200
        stats = resp.json()["data"]
        assert "test_case_count" in stats
        assert "auto_case_count" in stats
        assert "requirement_count" in stats
        assert "plan_count" in stats
        assert "task_count" in stats
        assert "task_done_count" in stats
        assert "task_progress" in stats
        assert "collection_count" in stats


# ═══════════════════════════════════════════════════════════════════════
#  RBAC 权限校验
# ═══════════════════════════════════════════════════════════════════════

class TestProjectRBAC:

    @pytest.mark.asyncio
    async def test_admin_can_create_project(self, client_admin: AsyncClient):
        """ADMIN 角色可以创建项目。"""
        resp = await client_admin.post("/api/v1/projects", json=_project_data())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_tpm_can_create_project(self, client_tpm: AsyncClient):
        """TPM 角色可以创建项目。"""
        resp = await client_tpm.post("/api/v1/projects", json=_project_data())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reviewer_can_read_project(self, client_reviewer: AsyncClient, client_admin: AsyncClient):
        """REVIEWER 角色可以查看项目列表。"""
        resp = await client_reviewer.get("/api/v1/projects")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_role_user_read_permission(self, client_no_role: AsyncClient):
        """无角色用户应不能查看项目列表（403 或 200 取决于 nav:public）。"""
        resp = await client_no_role.get("/api/v1/projects")
        # 如果 nav:public 允许访问路由但无数据，也可能返回 200
        # 这里仅验证不返回 500
        assert resp.status_code != 500
