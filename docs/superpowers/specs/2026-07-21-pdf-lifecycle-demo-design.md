# PDF lifecycle demo — design (8h pivot)

**Date:** 2026-07-21  
**Status:** Implemented (prototype)

## Goal

Consultant value prop: upload client **PDF** → anonymized **PDF** out → GPT-5.6 attacker findings → revise → revised PDF for any AI.

## Scope (tonight)

1. PDF-only primary path (Word/PPT on roadmap)
2. Option A revise: Privilege’s own attacker / Transform rewrite (not paste-from-ChatGPT)
3. Anonymized PDF is rebuilt from sanitized text (not layout-faithful redaction of the original)

## Surfaces

- `src/pdf_out.py` — text → PDF
- `PrivilegeService.export_safe` — adds `safe_pdf_base64`, `inferred_claims`, `matched_rules`, `repair_rounds`
- UI step 2/3 — upload PDF, Anonymize PDF, findings, Download PDF, Attack again → revise
- `PRIVILEGE_DEMO_ATTACK=1` with mock — offline Transform-then-Allow for demos
- Fixture: `tools/devpost-gallery/fixtures/client-brief.pdf`
- Recording: `docs/media/privilege-pdf-lifecycle.mp4`
