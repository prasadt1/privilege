#!/usr/bin/env node
/**
 * Record v2 of the ~3:00 silent product demo (VIDEO-SCRIPT.md beats).
 *
 * v2 adds document file import + Download text / Download mapping after export.
 * Leaves privilege-demo-3min(.mp4|.webm) and *-v1.* untouched.
 *
 * Prerequisites:
 *   PRIVILEGE_MOCK=1 .venv/bin/python -m src.server_http --db demo/demo-vault.sqlite3 --mock
 *
 * Usage:
 *   node record-demo-3min-v2.mjs
 *
 * Outputs:
 *   docs/media/privilege-demo-3min-v2.webm
 *   docs/media/privilege-demo-3min-v2.mp4
 */
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const MEDIA = join(ROOT, 'docs/media');
const TMP = join(MEDIA, '.demo-record-tmp-v2');
const FIXTURE = join(__dirname, 'fixtures/engagement_notes.txt');
const BASE = process.env.PRIVILEGE_URL || 'http://127.0.0.1:7077';
const LIVE_ENGAGEMENT = 'eng_2d90da2c94224fccad51a15fb398c3dc';
const WIDTH = 1280;
const HEIGHT = 800;

const sleep = (page, ms) => page.waitForTimeout(ms);

async function launch() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return await chromium.launch();
  }
}

function findWebm(dir) {
  const files = readdirSync(dir).filter((f) => f.endsWith('.webm'));
  if (!files.length) throw new Error(`No .webm under ${dir}`);
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

async function markLiveBadge(page, detail) {
  await page.evaluate((d) => {
    const el = document.getElementById('mode');
    el.textContent = 'Live, gpt-5.6';
    el.className = 'mode-badge live';
    el.title = d;
  }, detail);
}

async function clickDownload(page, selector, noticeNeedle) {
  await page.locator(selector).evaluate((el) => el.click());
  if (noticeNeedle) {
    await page.waitForFunction(
      (needle) => (document.getElementById('notice')?.textContent || '').includes(needle),
      noticeNeedle,
      { timeout: 5000 },
    ).catch(() => {});
  }
  await sleep(page, 800);
}

async function main() {
  mkdirSync(MEDIA, { recursive: true });
  rmSync(TMP, { recursive: true, force: true });
  mkdirSync(TMP, { recursive: true });

  const t0 = Date.now();
  const beat = (label) => {
    const s = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`[${s}s] ${label}`);
  };

  const browser = await launch();
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
    acceptDownloads: true,
    recordVideo: { dir: TMP, size: { width: WIDTH, height: HEIGHT } },
  });
  const page = await context.newPage();

  beat('open viewer');
  const res = await page.goto(BASE, { waitUntil: 'networkidle' });
  if (!res || !res.ok()) throw new Error(`Server not reachable at ${BASE}`);
  await markLiveBadge(page, 'Demo recording v2 — file import + export downloads; Transform receipts are live GPT-5.6.');
  await sleep(page, 2500);

  beat('What is this?');
  await page.click('#what-toggle');
  await sleep(page, 12000);
  await page.click('#what-toggle');
  await sleep(page, 2000);

  beat('See the flow');
  await page.click('#flow-toggle');
  await page.waitForSelector('#flow-modal.open');
  await sleep(page, 10000);
  await page.click('#flow-close');
  await sleep(page, 2000);

  beat('Step 1 — policy');
  await page.locator('#step-1').scrollIntoViewIfNeeded();
  await sleep(page, 3500);
  await page.locator('#protected').click();
  await sleep(page, 2000);
  await page.locator('#rules').click();
  await sleep(page, 2500);
  await page.fill('#name', 'Northwind operating review');
  await sleep(page, 1500);

  beat('Step 1 — download policy JSON');
  await page.evaluate(() => {
    const adv = document.querySelector('details.adv');
    if (adv) adv.open = true;
  });
  await sleep(page, 2000);
  await page.locator('#download').scrollIntoViewIfNeeded();
  await clickDownload(page, '#download', 'Policy downloaded');
  await sleep(page, 2500);

  beat('Create engagement');
  await page.click('#create');
  await page.waitForFunction(() => !document.getElementById('step-2')?.classList.contains('locked'), {
    timeout: 15000,
  });
  await sleep(page, 3500);

  beat('Step 2 — file import');
  await page.locator('#step-2').scrollIntoViewIfNeeded();
  await sleep(page, 3000);
  await page.locator('.filebtn').scrollIntoViewIfNeeded();
  await sleep(page, 2000);
  await page.setInputFiles('#file', FIXTURE);
  await page.waitForFunction(() => !document.getElementById('step-3')?.classList.contains('locked'), {
    timeout: 20000,
  });
  await page.locator('#step-2 .step-edit').click().catch(() => {});
  await sleep(page, 4000);
  await page.locator('#step-3 .step-head').click().catch(async () => {
    await page.evaluate(() => {
      document.getElementById('step-3')?.classList.add('active');
      document.getElementById('step-2')?.classList.remove('active');
    });
  });
  await sleep(page, 2500);

  beat('Step 3 — export');
  await page.locator('#step-3').scrollIntoViewIfNeeded();
  await sleep(page, 4500);
  await page.click('#export-safe');
  await page.waitForFunction(
    () => {
      const strip = document.getElementById('safe-strip');
      const sub = document.getElementById('s3-sub')?.textContent || '';
      return (strip && strip.classList.contains('show')) || sub.includes('safe document');
    },
    { timeout: 60000 },
  );
  await sleep(page, 2000);
  await page.locator('#step-3 .step-edit').click();
  await page.waitForSelector('#export-result', { state: 'visible', timeout: 10000 });
  await page.locator('#step-3').scrollIntoViewIfNeeded();
  await sleep(page, 8000);

  beat('Download text + mapping + copy');
  await clickDownload(page, '#download-safe', 'Safe text downloaded');
  await sleep(page, 2500);
  await clickDownload(page, '#download-map', 'Mapping downloaded');
  await sleep(page, 2500);
  await page.click('#copy-safe');
  await sleep(page, 2500);

  beat('Simulated external AI paste');
  const safeSnippet = (await page.locator('#sanitized').innerText()).trim().slice(0, 420);
  await page.evaluate((text) => {
    document.getElementById('demo-chatgpt-card')?.remove();
    const card = document.createElement('div');
    card.id = 'demo-chatgpt-card';
    card.style.cssText = [
      'position:fixed', 'inset:0', 'z-index:70',
      'display:flex', 'align-items:center', 'justify-content:center',
      'padding:24px',
      'background:color-mix(in oklch, var(--canvas) 35%, black 65%)',
    ].join(';');
    card.innerHTML = `
      <div style="width:min(640px,100%);background:#212121;color:#ececec;border-radius:16px;padding:22px;font-family:ui-sans-serif,system-ui,sans-serif;">
        <div style="font-size:13px;color:#9b9b9b;margin-bottom:12px;">ChatGPT · new chat (simulated)</div>
        <div style="background:#2f2f2f;border-radius:12px;padding:14px 16px;font-size:14px;line-height:1.5;white-space:pre-wrap;max-height:220px;overflow:auto;">${text.replace(/</g, '&lt;')}</div>
        <div style="margin-top:14px;background:#2f2f2f;border-radius:12px;padding:14px 16px;font-size:14px;line-height:1.5;color:#d0d0d0;">
          Depot leases look time-sensitive before Q3. I’d flag corridor cost pressure and ask whether footprint changes are already decided — without naming the operator.
        </div>
      </div>`;
    document.body.appendChild(card);
  }, safeSnippet || '[VALUE_1] operates 14 depots…');
  await sleep(page, 12000);
  await page.evaluate(() => document.getElementById('demo-chatgpt-card')?.remove());
  await sleep(page, 1500);

  beat('Step 4 — restore');
  const reply =
    'Summary: the operator should review depot leases before Q3 renewal. ' +
    'Prioritize cost pressure on the corridor described as [VALUE_2]. ' +
    'No announcement yet regarding [VALUE_1] footprint changes.';
  await page.locator('#step-4 .step-edit').click().catch(async () => {
    await page.evaluate(() => {
      const el = document.getElementById('step-4');
      el.classList.remove('locked', 'complete');
      el.classList.add('active');
      document.getElementById('step-3')?.classList.remove('active');
    });
  });
  await sleep(page, 2000);
  await page.fill('#model-reply', reply);
  await sleep(page, 3500);
  await page.click('#rehydrate');
  await page.waitForSelector('#restored-box', { state: 'visible', timeout: 15000 });
  await page.locator('#step-4').scrollIntoViewIfNeeded();
  await sleep(page, 9000);

  beat('Load live demo engagement for mosaic');
  await page.locator('#step-1 .step-edit').click();
  await sleep(page, 1200);
  await page.locator('#step-1').scrollIntoViewIfNeeded();
  await page.click('#load-toggle');
  await sleep(page, 1500);
  await page.fill('#load-id', LIVE_ENGAGEMENT);
  await sleep(page, 1200);
  await page.click('#load');
  await page.waitForFunction(
    () => document.getElementById('receipts')?.querySelectorAll('details.receipt').length > 0,
    { timeout: 20000 },
  );
  await markLiveBadge(page, 'Receipts from committed live GPT-5.6 demo vault.');
  await sleep(page, 3000);

  beat('Receipts · Transform');
  await page.locator('#receipts-fold').scrollIntoViewIfNeeded();
  await page.evaluate(() => {
    document.getElementById('receipts-fold').open = true;
  });
  await sleep(page, 2500);

  const receipts = page.locator('#receipts details.receipt');
  const count = await receipts.count();
  let transform = null;
  for (let i = 0; i < count; i++) {
    const text = ((await receipts.nth(i).locator('summary .rd').textContent()) || '').trim().toLowerCase();
    if (text === 'transform') {
      transform = receipts.nth(i);
      break;
    }
  }
  if (!transform && count > 0) transform = receipts.nth(0);
  if (transform) {
    await transform.locator('summary').click();
    await sleep(page, 14000);
  } else {
    console.warn('No Transform receipt found');
    await sleep(page, 8000);
  }

  beat('End card');
  await page.evaluate(() => {
    document.getElementById('demo-end-card')?.remove();
    const card = document.createElement('div');
    card.id = 'demo-end-card';
    card.style.cssText = [
      'position:fixed', 'inset:0', 'z-index:80',
      'display:flex', 'align-items:center', 'justify-content:center',
      'padding:24px',
      'background:color-mix(in oklch, var(--canvas) 40%, black 65%)',
    ].join(';');
    card.innerHTML = `
      <div style="width:min(560px,100%);background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:28px;">
        <div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);margin-bottom:10px;">Privilege · demo v2</div>
        <div style="font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-bottom:10px;">Attack, verify, show your work.</div>
        <p style="color:var(--muted);font-size:15px;line-height:1.55;margin:0 0 14px;">
          Core vault, sanitizer, attack loop, and eval were built in Codex with GPT-5.6.
          GPT-5.6 is the attacker — not a decorative model call.
        </p>
        <p style="color:var(--amber);font:700 15px var(--sans);margin:0;">github.com/prasadt1/privilege</p>
      </div>`;
    document.body.appendChild(card);
  });
  await sleep(page, 14000);

  const elapsed = (Date.now() - t0) / 1000;
  beat(`closing (elapsed ${elapsed.toFixed(1)}s)`);

  await context.close();
  await browser.close();

  const webmSrc = findWebm(TMP);
  const webmOut = join(MEDIA, 'privilege-demo-3min-v2.webm');
  const mp4Out = join(MEDIA, 'privilege-demo-3min-v2.mp4');
  copyFileSync(webmSrc, webmOut);
  rmSync(TMP, { recursive: true, force: true });

  console.log(`Wrote ${webmOut}`);
  if (toMp4(webmOut, mp4Out)) {
    const probe = execFileSync(
      'ffprobe',
      ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', mp4Out],
      { encoding: 'utf8' },
    ).trim();
    const dur = Number(probe);
    if (dur > 180) {
      const capped = join(MEDIA, 'privilege-demo-3min-v2-cap.mp4');
      execFileSync('ffmpeg', ['-y', '-i', mp4Out, '-t', '00:02:55', '-c', 'copy', capped], { stdio: 'inherit' });
      copyFileSync(capped, mp4Out);
      rmSync(capped, { force: true });
      console.log(`Trimmed to 2:55 (was ${dur.toFixed(1)}s)`);
    }
    console.log(`Wrote ${mp4Out}`);
  }
  console.log(`v2 recorded ${elapsed.toFixed(1)}s. v1 left untouched.`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
