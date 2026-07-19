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
