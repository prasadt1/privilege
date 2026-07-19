"""OpenAI-only remote calls for sanitized Privilege payloads.

Raw documents, identities, aliases, mappings, and restored output must never
be passed to this module. Its callers provide only sanitized text and abstract
policy rules.
"""

from __future__ import annotations

import json
import os
from typing import Any


class PreflightError(RuntimeError):
    """A remote failure or malformed response that must fail closed."""


class OpenAIClient:
    destination = "openai"

    def __init__(self, client: Any | None = None, model: str | None = None, timeout: float = 30.0) -> None:
        self.model = model or os.environ.get("PRIVILEGE_MODEL", "gpt-5.6")
        self.timeout = timeout
        if client is None:
            try:
                from openai import OpenAI

                client = OpenAI(timeout=timeout)
            except Exception as error:
                raise PreflightError("OpenAI client is unavailable") from error
        self._client = client

    def infer_claims(self, prior_payloads: list[str], candidate: str) -> list[str]:
        data = self._structured(
            "Infer material business claims from the sanitized candidate and prior sanitized "
            "OpenAI disclosures. Do not invent identities. Return JSON only.",
            {"prior_payloads": prior_payloads, "candidate": candidate},
            "infer_claims",
        )
        claims = data.get("claims")
        if not isinstance(claims, list) or not all(isinstance(claim, str) for claim in claims):
            raise PreflightError("malformed inferred claims")
        return claims

    def match_rules(self, inferred_claims: list[str], abstract_rules: list[str]) -> list[dict[str, object]]:
        data = self._structured(
            "Compare inferred claims with abstract policy rules. Return JSON only. "
            "A match is material only when it exposes a protected fact.",
            {"inferred_claims": inferred_claims, "abstract_rules": abstract_rules},
            "match_rules",
        )
        matches = data.get("matches")
        if not isinstance(matches, list):
            raise PreflightError("malformed rule matches")
        if not all(
            isinstance(match, dict)
            and isinstance(match.get("claim"), str)
            and isinstance(match.get("rule"), str)
            and isinstance(match.get("material"), bool)
            for match in matches
        ):
            raise PreflightError("malformed rule match")
        return matches

    def propose_rewrite(self, candidate: str, matched: list[dict[str, object]], preserve_facts: list[str]) -> str:
        data = self._structured(
            "Generalize the candidate by the smallest amount needed to remove the material "
            "disclosure while preserving requested utility. Return JSON only.",
            {"candidate": candidate, "matched": matched, "preserve_facts": preserve_facts},
            "propose_rewrite",
        )
        rewritten = data.get("candidate")
        if not isinstance(rewritten, str) or not rewritten.strip():
            raise PreflightError("malformed rewrite")
        return rewritten

    def analyze(self, task: str, sanitized_doc: str) -> str:
        try:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {"role": "developer", "content": "Analyze only the sanitized material provided."},
                    {"role": "user", "content": f"Task:\n{task}\n\nSanitized material:\n{sanitized_doc}"},
                ],
            )
            output = self._output_text(response)
        except PreflightError:
            raise
        except Exception as error:
            raise PreflightError("OpenAI analysis failed") from error
        if not output.strip():
            raise PreflightError("empty analysis")
        return output

    def _structured(self, instruction: str, payload: dict[str, object], schema_name: str) -> dict[str, object]:
        schemas = {
            "infer_claims": {
                "type": "object",
                "properties": {"claims": {"type": "array", "items": {"type": "string"}}},
                "required": ["claims"],
                "additionalProperties": False,
            },
            "match_rules": {
                "type": "object",
                "properties": {
                    "matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim": {"type": "string"},
                                "rule": {"type": "string"},
                                "material": {"type": "boolean"},
                            },
                            "required": ["claim", "rule", "material"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["matches"],
                "additionalProperties": False,
            },
            "propose_rewrite": {
                "type": "object",
                "properties": {"candidate": {"type": "string"}},
                "required": ["candidate"],
                "additionalProperties": False,
            },
        }
        schema = schemas[schema_name]
        try:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {"role": "developer", "content": instruction},
                    {"role": "user", "content": json.dumps(payload)},
                ],
                text={"format": {"type": "json_schema", "name": schema_name, "strict": True, "schema": schema}},
            )
            parsed = json.loads(self._output_text(response))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise PreflightError("malformed structured response") from error
        except Exception as error:
            raise PreflightError("OpenAI structured request failed") from error
        if not isinstance(parsed, dict):
            raise PreflightError("structured response is not an object")
        return parsed

    @staticmethod
    def _output_text(response: Any) -> str:
        output = getattr(response, "output_text", None)
        if isinstance(output, str):
            return output
        if isinstance(response, dict) and isinstance(response.get("output_text"), str):
            return response["output_text"]
        raise PreflightError("response has no output text")


class MockOpenAIClient:
    """Offline deterministic client selected only with PRIVILEGE_MOCK=1."""

    destination = "openai"
    model = "mock"

    def infer_claims(self, prior_payloads: list[str], candidate: str) -> list[str]:
        return []

    def match_rules(self, inferred_claims: list[str], abstract_rules: list[str]) -> list[dict[str, object]]:
        return []

    def propose_rewrite(self, candidate: str, matched: list[dict[str, object]], preserve_facts: list[str]) -> str:
        return candidate

    def analyze(self, task: str, sanitized_doc: str) -> str:
        return sanitized_doc


def client_from_environment() -> OpenAIClient | MockOpenAIClient:
    if os.environ.get("PRIVILEGE_MOCK") == "1":
        return MockOpenAIClient()
    return OpenAIClient()
