"""Run frozen Privilege scenarios with a deterministic mock or live OpenAI.

MockAttacker is a DETERMINISM/PLUMBING harness for CI only. Its keyword cues
mirror the frozen scenario vocabulary, so mock results are NOT evidence of
efficacy. Live mode delegates the unchanged workflow to GPT-5.6.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL_DIR))

from src.analyze import analyze_after_preflight
from src.openai_client import OpenAIClient
from src.policy import EngagementPolicy
from src.preflight import PreflightResult, run_preflight
from src.store import VaultStore

from scenarios import SCENARIOS


class MockAttacker:
    """CI-only determinism/plumbing harness, not an efficacy attacker.

    Its fixed keyword cues deliberately mirror the frozen scenario vocabulary.
    Do not interpret its scores as evidence that Privilege detects semantic
    disclosure risk; use committed live results for that limited evidence.
    """

    destination = "openai"
    model = "mock-attacker-v1"

    _PATTERNS = (
        (("withdrawal", "footprint", "margin"), "regional withdrawal"),
        (("sale", "data room", "buyer"), "sale process"),
        (("closure", "maintenance", "workforce"), "site closure"),
        (("launch", "channel", "embargoed"), "product launch"),
        (("migration", "dependency", "retirement"), "technology migration"),
        (("restructuring", "lease", "headcount"), "regional restructuring"),
        (("partnership", "procurement", "referral"), "commercial partnership"),
    )
    _GENERALIZATIONS = {
        "withdrawal": "coverage review",
        "sale": "commercial review",
        "closure": "site planning",
        "launch": "release planning",
        "migration": "transition",
        "restructuring": "organization planning",
        "partnership": "commercial coordination",
    }

    def infer_claims(self, prior_payloads: list[str], candidate: str) -> list[str]:
        corpus = " ".join([*prior_payloads, candidate]).lower()
        return [claim for cues, claim in self._PATTERNS if all(cue in corpus for cue in cues)]

    def match_rules(self, inferred_claims: list[str], abstract_rules: list[str]) -> list[dict[str, object]]:
        if not inferred_claims or not abstract_rules:
            return []
        return [
            {"claim": claim, "rule": abstract_rules[0], "material": True}
            for claim in inferred_claims
        ]

    def propose_rewrite(self, candidate: str, matched: list[dict[str, object]], preserve_facts: list[str]) -> str:
        rewritten = candidate
        for sensitive, general in self._GENERALIZATIONS.items():
            rewritten = rewritten.replace(sensitive, general)
        return rewritten

    def analyze(self, task: str, sanitized_doc: str) -> str:
        return sanitized_doc


def _client(live: bool) -> Any:
    return OpenAIClient() if live else MockAttacker()


def _turn_record(scenario_id: str, disclosure: dict[str, Any], result: PreflightResult) -> dict[str, object]:
    retained = all(value.lower() in result.final_payload.lower() for value in disclosure["must_retain"])
    return {
        "scenario": scenario_id,
        "turn": disclosure["turn"],
        "expected": disclosure["expected"],
        "decision": result.decision.lower(),
        "reveals_protected": disclosure["reveals_protected"],
        "attack_success_pre": result.rounds > 0 or result.decision == "Block",
        "attack_success_post": result.decision == "Block",
        "task_fact_retained": retained and result.decision != "Block",
        "payload_hash": __import__("hashlib").sha256(result.final_payload.encode()).hexdigest(),
        "rounds": result.rounds,
    }


def _run_scenario(scenario: dict[str, Any], *, cumulative: bool, live: bool) -> list[dict[str, object]]:
    with TemporaryDirectory() as directory:
        store = VaultStore(Path(directory) / "vault.sqlite3")
        engagement_id = store.create_engagement(scenario["id"], EngagementPolicy.from_dict(scenario["policy"]))
        client = _client(live)
        records: list[dict[str, object]] = []
        for disclosure in scenario["disclosures"]:
            document_id = store.import_document(engagement_id, f"turn-{disclosure['turn']}", disclosure["text"])
            result = run_preflight(engagement_id, document_id, f"Retain {', '.join(disclosure['must_retain'])}", store, client)
            records.append(_turn_record(scenario["id"], disclosure, result))
            if cumulative and result.decision in {"Allow", "Transform"}:
                analyze_after_preflight(result, store, client)
            if not cumulative:
                # Independent baseline: each next disclosure starts without a ledger.
                store = VaultStore(Path(directory) / f"turn-{disclosure['turn']}.sqlite3")
                engagement_id = store.create_engagement(scenario["id"], EngagementPolicy.from_dict(scenario["policy"]))
        return records


def _metrics(records: list[dict[str, object]]) -> dict[str, float]:
    protected = [record for record in records if record["reveals_protected"]]
    benign = [record for record in records if not record["reveals_protected"]]
    return {
        "leak_recall": _ratio(sum(record["decision"] != "allow" for record in protected), len(protected)),
        "false_block_rate": _ratio(sum(record["decision"] == "block" for record in benign), len(benign)),
        "attack_success_pre": _ratio(sum(bool(record["attack_success_pre"]) for record in protected), len(protected)),
        "attack_success_post": _ratio(sum(bool(record["attack_success_post"]) for record in protected), len(protected)),
        "task_fact_retention": _ratio(sum(bool(record["task_fact_retained"]) for record in records), len(records)),
        "expected_decision_agreement": _ratio(sum(record["decision"] == record["expected"] for record in records), len(records)),
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def run_evaluation(*, live: bool = False) -> dict[str, object]:
    """Run baseline and cumulative treatment, then verify deterministic replay."""
    baseline = [record for scenario in SCENARIOS for record in _run_scenario(scenario, cumulative=False, live=live)]
    treatment = [record for scenario in SCENARIOS for record in _run_scenario(scenario, cumulative=True, live=live)]
    replay = [record for scenario in SCENARIOS for record in _run_scenario(scenario, cumulative=True, live=live)]
    reproducible = sum(
        (record["decision"], record["payload_hash"], record["rounds"])
        == (again["decision"], again["payload_hash"], again["rounds"])
        for record, again in zip(treatment, replay, strict=True)
    )
    return {
        "mode": "live" if live else "mock",
        "scenario_count": len(SCENARIOS),
        "turn_count": len(treatment),
        "baseline": {"metrics": _metrics(baseline), "turns": baseline},
        "treatment": {
            "metrics": {**_metrics(treatment), "receipt_reproducibility": _ratio(reproducible, len(treatment))},
            "turns": treatment,
        },
        "limitations": [
            "MockAttacker is a DETERMINISM/PLUMBING CI harness only. Its keyword cues mirror scenario vocabulary; mock scores are NOT efficacy evidence.",
            "Live results depend on the configured OpenAI model and are not used to alter frozen labels.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run frozen Privilege evaluation scenarios")
    parser.add_argument("--live", action="store_true", help="Use OpenAI instead of the deterministic mock attacker")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    args = parser.parse_args(argv)
    results = run_evaluation(live=args.live)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
