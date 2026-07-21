import pytest

from src.policy import EngagementPolicy
from src.service import PrivilegeService
from src.store import VaultStore


class SafeClient:
    def __init__(self):
        self.infer_calls = 0

    def infer_claims(self, prior_payloads, candidate):
        self.infer_calls += 1
        return []

    def match_rules(self, inferred_claims, abstract_rules):
        return []

    def analyze(self, task, sanitized_doc):
        return "done"


def test_service_exposes_safe_status_and_receipt_export(tmp_path) -> None:
    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), SafeClient())
    engagement_id = service.create_engagement(
        "Private client",
        EngagementPolicy(
            protected_values=["Acme"],
            abstract_rules=["Acme plans are protected"],
            allowed_purpose="Review Acme strategy",
        ),
    )
    document_id = service.import_document(engagement_id, "notes", "Acme notes")
    service.attest_document(engagement_id, document_id)

    preflight = service.preflight(engagement_id, document_id, "review")
    analysis = service.analyze(preflight)
    status = service.status(engagement_id)
    receipt = service.export_receipt(analysis.receipt_id)

    assert "Private client" not in str(status)
    assert "Acme" not in str(status)
    assert status["allowed_purpose"] == "Review [VALUE_1] strategy"
    assert status["sanitized_disclosure_count"] == 1
    assert receipt["payload_json"]["outbound_sent"] is True


def test_export_safe_and_rehydrate_round_trip(tmp_path) -> None:
    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), SafeClient())
    engagement_id = service.create_engagement(
        "Private client",
        EngagementPolicy(protected_values=["Acme"], abstract_rules=["Acme plans are protected"]),
    )
    document_id = service.import_document(
        engagement_id, "notes", "Acme will close the Baltic corridor."
    )
    service.attest_document(engagement_id, document_id)

    package = service.export_safe(engagement_id, document_id)
    assert package["exportable"] is True
    assert package["decision"] == "Allow"
    assert "Acme" not in package["safe_text"]
    assert "[VALUE_1]" in package["safe_text"]
    assert package["mapping"]["[VALUE_1]"] == "Acme"
    assert service.status(engagement_id)["sanitized_disclosure_count"] == 1

    model_reply = "Recommendation: [VALUE_1] should delay the corridor decision."
    restored = service.rehydrate(engagement_id, model_reply)
    assert restored["restored_text"] == "Recommendation: Acme should delay the corridor decision."


def test_export_safe_blocks_when_attacker_matches(tmp_path) -> None:
    class BlockingClient:
        def infer_claims(self, prior_payloads, candidate):
            return ["exit planned"]

        def match_rules(self, inferred_claims, abstract_rules):
            return [{"rule": abstract_rules[0], "material": True, "reason": "hit"}]

        def analyze(self, task, sanitized_doc):
            raise AssertionError("analyze must not run on Block")

    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), BlockingClient())
    engagement_id = service.create_engagement(
        "Private client",
        EngagementPolicy(protected_values=["Acme"], abstract_rules=["Acme plans are protected"]),
    )
    document_id = service.import_document(engagement_id, "notes", "Acme notes")
    service.attest_document(engagement_id, document_id)

    package = service.export_safe(engagement_id, document_id)
    assert package["exportable"] is False
    assert package["decision"] == "Block"
    assert package["safe_text"] == ""
    assert package["mapping"] == {}
    assert service.status(engagement_id)["sanitized_disclosure_count"] == 0
    receipt = service.export_receipt(package["receipt_id"])
    assert receipt["payload_json"]["operator_attested"] is True
    assert receipt["payload_json"]["mode"] == "export_safe"


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
    service.attest_document(engagement_id, document_id)

    result = service.preflight(engagement_id, document_id, "Summarize.")
    assert result.decision == "Block"
    assert result.error == "PreflightError"
    assert result.final_payload == ""
    # The block is still auditable.
    assert len(service.list_receipts(engagement_id)) == 1


def test_preflight_refuses_unattested_document_before_attacker_runs(tmp_path) -> None:
    client = SafeClient()
    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), client)
    engagement_id = service.create_engagement(
        "Private client",
        EngagementPolicy(
            protected_values=["Private client"],
            abstract_rules=["Private client plans are protected"],
        ),
    )
    document_id = service.import_document(
        engagement_id,
        "brief.pdf",
        "Private client plans",
    )

    with pytest.raises(ValueError, match="attest"):
        service.export_safe(engagement_id, document_id)
    assert client.infer_calls == 0

    service.attest_document(engagement_id, document_id)
    package = service.export_safe(engagement_id, document_id)
    assert package["exportable"] is True
    receipt = service.export_receipt(package["receipt_id"])
    assert receipt["payload_json"]["operator_attested"] is True


def test_create_engagement_requires_policy_and_protects_display_name(tmp_path) -> None:
    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), SafeClient())

    with pytest.raises(ValueError, match="Client or project"):
        service.create_engagement(
            "",
            EngagementPolicy(
                protected_values=["Acme"],
                abstract_rules=["Acme plans are protected"],
            ),
        )
    with pytest.raises(ValueError, match="protected"):
        service.create_engagement(
            "Acme",
            EngagementPolicy(abstract_rules=["Acme plans are protected"]),
        )
    with pytest.raises(ValueError, match="inferable"):
        service.create_engagement(
            "Acme",
            EngagementPolicy(protected_values=["Acme"]),
        )

    engagement_id = service.create_engagement(
        "Acme",
        EngagementPolicy(
            protected_values=["Project Ember"],
            abstract_rules=["Project Ember plans are protected"],
        ),
    )
    policy = service.store.get_engagement(engagement_id).policy
    assert policy.protected_values == ["Project Ember", "Acme"]
