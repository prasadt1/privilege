from src.openai_client import DemoAttackClient
from src.pdf_out import text_to_pdf_bytes
from src.policy import EngagementPolicy
from src.service import PrivilegeService
from src.store import VaultStore


def test_text_to_pdf_bytes_is_pdf() -> None:
    raw = text_to_pdf_bytes("Hello [VALUE_1] corridor.", title="Test")
    assert raw.startswith(b"%PDF")
    assert len(raw) > 200


def test_export_safe_includes_pdf_and_findings(tmp_path) -> None:
    service = PrivilegeService(VaultStore(tmp_path / "vault.sqlite3"), DemoAttackClient())
    engagement_id = service.create_engagement(
        "Northwind operating review",
        EngagementPolicy(
            protected_values=["Northwind Freight", "Baltic corridor"],
            abstract_rules=[
                "[VALUE_1] withdrawing from [VALUE_2] is protected until the client announces it"
            ],
        ),
    )
    document_id = service.import_document(
        engagement_id,
        "brief.pdf",
        "Northwind Freight operates 14 depots. Baltic corridor volumes fell 22% year on year. "
        "Depot leases in that corridor expire in Q3. The board has not yet announced any change to the corridor.",
    )
    service.attest_document(engagement_id, document_id)

    package = service.export_safe(engagement_id, document_id)
    assert package["exportable"] is True
    assert package["decision"] == "Transform"
    assert package["repair_rounds"] == 1
    assert package["inferred_claims"]
    assert package["safe_pdf_base64"]
    assert "Acme" not in package["safe_text"]
    pdf = __import__("base64").b64decode(package["safe_pdf_base64"])
    assert pdf.startswith(b"%PDF")
    # Revised wording from DemoAttackClient.propose_rewrite
    assert "volumes changed versus the prior year" in package["safe_text"]
