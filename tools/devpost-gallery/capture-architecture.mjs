#!/usr/bin/env node
/**
 * Render architecture.html + consultant-workflow.html → docs/media/
 * Usage: node capture-architecture.mjs
 */
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const MEDIA = join(ROOT, 'docs/media');

async function launch() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return await chromium.launch();
  }
}

async function shot(browser, htmlName, outName, { width = 1440, height = 1080 } = {}) {
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: 2,
  });
  await page.goto('file://' + join(__dirname, htmlName));
  await page.waitForTimeout(250);
  const out = join(MEDIA, outName);
  // Clip to #frame so content-height pages don't leave empty bands in the PNG
  await page.locator('#frame').screenshot({ path: out });
  await page.close();
  console.log('wrote', out);
}

mkdirSync(MEDIA, { recursive: true });
const browser = await launch();
await shot(browser, 'architecture.html', 'architecture.png', { width: 1440, height: 1200 });
// Article embed uses consultant-workflow.png — ship cleaned visual B there.
// Keep text-heavy A as consultant-workflow-a.png for reference.
await shot(browser, 'consultant-workflow.html', 'consultant-workflow-a.png', { width: 1440, height: 1200 });
await shot(browser, 'consultant-workflow-b.html', 'consultant-workflow.png', { width: 1440, height: 1200 });
await shot(browser, 'consultant-workflow-b.html', 'consultant-workflow-b.png', { width: 1440, height: 1200 });
await browser.close();
