import pytest

from src.policy import EngagementPolicy
from src.store import UnknownEngagementError, VaultStore


def test_create_import_and_round_trip(tmp_path) -> None:
    store = VaultStore(tmp_path / "vault.sqlite3")
    engagement_id = store.create_engagement("Northstar", EngagementPolicy(allowed_purpose="review"))
    document_id = store.import_document(engagement_id, "notes", "Raw client notes")

    engagement = store.get_engagement(engagement_id)
    document = store.get_document(document_id)

    assert engagement.name == "Northstar"
    assert document.raw_text == "Raw client notes"
    assert document.engagement_id == engagement_id


def test_mappings_persist_and_ledger_and_receipts_are_rows(tmp_path) -> None:
    path = tmp_path / "vault.sqlite3"
    store = VaultStore(path)
    engagement_id = store.create_engagement("Northstar", {"allowed_purpose": "review"})
    store.upsert_mapping(engagement_id, "Amazon", "[CLIENT]")
    store.append_ledger(engagement_id, "openai", "[CLIENT] sanitized payload")
    receipt_id = store.save_receipt(engagement_id, "Allow", {"payload": "[CLIENT]"})
    store.close()

    reopened = VaultStore(path)
    assert reopened.get_mappings(engagement_id) == {"Amazon": "[CLIENT]"}
    assert reopened.list_ledger(engagement_id)[0]["destination"] == "openai"
    assert receipt_id.startswith("rcpt_")


def test_unknown_engagement_raises_cleanly(tmp_path) -> None:
    store = VaultStore(tmp_path / "vault.sqlite3")

    with pytest.raises(UnknownEngagementError, match="unknown engagement id"):
        store.import_document("eng_missing", "notes", "raw")
