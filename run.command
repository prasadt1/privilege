#!/bin/bash
# Privilege — double-click launcher (macOS)
# Opens the local viewer in your browser. Requires Python 3.11+ on the machine.
# First run installs a local .venv (may take a minute).

set -euo pipefail
cd "$(dirname "$0")"

# Prefer python3.13 / 3.12 / 3.11 if present
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  osascript -e 'display dialog "Privilege needs Python 3.11 or newer.\n\nInstall from https://www.python.org/downloads/ then double-click again." buttons {"OK"} default button 1 with title "Privilege"'
  exit 1
fi

if [ ! -d .venv ]; then
  echo "Creating local virtualenv with $PYTHON…"
  "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -e ".[files]"

export PRIVILEGE_MOCK="${PRIVILEGE_MOCK:-}"
# Prefer demo vault when present so judges see real receipts without a key
DB="demo/demo-vault.sqlite3"
if [ ! -f "$DB" ]; then
  DB="${HOME}/.privilege/vault.sqlite3"
fi

# Free mock mode if no API key — viewer still works offline
if [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${PRIVILEGE_MOCK:-}" ]; then
  export PRIVILEGE_MOCK=1
fi

PORT=7077
URL="http://127.0.0.1:${PORT}"

# Start server in background, open browser, keep Terminal attached for logs/Ctrl-C
python -m src.server_http --db "$DB" --port "$PORT" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

# Wait until the port answers
for _ in $(seq 1 40); do
  if curl -sf "$URL/api/mode" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

open "$URL"
echo ""
echo "Privilege is running at $URL"
echo "Vault: $DB"
echo "Stop with Ctrl-C in this window."
wait "$SERVER_PID"
