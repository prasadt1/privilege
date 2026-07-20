"""Command-line surface for the local Privilege vault."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .service import PrivilegeService
from .store import DEFAULT_DB_PATH, VaultStore


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _set_mode(args)

    if args.command == "eval":
        return _run_eval(args)

    service = PrivilegeService(VaultStore(args.db))
    try:
        if args.command == "init-engagement":
            policy = json.loads(args.policy_file.read_text())
            _print({"engagement_id": service.create_engagement(args.name, policy)})
        elif args.command == "import":
            document_id = service.import_document(args.engagement, args.file.name, args.file.read_text())
            _print({"document_id": document_id})
        elif args.command == "preflight":
            result = service.preflight(args.engagement, args.document, args.task)
            _print(_preflight_json(result))
        elif args.command == "analyze":
            preflight = service.preflight(args.engagement, args.document, args.task)
            analysis = service.analyze(preflight)
            _print({"preflight": _preflight_json(preflight), "analysis": asdict(analysis)})
        elif args.command == "status":
            _print({**service.status(args.engagement), "documents": service.list_documents(args.engagement), "receipts": service.list_receipts(args.engagement)})
        elif args.command == "export-receipt":
            args.output.write_text(json.dumps(service.export_receipt(args.id), indent=2, sort_keys=True) + "\n")
            _print({"output": str(args.output)})
        else:  # pragma: no cover - argparse dispatch guarantees a command.
            parser.error("unknown command")
    finally:
        service.store.close()
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="privilege", description="Local engagement confidentiality preflight")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="local SQLite vault path")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true", help="use the offline mock client")
    mode.add_argument("--live", action="store_true", help="use the configured OpenAI model")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init-engagement", help="create an engagement from a JSON policy")
    init.add_argument("--name", required=True)
    init.add_argument("--policy-file", type=Path, required=True)

    import_document = commands.add_parser("import", help="import a local UTF-8 text document")
    import_document.add_argument("--engagement", required=True)
    import_document.add_argument("--file", type=Path, required=True)

    for name in ("preflight", "analyze"):
        command = commands.add_parser(name, help=f"{name} a local document")
        command.add_argument("--engagement", required=True)
        command.add_argument("--document", required=True)
        command.add_argument("--task", required=True)

    status = commands.add_parser("status", help="show safe engagement status")
    status.add_argument("--engagement", required=True)

    receipt = commands.add_parser("export-receipt", help="write a sanitized receipt JSON file")
    receipt.add_argument("--id", required=True)
    receipt.add_argument("--output", type=Path, required=True)

    evaluate = commands.add_parser("eval", help="run frozen evaluation scenarios")
    evaluate.add_argument("--output", type=Path, default=Path("eval/results.json"))
    return parser


def _set_mode(args: argparse.Namespace) -> None:
    if args.mock:
        os.environ["PRIVILEGE_MOCK"] = "1"
    elif args.live:
        os.environ.pop("PRIVILEGE_MOCK", None)


def _run_eval(args: argparse.Namespace) -> int:
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / "eval" / "run.py"), "--output", str(args.output)]
    if args.live:
        command.append("--live")
    return subprocess.run(command, check=False).returncode


def _preflight_json(result: Any) -> dict[str, object]:
    data = asdict(result)
    return data


def _print(data: dict[str, object]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))
