# Flow walkthrough modal — design

**Date:** 2026-07-21  
**Surface:** `web/index.html` (local viewer only)  
**Status:** Approved

## Goal

Explain the four-step export path with a short animated walkthrough, linked from the page header, without driving the real wizard or writing to the vault.

## Entry

- Header control **See the flow** next to **What is this?**
- Opens a **modal overlay** (dimmed backdrop)
- Dismiss: Close button, backdrop click, Escape

## Content

Inline autoplay strip inside the modal:

| Step | Chip label | Caption |
|------|------------|---------|
| 1 | Policy | Name what must stay confidential |
| 2 | Upload | Add the document (file or paste) |
| 3 | Export | Make it safe — mask, attack-verify, copy/download |
| 4 | Restore | Paste the AI reply — restore real names locally |

- Autoplay advances about every 2.5s
- Soft pulse on the active step’s implied action
- Controls: Pause / Play · Replay · Close
- Demo-only: does not unlock steps, call APIs, or mutate vault state

## Tech

- CSS + JS in `web/index.html` only
- No video or new media assets
- `prefers-reduced-motion: reduce` → no autoplay; user advances via Replay / clicking chips (or show step 1 static with manual chip select)

## Out of scope

- Spotlight tour over the live form
- Recording for Devpost / submission embeds
- Changing step labels on the real wizard
