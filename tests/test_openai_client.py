from types import SimpleNamespace

import pytest

from src.openai_client import MockOpenAIClient, OpenAIClient, PreflightError, client_from_environment


class FakeResponses:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = iter(outputs)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=next(self.outputs))


def test_structured_openai_call_uses_json_schema(monkeypatch) -> None:
    monkeypatch.setenv("PRIVILEGE_MODEL", "test-model")
    responses = FakeResponses(['{"claims": ["a safe claim"]}'])
    client = OpenAIClient(SimpleNamespace(responses=responses))

    assert client.infer_claims(["prior"], "candidate") == ["a safe claim"]
    assert responses.calls[0]["model"] == "test-model"
    assert responses.calls[0]["text"]["format"]["type"] == "json_schema"


def test_malformed_structured_output_fails_closed() -> None:
    responses = FakeResponses(["not json"])
    client = OpenAIClient(SimpleNamespace(responses=responses))

    with pytest.raises(PreflightError, match="malformed structured response"):
        client.infer_claims([], "candidate")


def test_mock_environment_never_constructs_a_remote_client(monkeypatch) -> None:
    monkeypatch.setenv("PRIVILEGE_MOCK", "1")

    assert isinstance(client_from_environment(), MockOpenAIClient)
