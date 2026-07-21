"""Fail-closed local preflight and repair loop for sanitized OpenAI payloads."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any

from .openai_client import PreflightError
from .sanitize import sanitize
from .store import VaultStore


MAX_REPAIR_ROUNDS = 2


@dataclass(frozen=True)
class PreflightResult:
    engagement_id: str
    document_id: str
    decision: str
    final_payload: str
    sanitized_task: str
    rounds: int
    inferred_claims: list[str]
    matched_rules: list[dict[str, object]]
    prior_disclosure_count: int
    error: str | None = None
    receipt_id: str | None = None

    def receipt_payload(self, *, outbound_sent: bool = False, analysis_sent: bool = False) -> dict[str, Any]:
        """An inspectable receipt without local mappings or raw input."""
        return {
            "engagement_id": self.engagement_id,
            "document_id": self.document_id,
            "destination": "openai",
            "decision": self.decision,
            "prior_disclosure_count": self.prior_disclosure_count,
            "sanitized_candidate_hash": sha256(self.final_payload.encode()).hexdigest(),
            "sanitized_candidate_preview": self.final_payload[:240],
            "inferred_claims": self.inferred_claims,
            "matched_rules": self.matched_rules,
            "repair_rounds": self.rounds,
            "final_outbound_payload": self.final_payload,
            "outbound_sent": outbound_sent,
            "analysis_sent": analysis_sent,
            "error": self.error,
        }


def run_preflight(engagement_id: str, document_id: str, task: str, store: VaultStore, client: Any) -> PreflightResult:
    """Sanitize, blind-attack, judge, and repair up to two times."""
    try:
        engagement = store.get_engagement(engagement_id)
        document = store.get_document(document_id)
        if document.engagement_id != engagement_id:
            raise PreflightError("document does not belong to engagement")
        mappings = {**engagement.policy.assign_placeholders(), **store.get_mappings(engagement_id)}
        sanitized_document = sanitize(document.raw_text, mappings).text
        sanitized_task = sanitize(task, mappings).text
        candidate = f"Task:\n{sanitized_task}\n\nDocument:\n{sanitized_document}"
        prior_payloads = [entry["payload"] for entry in store.list_ledger(engagement_id, "openai")]
        abstract_rules = engagement.policy.to_abstract_for_judge()
        rounds = 0
        claims: list[str] = []
        matches: list[dict[str, object]] = []
        # Keep the last material attack so Transform receipts still show what
        # the model found before the rewrite cleared it.
        attack_claims: list[str] = []
        attack_matches: list[dict[str, object]] = []
        while True:
            claims = client.infer_claims(prior_payloads, candidate)
            matches = client.match_rules(claims, abstract_rules)
            material = [match for match in matches if match["material"]]
            if material:
                attack_claims = list(claims)
                attack_matches = list(matches)
            if not material:
                result = PreflightResult(
                    engagement_id, document_id, "Transform" if rounds else "Allow", candidate,
                    sanitized_task, rounds,
                    attack_claims if rounds else claims,
                    attack_matches if rounds else matches,
                    len(prior_payloads),
                )
                return _save_preflight_receipt(store, result)
            if rounds >= MAX_REPAIR_ROUNDS:
                result = PreflightResult(
                    engagement_id, document_id, "Block", candidate, sanitized_task, rounds,
                    claims, matches, len(prior_payloads), "material disclosure remains after repairs"
                )
                return _save_preflight_receipt(store, result)
            # Re-apply local mappings to an untrusted model rewrite before a
            # later request can leave the device.
            candidate = sanitize(client.propose_rewrite(candidate, material, [sanitized_task]), mappings).text
            rounds += 1
    except Exception as error:
        result = PreflightResult(engagement_id, document_id, "Block", "", "", 0, [], [], 0, type(error).__name__)
        try:
            store.get_engagement(engagement_id)
            return _save_preflight_receipt(store, result)
        except Exception:
            pass
        return result


def _save_preflight_receipt(store: VaultStore, result: PreflightResult) -> PreflightResult:
    """Persist a receipt for Allow, Transform, and Block before analysis starts."""
    receipt_id = store.save_receipt(result.engagement_id, result.decision, result.receipt_payload())
    return replace(result, receipt_id=receipt_id)
