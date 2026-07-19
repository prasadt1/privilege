# Submission checklist — Prasad owns the human parts

Admins: **you** name the project and write the Devpost description.
Do not paste AI prose into Devpost.

## Before Tuesday 5:00 PM PT

- [ ] Re-verify deadline on the admin posts
- [ ] Create Devpost submission page (editable until deadline)
- [ ] Open primary **Codex** session with GPT-5.6, run Session 1 from
      `CODEX-SESSIONS.md` (or re-implement/verify core there), capture
      `/feedback` Session ID into `.openai_session_id` (gitignored)
- [x] Project name: **Privilege** (package/CLI `privilege`)
- [ ] Repo public + `LICENSE`, or private shared with
      `testing@devpost.com` and `build-week-event@openai.com`
- [ ] Video ≤3 min on YouTube (Unlisted OK), incognito-tested
- [ ] Video audio narrates **Codex + GPT-5.6** usage honestly
- [ ] Description in **your** voice (outline below — rewrite, don't paste)

## Devpost outline (rewrite in first person)

1. **What I built** — one paragraph: local preflight that checks whether the
   next sanitized prompt, plus what OpenAI has already seen, reveals an
   engagement-confidential fact.
2. **Why** — client docs, wanting AI help, not pasting raw; mosaic leaks.
3. **How GPT-5.6 is load-bearing** — blind attacker + policy judge on
   sanitized text; Codex for the build sessions I cite.
4. **Trust boundary** — what stays local vs what still goes to OpenAI.
5. **Related work** — Hey Jude, CAMP, PlanTwin, SEMSIEDIT, Presidio; narrow wedge.
6. **Eval** — baseline vs cumulative; point at `eval/results.json`.
7. **What's next** — multi-provider ledgers later; not claiming compliance.

## Video shot list

1. Terminal: `python demo/seed.py --run-demo --mock` — Allow ×3, Block on #4
2. Browser: `http://127.0.0.1:7077` — raw vs sanitized vs receipt
3. Flash `eval/results.json` summary table
4. Close on repo URL + name

## Honest disclosure if Cursor helped package

If Codex did not author every line of the cited core, say so in the video and
README. Prefer: re-run Sessions 1–2 in Codex on a clean branch so the
`/feedback` ID matches the implementation story.
