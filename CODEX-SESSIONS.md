# Build plan — Codex sessions

The implementation is split into five sessions, each with a defined scope and
a done-condition. `STANDING CONTEXT` below carries the architecture and trust
boundary into every session, since Codex threads don't share memory.

Project name is locked: **Privilege** (package/CLI: `privilege`).
Env vars: `PRIVILEGE_MOCK`, `PRIVILEGE_MODEL`. Default vault: `~/.privilege/vault.sqlite3`.

---

## STANDING CONTEXT (prepend to every session)

```
PROJECT: Privilege — local engagement-policy confidentiality preflight for
consultants. Raw docs and identity mappings stay on-device. Before GPT-5.6
analyzes anything, the tool sanitizes known values locally, then uses GPT-5.6
as a blind attacker against the sanitized candidate PLUS prior sanitized
disclosures to the same OpenAI destination. Decisions: Allow / Transform /
Block + inspectable receipt.

STACK: Python 3.11+, sqlite3 stdlib, pytest, official `openai` SDK,
optional `mcp` SDK for the thin adapter. Minimal deps. No ORM. No cloud
hosting. No browser extension.

TRUST BOUNDARY (state in code comments and README):
- Raw documents, real identities, aliases, mappings, rehydrated output: LOCAL.
- OpenAI receives: sanitized text, abstract policy rules (no raw values),
  and prior sanitized payloads already sent to OpenAI.
- Do NOT claim anonymity, GDPR/HIPAA compliance, or "nothing sensitive
  reaches the cloud."
- MVP: OpenAI destination only. No multi-provider routing.

DESIGN STANCE:
- Engagement-defined semantic facts are the wedge (not just PII entities).
- Receipts are data (SQLite rows), not logs.
- Fail closed: API errors, malformed structured output, timeout, unknown IDs,
  exhausted repair rounds → Block.
- Max two repair rounds, then Block.
- Ledger append happens only AFTER a payload is actually sent.

CONSTRAINTS:
- Clean-room. Do not copy from Engram or any other codebase.
- Every module gets tests. Tests must pass before the session is done.
- Apache-2.0.
- Small, readable files. Prefer clarity — judges read this.
```

---

## SESSION 1 — store + policy + sanitizer + tests  (~3h · CITE THIS SESSION)

```
[STANDING CONTEXT]

TASK: Build the local vault, engagement policy model, and sanitizer.

Create repo layout:
  pyproject.toml (name=privilege, python>=3.11, deps: openai, pytest; optional mcp)
  CLI entry point: privilege = src.cli:main
  Default DB path: ~/.privilege/vault.sqlite3
  Env: PRIVILEGE_MOCK=1 for offline mock attacker; PRIVILEGE_MODEL for model slug
  LICENSE (Apache-2.0)
  src/store.py  src/policy.py  src/sanitize.py
  tests/test_store.py  tests/test_sanitize.py  tests/test_policy.py

SQLite schema (src/store.py):
  engagements(id TEXT PK, name TEXT, policy_json TEXT, created_at TEXT)
  documents(id TEXT PK, engagement_id TEXT, title TEXT, raw_text TEXT, created_at TEXT)
  mappings(engagement_id TEXT, real_value TEXT, placeholder TEXT,
           PRIMARY KEY(engagement_id, real_value))
  ledger(id TEXT PK, engagement_id TEXT, destination TEXT, payload TEXT, created_at TEXT)
  receipts(id TEXT PK, engagement_id TEXT, decision TEXT, payload_json TEXT, created_at TEXT)

API:
  create_engagement(name, policy) -> id
  import_document(engagement_id, title, raw_text) -> id
  get_document / get_engagement / list_ledger / append_ledger / save_receipt
  upsert_mapping(engagement_id, real_value, placeholder)

Policy model (src/policy.py):
  EngagementPolicy with:
    protected_values: list[str]
    aliases: dict[str, str]          # alias -> canonical real value
    abstract_rules: list[str]        # e.g. "[CLIENT] exit of [REGION] is protected"
    allowed_purpose: str
    strictness: str = "normal"       # normal | strict
  Methods: to_abstract_for_judge() -> list[str]  # NEVER includes raw values
            assign_placeholders() -> dict[str,str]

Sanitizer (src/sanitize.py):
  sanitize(text, mappings) -> SanitizeResult(text, applied: list[{real, placeholder}])
  Rules (deterministic, ordered):
    1. Longest-first replace of declared mappings / protected values / aliases
    2. Regex: emails, phones (simple international), credit-card-like digit runs
  restore(sanitized_text, mappings) -> text   # local only
  Do NOT call any cloud API in this module.

TESTS:
- create engagement, import doc, round-trip
- mappings persist; longest-match wins ("Amazon Web Services" before "Amazon")
- email/phone regex masks
- restore reverses placeholders
- to_abstract_for_judge never contains raw protected values
- unknown engagement id raises cleanly

DONE when: pytest green. Commit. Paste the /feedback Session ID somewhere safe.
```

---

## SESSION 2 — preflight loop + receipts + OpenAI client  (~3h)

```
[STANDING CONTEXT]

TASK: Implement GPT-5.6 blind inference, policy adjudication, repair loop,
receipts, and the shared service API.

Add:
  src/openai_client.py
  src/preflight.py
  src/analyze.py
  src/service.py
  tests/test_preflight.py
  tests/test_service.py

openai_client.py:
  - Uses OPENAI_API_KEY from env
  - Model default: gpt-5.6 (or the current GPT-5.6 slug available in the account)
  - Structured JSON outputs via response_format / parsed schema
  - Methods:
      infer_claims(prior_payloads: list[str], candidate: str) -> list[str]
      match_rules(inferred_claims: list[str], abstract_rules: list[str])
          -> list[{claim, rule, material: bool}]
      propose_rewrite(candidate: str, matched, preserve_facts: list[str]) -> str
      analyze(task: str, sanitized_doc: str) -> str
  - On timeout / malformed JSON / API error: raise PreflightError (caught as Block)

preflight.py:
  run_preflight(engagement_id, document_id, task, store, client) -> PreflightResult
  Algorithm exactly as SPEC:
    sanitize → blind infer (with ledger) → match abstract rules →
    if material: rewrite (max 2 rounds) → re-infer →
    Allow | Transform | Block
  Ledger is READ for prior payloads; DO NOT append until analyze actually sends.
  Return structured result including rounds, inferred claims, matched rules,
  final_payload, decision.

analyze.py:
  Only called after Allow (or Transform that ends in Allow).
  Sends final_payload + task to GPT-5.6, restores placeholders locally,
  appends ledger, saves receipt.

service.py (shared by CLI / web / MCP):
  create_engagement, import_document, preflight, analyze, status, export_receipt
  MCP-safe methods never return raw_text or mappings.

TESTS:
- Mock the OpenAI client; do not burn API quota in unit tests
- Sequence of 3 benign turns → Allow; 4th cumulative leak → Transform or Block
- Exhausted repairs → Block
- API error → Block
- Receipt has no raw mappings when exported
- Ledger grows only after successful analyze send

DONE when: pytest green with mocks. Commit.
```

---

## SESSION 3 — frozen eval  (~2h)

```
[STANDING CONTEXT]

TASK: Author frozen scenarios FIRST, commit them, THEN write the runner and
produce results.json. Do not invent labels with GPT.

Add:
  eval/scenarios.py   # COMMIT THIS BEFORE writing run.py results
  eval/run.py
  eval/results.json

scenarios.py — 10–12 synthetic engagements. Each has:
  policy (protected values + abstract rules)
  disclosures: list of {turn, text, expected: allow|transform|block,
                        reveals_protected: bool, must_retain: list[str]}
  No real client names from Prasad's work. Use fictional brands.

run.py:
  Modes:
    baseline  = sanitize + independent per-prompt check (no ledger context)
    treatment = full cumulative preflight
  Metrics: leak_recall, false_block_rate, attack_success_pre/post,
           task_fact_retention, receipt_reproducibility
  Use a MockAttacker for CI determinism AND an optional --live flag for
  real GPT-5.6 runs. Commit mock results always; live results if available.

DONE when: scenarios committed, runner green, results.json committed with
honest numbers. Weak results stay published.
```

---

## SESSION 4 — CLI → web → MCP  (~3h)

```
[STANDING CONTEXT]

TASK: Surfaces over service.py. Cut order if short on time: skip MCP, then
thin the web UI — never skip CLI.

src/cli.py — prog name `privilege`, commands:
  init-engagement --name --policy-file
  import --engagement ID --file path
  preflight --engagement ID --document ID --task "..."
  analyze  --engagement ID --document ID --task "..."
  status   --engagement ID
  export-receipt --id OUT.json
  eval     (wraps eval/run.py)
  Honor PRIVILEGE_MOCK / --mock for offline attacker.

src/server_http.py + web/index.html:
  Local HTTP on :7077
  Title/brand: Privilege
  Pages/panes: engagement setup, document import, preflight run,
  three-column view (raw local-only | sanitized | restored result),
  receipts feed, ledger length.
  Dark canvas + amber accents. Vanilla JS, no build step.
  API: /api/* calling service.py. Never send mappings to the browser beyond
  what the local operator needs; do not expose export of raw mappings via
  public-looking endpoints.

src/server_mcp.py (thin, optional if time):
  FastMCP server name: "privilege"
  Tools: preflight(engagement_id, document_id, task),
         analyze(...), status(engagement_id)
  NEVER tools for import_raw or dump_mappings.
  stdio transport, official mcp SDK.

DONE when: CLI demo works end-to-end with mocks or live key; web loads;
MCP optional. Commit.
```

---

## SESSION 5 — seed + README + polish  (~2h)

```
[STANDING CONTEXT]

TASK: Judge-ready packaging.

demo/seed.py — loads one synthetic "Nordic retail exit" engagement matching
the demo arc (3 safe turns + 1 mosaic leak).

README.md must include:
  - what it is / what it is NOT (trust boundary, no compliance claims)
  - setup (Python 3.11+, OPENAI_API_KEY, pip install -e .)
  - judge quickstart WITHOUT rebuilding (seed + CLI commands)
  - Codex + GPT-5.6 usage narrative for the video
  - related work: Hey Jude, CAMP, PlanTwin, SEMSIEDIT, Presidio
  - Engram conceptual prior-art note if receipts lineage is mentioned
  - LICENSE Apache-2.0

Rehearse the 90s demo arc from SPEC.md once. Fix broken edges only.

DONE when: a cold machine can follow README and hit the mosaic demo.
```
