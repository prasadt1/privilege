"""CLI surface tests.

Written outside Codex after the Codex quota was exhausted; see README
"How this was built". Replaces a Session 1 test that asserted the earlier
placeholder CLI, which Session 4 superseded with subcommands.
"""

import json

import pytest

from src import cli


def test_parser_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        cli.main([])


def test_init_engagement_and_import_round_trip(tmp_path, capsys) -> None:
    db = tmp_path / "vault.sqlite3"
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(
        json.dumps(
            {
                "protected_values": ["Northwind Freight"],
                "abstract_rules": ["[VALUE_1] restructuring is protected"],
                "allowed_purpose": "operating review",
            }
        )
    )

    assert cli.main(["--mock", "--db", str(db), "init-engagement", "--name", "acme", "--policy-file", str(policy_file)]) == 0
    engagement_id = json.loads(capsys.readouterr().out)["engagement_id"]

    document = tmp_path / "notes.txt"
    document.write_text("Northwind Freight is reviewing depot leases.")

    assert cli.main(["--mock", "--db", str(db), "import", "--engagement", engagement_id, "--file", str(document)]) == 0
    assert json.loads(capsys.readouterr().out)["document_id"]


def test_status_reports_an_empty_engagement(tmp_path, capsys) -> None:
    db = tmp_path / "vault.sqlite3"
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps({"protected_values": [], "abstract_rules": [], "allowed_purpose": "review"}))

    cli.main(["--mock", "--db", str(db), "init-engagement", "--name", "empty", "--policy-file", str(policy_file)])
    engagement_id = json.loads(capsys.readouterr().out)["engagement_id"]

    assert cli.main(["--mock", "--db", str(db), "status", "--engagement", engagement_id]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["documents"] == []
    assert status["receipts"] == []
