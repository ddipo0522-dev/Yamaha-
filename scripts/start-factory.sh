#!/usr/bin/env bash
# scripts/start-factory.sh — Start Fusion Factory resiliently, independent of terminal/session
#
# Uses setsid + nohup to fully detach from the controlling terminal so services
# survive Codespace terminal/browser closure. Idempotent: safe to run multiple times.
#
# Usage:
#   bash scripts/start-factory.sh        # Start all services (Fusion + tunnel)
#   bash scripts/start-factory.sh fusion # Start only Fusion dashboard
#   bash scripts/start-factory.sh tunnel # Start only Cloudflare tunnel
#   bash scripts/start-factory.sh status # Check service health
#   bash scripts/start-factory.sh stop   # Stop all services gracefully
#
# No API keys or bearer tokens are printed, logged to stdout, or committed.
set -euo pipefail

# Ensure ~/bin is in PATH (cloudflared is installed there)
export PATH="$HOME/bin:$PATH"

WORKSPACE="/workspaces/Yamaha-"
LOG_DIR="$WORKSPACE/.fusion/logs"
FUSION_LOG="$LOG_DIR/fusion-dashboard.log"
TUNNEL_LOG="$LOG_DIR/cloudflared-tunnel.log"
HEALTH_LOG="$LOG_DIR/health-check.log"
PID_DIR="$WORKSPACE/.fusion/pids"
FUSION_PID_FILE="$PID_DIR/fusion.pid"
TUNNEL_PID_FILE="$PID_DIR/tunnel.pid"

mkdir -p "$LOG_DIR" "$PID_DIR"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$HEALTH_LOG"
}

is_port_listening() {
  local port="$1"
  curl -s -m 5 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$port/api/health" 2>/dev/null | grep -q "200" || return 1
  return 0
}

is_process_running() {
  local pid_file="$1"
  [ -f "$pid_file" ] || return 1
  local pid
  pid=$(cat "$pid_file" 2>/dev/null || true)
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

start_fusion() {
  log "=== Starting Fusion Dashboard ==="

  # If already running, skip
  if is_process_running "$FUSION_PID_FILE"; then
    log "Fusion already running (PID $(cat "$FUSION_PID_FILE"))"
    if is_port_listening 4040; then
      log "Fusion health check: OK on port 4040"
      return 0
    fi
    log "Fusion process exists but not responding; will restart"
    stop_fusion
  fi

  # Kill any stray fusion processes on port 4040
  pkill -f "fn dashboard" 2>/dev/null || true
  sleep 2

  cd "$WORKSPACE"

  # Start Fusion with bearer-token auth (NOT --no-auth), fully detached
  # setsid: new session, detaches from controlling terminal
  # nohup: ignore SIGHUP when terminal closes
  # Redirect all output to log file (never print token to stdout)
  setsid nohup fn dashboard \
    > "$FUSION_LOG" 2>&1 < /dev/null &
  local fusion_pid=$!
  echo "$fusion_pid" > "$FUSION_PID_FILE"

  log "Fusion dashboard starting (PID $fusion_pid), waiting for health check..."

  # Wait up to 120 seconds for Fusion to become healthy
  local elapsed=0
  while [ $elapsed -lt 120 ]; do
    if is_port_listening 4040; then
      log "Fusion health check: OK on port 4040"
      log "Fusion dashboard is running and authenticated"
      return 0
    fi
    sleep 5
    elapsed=$((elapsed + 5))
  done

  log "ERROR: Fusion dashboard did not become healthy within 120 seconds"
  log "See $FUSION_LOG for details"
  return 1
}

stop_fusion() {
  if is_process_running "$FUSION_PID_FILE"; then
    local pid
    pid=$(cat "$FUSION_PID_FILE")
    log "Stopping Fusion dashboard (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 3
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$FUSION_PID_FILE"
  fi
  pkill -f "fn dashboard" 2>/dev/null || true
}

start_tunnel() {
  log "=== Starting Cloudflare Quick Tunnel ==="

  # If already running, skip
  if is_process_running "$TUNNEL_PID_FILE"; then
    log "Cloudflare tunnel already running (PID $(cat "$TUNNEL_PID_FILE"))"
    return 0
  fi

  # Kill any stray cloudflared processes
  pkill -f cloudflared 2>/dev/null || true
  sleep 2

  # Start cloudflared detached, logging to file
  setsid nohup cloudflared tunnel --url http://localhost:4040 \
    > "$TUNNEL_LOG" 2>&1 < /dev/null &
  local tunnel_pid=$!
  echo "$tunnel_pid" > "$TUNNEL_PID_FILE"

  log "Cloudflare tunnel starting (PID $tunnel_pid), waiting for tunnel URL..."

  # Wait up to 60 seconds for tunnel URL to appear in log
  local elapsed=0
  while [ $elapsed -lt 60 ]; do
    if [ -f "$TUNNEL_LOG" ] && grep -q "trycloudflare.com" "$TUNNEL_LOG" 2>/dev/null; then
      log "Cloudflare tunnel URL detected in $TUNNEL_LOG"
      log "Tunnel is running"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done

  log "WARNING: Cloudflare tunnel URL not yet detected; check $TUNNEL_LOG"
  return 0
}

stop_tunnel() {
  if is_process_running "$TUNNEL_PID_FILE"; then
    local pid
    pid=$(cat "$TUNNEL_PID_FILE")
    log "Stopping Cloudflare tunnel (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 2
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$TUNNEL_PID_FILE"
  fi
  pkill -f cloudflared 2>/dev/null || true
}

show_status() {
  echo "=== Fusion Factory Status ==="
  echo ""

  echo "--- Fusion Dashboard ---"
  if is_process_running "$FUSION_PID_FILE"; then
    echo "  Process: running (PID $(cat "$FUSION_PID_FILE"))"
    if is_port_listening 4040; then
      echo "  Health: OK (port 4040 responding)"
    else
      echo "  Health: NOT RESPONDING"
    fi
  else
    echo "  Process: not running"
  fi

  echo ""
  echo "--- Cloudflare Tunnel ---"
  if is_process_running "$TUNNEL_PID_FILE"; then
    echo "  Process: running (PID $(cat "$TUNNEL_PID_FILE"))"
    if [ -f "$TUNNEL_LOG" ] && grep -q "trycloudflare.com" "$TUNNEL_LOG" 2>/dev/null; then
      echo "  Tunnel URL: detected in $TUNNEL_LOG"
    else
      echo  "  Tunnel URL: not yet detected"
    fi
  else
    echo "  Process: not running"
  fi

  echo ""
  echo "--- Log files ---"
  echo "  Fusion:  $FUSION_LOG"
  echo "  Tunnel:  $TUNNEL_LOG"
  echo "  Health:  $HEALTH_LOG"
}

case "${1:-start}" in
  start|"")
    start_fusion
    start_tunnel
    log "=== Startup complete ==="
    ;;
  fusion)
    start_fusion
    ;;
  tunnel)
    start_tunnel
    ;;
  status)
    show_status
    ;;
  stop)
    stop_tunnel
    stop_fusion
    log "=== All services stopped ==="
    ;;
  restart)
    stop_tunnel
    stop_fusion
    start_fusion
    start_tunnel
    log "=== Restart complete ==="
    ;;
  *)
    echo "Usage: $0 {start|fusion|tunnel|status|stop|restart}"
    exit 1
    ;;
esac
