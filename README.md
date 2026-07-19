# Privilege

> **Pitch:** Existing tools protect identities. This one protects engagement
> confidentiality — cumulatively — before GPT-5.6 sees your next prompt.

Local-first **engagement-policy confidentiality preflight** for consultants,
freelancers, and architects. Raw client documents and identity mappings stay on
your laptop. Before analysis, the tool:

1. Masks declared values + simple PII locally
2. Asks **GPT-5.6** to blind-infer claims from the sanitized candidate **plus**
   prior sanitized disclosures already sent to OpenAI
3. Matches those claims against your **abstract engagement rules**
4. Returns **Allow / Transform / Block** and writes an inspectable **receipt**

**Track:** OpenAI Build Week · Work & Productivity  
**License:** Apache-2.0  
**Name:** Privilege (chosen by author — protects engagement-confidential *facts*, not just named entities)

---

## What this is NOT

- Not anonymity, not cryptography, not a GDPR / HIPAA / DORA certification
- Not a claim that “nothing sensitive ever reaches the cloud”
- OpenAI still receives **sanitized** text and **abstract** policy rules
- Only declared values + regex PII are masked before the attack; undeclared
  secrets can still leak

Honest boundary: *raw docs + mappings stay local; cumulative semantic leak risk
on sanitized text is checked before send.*

---

## Quick start (judge path, no rebuild)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Offline mosaic demo (deterministic mock attacker — no API key)
python demo/seed.py --db /tmp/privilege.sqlite3 --run-demo --mock

# Eval (baseline vs cumulative treatment)
python eval/run.py
# → eval/results.json
```

Expected mock story (also in `eval/results.json`):

| Mode | Protected-fact leak recall (mock) |
|---|---|
| Baseline (per-prompt, no ledger) | low (~0.3) |
| Treatment (cumulative preflight) | **1.0** |

Live GPT-5.6 (optional):

```bash
export OPENAI_API_KEY=sk-...
# optional: export PRIVILEGE_MODEL=gpt-5.6
python demo/seed.py --db /tmp/privilege-live.sqlite3 --live --run-demo
```

### CLI

```bash
privilege --mock --db /tmp/privilege.sqlite3 list
privilege --mock --db /tmp/privilege.sqlite3 status --engagement eng_...
privilege --mock --db /tmp/privilege.sqlite3 preflight \
  --engagement eng_... --document doc_... \
  --task "Is an exit from the Nordics on the table?"
```

### Local web UI

```bash
PRIVILEGE_MOCK=1 python -m src.server_http --db /tmp/privilege.sqlite3 --port 7077
# open http://127.0.0.1:7077
```

### Thin MCP adapter (optional)

```bash
pip install -e ".[mcp]"
PRIVILEGE_MOCK=1 python -m src.server_mcp --db /tmp/privilege.sqlite3
```

MCP tools: `preflight`, `analyze`, `status`, `list_documents`.  
**No** raw import / mapping dump tools — setup stays on the CLI/UI side.

---

## Demo arc (90s)

1. Seed the synthetic Helios engagement — show raw values local
2. Three benign analyzes → Allow; ledger grows
3. Fourth question completes a mosaic (“exit” + region + margin)
4. Preflight **Blocks** (or Transforms then re-attacks)
5. Open the receipt; flash baseline vs treatment eval table

---

## Architecture

```
import (local) → sanitize (local) → GPT-5.6 blind infer (sanitized + ledger)
     → GPT-5.6 match abstract rules → rewrite (≤2) → Allow|Transform|Block
     → on Allow: GPT-5.6 analyze → local restore → ledger append + receipt
```

Surfaces share `src/service.py`: CLI · local web · thin MCP.

---

## Related work (disclosed)

| Project | Overlap | Our narrow claim |
|---|---|---|
| [Hey Jude](https://github.com/sure-scale/hey-jude) | Re-id critic + audit logs | Engagement-defined **semantic** facts + cumulative ledger + solo surfaces |
| [CAMP](https://github.com/aman-panjwani/camp) | Cumulative PII exposure | Semantic rules beyond entity types |
| [PlanTwin](https://arxiv.org/abs/2603.18377) | Per-object disclosure budgets | Practitioner preflight with receipts |
| SEMSIEDIT (arxiv 2602.21496) | Semantic sensitive rewrite | Cumulative engagement policy + eval |
| Microsoft Presidio | Entity redaction | Commodity component; not the product |

Conceptual prior art: the author's Engram project (receipts / audit patterns for
a different domain). **No Engram code was copied.**

---

## Codex + GPT-5.6

Build Week requirement: core built with **Codex / GPT-5.6**. Paste prompts from
[`CODEX-SESSIONS.md`](CODEX-SESSIONS.md). Capture `/feedback` Session ID from
Session 1 early.

Runtime: GPT-5.6 is the **attacker and policy judge** — structurally
load-bearing, not decorative.

> **Note for judges:** If any peripheral packaging landed outside Codex, the
> video/README should say so honestly. Cited core sessions remain the Codex
> thread IDs in the submission form.

---

## Project layout

See [`SPEC.md`](SPEC.md) and [`HANDOFF.md`](HANDOFF.md).

---

## Author checklist

- [x] Project name chosen: **Privilege**
- [ ] Write Devpost description in your own voice ([`SUBMISSION.md`](SUBMISSION.md))
- [ ] Create Devpost page early; paste `/feedback` Session ID
- [ ] Record ≤3 min video narrating Codex + GPT-5.6 usage
