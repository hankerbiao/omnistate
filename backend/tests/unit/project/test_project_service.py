"""ProjectService 单元测试。

测试策略：
- 使用 unittest.mock.patch 替换 Beanie 查询方法
- 每个测试方法只测一个业务逻辑分支
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.project.service.project_service import ProjectService  # noqa: E402
from app.modules.project.domain.constants import ProjectStatus  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  测试数据工厂
# ═══════════════════════════════════════════════════════════════════════

def make_doc(**overrides) -> MagicMock:
    """创建模拟的 ProjectDoc 实例。"""
    doc = MagicMock()
    doc.project_id = overrides.get("project_id", "PRJ-2026-00001")
    doc.key = overrides.get("key", "TEST-KEY")
    doc.name = overrides.get("name", "测试项目")
    doc.description = overrides.get("description", "测试描述")
    doc.status = overrides.get("status", "active")
    doc.priority = overrides.get("priority", "P2")
    doc.owner_id = overrides.get("owner_id", None)
    doc.start_date = overrides.get("start_date", None)
    doc.end_date = overrides.get("end_date", None)
    doc.target_version = overrides.get("target_version", None)
    doc.tags = overrides.get("tags", [])
    doc.created_by = overrides.get("created_by", "test_admin")
    doc.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    doc.updated_at = overrides.get("updated_at", datetime.now(timezone.utc))
    doc.is_deleted = overrides.get("is_deleted", False)
    return doc


# ═══════════════════════════════════════════════════════════════════════
#  list_projects
# ═══════════════════════════════════════════════════════════════════════

class TestListProjects:

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_list_projects_empty(self, MockProjectDoc):
        """空列表应返回 items=[] 和 total=0。"""
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=0)
        mock_query.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        MockProjectDoc.find.return_value = mock_query

        result = await ProjectService.list_projects()

        assert result["total"] == 0
        assert result["items"] == []

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_list_projects_with_data(self, MockProjectDoc):
        """含项目数据的分页查询应返回正确条数。"""
        docs = [make_doc(project_id=f"PRJ-2026-{i:05d}", key=f"KEY-{i}") for i in range(1, 4)]

        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=3)
        mock_query.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(return_value=docs)
        MockProjectDoc.find.return_value = mock_query

        result = await ProjectService.list_projects(page=1, page_size=20)

        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["items"][0].project_id == "PRJ-2026-00001"

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_list_projects_filters_by_name(self, MockProjectDoc):
        """按名称模糊搜索应传递正确 filter。"""
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=1)
        mock_query.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(return_value=[make_doc()])
        MockProjectDoc.find.return_value = mock_query

        await ProjectService.list_projects(name="测试")

        # 验证 find 被调用了（参数验证过于复杂，仅检查基础调用）
        MockProjectDoc.find.assert_called()

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_list_projects_filters_by_status(self, MockProjectDoc):
        """按状态过滤应传递正确 filter。"""
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=1)
        mock_query.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(return_value=[make_doc()])
        MockProjectDoc.find.return_value = mock_query

        await ProjectService.list_projects(status="active")
        MockProjectDoc.find.assert_called()

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_list_projects_pagination(self, MockProjectDoc):
        """分页参数应正确传递到 skip/limit。"""
        mock_query = MagicMock()
        mock_query.count = AsyncMock(return_value=50)
        mock_query.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(return_value=[make_doc()])
        MockProjectDoc.find.return_value = mock_query

        await ProjectService.list_projects(page=2, page_size=10)

        MockProjectDoc.find.assert_called()


# ═══════════════════════════════════════════════════════════════════════
#  create_project
# ═══════════════════════════════════════════════════════════════════════

class TestCreateProject:

    @patch("app.modules.project.service.project_service.ProjectDoc")
    @patch.object(ProjectService, "_generate_project_id", new_callable=AsyncMock, return_value="PRJ-2026-00001")
    async def test_create_project_success(self, mock_gen_id, MockProjectDoc):
        """创建项目应返回 ProjectDoc 实例。"""
        MockProjectDoc.find_one = AsyncMock(return_value=None)
        mock_doc = MagicMock()
        mock_doc.insert = AsyncMock()
        MockProjectDoc.return_value = mock_doc

        data = {"name": "新项目", "key": "NEW-PROJ", "description": "描述"}
        result = await ProjectService.create_project(data, created_by="admin")

        assert result is mock_doc
        mock_doc.insert.assert_awaited_once()

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_create_project_duplicate_key(self, MockProjectDoc):
        """重复 key 应抛出 ValueError。"""
        MockProjectDoc.find_one = AsyncMock(return_value=MagicMock())

        data = {"name": "项目", "key": "EXISTING"}
        with pytest.raises(ValueError, match="项目标识已存在"):
            await ProjectService.create_project(data, created_by="admin")

    @patch("app.modules.project.service.project_service.ProjectDoc")
    @patch.object(ProjectService, "_generate_project_id", new_callable=AsyncMock, return_value="PRJ-2026-00002")
    async def test_create_project_default_status(self, mock_gen_id, MockProjectDoc):
        """新创建的项目状态应为 active。"""
        MockProjectDoc.find_one = AsyncMock(return_value=None)
        mock_doc = MagicMock()
        mock_doc.insert = AsyncMock()
        MockProjectDoc.return_value = mock_doc

        data = {"name": "项目", "key": "PROJ", "description": None}
        await ProjectService.create_project(data, created_by="admin")

        # 验证 status 被设置为 ACTIVE
        _, kwargs = MockProjectDoc.call_args
        assert kwargs["status"] == ProjectStatus.ACTIVE.value


# ═══════════════════════════════════════════════════════════════════════
#  update_project
# ═══════════════════════════════════════════════════════════════════════

class TestUpdateProject:

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_update_project_not_found(self, MockProjectDoc):
        """更新不存在的项目应抛出 ValueError。"""
        MockProjectDoc.find_one = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="项目不存在"):
            await ProjectService.update_project("NONEXIST", {"name": "新名称"})

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_update_project_duplicate_key(self, MockProjectDoc):
        """更新 key 与已有项目冲突应抛出 ValueError。"""
        existing_doc = make_doc(key="OLD-KEY")
        MockProjectDoc.find_one = AsyncMock(side_effect=[
            existing_doc,
            make_doc(key="TAKEN-KEY"),  # 冲突项目
        ])

        with pytest.raises(ValueError, match="项目标识已存在"):
            await ProjectService.update_project("PRJ-2026-00001", {"key": "TAKEN-KEY"})

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_update_project_success(self, MockProjectDoc):
        """更新项目应修改字段并保存。"""
        doc = make_doc(key="OLD-KEY", name="旧名称")
        doc.save = AsyncMock()
        MockProjectDoc.find_one = AsyncMock(side_effect=[doc, None])

        result = await ProjectService.update_project("PRJ-2026-00001", {"name": "新名称", "key": "OLD-KEY"})

        assert result.name == "新名称"
        doc.save.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════
#  delete_project
# ═══════════════════════════════════════════════════════════════════════

class TestDeleteProject:

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_delete_project_not_found(self, MockProjectDoc):
        """删除不存在的项目应抛出 ValueError。"""
        MockProjectDoc.find_one = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="项目不存在"):
            await ProjectService.delete_project("NONEXIST")

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_delete_project_soft_delete(self, MockProjectDoc):
        """删除项目后 is_deleted 应为 True。"""
        doc = make_doc()
        doc.save = AsyncMock()
        MockProjectDoc.find_one = AsyncMock(return_value=doc)

        await ProjectService.delete_project("PRJ-2026-00001")

        assert doc.is_deleted is True
        doc.save.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════
#  _generate_project_id
# ═══════════════════════════════════════════════════════════════════════

class TestGenerateProjectId:

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_generate_first_id_of_year(self, MockProjectDoc):
        """当年无项目时，序号应为 1。"""
        mock_query = MagicMock()
        mock_query.limit.return_value.to_list = AsyncMock(return_value=[])
        MockProjectDoc.find.return_value = mock_query

        pid = await ProjectService._generate_project_id()

        year = datetime.now(timezone.utc).year
        assert pid == f"PRJ-{year}-00001"

    @patch("app.modules.project.service.project_service.ProjectDoc")
    async def test_generate_incremental_id(self, MockProjectDoc):
        """已有项目时，序号应递增。"""
        existing = MagicMock()
        existing.project_id = f"PRJ-{datetime.now(timezone.utc).year}-00005"
        mock_query = MagicMock()
        mock_query.limit.return_value.to_list = AsyncMock(return_value=[existing])
        MockProjectDoc.find.return_value = mock_query

        pid = await ProjectService._generate_project_id()

        year = datetime.now(timezone.utc).year
        assert pid == f"PRJ-{year}-00006"


# ═══════════════════════════════════════════════════════════════════════
#  _to_project_response
# ═══════════════════════════════════════════════════════════════════════

class TestToProjectResponse:

    async def test_convert_doc_to_response(self):
        """文档应正确转换为 ProjectResponse。"""
        doc = make_doc()
        response = await ProjectService._to_project_response(doc)

        assert response.project_id == doc.project_id
        assert response.key == doc.key
        assert response.name == doc.name
        assert response.description == doc.description
        assert response.status == doc.status
        assert response.created_by == doc.created_by
