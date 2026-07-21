#!/usr/bin/env node
/**
 * Record the end-to-end PDF lifecycle demo (steps 1–4), including live ChatGPT
 * when a logged-in Chrome profile is available.
 *
 * Flow:
 *   policy → upload client-brief.pdf → attest → anonymize (Transform)
 *   → download PDF → attack again (Allow) → download v2
 *   → chatgpt.com attach anonymized PDF → reply → Privilege restore
 *
 * One-time setup (you do this, then leave):
 *   node setup-chatgpt-profile.mjs   # log into ChatGPT, press Enter
 *   ./run-full-demo.sh               # starts server + records
 *
 * Env:
 *   CHATGPT_MODE=live|sim|auto   (default auto: live, fall back to sim)
 *   CHROME_PROFILE=…             (default ./.chrome-profile)
 *   PRIVILEGE_URL=http://127.0.0.1:7077
 *
 * Privilege attacker for offline reliability:
 *   PRIVILEGE_MOCK=1 PRIVILEGE_DEMO_ATTACK=1 on the server
 */
import { execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { FALLBACK_REPLY, runLiveChatGPTOnPage } from './chatgpt-live.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const MEDIA = join(ROOT, 'docs/media');
const CODEX_DIR = join(MEDIA, 'codex');
const TMP = join(MEDIA, '.pdf-lifecycle-tmp');
const FIXTURE = join(__dirname, 'fixtures/client-brief.pdf');
const PROFILE = process.env.CHROME_PROFILE || join(__dirname, '.chrome-profile');
const BASE = process.env.PRIVILEGE_URL || 'http://127.0.0.1:7077';
const MODE = (process.env.CHATGPT_MODE || 'auto').toLowerCase();
const WIDTH = 1280;
const HEIGHT = 800;
const sleep = (page, ms) => page.waitForTimeout(ms);

const CODEX_SLIDES = [
  {
    file: join(CODEX_DIR, 'codex-session-gpt56.png'),
    kicker: 'Built in Codex',
    title: 'Core vault, sanitizer, attack loop — Codex + GPT-5.6',
    body: 'Session evidence: gpt-5.6-terra running tests, edits, and commits in this repo.',
  },
  {
    file: join(CODEX_DIR, 'codex-session-resume.png'),
    kicker: 'Codex session',
    title: 'Resume ID on the thread · model = gpt-5.6-terra',
    body: 'The attack-and-repair loop and eval were implemented in Codex sessions with GPT-5.6 as the coding model.',
  },
];

async function showCodexBeat(page, beat) {
  beat('Codex + GPT-5.6 evidence');
  for (const slide of CODEX_SLIDES) {
    if (!existsSync(slide.file)) {
      console.warn('Missing Codex slide:', slide.file);
      continue;
    }
    const b64 = readFileSync(slide.file).toString('base64');
    await page.evaluate(
      ({ b64, kicker, title, body }) => {
        document.getElementById('demo-codex-card')?.remove();
        const card = document.createElement('div');
        card.id = 'demo-codex-card';
        card.style.cssText = [
          'position:fixed',
          'inset:0',
          'z-index:85',
          'display:flex',
          'flex-direction:column',
          'background:#0b0b0b',
          'color:#f2f2f2',
          'font-family:ui-sans-serif,system-ui,sans-serif',
        ].join(';');
        card.innerHTML = `
          <div style="padding:14px 18px 8px;">
            <div style="font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#f5a623;margin-bottom:6px;">${kicker}</div>
            <div style="font-size:20px;font-weight:800;letter-spacing:-0.02em;margin-bottom:4px;">${title}</div>
            <div style="font-size:13px;color:#b0b0b0;max-width:920px;">${body}</div>
          </div>
          <div style="flex:1;min-height:0;padding:8px 18px 18px;display:flex;align-items:center;justify-content:center;">
            <img alt="Codex session" src="data:image/png;base64,${b64}"
              style="max-width:100%;max-height:100%;object-fit:contain;border-radius:8px;border:1px solid #333;" />
          </div>`;
        document.body.appendChild(card);
      },
      { b64, kicker: slide.kicker, title: slide.title, body: slide.body },
    );
    await sleep(page, 9000);
  }
  await page.evaluate(() => document.getElementById('demo-codex-card')?.remove());
  await sleep(page, 800);
}

function findWebm(dir) {
  const files = readdirSync(dir).filter((f) => f.endsWith('.webm'));
  if (!files.length) throw new Error(`No .webm under ${dir}`);
  files.sort((a, b) => statSync(join(dir, b)).mtimeMs - statSync(join(dir, a)).mtimeMs);
  return join(dir, files[0]);
}

async function typeSlow(page, selector, text, { delay = 18 } = {}) {
  await page.locator(selector).click();
  await page.fill(selector, '');
  await page.type(selector, text, { delay });
}

async function launchContext() {
  mkdirSync(PROFILE, { recursive: true });
  const opts = {
    headless: false,
    viewport: { width: WIDTH, height: HEIGHT },
    acceptDownloads: true,
    recordVideo: { dir: TMP, size: { width: WIDTH, height: HEIGHT } },
    args: ['--disable-blink-features=AutomationControlled'],
  };
  // Prefer system Google Chrome — that's where setup-chatgpt-profile logged in.
  try {
    return await chromium.launchPersistentContext(PROFILE, { ...opts, channel: 'chrome' });
  } catch (chromeErr) {
    console.warn('System Chrome launch failed:', chromeErr.message.split('\n')[0]);
    try {
      return await chromium.launchPersistentContext(PROFILE, opts);
    } catch (chromiumErr) {
      throw new Error(
        [
          'Could not launch a browser for recording.',
          '1) Prefer: open Google Chrome (system) — used for ChatGPT login.',
          '2) Or install Playwright Chromium:',
          '     cd tools/devpost-gallery && npx playwright install chromium',
          `Chrome error: ${chromeErr.message.split('\n')[0]}`,
          `Chromium error: ${chromiumErr.message.split('\n')[0]}`,
        ].join('\n'),
      );
    }
  }
}

async function showSimChatGPT(page, filename, reply) {
  await page.evaluate(
    ({ filename: fn, reply: r }) => {
      document.getElementById('demo-chatgpt-card')?.remove();
      const card = document.createElement('div');
      card.id = 'demo-chatgpt-card';
      card.style.cssText = [
        'position:fixed',
        'inset:0',
        'z-index:70',
        'display:flex',
        'align-items:center',
        'justify-content:center',
        'padding:24px',
        'background:color-mix(in oklch, var(--canvas) 35%, black 65%)',
      ].join(';');
      card.innerHTML = `
      <div style="width:min(700px,100%);background:#212121;color:#ececec;border-radius:16px;padding:22px;font-family:ui-sans-serif,system-ui,sans-serif;">
        <div style="font-size:13px;color:#9b9b9b;margin-bottom:14px;">ChatGPT · fallback handoff (live session unavailable)</div>
        <div style="display:inline-flex;align-items:center;gap:10px;background:#2f2f2f;border:1px solid #3a3a3a;border-radius:10px;padding:10px 12px;margin-bottom:14px;">
          <span style="font-size:18px;">📄</span>
          <div>
            <div style="font-size:13px;font-weight:700;">${fn}</div>
            <div style="font-size:11px;color:#9b9b9b;">Attached · from Privilege download</div>
          </div>
        </div>
        <div style="background:#2f2f2f;border-radius:12px;padding:14px 16px;font-size:14px;line-height:1.5;color:#d0d0d0;">${r.replace(/</g, '&lt;')}</div>
      </div>`;
      document.body.appendChild(card);
    },
    { filename, reply },
  );
  await sleep(page, 10000);
  await page.evaluate(() => document.getElementById('demo-chatgpt-card')?.remove());
}

async function main() {
  mkdirSync(MEDIA, { recursive: true });
  rmSync(TMP, { recursive: true, force: true });
  mkdirSync(TMP, { recursive: true });

  if ((MODE === 'live' || MODE === 'auto') && !existsSync(PROFILE)) {
    console.warn(`No Chrome profile at ${PROFILE}`);
    console.warn('Run: node setup-chatgpt-profile.mjs');
  }

  const t0 = Date.now();
  const beat = (label) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1)}s] ${label}`);

  const context = await launchContext();
  const page = context.pages()[0] || (await context.newPage());

  beat('open Privilege');
  const res = await page.goto(BASE, { waitUntil: 'networkidle' });
  if (!res || !res.ok()) throw new Error(`Server not reachable at ${BASE}`);
  await sleep(page, 2500);

  beat('What is this?');
  await page.click('#what-toggle');
  await sleep(page, 6000);
  await page.click('#what-toggle');
  await sleep(page, 1200);

  beat('Step 1 — policy');
  await page.locator('#step-1').scrollIntoViewIfNeeded();
  await page.selectOption('#template', 'restructuring');
  await sleep(page, 1800);
  await typeSlow(page, '#name', 'Northwind Freight', { delay: 30 });
  await sleep(page, 1000);
  await page.fill('#protected', 'Northwind Freight\nBaltic corridor');
  await page.locator('#protected').dispatchEvent('input');
  await sleep(page, 1500);
  await page.evaluate(() => {
    const adv = [...document.querySelectorAll('details.adv')].find((d) =>
      (d.querySelector('summary')?.textContent || '').includes('Aliases'),
    );
    if (adv) adv.open = true;
  });
  await page.fill('#aliases', 'Northwind = Northwind Freight');
  await page.locator('#aliases').dispatchEvent('input');
  await sleep(page, 1200);
  await page.fill(
    '#rules',
    'Northwind Freight withdrawing from the Baltic corridor is protected until the client announces it',
  );
  await page.locator('#rules').dispatchEvent('input');
  await sleep(page, 2200);

  beat('Create engagement');
  await page.click('#create');
  await page.waitForFunction(() => !document.getElementById('step-2')?.classList.contains('locked'), {
    timeout: 15000,
  });
  await sleep(page, 2500);

  beat('Step 2 — choose client-brief.pdf');
  await page.locator('#filebtn').scrollIntoViewIfNeeded();
  await sleep(page, 2000);
  await page.evaluate(() => {
    document.getElementById('demo-picker')?.remove();
    const card = document.createElement('div');
    card.id = 'demo-picker';
    card.style.cssText =
      'position:fixed;inset:0;z-index:75;display:flex;align-items:center;justify-content:center;padding:24px;background:color-mix(in oklch, var(--canvas) 40%, black 60%)';
    card.innerHTML = `
      <div style="width:min(520px,100%);background:#f6f6f6;color:#1a1a1a;border-radius:12px;overflow:hidden;border:1px solid #d0d0d0;font-family:ui-sans-serif,system-ui,sans-serif;">
        <div style="padding:12px 16px;border-bottom:1px solid #ddd;font-size:13px;font-weight:600;">Open — Select client PDF</div>
        <div style="margin:12px;padding:10px 12px;background:#fff;border:1px solid #c8c8c8;border-radius:8px;display:flex;gap:10px;align-items:center;">
          <span style="font-size:20px;">📄</span>
          <div><div style="font-weight:700;font-size:14px;">client-brief.pdf</div>
          <div style="font-size:12px;color:#666;">PDF · dense operating review</div></div>
          <span style="margin-left:auto;font-size:12px;color:#0a7;font-weight:700;">selected</span>
        </div>
      </div>`;
    document.body.appendChild(card);
  });
  await sleep(page, 3000);
  await page.evaluate(() => document.getElementById('demo-picker')?.remove());

  beat('Step 2 — upload');
  await page.setInputFiles('#file', FIXTURE);
  await page.waitForSelector('#file-selected.show', { timeout: 20000 });
  await page.locator('#file-selected').scrollIntoViewIfNeeded();
  await sleep(page, 4000);
  await page.waitForSelector('#attest-box', { state: 'visible', timeout: 20000 });
  await page.locator('#attest-box').scrollIntoViewIfNeeded();
  await sleep(page, 2500);

  beat('Step 2 — attest');
  await page.check('#attest-check');
  await sleep(page, 1200);
  await page.click('#attest-document');
  await page.waitForFunction(() => !document.getElementById('step-3')?.classList.contains('locked'), {
    timeout: 15000,
  });
  await sleep(page, 2200);

  beat('Step 3 — anonymize (Transform)');
  await page.click('#export-safe');
  await page.waitForSelector('#export-result', { state: 'visible', timeout: 30000 });
  await page.waitForFunction(
    () => (document.getElementById('decision-badge')?.textContent || '').includes('Transform'),
    { timeout: 30000 },
  );
  await sleep(page, 6500);

  async function downloadPdf(label) {
    beat(label);
    await page.locator('#download-pdf').scrollIntoViewIfNeeded();
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      page.locator('#download-pdf').click(),
    ]);
    const suggested = download.suggestedFilename() || 'privilege-anonymized.pdf';
    await page.waitForSelector('#dl-toast.show', { timeout: 5000 }).catch(() => {});
    const tmpPath = join(TMP, suggested);
    await download.saveAs(tmpPath);
    await sleep(page, 3000);
    return { suggested, tmpPath };
  }

  const dl1 = await downloadPdf('Download PDF v1');
  await page.evaluate((filename) => {
    document.getElementById('demo-pdf-preview')?.remove();
    const text = (document.getElementById('sanitized')?.textContent || '').trim().slice(0, 700);
    const card = document.createElement('div');
    card.id = 'demo-pdf-preview';
    card.style.cssText =
      'position:fixed;inset:0;z-index:72;display:flex;align-items:center;justify-content:center;padding:24px;background:color-mix(in oklch, var(--canvas) 35%, black 65%)';
    card.innerHTML = `
      <div style="width:min(640px,100%);background:#fafafa;color:#1a1a1a;border-radius:12px;overflow:hidden;border:1px solid #ccc;font-family:ui-sans-serif,system-ui,sans-serif;">
        <div style="padding:12px 16px;background:#ececec;border-bottom:1px solid #ddd;font-weight:700;">📄 ${filename}</div>
        <pre style="margin:0;padding:18px;font:12px/1.55 ui-monospace,Menlo,monospace;white-space:pre-wrap;max-height:340px;overflow:auto;">${text.replace(/</g, '&lt;')}</pre>
      </div>`;
    document.body.appendChild(card);
  }, dl1.suggested);
  await sleep(page, 6000);
  await page.evaluate(() => document.getElementById('demo-pdf-preview')?.remove());

  beat('Attack again → Allow');
  await page.locator('#revise-pdf').click();
  await page.waitForFunction(
    () => {
      const pass = document.getElementById('pass-label')?.textContent || '';
      const badge = document.getElementById('decision-badge')?.textContent || '';
      return pass.includes('pass 2') && badge.includes('Allow');
    },
    { timeout: 30000 },
  );
  await sleep(page, 5000);

  const dl2 = await downloadPdf('Download PDF v2');
  await sleep(page, 1500);

  let reply = FALLBACK_REPLY;
  let usedLive = false;
  const wantLive = MODE === 'live' || MODE === 'auto';

  // Snapshot Privilege SPA so we can return after ChatGPT on the same page (one video).
  const snap = await page.evaluate(() => ({
    engagementId: state.engagementId,
    engagementName: state.engagementName,
    documentId: state.documentId,
    documentTitle: state.documentTitle,
    documentAttested: state.documentAttested,
    exportPass: state.exportPass,
  }));

  if (wantLive) {
    try {
      beat('ChatGPT — live session (same tab)');
      const live = await runLiveChatGPTOnPage(page, dl2.tmpPath, { beat, sleep });
      reply = live.reply;
      usedLive = true;
    } catch (err) {
      console.warn('Live ChatGPT failed:', err.message);
      if (err.screenshot) console.warn('Screenshot:', err.screenshot);
      if (MODE === 'live') throw err;
      beat('ChatGPT — falling back to labeled handoff');
    }
  }

  beat('Back to Privilege — restore SPA + Step 4');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await sleep(page, 2000);
  await page.evaluate((s) => {
    state.engagementId = s.engagementId;
    state.engagementName = s.engagementName;
    state.documentId = s.documentId;
    state.documentTitle = s.documentTitle;
    state.documentAttested = s.documentAttested;
    state.exportPass = s.exportPass || 2;
    for (let i = 1; i <= 4; i++) {
      const el = document.getElementById('step-' + i);
      el.classList.remove('locked', 'active');
      el.classList.add('complete');
    }
    document.getElementById('step-4').classList.add('active');
    document.getElementById('step-4').classList.remove('complete');
    document.getElementById('s1-sub').textContent = `✓ ${s.engagementName}`;
    document.getElementById('s2-sub').textContent = `✓ ${s.documentTitle} · operator confirmed`;
    document.getElementById('s3-sub').textContent = '✓ Allow — anonymized PDF ready';
  }, snap);

  if (!usedLive) {
    await showSimChatGPT(page, dl2.suggested, reply);
  }

  await sleep(page, 1500);

  // Truncate very long replies for the restore box camera beat
  const replyForRestore = reply.length > 1800 ? `${reply.slice(0, 1800)}\n…` : reply;
  await page.fill('#model-reply', replyForRestore);
  await sleep(page, 3000);
  await page.click('#rehydrate');
  await page.waitForSelector('#restored-box', { state: 'visible', timeout: 20000 });
  await page.locator('#step-4').scrollIntoViewIfNeeded();
  await sleep(page, 7000);

  await showCodexBeat(page, beat);

  beat(`End card (ChatGPT=${usedLive ? 'live' : 'fallback'})`);
  await page.evaluate((live) => {
    document.getElementById('demo-end-card')?.remove();
    const card = document.createElement('div');
    card.id = 'demo-end-card';
    card.style.cssText =
      'position:fixed;inset:0;z-index:80;display:flex;align-items:center;justify-content:center;padding:24px;background:color-mix(in oklch, var(--canvas) 40%, black 65%)';
    card.innerHTML = `
      <div style="width:min(560px,100%);background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:28px;">
        <div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint);margin-bottom:10px;">Privilege · PDF lifecycle</div>
        <div style="font-size:22px;font-weight:800;letter-spacing:-0.02em;margin-bottom:10px;">PDF in. Attack. PDF out. ${live ? 'Real ChatGPT.' : 'Any AI.'} Restore.</div>
        <p style="color:var(--muted);font-size:15px;line-height:1.55;margin:0 0 14px;">
          Core built in Codex with GPT-5.6. GPT-5.6 is also the attacker.
          Local masking → anonymized PDF → external AI → names restored on your machine.
        </p>
        <p style="color:var(--amber);font:700 15px var(--sans);margin:0;">github.com/prasadt1/privilege</p>
      </div>`;
    document.body.appendChild(card);
  }, usedLive);
  await sleep(page, 10000);

  await context.close();

  const webm = findWebm(TMP);
  const webmOut = join(MEDIA, 'privilege-pdf-lifecycle.webm');
  const mp4Out = join(MEDIA, 'privilege-pdf-lifecycle.mp4');
  copyFileSync(webm, webmOut);
  rmSync(TMP, { recursive: true, force: true });
  execFileSync(
    'ffmpeg',
    ['-y', '-i', webmOut, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4Out],
    { stdio: 'inherit' },
  );
  const probe = execFileSync(
    'ffprobe',
    ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', mp4Out],
    { encoding: 'utf8' },
  ).trim();
  console.log(
    'Wrote',
    mp4Out,
    `duration ${Number(probe).toFixed(1)}s`,
    `elapsed ${((Date.now() - t0) / 1000).toFixed(1)}s`,
    usedLive ? 'ChatGPT=live' : 'ChatGPT=fallback',
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
