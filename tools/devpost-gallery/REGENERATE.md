# Regenerating Privilege Devpost gallery images

Outputs land in `docs/media/` with the filenames embedded in `SUBMISSION.md`.

## Prerequisites

```bash
cd tools/devpost-gallery
npm install
npm run install-browser
```

Uses the system Chrome channel when available (`channel: 'chrome'`); otherwise
falls back to Playwright Chromium.

## Architecture + consultant workflow

```bash
cd tools/devpost-gallery
node capture-architecture.mjs
# → docs/media/architecture.png
# → docs/media/consultant-workflow.png
```

No separate data-flow diagram: the trust-boundary architecture already shows
what crosses to OpenAI. The workflow diagram is the Work & Productivity story
(how a consultant uses Privilege day-to-day).

## UI captures

Start the local viewer against the committed live-run vault (separate terminal):

```bash
# from repo root
.venv/bin/python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077
```

Then:

```bash
cd tools/devpost-gallery
node capture-ui.mjs
# → docs/media/viewer-three-column.png
# → docs/media/receipt-expanded.png

# policy-form.png is a landscape article card (same content, less scroll):
node capture-architecture.mjs   # also refreshes architecture + workflow
```

## Gallery index

Titles and captions for the Devpost image gallery: `docs/media/DEVPOST-GALLERY.md`.
