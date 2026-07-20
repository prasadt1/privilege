"""Optional, thin stdio MCP adapter with no raw import or mapping tools."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import os
from pathlib import Path

from .service import PrivilegeService
from .store import DEFAULT_DB_PATH, VaultStore


def build_server(db_path: Path = DEFAULT_DB_PATH):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise RuntimeError("Install the optional MCP dependency with: pip install -e '.[mcp]'") from error

    service = PrivilegeService(VaultStore(db_path))
    mcp = FastMCP("privilege")

    @mcp.tool()
    def preflight(engagement_id: str, document_id: str, task: str) -> dict[str, object]:
        """Return a sanitized preflight result and receipt ID for opaque local IDs."""
        return asdict(service.preflight(engagement_id, document_id, task))

    @mcp.tool()
    def analyze(engagement_id: str, document_id: str, task: str) -> dict[str, object]:
        """Analyze an allowed payload without returning locally restored values."""
        result = service.preflight(engagement_id, document_id, task)
        analysis = service.analyze_sanitized(result)
        return {"preflight": asdict(result), "analysis": asdict(analysis)}

    @mcp.tool()
    def status(engagement_id: str) -> dict[str, object]:
        """Return safe status without raw text or mappings."""
        return service.status(engagement_id)

    return mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Privilege MCP adapter over stdio")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args(argv)
    if args.mock:
        os.environ["PRIVILEGE_MOCK"] = "1"
    build_server(args.db).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
