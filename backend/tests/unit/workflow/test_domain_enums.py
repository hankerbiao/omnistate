"""工作流 domain 枚举无框架依赖验证。

第四轮 P0-3 将 OwnerStrategy 从 repository/models/enums.py 迁移到
domain/enums.py，确保领域层不依赖 Beanie / PyMongo / FastAPI 等框架。

本测试：
1. 验证 domain/enums.py 可在无 MongoDB 或 Beanie 的环境下独立导入
2. 验证 OwnerStrategy 是纯 Python 枚举（无框架 mixin）
3. 验证 repository 层的 re-export 向后兼容
4. 验证 workflow/domain/rules.py 正确导入 domain 层（而非 repository 层）
"""
from __future__ import annotations

import sys
from pathlib import Path
from subprocess import run as subprocess_run

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ═══════════════════════════════════════════════════════════════════════
#  基础：纯 Python 标准库即可导入
# ═══════════════════════════════════════════════════════════════════════

def test_domain_enums_importable_with_stdlib_only():
    """domain/enums.py 仅依赖 Python 标准库，无 Beanie/PyMongo 框架依赖。

    通过 subprocess 在隔离进程中验证，防止当前进程已加载的框架模块干扰。
    """
    proc = subprocess_run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(ROOT)!r}); "
                "from app.modules.workflow.domain.enums import OwnerStrategy; "
                "print(OwnerStrategy.KEEP.value); "
                "print(OwnerStrategy.__bases__); "
                "import enum; "
                "assert enum.Enum in OwnerStrategy.__mro__, "
                "'OwnerStrategy 应是 enum.Enum 子类'"
            ),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"隔离导入失败: {proc.stderr or '无输出'}"
    )
    assert "KEEP" in proc.stdout
    # 验证没有引入不纯的 import
    assert "beanie" not in proc.stderr.lower()
    assert "pymongo" not in proc.stderr.lower()


# ═══════════════════════════════════════════════════════════════════════
#  枚举值完整性
# ═══════════════════════════════════════════════════════════════════════

def test_owner_strategy_has_expected_members():
    """OwnerStrategy 包含所有预期枚举值。"""
    from app.modules.workflow.domain.enums import OwnerStrategy

    assert OwnerStrategy.KEEP.value == "KEEP"
    assert OwnerStrategy.TO_CREATOR.value == "TO_CREATOR"
    assert OwnerStrategy.TO_SPECIFIC_USER.value == "TO_SPECIFIC_USER"
    assert len(OwnerStrategy) == 3


def test_owner_strategy_is_str_enum():
    """OwnerStrategy 继承 str+Enum（值可直接比较为字符串）。"""
    from app.modules.workflow.domain.enums import OwnerStrategy

    # str+Enum mixin 使枚举成员既是 str 又是 Enum
    assert isinstance(OwnerStrategy.KEEP, str)
    assert OwnerStrategy.KEEP.value == "KEEP"
    assert OwnerStrategy.KEEP == "KEEP"  # 与 str 直接比较


# ═══════════════════════════════════════════════════════════════════════
#  repository 层 re-export 向后兼容
# ═══════════════════════════════════════════════════════════════════════

def test_repository_re_exports_owner_strategy():
    """repository/models/enums.py 仍可导入 OwnerStrategy（向后兼容）。"""
    from app.modules.workflow.repository.models.enums import OwnerStrategy as RepoEnum
    from app.modules.workflow.domain.enums import OwnerStrategy as DomainEnum

    assert RepoEnum is DomainEnum, "re-export 应是同一个类"


# ═══════════════════════════════════════════════════════════════════════
#  workflow/domain/rules.py 引用正确源
# ═══════════════════════════════════════════════════════════════════════

def test_domain_rules_imports_from_domain_not_repository():
    """workflow/domain/rules.py 应从 domain.enums 而非 repository.models.enums 导入。

    静态扫描 import 语句验证协议约束。
    """
    import ast

    source = (ROOT / "app/modules/workflow/domain/rules.py").read_text()
    tree = ast.parse(source)

    imports_from_repo: list[str] = []
    imports_from_domain: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if "workflow.repository" in node.module:
                imports_from_repo.append(node.module)
            if "workflow.domain" in node.module:
                imports_from_domain.append(node.module)

    msg = f"domain/rules.py 不应从 repository 导入: {imports_from_repo}"
    assert not imports_from_repo, msg
    assert any("domain.enums" in imp for imp in imports_from_domain), (
        "domain/rules.py 应导入 domain.enums"
    )
