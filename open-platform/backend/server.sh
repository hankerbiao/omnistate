#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${DML_GATEWAY_PID_FILE:-$ROOT_DIR/.gateway_service.pid}"
LOG_DIR="${DML_GATEWAY_LOG_DIR:-$ROOT_DIR/logs}"
LOG_FILE="${DML_GATEWAY_STDOUT_LOG:-$LOG_DIR/gateway_service.log}"
PYTHON_BIN="${DML_GATEWAY_PYTHON:-$ROOT_DIR/.venv/bin/python}"
HOST="${DML_GATEWAY_HOST:-127.0.0.1}"
PORT="${DML_GATEWAY_PORT:-8820}"
UPSTREAMS="${DML_GATEWAY_UPSTREAMS:-http://127.0.0.1:8801}"

usage() {
  cat <<USAGE
Usage: ./server.sh {start|stop|restart|status|logs}

Environment overrides:
  DML_GATEWAY_HOST        default: 127.0.0.1
  DML_GATEWAY_PORT        default: 8820
  DML_GATEWAY_UPSTREAMS   default: http://127.0.0.1:8801
  DML_GATEWAY_PYTHON      default: ./backend/.venv/bin/python
  DML_GATEWAY_LOG_DIR     default: ./backend/logs
USAGE
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(cat "$PID_FILE")"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

ensure_python() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python executable not found: $PYTHON_BIN" >&2
    echo "Run dependency setup first, for example: cd $ROOT_DIR && uv sync --extra dev" >&2
    exit 1
  fi
}

start() {
  if is_running; then
    echo "gateway_service is already running (pid $(cat "$PID_FILE"), port $PORT)."
    return 0
  fi

  ensure_python
  mkdir -p "$LOG_DIR"

  cd "$ROOT_DIR"
  echo "Starting gateway_service on http://$HOST:$PORT ..."
  DML_GATEWAY_HOST="$HOST" \
  DML_GATEWAY_PORT="$PORT" \
  DML_GATEWAY_UPSTREAMS="$UPSTREAMS" \
    nohup "$PYTHON_BIN" -m gateway_service >>"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"

  sleep 1
  if is_running; then
    echo "gateway_service started (pid $(cat "$PID_FILE"))."
    echo "Log: $LOG_FILE"
  else
    echo "gateway_service failed to start. Recent log:" >&2
    tail -40 "$LOG_FILE" >&2 || true
    rm -f "$PID_FILE"
    exit 1
  fi
}

stop() {
  if ! is_running; then
    echo "gateway_service is not running."
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  echo "Stopping gateway_service (pid $pid) ..."
  kill "$pid"

  for _ in {1..20}; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      rm -f "$PID_FILE"
      echo "gateway_service stopped."
      return 0
    fi
    sleep 0.2
  done

  echo "gateway_service did not stop gracefully; sending SIGKILL."
  kill -9 "$pid" >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
  echo "gateway_service stopped."
}

status() {
  if is_running; then
    echo "gateway_service is running (pid $(cat "$PID_FILE"), url http://$HOST:$PORT)."
  else
    echo "gateway_service is not running."
    [[ ! -f "$PID_FILE" ]] || echo "Stale pid file: $PID_FILE"
    return 1
  fi
}

logs() {
  mkdir -p "$LOG_DIR"
  touch "$LOG_FILE"
  tail -n "${TAIL_LINES:-120}" "$LOG_FILE"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) logs ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
