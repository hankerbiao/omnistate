#!/usr/bin/env bash
# DML V4 API process management for hosts without systemd.

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/.server.pid"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/server.log"
APP_MODULE="app.main:app"
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

is_api_process() {
    local pid="$1"
    local process_command
    process_command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    [[ "$process_command" == *"$APP_MODULE"* ]]
}

find_pid() {
    local pid
    pid="$(read_pid)"
    if is_running "$pid" && is_api_process "$pid"; then
        printf '%s\n' "$pid"
        return 0
    fi
    [[ -f "$PID_FILE" ]] && rm -f "$PID_FILE"
    return 1
}

runtime_address() {
    "$PYTHON_BIN" -c \
        'from app.shared.config import get_settings; s = get_settings(); print(s.app.host, s.app.port)'
}

cmd_run() {
    local host port
    read -r host port < <(runtime_address)
    local args=("$APP_MODULE" --host "$host" --port "$port")
    if [[ "$DML_ENV" == "dev" || "$DML_ENV" == "development" ]]; then
        args+=(--reload)
    fi
    cd "$PROJECT_ROOT"
    exec "$PYTHON_BIN" -m uvicorn "${args[@]}"
}

cmd_start() {
    local pid
    if pid="$(find_pid)"; then
        warn "API is already running (PID: $pid)"
        return 0
    fi

    mkdir -p "$LOG_DIR"
    nohup "$0" run >> "$LOG_FILE" 2>&1 &
    pid=$!
    printf '%s\n' "$pid" > "$PID_FILE"

    sleep 1
    if ! is_running "$pid"; then
        rm -f "$PID_FILE"
        error "API exited during startup. Check $LOG_FILE"
        return 1
    fi
    info "API started (PID: $pid, environment: $DML_ENV)"
    printf '     log: %s\n' "$LOG_FILE"
}

cmd_stop() {
    local pid
    if ! pid="$(find_pid)"; then
        warn "API is not running"
        return 0
    fi

    printf 'Stopping API (PID: %s)...\n' "$pid"
    kill -TERM "$pid" 2>/dev/null || true

    local checks=$((STOP_TIMEOUT_SECONDS * 2))
    local index
    for ((index = 0; index < checks; index++)); do
        if ! is_running "$pid"; then
            rm -f "$PID_FILE"
            info "API stopped"
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
        info "API is running (PID: $pid)"
        return 0
    fi
    error "API is not running"
    return 1
}

usage() {
    cat <<'EOF'
Usage: ./server.sh {start|dev|run|stop|restart|status}

  start    Start the API in production mode (background fallback)
  dev      Start the API with the dev config overlay and hot reload
  run      Run the API in the foreground (used by systemd)
  stop     Gracefully stop the background API
  restart  Restart the background API
  status   Show background API status
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
