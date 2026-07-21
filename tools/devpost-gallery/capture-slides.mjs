#!/usr/bin/env node
/**
 * Capture open / end / Codex slides → docs/media/clips/slides/
 * Usage: node capture-slides.mjs
 */
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const OUT = join(ROOT, 'docs/media/clips/slides');
const CODEX = join(ROOT, 'docs/media/codex/codex-session-gpt56.png');

async function launch() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return await chromium.launch();
  }
}

async function shot(browser, fileUrl, outName) {
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1248 },
    deviceScaleFactor: 2,
  });
  await page.goto(fileUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(200);
  const out = join(OUT, outName);
  await page.locator('#frame').screenshot({ path: out, type: 'png' });
  await page.close();
  console.log('wrote', out);
}

mkdirSync(OUT, { recursive: true });
const browser = await launch();
const slides = join(__dirname, 'slides');
await shot(browser, `file://${join(slides, 'open.html')}`, 'open.png');
await shot(browser, `file://${join(slides, 'end.html')}`, 'end.png');
await shot(
  browser,
  `file://${join(slides, 'codex.html')}?src=${encodeURIComponent(`file://${CODEX}`)}`,
  'codex.png',
);
await browser.close();
