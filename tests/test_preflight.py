import json

from src.analyze import analyze_after_preflight
from src.policy import EngagementPolicy
from src.preflight import MAX_REPAIR_ROUNDS, run_preflight
from src.store import VaultStore


class FakeClient:
    destination = "openai"

    def __init__(self, material_results: list[bool], output: str = "[VALUE_1] is ready") -> None:
        self.material_results = iter(material_results)
        self.infer_inputs: list[tuple[list[str], str]] = []
        self.rewrites = 0
        self.analyze_inputs: list[tuple[str, str]] = []
        self.output = output

    def infer_claims(self, prior_payloads, candidate):
        self.infer_inputs.append((prior_payloads, candidate))
        return ["a business claim"]

    def match_rules(self, inferred_claims, abstract_rules):
        return [{"claim": inferred_claims[0], "rule": abstract_rules[0], "material": next(self.material_results)}]

    def propose_rewrite(self, candidate, matched, preserve_facts):
        self.rewrites += 1
        return candidate.replace("confidential", "general")

    def analyze(self, task, sanitized_doc):
        self.analyze_inputs.append((task, sanitized_doc))
        return self.output


def make_vault(tmp_path):
    store = VaultStore(tmp_path / "vault.sqlite3")
    policy = EngagementPolicy(
        protected_values=["Acme Corp"],
        abstract_rules=["Acme Corp exit strategy is protected"],
        allowed_purpose="review",
    )
    engagement_id = store.create_engagement("Synthetic", policy)
    document_id = store.import_document(engagement_id, "brief", "Acme Corp confidential planning")
    return store, engagement_id, document_id


def test_preflight_reads_only_openai_ledger_and_does_not_append(tmp_path) -> None:
    store, engagement_id, document_id = make_vault(tmp_path)
    store.append_ledger(engagement_id, "other", "other destination")
    store.append_ledger(engagement_id, "openai", "prior sanitized payload")
    client = FakeClient([False])

    result = run_preflight(engagement_id, document_id, "Review Acme Corp", store, client)

    assert result.decision == "Allow"
    assert client.infer_inputs[0][0] == ["prior sanitized payload"]
    assert "Acme Corp" not in client.infer_inputs[0][1]
    assert "[VALUE_1]" in client.infer_inputs[0][1]
    assert len(store.list_ledger(engagement_id, "openai")) == 1


def test_transform_then_analyze_restores_locally_and_appends_after_send(tmp_path) -> None:
    store, engagement_id, document_id = make_vault(tmp_path)
    client = FakeClient([True, False])
    preflight = run_preflight(engagement_id, document_id, "Review Acme Corp", store, client)

    result = analyze_after_preflight(preflight, store, client)

    assert preflight.decision == "Transform"
    assert preflight.rounds == 1
    assert result.output == "Acme Corp is ready"
    assert len(client.analyze_inputs) == 1
    assert len(store.list_ledger(engagement_id, "openai")) == 1
    receipt = json.loads(store.get_receipt(result.receipt_id)["payload_json"])
    assert receipt["outbound_sent"] is True
    assert "Acme Corp" not in json.dumps(receipt)


def test_exhausted_repairs_block_and_save_sanitized_receipt(tmp_path) -> None:
    store, engagement_id, document_id = make_vault(tmp_path)
    client = FakeClient([True, True, True])

    result = run_preflight(engagement_id, document_id, "Review", store, client)

    assert result.decision == "Block"
    assert result.rounds == MAX_REPAIR_ROUNDS
    assert client.rewrites == MAX_REPAIR_ROUNDS
    assert store.list_ledger(engagement_id) == []
    receipts = store._connection.execute("SELECT payload_json FROM receipts").fetchall()
    assert len(receipts) == 1
    assert "Acme Corp" not in receipts[0]["payload_json"]


def test_remote_failure_blocks_without_ledger_append(tmp_path) -> None:
    store, engagement_id, document_id = make_vault(tmp_path)

    class FailingClient:
        def infer_claims(self, prior_payloads, candidate):
            raise RuntimeError("network failure")

    result = run_preflight(engagement_id, document_id, "Review", store, FailingClient())

    assert result.decision == "Block"
    assert store.list_ledger(engagement_id) == []
