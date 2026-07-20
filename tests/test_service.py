from src.policy import EngagementPolicy
from src.service import PrivilegeService
from src.store import VaultStore


class SafeClient:
    def infer_claims(self, prior_payloads, candidate):
        return []

    def match_rules(self, inferred_claims, abstract_rules):
        return []

    def analyze(self, task, sanitized_doc):
        return "done"


def test_service_exposes_safe_status_and_receipt_export(tmp_path) -> None:
    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), SafeClient())
    engagement_id = service.create_engagement(
        "Private client",
        EngagementPolicy(protected_values=["Acme"], abstract_rules=["Acme plans are protected"]),
    )
    document_id = service.import_document(engagement_id, "notes", "Acme notes")

    preflight = service.preflight(engagement_id, document_id, "review")
    analysis = service.analyze(preflight)
    status = service.status(engagement_id)
    receipt = service.export_receipt(analysis.receipt_id)

    assert "Private client" not in str(status)
    assert "Acme" not in str(status)
    assert status["sanitized_disclosure_count"] == 1
    assert receipt["payload_json"]["outbound_sent"] is True


def test_preflight_blocks_when_no_client_can_be_built(tmp_path) -> None:
    """A missing credential is a failure to check, so it must Block.

    Written outside Codex after quota exhaustion.
    """
    from src.openai_client import PreflightError
    from src.service import PrivilegeService
    from src.store import VaultStore

    class RefusingService(PrivilegeService):
        @property
        def client(self):
            raise PreflightError("OpenAI client is unavailable")

    service = RefusingService(VaultStore(tmp_path / "v.sqlite3"))
    engagement_id = service.create_engagement(
        "t", {"protected_values": ["Acme"], "abstract_rules": ["Acme exit is protected"], "allowed_purpose": "r"}
    )
    document_id = service.import_document(engagement_id, "n.txt", "Acme is exiting.")

    result = service.preflight(engagement_id, document_id, "Summarize.")
    assert result.decision == "Block"
    assert result.error == "PreflightError"
    assert result.final_payload == ""
    # The block is still auditable.
    assert len(service.list_receipts(engagement_id)) == 1
