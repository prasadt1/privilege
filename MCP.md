# Privilege MCP connector

Privilege already ships a **stdio MCP adapter**. Any client that speaks MCP —
including **OpenAI Codex**, Claude Desktop, and Cursor — can call it as a
preflight tool.

The adapter exposes only:

| Tool | Purpose |
|---|---|
| `preflight` | Attack a vaulted document; return Allow / Transform / Block + receipt id |
| `analyze` | Run analysis on an allowed sanitized payload (**no restored/raw text**) |
| `status` | Safe engagement status (no mappings, no raw documents) |

There is **no** tool to import raw text or dump mappings. That is intentional.

## Trust model (read this)

MCP does **not** make it safe to paste a raw client PDF into the cloud agent.

If the consultant hands the raw document to Codex/Claude/Cursor first, that
text has already left the machine. Privilege cannot undo that.

The correct flow:

1. Import the document into Privilege's **local vault** (CLI or local viewer).
2. Point the agent at Privilege via MCP.
3. The agent calls `preflight` / `analyze` with opaque `engagement_id` /
   `document_id` only.

## Quick install (developer path)

```bash
cd /path/to/privilege
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[mcp,files]"
```

### Codex / Cursor — `mcp.json` fragment

Replace the path with your clone. Use the venv Python so `mcp` is available.

```json
{
  "mcpServers": {
    "privilege": {
      "command": "/ABSOLUTE/PATH/TO/privilege/.venv/bin/python",
      "args": ["-m", "src.server_mcp", "--db", "/ABSOLUTE/PATH/TO/privilege/demo/demo-vault.sqlite3"],
      "env": {
        "PRIVILEGE_MOCK": "1"
      }
    }
  }
}
```

For a live attacker (needs `OPENAI_API_KEY`):

```json
{
  "mcpServers": {
    "privilege": {
      "command": "/ABSOLUTE/PATH/TO/privilege/.venv/bin/python",
      "args": ["-m", "src.server_mcp", "--db", "/ABSOLUTE/PATH/TO/HOME/.privilege/vault.sqlite3"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

### Claude Desktop

Same JSON shape under `mcpServers` in Claude's config file, then restart the app.

### Smoke-check without an agent

```bash
PRIVILEGE_MOCK=1 python -m src.server_mcp --db demo/demo-vault.sqlite3
```

The process waits on stdio (normal for MCP). Stop with Ctrl-C.

## Helper script

macOS: double-click or run [`install-mcp.command`](install-mcp.command) to print a
ready-to-paste config with paths filled in for this clone.

## Roadmap (not in this submission)

- **`.mcpb` / one-click desktop extension** — bundle Python so non-technical
  users install without editing JSON.
- **Directory listing** — submit to the platform MCP catalog after review.
- **Signed `.app` / `.exe`** — double-click Privilege with no system Python
  (needs packaging + notarization; separate from the engine).

The hard part for those is already done: the engine and the MCP adapter exist.
