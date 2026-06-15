#!/bin/bash
#
# server.sh — DML V4 后端服务启停管理脚本
#
# Usage:
#   ./server.sh start     启动服务（后台运行）
#   ./server.sh stop      停止服务
#   ./server.sh restart   重启服务
#   ./server.sh status    查看服务状态

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_ROOT/.server.pid"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/server.log"
APP_MODULE="app.main:app"
HOST="0.0.0.0"
PORT="8801"

# 优先使用虚拟环境的 Python
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ -x "$VENV_PYTHON" ]]; then
    PYTHON_BIN="$VENV_PYTHON"
else
    PYTHON_BIN="$(command -v python3)"
fi

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

# 查找 uvicorn 主进程 PID（匹配端口和模块）
find_pid() {
    pgrep -f "uvicorn.*${APP_MODULE}.*${PORT}" 2>/dev/null | head -1
}

read_pid() {
    if [[ -f "$PID_FILE" ]]; then
        cat "$PID_FILE"
    fi
}

is_running() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

cmd_status() {
    local pid
    pid=$(find_pid)
    if [[ -n "$pid" ]]; then
        info "Server is running (PID: $pid)"
        # 同步 PID 文件
        echo "$pid" > "$PID_FILE"
    else
        if [[ -f "$PID_FILE" ]]; then
            warn "Stale PID file found, process not running"
            rm -f "$PID_FILE"
        fi
        error "Server is not running"
        return 1
    fi
}

cmd_start() {
    local pid
    pid=$(find_pid)
    if [[ -n "$pid" ]]; then
        warn "Server is already running (PID: $pid)"
        exit 1
    fi

    mkdir -p "$LOG_DIR"

    # 后台启动 uvicorn，端口通过 DML_APP_PORT 环境变量暴露给应用
    export DML_APP_PORT="$PORT"
    nohup "$PYTHON_BIN" -m uvicorn "$APP_MODULE" \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        >> "$LOG_FILE" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"
    info "Server started (PID: $new_pid)"
    echo "    Log: $LOG_FILE"

    sleep 1
    if ! is_running "$new_pid"; then
        warn "Server exited shortly after starting — check logs:"
        echo "    tail -n 20 $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

cmd_stop() {
    local pid
    pid=$(find_pid)

    if [[ -z "$pid" ]]; then
        error "Server is not running"
        rm -f "$PID_FILE"
        return
    fi

    echo "Stopping server (PID: $pid)..."

    # 先 SIGTERM 优雅停止
    kill "$pid" 2>/dev/null || true

    # 等待最多 5 秒
    local waited=0
    while is_running "$pid" && [[ $waited -lt 5 ]]; do
        sleep 0.5
        waited=$((waited + 1))
    done

    # 超时则强制 SIGKILL
    if is_running "$pid"; then
        warn "Force killing..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 0.5
    fi

    rm -f "$PID_FILE"
    info "Server stopped"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

main() {
    local action="${1:-}"
    case "$action" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        *)
            echo "Usage: $(basename "$0") {start|stop|restart|status}"
            echo ""
            echo "Commands:"
            echo "  start     Start the server (daemon mode)"
            echo "  stop      Stop the server"
            echo "  restart   Restart the server"
            echo "  status    Show server status"
            exit 1
            ;;
    esac
}

main "$@"
