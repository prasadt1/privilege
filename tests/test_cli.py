from src import cli


def test_cli_initializes_and_closes_the_default_vault(monkeypatch, capsys) -> None:
    events: list[object] = []

    class FakeStore:
        def __init__(self, path) -> None:
            events.append(path)

        def close(self) -> None:
            events.append("closed")

    monkeypatch.setattr(cli, "VaultStore", FakeStore)

    assert cli.main() == 0
    assert events == [cli.DEFAULT_DB_PATH, "closed"]
    assert "Privilege vault ready" in capsys.readouterr().out
