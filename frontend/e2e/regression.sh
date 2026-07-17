#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  DML Sentio E2E 全量回归测试脚本
#
#  按推荐顺序分级运行，每级失败时可选继续或终止。
#  默认有头模式（显示浏览器窗口），方便观察运行过程。
#
#  使用方式：
#    bash e2e/regression.sh           # 有头模式运行全部
#    bash e2e/regression.sh --headed  # 有头模式（同默认）
#    bash e2e/regression.sh --headless # 无头模式
#    bash e2e/regression.sh --stop    # 任意失败时停止
#    bash e2e/regression.sh --ui      # 打开 Playwright UI 模式
# ════════════════════════════════════════════════════════════════

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# ── 参数解析 ────────────────────────────────────────────────
# 默认有头（config 中 headless: true，需传 --headed 覆盖）
HEADED=true
STOP_ON_FAIL=false
UI_MODE=false

for arg in "$@"; do
  case "$arg" in
    --headed)   HEADED=true   ;;
    --headless) HEADED=false  ;;
    --stop)     STOP_ON_FAIL=true ;;
    --ui)       UI_MODE=true    ;;
    --help)
      echo "用法: bash e2e/regression.sh [选项]"
      echo ""
      echo "选项:"
      echo "  --headed    有头模式（显示浏览器，默认有头）"
      echo "  --headless  无头模式"
      echo "  --stop      任意测试失败时停止（默认继续）"
      echo "  --ui        打开 Playwright UI 模式（交互式调试）"
      echo "  --help      显示此帮助"
      exit 0
      ;;
  esac
done

# ── 辅助函数 ────────────────────────────────────────────────
PASSED=0
FAILED=0
FAILED_FILES=""

run_group() {
  local group_name="$1"
  local spec_files="$2"

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  ▶ $group_name"
  echo "═══════════════════════════════════════════════════════════"

  local headless_flag=""
  if [ "$HEADED" = true ]; then
    headless_flag="--headed"
  fi

  # 为了兼容不同版本的 Playwright，用 --headed/--headed=false 的方式
  if npx playwright test $spec_files $headless_flag --reporter=list 2>&1; then
    echo "  ✅ $group_name 通过"
  else
    echo "  ❌ $group_name 失败"
    if [ "$STOP_ON_FAIL" = true ]; then
      echo "  ⛔ --stop 已设置，终止执行"
      exit 1
    fi
  fi
}

# ── UI 模式 ────────────────────────────────────────────────
if [ "$UI_MODE" = true ]; then
  echo "▶ 打开 Playwright UI 模式..."
  npx playwright test --ui
  exit 0
fi

# ── 信息 ────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          DML Sentio E2E 全量回归测试                     ║"
echo "╠══════════════════════════════════════════════════════════╣"
if [ "$HEADED" = true ]; then
  echo "║  模式: 有头 (headed)     config 中 headless 被 CLI 覆盖  ║"
else
  echo "║  模式: 无头 (headless)   使用 config 默认设置            ║"
fi
echo "║  目录: e2e/                                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ══════════════════════════════════════════════════════════════
#  第 1 级：路由守卫 + 页面冒烟（最快，3~10s）
# ══════════════════════════════════════════════════════════════
run_group "1/6  认证 + 冒烟"     "e2e/auth-flow.spec.ts e2e/smoke.spec.ts"

# ══════════════════════════════════════════════════════════════
#  第 2 级：导航核心 + 登录全套
# ══════════════════════════════════════════════════════════════
run_group "2/6  导航 + 登录"     "e2e/navigation.spec.ts e2e/login.spec.ts"

# ══════════════════════════════════════════════════════════════
#  第 3 级：UI 交互（主题、用户切换、角色权限）
# ══════════════════════════════════════════════════════════════
run_group "3/6  UI 交互"        "e2e/theming.spec.ts e2e/user-switch.spec.ts e2e/dashboard.spec.ts"

# ══════════════════════════════════════════════════════════════
#  第 4 级：独立页面验证（页面内容 + 搜索）
# ══════════════════════════════════════════════════════════════
run_group "4/6  页面验证"       "e2e/my-tasks.spec.ts e2e/profile.spec.ts e2e/search.spec.ts e2e/management-pages.spec.ts"

# ══════════════════════════════════════════════════════════════
#  第 5 级：简单 CRUD（项目、Lab、预制用例集、用户）
# ══════════════════════════════════════════════════════════════
run_group "5/6  简单 CRUD"      "e2e/projects.spec.ts e2e/catalog-labs.spec.ts e2e/collections.spec.ts e2e/users.spec.ts"

# ══════════════════════════════════════════════════════════════
#  第 6 级：复杂 CRUD（手工用例、需求+级联、执行计划向导）
# ══════════════════════════════════════════════════════════════
run_group "6/6  复杂 CRUD"      "e2e/testcases.spec.ts e2e/requirements.spec.ts e2e/execution-plans.spec.ts"

# ══════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🎯  全量回归测试完成                                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 生成完整 HTML 报告
echo "▶ 生成 HTML 报告..."
npx playwright test --reporter=html 2>/dev/null || true
echo ""
echo "▶ 查看报告: npx playwright show-report"
echo ""
