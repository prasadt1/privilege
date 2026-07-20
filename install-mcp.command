#!/bin/bash
# Print a ready-to-paste MCP config for this Privilege clone.
# Does not modify your Codex/Cursor/Claude config files.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
DB_DEMO="$ROOT/demo/demo-vault.sqlite3"
DB_HOME="${HOME}/.privilege/vault.sqlite3"

if [ ! -x "$PY" ]; then
  echo "No .venv yet. Creating one and installing MCP extras…"
  PYTHON=""
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
  if [ -z "$PYTHON" ]; then
    echo "Need Python 3.11+. Install Python, then re-run."
    exit 1
  fi
  "$PYTHON" -m venv "$ROOT/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
if ! python -c "import mcp" >/dev/null 2>&1; then
  echo "Installing MCP extras into .venv…"
  python -m pip install -q -e ".[mcp,files]"
fi
if ! python -c "import mcp" >/dev/null 2>&1; then
  echo "Could not import mcp. Run: pip install -e \".[mcp,files]\""
  exit 1
fi

DB="$DB_DEMO"
if [ ! -f "$DB" ]; then
  DB="$DB_HOME"
fi

echo ""
echo "Paste this into your MCP client config (Codex / Cursor / Claude Desktop)."
echo "Then restart the client. Docs: MCP.md"
echo ""
cat <<EOF
{
  "mcpServers": {
    "privilege": {
      "command": "$PY",
      "args": ["-m", "src.server_mcp", "--db", "$DB"],
      "env": {
        "PRIVILEGE_MOCK": "1"
      }
    }
  }
}
EOF
echo ""
echo "For live GPT-5.6 attacks: remove PRIVILEGE_MOCK and set OPENAI_API_KEY in env."
echo "Remember: import documents into the local vault first — never hand raw client files to the cloud agent."
