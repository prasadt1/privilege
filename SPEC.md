# Build Week spec — Privilege
*(Name chosen by Prasad: Privilege — engagement-confidential facts, not just entities.)*

**Track:** Work & Productivity · **Deadline:** Tue Jul 21, 5:00 PM PT (= Wed 2:00 AM CEST)
**Pitch:** Existing tools protect identities. This one protects engagement confidentiality —
cumulatively — before GPT-5.6 sees your next prompt.
**Package / CLI:** `privilege` · **Env:** `PRIVILEGE_MOCK`, `PRIVILEGE_MODEL` · **Vault:** `~/.privilege/vault.sqlite3`

**Ground rules (compliance-critical):**
- Majority of core functionality is built IN CODEX — this spec gets pasted into
  a Codex session; grab the `/feedback` Session ID from that thread EARLY.
- Use **GPT-5.6** for the core implementation passes you'll cite in the video;
  GPT-5.6 also powers the runtime attacker/judge (structurally load-bearing).
- NEW codebase. Do NOT copy Engram code. Engram may be disclosed only as
  conceptual prior art for receipts/audit patterns — not as a source to lift from.
- Claude/Cursor role: spec + review + peripheral docs. Codex implements the cited core.
- Project name is **Privilege** (chosen by Prasad). Prasad writes the Devpost description in his own voice.

## Product promise

A consultant imports a document locally, defines what an engagement considers
confidential, and asks GPT-5.6 to work on it without sending the raw document
or identity mappings. Before analysis, GPT-5.6 tests whether the sanitized
candidate plus prior sanitized disclosures reveal a protected business fact.

The product reports **Allow**, **Transform**, or **Block** and saves a receipt.
It reduces cumulative semantic-disclosure risk; it does **not** guarantee
anonymity, compliance, or that OpenAI never processes sensitive information.

### Accepted trust boundary
- Raw documents, real identities, aliases, mappings, and local rehydrated
  output stay on-device.
- OpenAI receives sanitized text, abstract policy rules, and sanitized text
  previously sent to that **same** destination.
- MVP supports OpenAI only. Cross-provider ledgers and routing are deferred.

## One core, three surfaces

1. **Local web app** — create engagement profiles, import documents into a
   private vault, run the workflow, compare original/sanitized/final views,
   inspect receipts.
2. **CLI** — scriptable import, preflight, analysis, status, eval, receipt export.
3. **MCP adapter** — receives opaque engagement/document IDs plus a task;
   returns sanitized analysis and receipt data only. Setup, raw import, and
   rehydration never happen through the model-facing MCP interface.

The MCP adapter is a convenience interface, not the security boundary.
All three surfaces call the same core service.

## Core modules

### Engagement policy (`src/policy.py`)
Local profile contains:
- direct protected values and aliases;
- stable placeholder mappings (e.g. `Amazon` → `[CLIENT-A]`);
- user-authored abstract rules such as
  `[CLIENT] market-exit strategy for [REGION-1] is protected`;
- allowed-purpose notes and optional strictness level.

Raw values are **never** included in model prompts. Abstract rules may reveal
categories of interest — the UI must preview exactly what the policy judge
will receive.

### Sanitizer (`src/sanitize.py`)
Local, deterministic:
- declared entities / aliases / known protected values → stable placeholders;
- regex patterns for emails, phones, common PII;
- optional Presidio as a disclosed dependency if available; otherwise regex +
  declared-entity masking is the MVP path (do not block the build on Presidio).

### Preflight loop (`src/preflight.py`)
1. Sanitize PII, declared entities, aliases, and known values locally.
2. Ask GPT-5.6, **without** policy targets, to enumerate claims inferable from
   prior sanitized disclosures plus the candidate.
3. Ask GPT-5.6 to compare those inferred claims with abstract engagement rules.
4. If a match is material, generate the smallest utility-preserving
   generalization and rerun the blind attack.
5. Stop after **two** repair rounds. Remaining material risk fails closed as
   **Block**.
6. Only an **Allow** payload may proceed to the requested analysis call.
7. Append the exact final outbound payload to the same-destination ledger
   **only after** it is actually sent.

Malformed structured output, API errors, timeout, unknown engagement/document
IDs, or exhausted repair rounds fail closed. Exported receipts contain no raw
mappings.

### Store (`src/store.py`) — SQLite
```
engagements(id, name, policy_json, created_at)
documents(id, engagement_id, title, raw_path, created_at)
mappings(engagement_id, real_value, placeholder)  -- local only, never exported
ledger(id, engagement_id, destination, payload, created_at)
receipts(id, engagement_id, decision, payload_json, created_at)
```

### Receipts
Each receipt records:
- opaque engagement and document IDs;
- provider/model and timestamp;
- prior sanitized disclosure count;
- sanitized candidate hash and preview;
- inferred claims and matched abstract rules;
- Allow / Transform / Block decision;
- transformation diff and attack rounds;
- exact final outbound payload;
- utility-check result and limitations.

Receipts are persisted data, not application logs. A local-only view may
display rehydrated labels; exported receipts remain sanitized.

## Frozen eval (`eval/`)

Commit authored scenarios **before** running results:
- 10–12 synthetic consultant engagements;
- 3–5 individually innocuous disclosures per sequence;
- known protected abstract facts, revealing cue combinations, benign controls,
  and expected task facts that must survive;
- **no real client material**.

Compare:
- **Baseline:** local direct masking + independent per-prompt checking.
- **Treatment:** cumulative inference + policy match + rewrite + re-attack.

Report:
- protected-fact leak detection recall;
- benign-turn false-block rate;
- attack success before and after transformation;
- required task-fact retention;
- exact receipt/payload reproducibility.

Ground truth is authored and checked locally. GPT-5.6 must not create and
grade the same labels. Publish weak or mixed results unchanged.

## Demo arc (90s)

1. Import a synthetic engagement; show raw values remain local.
2. Run three sanitized work requests; each passes and the ledger grows.
3. Submit a fourth request that is harmless alone but completes a protected
   strategic fact cumulatively.
4. GPT-5.6 reconstructs the fact; UI changes Allow → Transform, highlights
   decisive cues, reruns the attack.
5. Transformed payload passes; GPT-5.6 completes the analysis; local UI
   restores placeholders.
6. Open the receipt; flash baseline-vs-treatment eval results.

## Repo layout
```
README.md
LICENSE                 # Apache-2.0
SPEC.md  HANDOFF.md  CODEX-SESSIONS.md
pyproject.toml
src/
  __init__.py
  store.py              # SQLite vault + ledger + receipts
  policy.py             # engagement policy model
  sanitize.py           # local masking
  openai_client.py      # GPT-5.6 structured calls
  preflight.py          # attack / judge / repair loop
  analyze.py            # post-Allow analysis + local restore
  service.py            # shared core API used by all surfaces
  cli.py                # CLI entry
  server_http.py        # local web app (:7077)
  server_mcp.py         # thin MCP adapter (stdio)
web/
  index.html            # single-page dark UI
eval/
  scenarios.py          # frozen scenarios (committed first)
  run.py
  results.json
demo/
  seed.py               # synthetic engagement for judges
tests/
  test_store.py
  test_sanitize.py
  test_preflight.py
  test_service.py
```

## Strict MVP cuts

**Include:** English text / Markdown / text-based PDF import; one OpenAI
destination + GPT-5.6; one local vault; SQLite ledger; structured model
outputs; two repair rounds; shared core; CLI; local single-page UI; thin MCP.

**Exclude:** browser extensions, universal LLM proxying, multi-provider
routing, OCR, DOCX/PPTX fidelity, automated NDA interpretation, compliance
certification, collaborative accounts, cloud hosting, automatic discovery of
every undeclared secret.

**Cutoff order if behind:** PDF import → MCP adapter → UI polish.
**Never cut:** sanitizer tests, cumulative ledger, attack/repair loop,
receipts, eval, runnable demo.

## Related work (disclose in README)

Hey Jude (re-identification critic + audit logs), CAMP (cumulative PII
exposure), PlanTwin (per-object cumulative disclosure budgets), SEMSIEDIT
(semantic sensitive information rewriting), Microsoft Presidio (entity
redaction). Claim the narrow composition: engagement-defined semantic facts +
cumulative sanitized disclosures + three user surfaces + inspectable receipts
for solo practitioners — not “we invented redaction.”

## Build order (Codex sessions, ~1.5 days)
1. store + policy + sanitizer + tests (cite this session) — ~3h
2. preflight loop + receipts + failure behavior — ~3h
3. freeze scenarios + eval runner + honest results — ~2h
4. CLI → local web → thin MCP — ~3h
5. seed + README + packaging + rehearsal — ~2h
6. Video + Prasad-written description + submit with ≥3h buffer — ~3h

## Submission checklist
- [ ] `/feedback` Codex Session ID in the form (primary build thread)
- [ ] Video ≤3 min, YouTube (Unlisted OK), narrates Codex + GPT-5.6 usage
- [ ] Repo public + LICENSE (or private + shared with testing@devpost.com and
      build-week-event@openai.com)
- [ ] README: setup, sample data, judge path without rebuilding, related work,
      honest trust-boundary limits
- [ ] Description written by Prasad, not pasted AI prose
- [x] Name chosen by Prasad: **Privilege**
- [ ] Devpost submission page created EARLY
