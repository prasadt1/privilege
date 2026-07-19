# Build Week — session handoff

> Read this first. It is written for a **fresh** Claude / Codex / Cursor session
> with no prior context. Everything you need is here or in `SPEC.md` beside it.
>
> **Last updated:** Sun 19 Jul 2026, 18:35 CEST

---

## 1. What this project is

A **local engagement-policy confidentiality preflight** for consultants and
freelancers. Raw client documents stay on the laptop. Before GPT-5.6 analyzes
anything, the tool sanitizes known values locally, then uses GPT-5.6 as a
**blind attacker** against the sanitized candidate **plus** prior sanitized
disclosures to the same destination. If a protected business fact becomes
inferable, it Transforms or Blocks and writes an inspectable receipt.

**Pitch:** Existing tools protect identities. This one protects engagement
confidentiality — cumulatively — before the model sees your next prompt.

**Track:** Work & Productivity · **Hackathon:** OpenAI Build Week
**Deadline:** Tue 21 Jul 2026, 5:00 PM PT (= Wed 22 Jul, 2:00 AM CEST)
**⚠ Verify the deadline yourself** against admin posts.

Full technical spec: **`SPEC.md`**.

---

## 2. Status

Design locked and **implemented** (Sun 19 Jul evening). Working tree includes
`src/`, `web/`, `eval/`, `demo/`, tests (19 passing), and mock eval results
showing baseline leak recall ≪ treatment. Engram/Qwen untouched.

```
OpenAI-hackathon/
├── SPEC.md  HANDOFF.md  CODEX-SESSIONS.md  README.md  SUBMISSION.md
├── src/     store, policy, sanitize, preflight, service, cli, http, mcp
├── web/     index.html
├── eval/    scenarios.py, run.py, results.json
├── demo/    seed.py
└── tests/
```

**Still required from Prasad:** project name, Devpost page + own-voice
description, Codex `/feedback` Session ID (re-run Sessions 1–2 in Codex for a
clean citation story), video.

---

## 3. Hard constraints (compliance-critical — do not quietly relax)

1. **The majority of core functionality must be built IN CODEX**, and the video
   narrates that. If another tool writes the cited core, the submission is
   misrepresented.
2. **Use GPT-5.6** for implementation passes that get cited **and** for the
   runtime attacker/judge (structurally load-bearing — not decorative).
3. **Capture the `/feedback` Session ID** from the primary Codex thread EARLY.
4. **Clean-room.** Do NOT copy code from Engram (`~/qwen hackathon/engram`).
   Engram is frozen. Disclose only as conceptual prior art for receipts if needed.
5. **Prasad names the project.** Admin rule: don't let AI name it.
6. **The Devpost description must be written by Prasad**, not pasted AI prose.
7. **Honest trust boundary.** Claim: raw docs + mappings stay local; OpenAI
   receives sanitized text + abstract rules + prior sanitized disclosures to
   OpenAI. Do **not** claim anonymity, GDPR/HIPAA compliance, or "nothing
   sensitive ever reaches the cloud."

---

## 4. Role split

| Tool | Role |
|---|---|
| **Codex (GPT-5.6)** | Writes the cited implementation. Compliance-critical path. |
| **Claude** | Spec, review, architecture critique, submission checklist. |
| **Cursor** | Peripheral work (docs polish, packaging helpers). Keep cited core in Codex. |

If asked to write core implementation outside Codex, push back and point here —
unless Prasad explicitly overrides for a time-boxed rescue build (then disclose
honestly in the video/README what was built where).

---

## 5. Prior art (disclose — do not overclaim novelty)

| Project | What it already does |
|---|---|
| **Hey Jude** | Local anonymize → Presidio → re-id critic → audit logs → LLM proxy |
| **CAMP** | Cumulative PII exposure scoring across turns |
| **PlanTwin** | Per-object cumulative disclosure budgets (research) |
| **SEMSIEDIT** | Semantic sensitive information rewriting (research) |
| **Presidio** | Entity detection / redaction |

**Our narrow wedge:** engagement-defined **semantic** confidential facts (not
just PII entities) + cumulative sanitized disclosures + Allow/Transform/Block
receipts + solo-practitioner surfaces (CLI / local web / thin MCP).

---

## 6. Immediate next actions

1. Create the Devpost submission page (empty is fine).
2. Open primary Codex session, grab `/feedback` Session ID, store it safely.
3. Pick the name (repo + package + README).
4. Run Session 1 from `CODEX-SESSIONS.md`.

---

## 7. Scope decision rule

Build in the spec's order. If Monday evening arrives without the core solid
(store + sanitizer + preflight loop + receipts + eval), cut in this order:
**PDF import → MCP adapter → UI polish**. Never cut the sanitizer tests,
cumulative ledger, attack/repair loop, receipts, eval, or runnable CLI demo.

---

## 8. Open decisions the author owns

- [ ] Project name
- [ ] Deadline re-verified against admin posts
- [ ] Repo public, or private + shared with `testing@devpost.com` and
      `build-week-event@openai.com`
- [ ] `/feedback` Session ID captured

---

## 9. Working directory

```
~/OpenAI-hackathon/
```

Engram (frozen, do not touch): `~/qwen hackathon/engram`
