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

from .intake import (
    SUPPORTED_SUFFIXES,
    DocumentExtractionError,
    UnsupportedDocumentError,
    extract_text,
)
from .openai_client import PreflightError
from .service import PrivilegeService
from .store import (
    DEFAULT_DB_PATH,
    UnknownDocumentError,
    UnknownEngagementError,
    VaultStore,
)


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
            document_id = service.import_document(args.engagement, args.file.name, extract_text(args.file))
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
        elif args.command == "export-safe":
            package = service.export_safe(args.engagement, args.document, args.task)
            if args.bundle is not None:
                args.bundle.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n")
            if package["exportable"]:
                if args.output is not None:
                    args.output.write_text(str(package["safe_text"]))
                if args.mapping is not None:
                    args.mapping.write_text(json.dumps(package["mapping"], indent=2, sort_keys=True) + "\n")
            summary = {
                "decision": package["decision"],
                "exportable": package["exportable"],
                "receipt_id": package["receipt_id"],
                "error": package["error"],
                "safe_chars": len(str(package["safe_text"])),
                "mapping_entries": len(package["mapping"]),
            }
            if args.output is not None:
                summary["output"] = str(args.output)
            if args.mapping is not None:
                summary["mapping"] = str(args.mapping)
            if args.bundle is not None:
                summary["bundle"] = str(args.bundle)
            _print(summary)
            if not package["exportable"]:
                return 2
        elif args.command == "rehydrate":
            text = args.file.read_text() if args.file is not None else sys.stdin.read()
            result = service.rehydrate(args.engagement, text)
            if args.output is not None:
                args.output.write_text(result["restored_text"])
                _print({"output": str(args.output), "chars": len(result["restored_text"])})
            else:
                print(result["restored_text"], end="" if result["restored_text"].endswith("\n") else "\n")
        else:  # pragma: no cover - argparse dispatch guarantees a command.
            parser.error("unknown command")
    except (DocumentExtractionError, UnsupportedDocumentError, PreflightError) as error:
        # Expected operator-facing failures: an unreadable file, an unsupported
        # format, or a missing credential. A stack trace would only obscure them.
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (UnknownEngagementError, UnknownDocumentError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as error:
        print(f"error: policy file is not valid JSON: {error}", file=sys.stderr)
        return 2
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
    import_document.add_argument(
        "--file", type=Path, required=True, help=f"local file ({', '.join(SUPPORTED_SUFFIXES)}), extracted on this machine"
    )

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

    export_safe = commands.add_parser(
        "export-safe",
        help="attack-verify and export a sanitized document for an external AI tool",
    )
    export_safe.add_argument("--engagement", required=True)
    export_safe.add_argument("--document", required=True)
    export_safe.add_argument(
        "--task",
        default=None,
        help="optional check task; default verifies export fitness, not a content question",
    )
    export_safe.add_argument("--output", type=Path, help="write the redacted document text")
    export_safe.add_argument("--mapping", type=Path, help="write placeholder→real mapping JSON")
    export_safe.add_argument("--bundle", type=Path, help="write the full export package JSON")

    rehydrate = commands.add_parser(
        "rehydrate",
        help="restore real names in pasted model output using local mappings",
    )
    rehydrate.add_argument("--engagement", required=True)
    rehydrate.add_argument("--file", type=Path, help="sanitized model reply; omit to read stdin")
    rehydrate.add_argument("--output", type=Path, help="write restored text; omit to print")

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


if __name__ == "__main__":
    raise SystemExit(main())
