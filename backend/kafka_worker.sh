#!/bin/bash
#
# kafka_worker.sh — DML V4 Kafka Worker 启停管理脚本
#
# Usage:
#   ./kafka_worker.sh start     启动 worker（后台运行）
#   ./kafka_worker.sh stop      停止 worker
#   ./kafka_worker.sh restart   重启 worker
#   ./kafka_worker.sh status    查看 worker 状态

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_ROOT/.kafka_worker.pid"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/kafka_worker.log"
APP_MODULE="app.workers.kafka_worker_main"

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

find_pid() {
    pgrep -f "${APP_MODULE}" 2>/dev/null | head -1
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

cmd_start() {
    local pid
    pid=$(find_pid)
    if [[ -n "$pid" ]]; then
        warn "Kafka Worker is already running (PID: $pid)"
        exit 1
    fi

    mkdir -p "$LOG_DIR"

    nohup "$PYTHON_BIN" -m "$APP_MODULE" \
        >> "$LOG_FILE" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"
    info "Kafka Worker started (PID: $new_pid)"
    echo "    Log: $LOG_FILE"

    sleep 1
    if ! is_running "$new_pid"; then
        warn "Kafka Worker exited shortly after starting — check logs:"
        echo "    tail -n 20 $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

cmd_stop() {
    local pid
    pid=$(find_pid)

    if [[ -z "$pid" ]]; then
        error "Kafka Worker is not running"
        rm -f "$PID_FILE"
        return
    fi

    echo "Stopping Kafka Worker (PID: $pid)..."

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
    info "Kafka Worker stopped"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_status() {
    local pid
    pid=$(find_pid)
    if [[ -n "$pid" ]]; then
        info "Kafka Worker is running (PID: $pid)"
        echo "$pid" > "$PID_FILE"
    else
        if [[ -f "$PID_FILE" ]]; then
            warn "Stale PID file found, process not running"
            rm -f "$PID_FILE"
        fi
        error "Kafka Worker is not running"
        return 1
    fi
}

cmd_dev() {
    info "Starting Kafka Worker in DEV mode (DML_ENV=dev)..."
    DML_ENV=dev cmd_start
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
        dev)
            cmd_dev
            ;;
        status)
            cmd_status
            ;;
        *)
            echo "Usage: $(basename "$0") {start|stop|restart|dev|status}"
            echo ""
            echo "Commands:"
            echo "  start     Start the Kafka Worker (daemon mode, production)"
            echo "  dev       Start the Kafka Worker in DEV mode (DML_ENV=dev)"
            echo "  stop      Stop the Kafka Worker"
            echo "  restart   Restart the Kafka Worker"
            echo "  status    Show Kafka Worker status"
            exit 1
            ;;
    esac
}

main "$@"
