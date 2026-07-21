#!/usr/bin/env node
/**
 * Record the "See the flow" walkthrough modal as a short demo video.
 *
 * Prerequisites: Privilege HTTP server on :7077, e.g.
 *   PRIVILEGE_MOCK=1 .venv/bin/python -m src.server_http --db demo/demo-vault.sqlite3 --mock
 *
 * Usage: node record-flow-walkthrough.mjs
 *
 * Outputs:
 *   docs/media/flow-walkthrough.webm
 *   docs/media/flow-walkthrough.mp4  (if ffmpeg is available)
 */
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readdirSync, renameSync, rmSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const MEDIA = join(ROOT, 'docs/media');
const TMP = join(MEDIA, '.flow-record-tmp');
const BASE = process.env.PRIVILEGE_URL || 'http://127.0.0.1:7077';
const WIDTH = 900;
const HEIGHT = 720;

async function launch() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return await chromium.launch();
  }
}

function findWebm(dir) {
  const files = readdirSync(dir).filter((f) => f.endsWith('.webm'));
  if (!files.length) throw new Error(`No .webm written under ${dir}`);
  files.sort((a, b) => statSync(join(dir, b)).mtimeMs - statSync(join(dir, a)).mtimeMs);
  return join(dir, files[0]);
}

function toMp4(webm, mp4) {
  try {
    execFileSync(
      'ffmpeg',
      ['-y', '-i', webm, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4],
      { stdio: 'inherit' },
    );
    return true;
  } catch {
    return false;
  }
}

async function main() {
  mkdirSync(MEDIA, { recursive: true });
  rmSync(TMP, { recursive: true, force: true });
  mkdirSync(TMP, { recursive: true });

  const browser = await launch();
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 2,
    recordVideo: { dir: TMP, size: { width: WIDTH, height: HEIGHT } },
  });
  const page = await context.newPage();

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);

  // Brief beat on the landing UI, then open the walkthrough.
  await page.locator('#flow-toggle').click();
  await page.waitForSelector('#flow-modal.open', { timeout: 5000 });

  // Autoplay is 2.5s × 4 steps; stay for a full loop + one extra step.
  await page.waitForTimeout(2500 * 5);

  await page.locator('#flow-close').click();
  await page.waitForTimeout(600);

  await context.close();
  await browser.close();

  const webmSrc = findWebm(TMP);
  const webmOut = join(MEDIA, 'flow-walkthrough.webm');
  const mp4Out = join(MEDIA, 'flow-walkthrough.mp4');
  copyFileSync(webmSrc, webmOut);
  rmSync(TMP, { recursive: true, force: true });

  console.log(`Wrote ${webmOut}`);
  if (toMp4(webmOut, mp4Out)) {
    console.log(`Wrote ${mp4Out}`);
  } else {
    console.log('ffmpeg convert skipped — webm is ready to play.');
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
