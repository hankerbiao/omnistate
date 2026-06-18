"""
初始化默认项目数据。

运行方式：
    python app/init_projects.py                  # 仅创建默认项目
    python app/init_projects.py --migrate-existing  # 创建默认项目 + 迁移历史数据
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def init_default_project() -> str:
    """创建或获取默认项目，返回 project_id。"""
    from app.modules.project.repository.models import ProjectDoc

    existing = await ProjectDoc.find_one({"key": "DEFAULT", "is_deleted": False})
    if existing:
        print(f"[SKIP] 默认项目已存在: {existing.project_id} ({existing.key})")
        return existing.project_id

    # 生成 project_id
    from app.modules.project.service.project_service import ProjectService
    project_id = await ProjectService._generate_project_id()

    doc = ProjectDoc(
        project_id=project_id,
        key="DEFAULT",
        name="默认项目",
        description="系统自动创建的默认项目，用于承载未指定项目的历史数据。"
                     "建议创建正式项目后将数据重新分配到对应项目。",
        status="active",
    )
    await doc.insert()
    print(f"[CREATE] 默认项目已创建: {project_id} (DEFAULT)")
    return project_id


async def migrate_existing_data(project_id: str) -> None:
    """将现有无 project_ids 的历史数据关联到默认项目。"""
    from app.modules.project.domain.constants import PROJECT_RELATED_MODEL_PATHS

    total = 0
    for module_path, class_name in PROJECT_RELATED_MODEL_PATHS:
        try:
            import importlib
            module = importlib.import_module(module_path)
            model = getattr(module, class_name)
        except (ImportError, AttributeError):
            print(f"[WARN] 无法加载模型 {module_path}.{class_name}，跳过")
            continue

        result = await model.find({
            "is_deleted": False,
            "$or": [
                {"project_ids": {"$exists": False}},
                {"project_ids": []},
                {"project_ids": None},
            ],
        }).update_many({"$set": {"project_ids": [project_id]}})

        count = result.modified_count
        if count > 0:
            print(f"[MIGRATE] {class_name}: {count} 条数据已关联默认项目")
        else:
            print(f"[SKIP] {class_name}: 无需迁移")
        total += count

    print(f"\n[MIGRATE] 迁移完成，共处理 {total} 条数据")


async def main():
    # 连接数据库
    from app.shared.db.connection import get_database
    db = await get_database()

    # 注册 Beanie 模型
    from app.shared.infrastructure.bootstrap import initialize_beanie
    await initialize_beanie(db)

    # 创建默认项目
    project_id = await init_default_project()

    # 迁移历史数据
    if "--migrate-existing" in sys.argv:
        print("\n开始迁移历史数据...")
        await migrate_existing_data(project_id)
    else:
        print("\n提示: 传递 --migrate-existing 参数可迁移历史数据到默认项目")


if __name__ == "__main__":
    asyncio.run(main())
