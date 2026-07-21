# Regenerating Privilege Devpost gallery images

Outputs land in `docs/media/` (PNG filenames embedded in the Devpost story).
Demo **videos** are gitignored — upload to YouTube; do not commit `.mp4`/`.webm`.

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

## UI captures

```bash
# from repo root
.venv/bin/python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077
```

```bash
cd tools/devpost-gallery
node capture-ui.mjs
node capture-architecture.mjs
```

## PDF lifecycle demo recording (local only)

Videos are not committed. Fixture PDF is:

`tools/devpost-gallery/fixtures/client-brief.pdf`

```bash
# from repo root
rm -f /tmp/privilege-pdf-demo.sqlite3
PRIVILEGE_MOCK=1 PRIVILEGE_DEMO_ATTACK=1 \
  .venv/bin/python -m src.server_http --db /tmp/privilege-pdf-demo.sqlite3 --mock --port 7077

cd tools/devpost-gallery
# optional live ChatGPT: node setup-chatgpt-profile.mjs  (profile is gitignored)
./run-full-demo.sh
# → docs/media/privilege-pdf-lifecycle.mp4 (gitignored)
```

Rebuild fixture:

```bash
.venv/bin/python tools/devpost-gallery/fixtures/build-client-brief.py
```

## Gallery index

Titles and captions: `docs/media/DEVPOST-GALLERY.md`.
