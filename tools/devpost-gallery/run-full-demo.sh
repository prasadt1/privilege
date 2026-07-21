#!/usr/bin/env bash
# One-shot: start demo-attack server + record full PDF lifecycle (incl. live ChatGPT).
#
# Before first run (once):
#   cd tools/devpost-gallery && node setup-chatgpt-profile.mjs
#
# Then leave this running:
#   ./run-full-demo.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GALLERY="$ROOT/tools/devpost-gallery"
PORT="${PRIVILEGE_PORT:-7077}"
DB="${PRIVILEGE_DEMO_DB:-/tmp/privilege-pdf-demo.sqlite3}"
MODE="${CHATGPT_MODE:-auto}"

cd "$ROOT"
rm -f "$DB"

pid="$(lsof -ti ":$PORT" 2>/dev/null || true)"
if [[ -n "${pid}" ]]; then
  echo "Stopping process on :$PORT ($pid)"
  kill "$pid" || true
  sleep 1
fi

echo "Starting Privilege (mock + demo attack) on :$PORT"
PRIVILEGE_MOCK=1 PRIVILEGE_DEMO_ATTACK=1 \
  "$ROOT/.venv/bin/python" -m src.server_http --db "$DB" --mock --port "$PORT" \
  > /tmp/privilege-pdf-demo-server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:$PORT/" >/dev/null; then
    break
  fi
  sleep 0.25
done
if ! curl -sf "http://127.0.0.1:$PORT/" >/dev/null; then
  echo "Server failed to start. Log:"
  tail -40 /tmp/privilege-pdf-demo-server.log || true
  exit 1
fi
echo "Server up (pid $SERVER_PID). ChatGPT mode=$MODE"
echo "Chrome profile: ${CHROME_PROFILE:-$GALLERY/.chrome-profile}"

# Stale Playwright/Chrome from setup can hold the profile lock.
PROFILE_DIR="${CHROME_PROFILE:-$GALLERY/.chrome-profile}"
if pgrep -f "user-data-dir=${PROFILE_DIR}" >/dev/null 2>&1; then
  echo "Closing previous Chrome using the demo profile…"
  pkill -f "user-data-dir=${PROFILE_DIR}" 2>/dev/null || true
  sleep 1
  pkill -9 -f "user-data-dir=${PROFILE_DIR}" 2>/dev/null || true
  sleep 1
fi
rm -f "$PROFILE_DIR/SingletonLock" "$PROFILE_DIR/SingletonSocket" "$PROFILE_DIR/SingletonCookie" 2>/dev/null || true

cd "$GALLERY"
CHATGPT_MODE="$MODE" PRIVILEGE_URL="http://127.0.0.1:$PORT" node record-pdf-lifecycle.mjs

echo "Done → $ROOT/docs/media/privilege-pdf-lifecycle.mp4"
