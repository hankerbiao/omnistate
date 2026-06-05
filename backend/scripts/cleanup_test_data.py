#!/usr/bin/env python3
"""一键清理集成测试残留在 MongoDB 中的垃圾数据。

清理范围（pytest tests/integration/ 写入的测试数据）：
  users            用户（test_tpm_*、user_test_*、@test.local 等）
  permissions      权限（test_perm_*、test.code.test_*）
  roles            角色（role_test_*）
  navigation       导航页（test_view_*、test_update_*、test_delete_*）
  catalog          Lab、测试用例、目录段（integration/prefix_/seg_）
  workflow         工作流事项、测试需求（Test Requirement test_* 等）

保留数据：
  - 用户：test_admin、seed 账号（admin/tpm/...）、集成复用账号（integ_*）
  - 角色：ADMIN、TPM、REVIEWER 等系统角色
  - Lab：DEFAULT、BIOS、DDR5、BMC 等预设 Lab

用法:
  cd backend
  python scripts/cleanup_test_data.py --dry-run          # 预览，不写入
  python scripts/cleanup_test_data.py                    # 执行清理
  python scripts/cleanup_test_data.py --only users,catalog
  python scripts/cleanup_test_data.py -v                 # 显示样例明细

数据库连接读取 config.yaml / 环境变量（settings.MONGO_URI）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for path in (ROOT, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.shared.db.config import settings
from integration_test_cleanup import ALL_MODULES, run_cleanup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean integration-test junk data from MongoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available modules: {', '.join(ALL_MODULES)}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report only; do not modify the database",
    )
    parser.add_argument(
        "--only",
        metavar="MODULES",
        help=f"Comma-separated modules to clean (default: all). Choices: {', '.join(ALL_MODULES)}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print sample records for each category",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=15,
        help="Max sample lines per category when --verbose (default: 15)",
    )
    args = parser.parse_args()

    modules = None
    if args.only:
        modules = [m.strip() for m in args.only.split(",") if m.strip()]

    print("Integration test data cleanup")
    print(f"  database : {settings.MONGO_DB_NAME}")
    print(f"  mongo    : {settings.MONGO_URI}")
    print(f"  mode     : {'dry-run' if args.dry_run else 'execute'}")
    print(f"  modules  : {', '.join(modules or ALL_MODULES)}")
    print()

    results = run_cleanup(
        modules,
        dry_run=args.dry_run,
        verbose=args.verbose,
        sample_limit=args.sample_limit,
    )

    print("Summary")
    print(f"  {'module':12} {'collection':22}  result")
    print(f"  {'-' * 12} {'-' * 22}  {'-' * 24}")
    total_found = 0
    total_affected = 0
    for r in results:
        print(r.summary_line(dry_run=args.dry_run))
        total_found += r.found
        total_affected += r.affected if not args.dry_run else 0

    print()
    if args.dry_run:
        print(f"Dry-run complete: {total_found} record(s) would be cleaned.")
    else:
        print(f"Done: {total_affected} record(s) cleaned ({total_found} matched).")


if __name__ == "__main__":
    main()
