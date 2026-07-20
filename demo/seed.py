"""Seed a synthetic engagement and replay the demo arc.

Written outside Codex after the Codex quota was exhausted; see README
"How this was built". All core logic it calls was built in Codex.

The arc is three individually-benign disclosures followed by one that
completes a mosaic. Per-prompt checking clears all four. Cumulative
checking is expected to act on the fourth.

Nothing here is real client data. "Northwind Freight" is invented.

    python demo/seed.py --mock          # no API key, no spend
    python demo/seed.py --live          # real GPT-5.6 attacker
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.service import PrivilegeService  # noqa: E402
from src.store import VaultStore  # noqa: E402


DEMO_DB = Path("/tmp/privilege-demo.sqlite3")

POLICY = {
    "protected_values": ["Northwind Freight", "Baltic corridor"],
    "aliases": {"Northwind": "Northwind Freight"},
    "abstract_rules": [
        "[VALUE_1] withdrawal from [VALUE_2] is protected until the client announces it",
    ],
    "allowed_purpose": "operating cost review",
}

DOCUMENT = (
    "Northwind Freight operates 14 depots. Baltic corridor volumes fell 22% "
    "year on year. Depot leases in that corridor expire in Q3. The board has "
    "not yet announced any change to the corridor."
)

# Each turn is a task an agent might plausibly ask. The first three are
# individually harmless. The fourth completes the picture.
TURNS = [
    "Summarize the depot cost structure.",
    "Which corridors show declining volume?",
    "When do the affected leases expire?",
    "Draft the corridor withdrawal announcement timeline.",
]


def _mode_banner(live: bool) -> str:
    return "LIVE (GPT-5.6 attacker)" if live else "MOCK (offline, no API spend)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed and replay the Privilege demo arc")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true", help="offline mock attacker, no API key needed")
    mode.add_argument("--live", action="store_true", help="real GPT-5.6 attacker, requires OPENAI_API_KEY")
    parser.add_argument("--db", type=Path, default=DEMO_DB)
    parser.add_argument("--keep", action="store_true", help="keep an existing demo vault instead of resetting")
    args = parser.parse_args(argv)

    live = args.live
    if not live:
        os.environ["PRIVILEGE_MOCK"] = "1"

    if args.db.exists() and not args.keep:
        args.db.unlink()

    service = PrivilegeService(VaultStore(args.db))
    try:
        engagement_id = service.create_engagement("Northwind operating review", POLICY)
        document_id = service.import_document(engagement_id, "engagement_notes.txt", DOCUMENT)

        print(f"\nPrivilege demo — {_mode_banner(live)}")
        print(f"vault: {args.db}")
        print(f"engagement: {engagement_id}\n")
        print("Raw document stays local. Only sanitized text is ever sent.\n")

        for index, task in enumerate(TURNS, start=1):
            result = service.preflight(engagement_id, document_id, task)
            marker = {"Allow": "ALLOW", "Transform": "TRANSFORM", "Block": "BLOCK"}.get(result.decision, result.decision.upper())
            print(f"[{index}] {task}")
            print(f"    decision        : {marker}")
            print(f"    prior disclosures: {result.prior_disclosure_count}")
            print(f"    repair rounds   : {result.rounds}")
            if result.inferred_claims:
                print(f"    attacker inferred: {'; '.join(result.inferred_claims)}")
            if result.error:
                print(f"    error           : {result.error}")
            print(f"    receipt         : {result.receipt_id}")

            if result.decision in {"Allow", "Transform"}:
                analysis = service.analyze(result)
                if analysis.output:
                    preview = analysis.output.strip().replace("\n", " ")[:120]
                    print(f"    restored locally : {preview}")
            print()

        status = service.status(engagement_id)
        print(f"sanitized disclosures sent to openai: {status['sanitized_disclosure_count']}")
        print(f"receipts written: {len(service.list_receipts(engagement_id))}")
        print(f"\nInspect receipts:  privilege --db {args.db} status --engagement {engagement_id}")
        print(f"Live viewer:       python -m src.server_http --db {args.db}\n")
    finally:
        service.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
