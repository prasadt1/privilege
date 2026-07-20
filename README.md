# Privilege

**Existing tools protect identities. Privilege protects engagement confidentiality — cumulatively — before GPT-5.6 sees your next prompt.**

A local-first confidentiality preflight for consultants, freelancers, and
architects who want AI help on client work without pasting raw client
documents into a chatbot. Raw documents and the mapping from real names to
placeholders stay on your machine. Before anything is sent, Privilege turns
GPT-5.6 into a **blind attacker** against the sanitized text plus everything
already disclosed in this engagement, and refuses to send if a protected
business fact would become inferable.

**Track:** OpenAI Build Week, Work & Productivity · **License:** Apache-2.0

---

## The problem

A consultant has a client PDF and wants an AI to summarise the risks in it.
Two bad options today: paste the raw document into a chatbot (a confidentiality
breach), or forgo the AI entirely (lose the leverage). Redaction tools address
the first name-shaped fields, but the real leak is subtler. Three individually
harmless questions can, together, let a capable model re-identify the client
from context alone. That is the mosaic effect, and no entity-based redactor
sees it coming.

## What Privilege does

For each request, on your machine:

1. **Mask locally.** Declared client values and simple PII are replaced with
   placeholders. The raw text never leaves the device.
2. **Attack with GPT-5.6.** The sanitized candidate, plus every sanitized
   payload already sent in this engagement, is handed to GPT-5.6 with one job:
   infer who and what this is about.
3. **Judge against your policy.** Inferred claims are checked against your
   engagement's abstract rules (which themselves carry no real names).
4. **Allow, Transform, or Block**, and write an inspectable **receipt** of what
   was inferred, what was matched, and what was actually transmitted.
5. On Allow, you get the **verified-safe document** to use with any AI tool
   yourself, and restore the real names locally from the reply — or let
   Privilege run the analysis and hand back the restored answer.

GPT-5.6 is the measuring instrument. The threat you are defending against is
frontier-model inference, so the only honest way to measure the risk is to
point a frontier model at the sanitized document and let it try. That is why
the model is structurally load-bearing here, not decorative.

## What Privilege is NOT

- Not anonymity or cryptography, and not a GDPR / HIPAA / DORA certification.
- Not a claim that nothing sensitive reaches the cloud. OpenAI receives
  sanitized text, abstract rules, and prior sanitized payloads.
- Not a replacement for client consent. It is a data-minimisation control.

See **[Masking limits](#masking-limits)** for the specific, tested boundaries.

---

## Quick start for judges (no API key, ~60 seconds)

```bash
git clone https://github.com/prasadt1/privilege
cd privilege
python3.11 -m venv .venv          # 3.11+ required
.venv/bin/pip install -e ".[dev,files]"
.venv/bin/python -m pytest -q     # expect: 78 passed
```

**See real GPT-5.6 results with no key and no spend.** A prefilled vault from a
live run ships in the repo:

```bash
.venv/bin/python -m src.server_http --db demo/demo-vault.sqlite3
# open http://127.0.0.1:7077, paste the engagement id below into
# "eng_... from a saved vault", and click "Load existing"
.venv/bin/python -c "import sqlite3; print(list(sqlite3.connect('demo/demo-vault.sqlite3').execute('select id from engagements'))[0][0])"
```

The receipts feed shows four turns: three Allows with prior disclosures
climbing 0, 1, 2, then a Transform at 3. Expand a receipt to read exactly what
GPT-5.6 inferred, including the turn where it re-identifies the protected
corridor **by description**, with no name present.

**Run the offline flow yourself** (mock attacker, no key; note the mock infers
nothing, so every decision is Allow by design):

```bash
.venv/bin/python demo/seed.py --mock
```

**Run it live** (needs `OPENAI_API_KEY`, costs a few cents):

```bash
export OPENAI_API_KEY=sk-...
PRIVILEGE_MODEL=gpt-5.6-terra .venv/bin/python demo/seed.py --live
```

A full manual test pass is in **[TESTING.md](TESTING.md)**.

---

## Interfaces

All three share one local service (`src/service.py`).

**CLI**

```bash
privilege --mock init-engagement --name "My review" --policy-file policies/restructuring.json
privilege --mock import   --engagement eng_... --file notes.pdf
privilege --live preflight --engagement eng_... --document doc_... --task "Summarise the risks."
privilege --live analyze   --engagement eng_... --document doc_... --task "Summarise the risks."
privilege --live export-safe --engagement eng_... --document doc_... --output safe.txt --mapping map.json
privilege --mock rehydrate --engagement eng_... --file model-reply.txt --output restored.txt
privilege --mock status    --engagement eng_...
```

`export-safe` runs the same attacker check, then writes the redacted document
and a placeholder→real mapping for paste into ChatGPT, Claude, or another tool.
Paste the model reply into `rehydrate` to put real names back on this machine.

Files accepted: `.txt`, `.md`, `.pdf`, `.docx`, extracted locally. Spreadsheets,
slides, and scanned images are refused with a clear "not supported yet".

**Local web UI** — `python -m src.server_http --db vault.sqlite3`, then
`http://127.0.0.1:7077`. A policy form with templates (no raw JSON required), a
live preview of exactly what the model would receive as policy, file upload, a
three-column raw / sanitized / restored view, export for paste into another AI
tool with local name restore, and the receipts feed. The header shows whether
you are in Live, Mock, or unconfigured mode.

**Thin MCP adapter** (optional) — see [`MCP.md`](MCP.md). Install extras with
`pip install -e ".[mcp]"`, then `python -m src.server_mcp`. Exposes `preflight`,
`analyze`, `status`. It has no raw-text or mapping tools by design. Quick path:
run [`install-mcp.command`](install-mcp.command) to print a ready-to-paste config
for Codex / Cursor / Claude Desktop.

**Local viewer, double-click:** macOS [`run.command`](run.command) · Windows
[`run.bat`](run.bat) (still needs Python 3.11+ on the machine).

---

## Evaluation

Ten hand-authored scenarios ([`eval/scenarios.py`](eval/scenarios.py)) were
frozen and committed **before** the runner and results. Each is a sequence of
disclosures with a labelled expected decision. Two modes run over them: a
`baseline` that checks each prompt independently, and the shipped `treatment`
that checks cumulatively.

One live GPT-5.6 run, published unchanged:

| Metric | Baseline | Cumulative treatment |
|---|---:|---:|
| Protected-fact leak recall | 0.429 (3/7) | **0.571 (4/7)** |
| False-block rate | 0.0 | 0.0 |
| Task-fact retention | 1.0 | 1.0 |

**Read this honestly.** The advantage is one turn across seven protected cases;
seven cases cannot support a strong efficacy claim. Absolute recall of 0.571
means the prototype **misses more than 40% of authored leaks**. What the result
does show is directional and matters: cumulative checking caught more, at zero
false blocks and full task-fact retention, so it did not "win" by blocking
everything. The full method, the invalid first run that a fail-closed outage
produced, and why the numbers are not re-rolled are in
[`eval/README.md`](eval/README.md).

Reproduce (needs a key):

```bash
PRIVILEGE_MODEL=gpt-5.6-terra .venv/bin/python eval/run.py --live --output eval/results.live.json
```

---

## Masking limits

Privilege is two layers. Local masking is layer one, deterministic and
best-effort. The cumulative GPT-5.6 attack is layer two, and it is the
load-bearing control: it reads the sanitized candidate the way the frontier
model will and refuses to proceed if the client is inferable. A name that slips
past the masker in readable form is exactly what the attacker is there to catch,
because the model reads a lookalike as the real name.

The masker was hardened across two adversarial review passes (each a fan-out of
independent attackers, every claimed break re-verified). Where it stands:

- **Handled, and regression-tested:** case, extra whitespace, line breaks (as
  PDF extraction produces them), run-together words, fullwidth and accented
  forms, invisible and formatting characters (zero-width, bidi, tag block,
  Hangul and Braille fillers), combining marks, and Cyrillic, Greek, Armenian,
  Cherokee, Coptic, and Latin-block lookalike letters. Folding is one-to-one, so
  masking never corrupts adjacent text, and text outside a match is returned
  byte for byte (German, French, and CJK documents round-trip exactly).
- **Known residual, by construction:** deterministic matching cannot be complete
  against all of Unicode. A document that deliberately embeds an exotic lookalike
  not in the confusables table (some Lisu letters, a digit substituted for a
  letter, a rare phonetic glyph) can still carry a declared name through layer
  one. Full coverage would need the Unicode confusables data set and would still
  lag new code points. This residual is why layer two exists and is load-bearing.
- **By design, not a bug:** a proper noun written into an *abstract rule* that is
  not on the protected list is sent as written. The web UI warns when a
  capitalised term in a rule is not protected. Only values you declare are masked.

Everything fails closed: an unreadable file, a missing key, a malformed model
response, or an exhausted repair round becomes Block, never a silent send.

---

## How this was built

The core was built in **Codex with GPT-5.6** across four sessions: the vault and
policy model, the deterministic sanitizer, the fail-closed preflight and repair
loop with receipts, the OpenAI client, and the frozen evaluation harness. Every
Python commit for that core is a Codex session; the build plan is in
[`CODEX-SESSIONS.md`](CODEX-SESSIONS.md).

After the Codex usage quota was exhausted, the remaining work was completed
outside Codex and is disclosed plainly: file intake (`src/intake.py`), the
policy form and mode indicator in the web UI, the demo seed script, the security
hardening that followed two adversarial review passes, and this documentation.
Files carrying that work say so in their own docstrings, and `git log` shows the
split.

GPT-5.6 is used at runtime as the blind attacker and policy judge.

## Prior art

Privilege reimplements, for coding and consulting agents, the receipts-and-audit
pattern the author first built in **Engram** (a different domain). No Engram code
was copied. Related work in this space, disclosed because the pieces exist
separately even though this composition does not:
[Hey Jude](https://github.com/sure-scale/hey-jude) (re-identification critic and
audit logs), [CAMP](https://github.com/aman-panjwani/camp) (cumulative PII
exposure), PlanTwin (per-object disclosure budgets), and Microsoft Presidio
(entity redaction, a commodity component here). Privilege's narrow claim is
engagement-defined **semantic** facts, checked cumulatively, with receipts, for
the solo practitioner.

## Repository

`src/` the service, `web/` the local UI, `eval/` the frozen evaluation,
`demo/` the seed and prefilled vault, `policies/` example policies, `tests/`.
Design in [`SPEC.md`](SPEC.md), manual test pass in [`TESTING.md`](TESTING.md).
