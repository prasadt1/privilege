# Devpost gallery — Privilege

Upload from `docs/media/`. Captions are **≤100 characters** for the Devpost form.

## Upload order (recommended)

| # | File | Gallery title | Caption (≤100) | Chars |
|---|------|---------------|----------------|------:|
| 1 | `consultant-workflow.png` | Consultant workflow | PDF in → attest → GPT-5.6 attack → anonymized PDF out → restore names. | 70 |
| 2 | `architecture.png` | Trust boundary | Raw docs stay local. OpenAI only sees sanitized text and abstract rules. | 72 |
| 3 | `viewer-three-column.png` | Step UI · anonymized PDF | Step UI: Allow under policy, then download the anonymized PDF. | 62 |
| 4 | `receipt-expanded.png` | Receipt · mosaic Transform | Live GPT-5.6 receipt: mosaic Transform when the corridor is re-identified. | 74 |
| 5 | `policy-form.png` | Policy + abstracted preview | Engagement policy fields next to the abstracted preview OpenAI would see. | 73 |
| 6 | `codex/codex-session-gpt56.png` | Codex CLI · GPT-5.6 | Codex CLI with GPT-5.6: vault, sanitizer, attack loop — runtime attacker. | 73 |

## Embedded in the story vs gallery-only

**Usually in the lean article embeds:** workflow, viewer, receipt (and sometimes architecture).  
**Still upload them to the gallery** — Devpost gallery is separate from story embeds; judges browse both.

**Extra vs the lean story (upload these too):**
- `policy-form.png` — policy UX without cluttering the story
- `codex/codex-session-gpt56.png` — Codex evidence (strong for Build Week)

## Do not upload

| File | Why |
|------|-----|
| `consultant-workflow-a.png` | Archive / duplicate story |
| `consultant-workflow-b.png` | Duplicate of #1 |
| `codex/codex-session-resume.png` | Redundant with #6 |
| `codex/codex-terminal-alt.png` | Weaker / redundant |
| Video files | Upload to YouTube, not the image gallery |

Regenerate PNGs: [`tools/devpost-gallery/REGENERATE.md`](../../tools/devpost-gallery/REGENERATE.md).
