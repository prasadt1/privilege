# Privilege — hostile security review

**Date:** Mon 20 Jul 2026  
**Reviewer:** Cursor (hostile / falsification posture)  
**Repo:** `~/OpenAI-hackathon`  
**Scope:** Hackathon submission that will be publicly judged. Real findings only.

**Constraints honored**
- `eval/scenarios.py` not edited; eval not re-run; published numbers untouched.
- `src/` logic not modified.
- Tests added only: `tests/test_adversarial_security.py`.
- Manual checks used `--mock` (no API credits).

---

## What it claims

Privilege is a local-first confidentiality preflight for consultants. Raw client documents stay on the machine. Before GPT-5.6 analyzes anything, known values are masked locally, then GPT-5.6 acts as a blind attacker against the sanitized candidate **plus** prior sanitized disclosures to the same destination. If a protected business fact becomes inferable it Transforms or Blocks and writes a receipt.

### The central claim to falsify

> Raw documents, real identities, aliases, mappings, and restored output never leave the device. OpenAI receives only sanitized text, abstract policy rules containing no real values, and prior sanitized payloads.

Every path into `src/openai_client.py` was traced for whether an unsanitized value can arrive.

---

## Verdict

**The central claim does not fully hold.**

Document/task masking before `infer` / `match` / `analyze` is real, and hostile rewrite reinjection is stripped. **Abstract policy rules can still ship real confidential nouns to OpenAI.** Case/linebreak/concatenation bypasses can also put raw document names on the wire.

**Automated tests:** `pytest` → **38 passed** (was 29 before adversarial tests; `TESTING.md` still says 28).

---

## Ranked findings

### 1. High — Unlisted nouns in abstract rules go to OpenAI verbatim

**Location:** `src/policy.py:36-45`

`to_abstract_for_judge()` only replaces keys in `protected_values` / `aliases`. Anything else in a rule is sent as written into `client.match_rules(...)`.

**Failure scenario:** Policy protects `Northwind Freight` but the rule says:

```text
The Meridian Capital bid is protected
```

Server sends that string unchanged to OpenAI.

**Demonstrated:**

```text
ABSTRACT: ['[VALUE_1] withdrawing from Baltic corridor is protected',
           'The Meridian Capital bid is protected']
```

Also: `Baltic corridor` survived when it was in the rule but not in `protected_values`.

**Claim impact:** Falsifies *“abstract policy rules containing no real values.”*

**Surfaces:** CLI has **no** warning. Web warns only via a Title-Case heuristic (see Finding 2).

---

### 2. High — Web “safe preview” can lie; lowercase secrets slip through

**Location:** `web/index.html:126-154` vs `src/policy.py:36-45`

- `abstractPreview()` matches Python replacement for **valid** policies (longest-first, aliases → placeholders).
- `survivingNames()` does **not** equal “what OpenAI receives.”

**Failure scenario:** Rule:

```text
the meridian capital bid is protected
```

- Preview: no red warning (`survivingNames` → empty set)
- Server: sends that string unchanged

**Also misses:**
- Leading ALL-CAPS codename: `OPSCLEARANCE window is protected` — skipped as sentence-initial singleton
- Hyphenated brands: `Acme-Corp exit…` — warns only `Corp`, not `Acme`

**Claim impact:** Operator can believe the UI said “safe” while OpenAI still receives a real name.

---

### 3. High — Sanitizer bypasses put raw client names in `final_payload`

**Location:** `src/sanitize.py:29-33`  
(literal, case-sensitive `str.replace`, no word boundaries)

| Input | Result |
|---|---|
| `northwind freight leaving` | unchanged (case) |
| `Northwind\nFreight leaving` | `[VALUE_2]\nFreight…` (linebreak split) |
| `NorthwindFreight leaving` | `[VALUE_2]Freight…` (concatenation) |

**Failure scenario:** Document uses a line break or different casing than the protected list → raw name remains inside the candidate passed to `infer_claims` and later `analyze`.

**Related integrity bug (not a confidentiality leak):** short value `port` → `im[V]ant re[V]` inside `important report`.

---

### 4. Medium — Upload temp files: raw client bytes on disk outside the vault

**Location:** `src/server_http.py:102-112`

Flow: `NamedTemporaryFile(..., delete=False)` → write → extract → `unlink` in `finally`.

| Check | Result |
|---|---|
| File permissions (this Mac) | **`0o600`** — held |
| Crash / SIGKILL between write and unlink | File **survives** under process temp dir with raw bytes |
| Filename path traversal | **Held** — only suffix used; path is mkstemp-owned |
| Temp parent dir | Often world-listable; mode 600 helps content, not crash residue |

**Also:** `/api/upload` returns `raw_text` in JSON (`server_http.py:69`). Acceptable while bound to `127.0.0.1`; footgun if bind changes.

**Is uploaded text written before sanitization?** Yes — into the temp file and then into the vault as `documents.raw_text`. That is local-by-design, but it is still raw client data at rest outside “sanitized-only” paths.

---

### 5. Medium — No upload size / zip-bomb / hostile-Office limits

**Location:** `src/server_http.py:94-106`, `src/intake.py:117-138`

- Base64 body length unbounded → memory DoS.
- `.docx` is a ZIP; `python-docx` opens it with no entry-count/size caps → zip bomb risk.
- Empty extraction refused: **correct** for this product (avoids sanitizing text the operator never saw). Held as design, not a bug.
- XXE via `python-docx`: **not demonstrated**; residual risk only.

---

### 6. Medium — Shared SQLite connection + unlocked readers

**Location:** `src/store.py:55-71` (used by `ThreadingHTTPServer`)

Writes are locked; **reads are not**. Same connection with `check_same_thread=False`.

**Failure scenario:** Concurrent `append_ledger` + `list_ledger` (e.g. UI “check” + receipts refresh) produced:

- `InterfaceError: bad parameter or other API misuse`
- `TypeError` on `json.loads(None)` (torn / bad row state)
- spurious `UnknownEngagementError`

Short stress run: **94 errors**. Realistic under the threaded local viewer.

---

### 7. Medium — Fail-closed for *send* mostly holds; CLI/docs disagree

**Held**
- Missing key / unknown ids / exceptions in `run_preflight` → **Block**, empty `final_payload` (nothing to send).
- Rewrite path: `preflight.py:85` re-sanitizes model rewrite before the next infer. Hostile `AcmeCorp` reinjection was stripped in test.
- Restored output not sent to OpenAI: `analyze.py` restores only after `client.analyze(sanitized_*)`.
- MCP: `analyze_sanitized` uses `restore_output=False`; no raw import / mapping dump tools.
- `/api/mode`: no key material echoed (`server_http.py:125-149`).

**Gaps / mismatches**
- `TESTING.md` §7 expects stderr `OpenAI client is unavailable` and **exit 2**. Actual: JSON `Block`, **`exit 0`**, `receipt_id: null` ( `_blocked_before_check` in `service.py:48-55` may save a receipt without attaching the id to the returned result).
- Mock mode always **Allow** (by design — mock infers nothing). Do not treat mock Allow as evidence the attacker works.
- MCP `status` returns abstracted rules only — but those can still contain Finding 1 leaks.

**Note on client-construction vs `run_preflight`:** `service.preflight()` catches client-construction `PreflightError` separately and returns Block. That split is airtight for *not Allowing*. It is not airtight for CLI exit codes / receipt id surfacing.

---

### 8. Low — Repo hygiene / TESTING drift

- `TESTING.md` expects **28** passed → observed **38** after adversarial tests (29 before them).
- `.gitignore` ignores `HANDOFF.md` and `SUBMISSION.md` — odd for a judged repo; not a data leak by itself.
- `git ls-files` secret check: no real `.env`; `demo/demo-vault.sqlite3` present as documented synthetic data. `.openai_session_id` is gitignored.

---

## Central claim trace (outbound to `openai_client.py`)

| Path | Sanitized before send? | Result |
|---|---|---|
| Document + task → `infer_claims` / `analyze` | Yes (`preflight.py:59-61`) | **Held** if values match mappings exactly |
| Model `propose_rewrite` output | Re-sanitized (`preflight.py:85`) | **Held** |
| `match_rules(..., abstract_rules)` | Only listed values replaced | **Falsified** (Finding 1) |
| Local `restore()` output | Not passed to client | **Held** |
| Case / linebreak / concat document text | Missed by sanitizer | **Falsified** (Finding 3) |

### `abstractPreview` vs server

Replacement algorithms **agree** for valid policies. The operator-facing lie is primarily `survivingNames` false negatives (Finding 2), not preview/server replacement drift.

---

## Priority-area answers (as asked)

### Priority 1 — File intake

- Temp permissions: **0o600** held.
- Crash residue: **yes**, raw bytes can remain until manual cleanup.
- `/tmp` (or OS temp): acceptable with 600; not ideal for crash residue.
- Crafted filename path problem: **not demonstrated** (suffix-only).
- Malformed PDF/DOCX resource exhaustion / zip bomb: **plausible, not size-capped** (Finding 5).
- XXE: not proven.
- Refusing empty extraction: **correct**.
- Uploaded file text before sanitization: written to temp + vault raw column — local by design.

### Priority 2 — Leak paths

- `to_abstract_for_judge`: **High** leak for unlisted nouns (Finding 1).
- Web heuristic false negatives: **High** (Finding 2).
- Preflight sanitize before every outbound call including rewrite: **Held** for rewrite; **not** for abstract rules.
- Restored output sent out: **not to OpenAI**; returned to local HTTP/CLI operator only.
- MCP extract raw/mappings: **no dedicated tools**; abstract-rule leak still possible via `status` / preflight payloads that embed rules indirectly through match results.
- `/api/mode` credentials: **held**.

### Priority 3 — Fail closed

Any check failure that reaches `run_preflight` / analyze error paths becomes **Block**, not Allow — **held for send**. Mock always Allows — by design. CLI exit-code / TESTING.md expectations — **not held**.

### Priority 4 — Concurrency

Unlocked readers on a shared `sqlite3` connection under `ThreadingHTTPServer` — **reproduced** (Finding 6).

### Sanitizer edge cases

Ordering longest-first for overlapping declared values (`Northwind Freight` before `Northwind`): **held** when casing/spacing match.  
Failures: case, punctuation/concat, linebreak span, unicode lookalikes (not specially normalized), short values inside longer words (over-redaction).

---

## TESTING.md manual pass (`--mock`)

| Step | Result |
|---|---|
| `pytest -q` | **38 passed** (doc says 28) |
| CLI preflight placeholders | **Pass** — `Northwind Freight` / `Baltic corridor` → `[VALUE_*]` |
| status `abstract_rules` | **Pass** for `policies/restructuring.json` |
| unsupported `.xlsx` / `.zip` / missing file | **Pass** — exit 2, clean errors |
| docx tables | **Pass** — `Corridor \| Baltic` extracted |
| no API key `--live` | **Mismatch** — Block JSON, exit 0; not stderr exit 2 |
| unknown ids | **Pass** — Block with `UnknownEngagementError` |
| receipts grow | **Pass** — 3 after preflight + analyze |

Mock note (as TESTING.md states): mock client infers nothing → everything Allows in mock mode. That exercises plumbing only, not detection.

---

## Tests added

**File:** `tests/test_adversarial_security.py`

Covers:
- abstract-rule leak of unlisted proper nouns
- sanitizer case / linebreak / concatenation bypasses
- short-value over-redaction
- hostile rewrite reinjection stripped before next infer
- upload temp unlink behavior
- `/api/mode` never echoes API key material
- SQLite concurrent read/write errors
- web heuristic false negative for lowercase confidential terms

---

## Recommended fix order (not implemented)

1. **Fail closed on abstract rules:** refuse engagement creation (or Block preflight) if any rule still contains a non-placeholder confidential token after substitution — or require every proper noun in rules to be listed in `protected_values`.
2. **Harden sanitizer:** casefold / normalize whitespace; consider rejecting or normalizing linebreak-split names; word-boundary awareness for short values.
3. **Serialize all SQLite access** on one lock (or one connection per request).
4. **Upload hygiene:** size cap; prefer vault-adjacent temp; keep `delete` reliable; never bind HTTP off localhost without auth.

---

## Claims that held (summary)

- Document + task go through local `sanitize()` before `infer_claims` / `analyze` when mappings match exactly.
- Model rewrite is re-sanitized before the next attack round.
- Restored (real-name) analysis is not passed into `openai_client`.
- MCP has no raw-import or mapping-dump tools; MCP analyze uses non-restored output.
- `/api/mode` does not expose credential material.
- Temp upload files are mode `0o600` when created normally.
- Filename alone does not path-traverse into the vault.
- Empty extraction refusal is the right product choice.
- Failures in the preflight/analyze check path Block rather than Allow a send.

---

## End of review
