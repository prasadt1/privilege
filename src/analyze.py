"""Post-Allow analysis and local-only placeholder restoration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .preflight import PreflightResult
from .sanitize import restore
from .store import VaultStore


@dataclass(frozen=True)
class AnalysisResult:
    decision: str
    output: str | None
    receipt_id: str
    error: str | None = None


def analyze_after_preflight(preflight: PreflightResult, store: VaultStore, client: Any) -> AnalysisResult:
    """Send an allowed sanitized payload, then append it to the local ledger."""
    if preflight.decision not in {"Allow", "Transform"}:
        receipt_id = store.save_receipt(preflight.engagement_id, "Block", preflight.receipt_payload())
        return AnalysisResult("Block", None, receipt_id, "preflight did not allow analysis")
    try:
        sanitized_output = client.analyze(preflight.sanitized_task, preflight.final_payload)
        engagement = store.get_engagement(preflight.engagement_id)
        policy_mappings = engagement.policy.assign_placeholders()
        restore_mappings = {value: policy_mappings[value] for value in engagement.policy.protected_values}
        restore_mappings.update(store.get_mappings(preflight.engagement_id))
        output = restore(sanitized_output, restore_mappings)
        store.append_ledger(preflight.engagement_id, "openai", preflight.final_payload)
        receipt_id = store.save_receipt(
            preflight.engagement_id, preflight.decision,
            preflight.receipt_payload(outbound_sent=True, analysis_sent=True),
        )
        return AnalysisResult(preflight.decision, output, receipt_id)
    except Exception as error:
        receipt_id = store.save_receipt(preflight.engagement_id, "Block", preflight.receipt_payload())
        return AnalysisResult("Block", None, receipt_id, type(error).__name__)
