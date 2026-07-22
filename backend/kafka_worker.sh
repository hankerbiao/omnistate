#!/usr/bin/env bash
# DML V4 Kafka worker process management for hosts without systemd.

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/.kafka_worker.pid"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/kafka_worker.log"
APP_MODULE="app.workers.kafka_worker_main"
STOP_TIMEOUT_SECONDS="${DML_STOP_TIMEOUT_SECONDS:-30}"

export DML_ENV="${DML_ENV:-production}"
export CONFIG_PATH="${CONFIG_PATH:-$PROJECT_ROOT/config/config.yaml}"
export SKIP_INDEX_SYNC="${SKIP_INDEX_SYNC:-1}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[x] uv environment is unavailable. Run ./deploy.sh install first." >&2
    exit 1
fi
PYTHON_BIN="$VENV_PYTHON"

info() { printf '[ok] %s\n' "$1"; }
warn() { printf '[!] %s\n' "$1" >&2; }
error() { printf '[x] %s\n' "$1" >&2; }

read_pid() {
    [[ -f "$PID_FILE" ]] && tr -dc '0-9' < "$PID_FILE"
}

is_running() {
    local pid="${1:-}"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

is_worker_process() {
    local pid="$1"
    local process_command
    process_command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    [[ "$process_command" == *"$APP_MODULE"* ]]
}

find_pid() {
    local pid
    pid="$(read_pid)"
    if is_running "$pid" && is_worker_process "$pid"; then
        printf '%s\n' "$pid"
        return 0
    fi
    [[ -f "$PID_FILE" ]] && rm -f "$PID_FILE"
    return 1
}

cmd_run() {
    cd "$PROJECT_ROOT"
    exec "$PYTHON_BIN" -m "$APP_MODULE"
}

cmd_start() {
    local pid
    if pid="$(find_pid)"; then
        warn "Kafka worker is already running (PID: $pid)"
        return 0
    fi

    mkdir -p "$LOG_DIR"
    nohup "$0" run >> "$LOG_FILE" 2>&1 &
    pid=$!
    printf '%s\n' "$pid" > "$PID_FILE"

    sleep 1
    if ! is_running "$pid"; then
        rm -f "$PID_FILE"
        error "Kafka worker exited during startup. Check $LOG_FILE"
        return 1
    fi
    info "Kafka worker started (PID: $pid, environment: $DML_ENV)"
    printf '     log: %s\n' "$LOG_FILE"
}

cmd_stop() {
    local pid
    if ! pid="$(find_pid)"; then
        warn "Kafka worker is not running"
        return 0
    fi

    printf 'Stopping Kafka worker (PID: %s)...\n' "$pid"
    kill -TERM "$pid" 2>/dev/null || true

    local checks=$((STOP_TIMEOUT_SECONDS * 2))
    local index
    for ((index = 0; index < checks; index++)); do
        if ! is_running "$pid"; then
            rm -f "$PID_FILE"
            info "Kafka worker stopped"
            return 0
        fi
        sleep 0.5
    done

    warn "Graceful stop timed out after ${STOP_TIMEOUT_SECONDS}s; sending SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
}

cmd_status() {
    local pid
    if pid="$(find_pid)"; then
        info "Kafka worker is running (PID: $pid)"
        return 0
    fi
    error "Kafka worker is not running"
    return 1
}

usage() {
    cat <<'EOF'
Usage: ./kafka_worker.sh {start|dev|run|stop|restart|status}

  start    Start the worker in production mode (background fallback)
  dev      Start the worker with the dev config overlay
  run      Run the worker in the foreground (used by systemd)
  stop     Gracefully stop the background worker
  restart  Restart the background worker
  status   Show background worker status
EOF
}

case "${1:-}" in
    start) DML_ENV=production; export DML_ENV; cmd_start ;;
    dev) DML_ENV=dev; export DML_ENV; cmd_start ;;
    run) cmd_run ;;
    stop) cmd_stop ;;
    restart) cmd_stop; sleep 1; cmd_start ;;
    status) cmd_status ;;
    *) usage; exit 1 ;;
esac
