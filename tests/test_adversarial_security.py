"""Adversarial tests for confidentiality claims. Do not weaken product assertions."""

from __future__ import annotations

import base64
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from src.policy import EngagementPolicy
from src.preflight import run_preflight
from src.sanitize import sanitize
from src.server_http import PrivilegeHandler, _runtime_mode
from src.service import PrivilegeService
from src.store import VaultStore


def test_abstract_rules_transmit_unlisted_proper_nouns():
    """Central claim gap: only protected_values/aliases are stripped from rules."""
    policy = EngagementPolicy(
        protected_values=["Northwind Freight"],
        abstract_rules=[
            "Northwind Freight withdrawing from Baltic corridor is protected",
            "The Meridian Capital bid is protected",
        ],
    )
    abstract = policy.to_abstract_for_judge()
    assert "[VALUE_1]" in abstract[0]
    assert "Northwind Freight" not in "\n".join(abstract)
    assert "Baltic corridor" in abstract[0]
    assert "Meridian Capital" in abstract[1]


@pytest.mark.parametrize(
    "text",
    [
        "Northwind Freight leaving",
        "northwind freight leaving",
        "NORTHWIND FREIGHT leaving",
        "Northwind\nFreight leaving",       # PDF text extraction wraps lines
        "Northwind  Freight leaving",       # layout padding
        "NorthwindFreight leaving",         # layout dropped the space
    ],
)
def test_declared_values_are_masked_despite_case_and_spacing(text: str):
    """Regression: each of these previously sent a real client name to OpenAI.

    The line-break case is the dangerous one. Extracting text from a PDF wraps
    lines wherever the layout did, so a name split across two lines is the
    normal case for the file type this tool is built to accept.
    """
    mappings = {"Northwind Freight": "[VALUE_1]", "Northwind": "[VALUE_1]"}
    out = sanitize(text, mappings).text
    assert "northwind" not in out.lower()
    assert "[VALUE_1]" in out


def test_short_protected_value_does_not_mutate_unrelated_words():
    """Regression: "port" once matched inside "important"."""
    out = sanitize("important report at the port", {"port": "[V]"}).text
    assert out == "important report at the [V]"


def test_longest_declared_value_wins_over_its_own_prefix():
    mappings = {"Northwind Freight": "[VALUE_1]", "Northwind": "[VALUE_2]"}
    out = sanitize("Northwind Freight and Northwind alone", mappings).text
    assert out == "[VALUE_1] and [VALUE_2] alone"


def test_hostile_rewrite_reinjection_is_stripped_before_next_infer(tmp_path: Path):
    store = VaultStore(tmp_path / "vault.sqlite3")
    policy = EngagementPolicy(
        protected_values=["AcmeCorp"],
        abstract_rules=["AcmeCorp exit is protected"],
    )
    eid = store.create_engagement("e", policy)
    did = store.import_document(eid, "t.txt", "AcmeCorp will exit next quarter.")

    class Hostile:
        destination = "openai"

        def __init__(self) -> None:
            self.round = 0

        def infer_claims(self, prior, candidate):
            assert "AcmeCorp" not in candidate
            self.round += 1
            return ["exit planned"] if self.round == 1 else []

        def match_rules(self, claims, rules):
            if claims:
                return [{"claim": claims[0], "rule": rules[0], "material": True}]
            return []

        def propose_rewrite(self, candidate, matched, preserve):
            return candidate + "\nReconsider AcmeCorp privately."

        def analyze(self, task, doc):
            raise AssertionError("analyze should not run in this test")

    result = run_preflight(eid, did, "Summarize AcmeCorp", store, Hostile())
    assert result.decision == "Transform"
    assert "AcmeCorp" not in result.final_payload
    store.close()


def test_upload_endpoint_returns_raw_text_and_leaves_no_temp(tmp_path: Path, monkeypatch):
    store = VaultStore(tmp_path / "vault.sqlite3")
    service = PrivilegeService(store)
    PrivilegeHandler.service = service
    eid = service.create_engagement(
        "e",
        EngagementPolicy(protected_values=["Northwind Freight"], abstract_rules=["Northwind Freight x"]),
    )
    raw = b"Northwind Freight confidential memo"
    body = {
        "engagement_id": eid,
        "filename": "memo.txt",
        "content_base64": base64.b64encode(raw).decode(),
    }

    class FakeRequest:
        def __init__(self):
            self.headers = {"Content-Length": str(len(json.dumps(body)))}
            self.rfile = __import__("io").BytesIO(json.dumps(body).encode())
            self.wfile = __import__("io").BytesIO()
            self.path = "/api/upload"
            self.requestline = "POST /api/upload HTTP/1.1"
            self.request_version = "HTTP/1.1"
            self.command = "POST"
            self._headers_buffer = []

        def send_response(self, code):
            self.status = code

        def send_header(self, k, v):
            self._headers_buffer.append((k, v))

        def end_headers(self):
            pass

    # Unit-test the extractor path used by upload
    text = PrivilegeHandler._extract_upload("memo.txt", body["content_base64"])
    assert text == raw.decode()
    # No leftover Privilege temps with our payload in the process temp dir is hard
    # to assert globally; instead assert the helper deletes its own file by
    # monkeypatching unlink tracking.
    deleted: list[Path] = []
    real_unlink = Path.unlink

    def tracking_unlink(self, missing_ok=False):
        deleted.append(self)
        return real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", tracking_unlink)
    PrivilegeHandler._extract_upload("memo.txt", body["content_base64"])
    assert deleted, "temp upload file must be unlinked"
    store.close()


def test_runtime_mode_never_echoes_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-should-not-leak")
    monkeypatch.delenv("PRIVILEGE_MOCK", raising=False)
    payload = json.dumps(_runtime_mode())
    assert "sk-secret" not in payload
    assert _runtime_mode()["mode"] == "live"


def test_sqlite_shared_connection_errors_under_concurrent_read_write(tmp_path: Path):
    store = VaultStore(tmp_path / "c.sqlite3")
    eid = store.create_engagement(
        "e", EngagementPolicy(protected_values=["Acme"], abstract_rules=["Acme x"])
    )
    errors: list[str] = []

    def writer() -> None:
        for i in range(40):
            try:
                store.append_ledger(eid, "openai", f"payload-{i}")
            except Exception as exc:  # noqa: BLE001 - collecting failure modes
                errors.append(type(exc).__name__)

    def reader() -> None:
        for _ in range(40):
            try:
                store.list_ledger(eid)
            except Exception as exc:  # noqa: BLE001
                errors.append(type(exc).__name__)

    threads = [threading.Thread(target=writer) for _ in range(3)] + [
        threading.Thread(target=reader) for _ in range(3)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    entries = store.list_ledger(eid, "openai")
    store.close()
    # Regression: readers were unlocked on a shared sqlite3 connection, which
    # raised InterfaceError and returned torn rows while the threaded viewer
    # wrote. Reads and writes now share one lock.
    assert not errors, f"concurrent access raised: {sorted(set(errors))}"
    assert len(entries) == 120, "every committed ledger row must be readable"


def test_web_heuristic_misses_lowercase_confidential_terms():
    """Mirrors web/index.html survivingNames false-negative class."""
    import re

    stop = {
        "A", "An", "The", "Any", "All", "No", "Not", "Is", "Are", "Was", "Were",
        "This", "That", "These", "Those", "If", "When", "Until", "Before", "After",
        "During", "Q1", "Q2", "Q3", "Q4",
    }

    def surviving_names(rules: list[str]) -> set[str]:
        found: set[str] = set()
        for rule in rules:
            without = re.sub(r"\[VALUE_\d+\]", " ", rule)
            for match in re.finditer(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*", without):
                words = match.group(0).split()
                while words and words[0] in stop:
                    words.pop(0)
                if not words:
                    continue
                starts = match.start() == 0 or without[: match.start()].strip() == ""
                if len(words) == 1 and starts:
                    continue
                found.add(" ".join(words))
        return found

    abstract = EngagementPolicy(
        protected_values=["Northwind Freight"],
        abstract_rules=["the meridian capital bid is protected"],
    ).to_abstract_for_judge()
    assert abstract == ["the meridian capital bid is protected"]
    assert surviving_names(abstract) == set()


@pytest.mark.parametrize(
    "label,text",
    [
        ("cyrillic-A", "Аcme Corp is exiting"),
        ("cyrillic-C", "Acme Сorp is exiting"),
        ("greek-omicron", "Acme Cοrp is exiting"),
        ("fullwidth", "Ａｃｍｅ　Ｃｏｒｐ is exiting"),
        ("zero-width-space-inside", "Ac​me Corp is exiting"),
        ("zero-width-space-between", "Acme​ Corp is exiting"),
        ("zero-width-joiner", "Acme‍Corp is exiting"),
        ("soft-hyphen", "Ac­me Corp is exiting"),
        ("combining-acute", "Acmé Corp is exiting"),
    ],
)
def test_lookalikes_and_invisibles_cannot_smuggle_a_declared_value(label: str, text: str):
    """Regression: a name that reads as declared must mask however it is encoded.

    Each of these rendered identically to "Acme Corp" on screen while reaching
    OpenAI as a real client name.
    """
    out = sanitize(text, {"Acme Corp": "[V1]"}).text
    assert "[V1]" in out, f"{label} was not masked: {out!r}"
    assert "orp" not in out.replace("[V1]", ""), f"{label} left a fragment: {out!r}"


@pytest.mark.parametrize(
    "text",
    [
        "Müller GmbH in Zürich reviewed Acme Corp",
        "Le café près d'Acme Corp",
        "東京 office of Acme Corp",
        "line one\nAcme Corp\nline three",
    ],
)
def test_text_outside_a_match_is_returned_unchanged(text: str):
    """Folding is for matching only. Accents and layout must survive."""
    out = sanitize(text, {"Acme Corp": "[V1]"}).text
    assert out.replace("[V1]", "Acme Corp") == text


def test_value_of_only_invisible_characters_matches_nothing():
    """An empty folded value must not compile to a pattern that matches everywhere."""
    out = sanitize("nothing confidential here", {"​‍": "[V1]"}).text
    assert out == "nothing confidential here"


@pytest.mark.parametrize(
    "label,text,mapping",
    [
        ("cherokee-A", "Ꭺcme Corp", {"Acme Corp": "[V1]"}),
        ("armenian-o", "Acme Cօrp", {"Acme Corp": "[V1]"}),
        ("coptic-c", "Aⲥme Corp", {"Acme Corp": "[V1]"}),
        ("small-caps-block", "ᴀᴄᴍᴇ ᴄᴏʀᴘ", {"Acme Corp": "[V1]"}),
        ("ipa-script-g", "Northɡate", {"Northgate": "[V1]"}),
        ("rlm-bidi", "Acme Co‏rp", {"Acme Corp": "[V1]"}),
        ("lrm-bidi", "Ac‎me Corp", {"Acme Corp": "[V1]"}),
        ("tag-block", "Ac\U000e0041me Corp", {"Acme Corp": "[V1]"}),
        ("invisible-times", "Ac⁢me Corp", {"Acme Corp": "[V1]"}),
        ("mongolian-vs", "Ac᠎me Corp", {"Acme Corp": "[V1]"}),
    ],
)
def test_second_pass_lookalike_and_format_classes_are_masked(label, text, mapping):
    """Regression for the pass-2 review: category-based folding closes whole
    classes (all format/control chars, all combining marks) and broader
    cross-script and Latin-block lookalikes, not a hand-picked list."""
    out = sanitize(text, mapping).text
    assert "[V1]" in out, f"{label} leaked: {out!r}"


def test_multichar_glyph_expansion_does_not_over_mask():
    """A single glyph folding to several characters must not have part of it
    matched and the whole glyph spliced away. Masking "C" must leave 5℃ alone."""
    out = sanitize("held at 5℃ overnight", {"C": "[V1]"}).text
    assert out == "held at 5℃ overnight"


@pytest.mark.parametrize(
    "text",
    [
        "Müller GmbH reviewed Acme Corp",
        "Le café d'Acme Corp",
        "東京 office of Acme Corp",
    ],
)
def test_folding_preserves_unmatched_text_exactly(text):
    """Folding is for matching only; bytes outside a match are returned as-is."""
    out = sanitize(text, {"Acme Corp": "[V1]"}).text
    assert out.replace("[V1]", "Acme Corp") == text
