# Devpost gallery — Privilege

Regenerate: see [`tools/devpost-gallery/REGENERATE.md`](../../tools/devpost-gallery/REGENERATE.md).

Embeds in the project story use raw GitHub URLs under `docs/media/`. Upload the
same PNGs to the Devpost image gallery with the titles below.

| File | Gallery title | Caption |
|------|---------------|---------|
| `consultant-workflow.png` | Consultant workflow | Import once, ask many times: local vault → policy → GPT-5.6 preflight → Allow / Transform / Block → restored answer. Optional MCP path never hands raw files to the agent. |
| `architecture.png` | Trust boundary | Raw documents, the vault, and restored output stay on the laptop. OpenAI receives only sanitized text, abstract rules, and prior sanitized payloads. |
| `viewer-three-column.png` | Three columns: local, sent, restored | Left never leaves the machine; middle is exactly what OpenAI receives; right is restored locally. Every decision writes a receipt. |
| `receipt-expanded.png` | Receipt: GPT-5.6 inferences on the mosaic turn | Prior disclosures climb; on the Transform turn the attacker re-identifies the corridor by description. Nothing staged — committed live vault. |
| `policy-form.png` | Policy form + what OpenAI would receive | Templates and plain-English rules; the preview shows the abstracted policy the judge model sees — no real names. |
| `eval-table.png` | Live eval: cumulative vs per-prompt | Frozen scenarios, one live GPT-5.6 run, published unchanged. Cumulative checking 4/7 vs 3/7 at zero false blocks. |

Suggested Devpost gallery order: workflow → architecture → viewer → receipt → policy → eval.
