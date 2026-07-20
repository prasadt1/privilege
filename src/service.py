"""Shared local API for future CLI, web, and MCP surfaces."""

from __future__ import annotations

from dataclasses import replace
import json
from typing import Any

from .analyze import AnalysisResult, analyze_after_preflight
from .openai_client import PreflightError, client_from_environment
from .policy import EngagementPolicy
from .preflight import PreflightResult, run_preflight
from .store import DEFAULT_DB_PATH, VaultStore


class PrivilegeService:
    def __init__(self, store: VaultStore | None = None, client: Any | None = None) -> None:
        self.store = store or VaultStore(DEFAULT_DB_PATH)
        self._client = client

    @property
    def client(self) -> Any:
        """Build the remote client on first use.

        Creating an engagement, importing a document, and reading status are
        entirely local. Constructing them must not require an API key, so the
        client is resolved only when something is actually about to be sent.
        """
        if self._client is None:
            self._client = client_from_environment()
        return self._client

    def create_engagement(self, name: str, policy: EngagementPolicy | dict[str, Any]) -> str:
        return self.store.create_engagement(name, policy)

    def import_document(self, engagement_id: str, title: str, raw_text: str) -> str:
        return self.store.import_document(engagement_id, title, raw_text)

    def preflight(self, engagement_id: str, document_id: str, task: str) -> PreflightResult:
        try:
            client = self.client
        except PreflightError as error:
            # Resolving the client is part of the check. Failing to build one
            # is a failure to check, which must Block like any other error
            # rather than escape as an exception.
            return self._blocked_before_check(engagement_id, document_id, type(error).__name__)
        return run_preflight(engagement_id, document_id, task, self.store, client)

    def _blocked_before_check(self, engagement_id: str, document_id: str, error: str) -> PreflightResult:
        result = PreflightResult(engagement_id, document_id, "Block", "", "", 0, [], [], 0, error)
        try:
            receipt_id = self.store.save_receipt(engagement_id, result.decision, result.receipt_payload())
        except Exception:
            # An unknown engagement cannot carry a receipt. The Block stands.
            return result
        # Surface the id so the caller can export the receipt for this Block.
        return replace(result, receipt_id=receipt_id)

    def analyze(self, preflight: PreflightResult) -> AnalysisResult:
        return analyze_after_preflight(preflight, self.store, self.client)

    def analyze_sanitized(self, preflight: PreflightResult) -> AnalysisResult:
        """MCP-safe analysis variant that never returns locally restored values."""
        return analyze_after_preflight(preflight, self.store, self.client, restore_output=False)

    def status(self, engagement_id: str) -> dict[str, object]:
        """An MCP-safe view without raw document text or mappings."""
        engagement = self.store.get_engagement(engagement_id)
        return {
            "engagement_id": engagement.id,
            "abstract_rules": engagement.policy.to_abstract_for_judge(),
            "allowed_purpose": engagement.policy.allowed_purpose,
            "strictness": engagement.policy.strictness,
            "sanitized_disclosure_count": len(self.store.list_ledger(engagement_id, "openai")),
        }

    def export_receipt(self, receipt_id: str) -> dict[str, object]:
        receipt = self.store.get_receipt(receipt_id)
        return {**receipt, "payload_json": json.loads(receipt["payload_json"])}

    def list_documents(self, engagement_id: str) -> list[dict[str, str]]:
        return self.store.list_documents(engagement_id)

    def list_receipts(self, engagement_id: str) -> list[dict[str, object]]:
        receipts = self.store.list_receipts(engagement_id)
        return [{**receipt, "payload_json": json.loads(receipt["payload_json"])} for receipt in receipts]
