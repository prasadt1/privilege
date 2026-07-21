#!/usr/bin/env node
/**
 * Tight PDF-lifecycle demo (~2:30–2:50) for voiceover:
 *   intro problem → steps 1–4 → ChatGPT PDF handoff → architecture → Codex → end
 *
 * Default CHATGPT_MODE=sim (no live wait / dead air). Use live only if needed:
 *   CHATGPT_MODE=live ./run-full-demo.sh
 *
 * Prerequisites: Privilege mock+demo-attack on :7077
 * Outputs: docs/media/privilege-pdf-lifecycle.mp4 (+ .webm)
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
const ARCH = join(MEDIA, 'architecture.png');
const PROFILE = process.env.CHROME_PROFILE || join(__dirname, '.chrome-profile');
const BASE = process.env.PRIVILEGE_URL || 'http://127.0.0.1:7077';
// sim = predictable pacing for VO (default). live/auto for real ChatGPT.
const MODE = (process.env.CHATGPT_MODE || 'sim').toLowerCase();
const WIDTH = 1280;
const HEIGHT = 800;
const sleep = (page, ms) => page.waitForTimeout(ms);

function findWebm(dir) {
  const files = readdirSync(dir).filter((f) => f.endsWith('.webm'));
  if (!files.length) throw new Error(`No .webm under ${dir}`);
  files.sort((a, b) => statSync(join(dir, b)).mtimeMs - statSync(join(dir, a)).mtimeMs);
  return join(dir, files[0]);
}

async function typeSlow(page, selector, text, { delay = 12 } = {}) {
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
  const chromeBin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if (existsSync(chromeBin)) {
    try {
      return await chromium.launchPersistentContext(PROFILE, {
        ...opts,
        executablePath: chromeBin,
      });
    } catch (err) {
      console.warn('executablePath Chrome failed:', err.message.split('\n')[0]);
    }
  }
  try {
    return await chromium.launchPersistentContext(PROFILE, { ...opts, channel: 'chrome' });
  } catch (chromeErr) {
    console.warn('channel:chrome failed:', chromeErr.message.split('\n')[0]);
    return await chromium.launchPersistentContext(PROFILE, opts);
  }
}

async function showOverlay(page, { id, html, ms, dim = 'rgba(8,8,10,.55)' }) {
  await page.evaluate(
    ({ id, html, dim }) => {
      document.getElementById(id)?.remove();
      const el = document.createElement('div');
      el.id = id;
      el.style.cssText = [
        'position:fixed',
        'inset:0',
        'z-index:90',
        'display:flex',
        'align-items:center',
        'justify-content:center',
        'padding:32px',
        `background:${dim}`,
        'backdrop-filter:blur(10px)',
        '-webkit-backdrop-filter:blur(10px)',
        'font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif',
        'color:#f4f1ea',
      ].join(';');
      el.innerHTML = html;
      document.body.appendChild(el);
    },
    { id, html, dim },
  );
  await sleep(page, ms);
  await page.evaluate((id) => document.getElementById(id)?.remove(), id);
}

async function showMacOpenDialog(page, filename) {
  await page.evaluate((fn) => {
    document.getElementById('demo-picker')?.remove();
    const wrap = document.createElement('div');
    wrap.id = 'demo-picker';
    wrap.style.cssText =
      'position:fixed;inset:0;z-index:80;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.28);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif';
    const rows = [
      ['notes-q2.txt', 'Yesterday', '12 KB', false],
      [fn, 'Today, 7:55 PM', '5 KB', false],
      ['board-pack-draft.docx', 'Jul 18', '84 KB', false],
      ['lease-summary.pdf', 'Jul 14', '210 KB', false],
    ];
    wrap.innerHTML = `
      <div style="width:720px;height:440px;background:#ececec;border-radius:10px;overflow:hidden;box-shadow:0 24px 80px rgba(0,0,0,.45),0 0 0 0.5px rgba(0,0,0,.25);display:flex;flex-direction:column;">
        <div style="height:52px;background:linear-gradient(#f6f6f6,#e8e8e8);border-bottom:1px solid #cfcfcf;display:flex;align-items:center;padding:0 14px;gap:10px;">
          <div style="display:flex;gap:7px;">
            <span style="width:12px;height:12px;border-radius:50%;background:#ff5f57;box-shadow:inset 0 0 0 0.5px rgba(0,0,0,.2)"></span>
            <span style="width:12px;height:12px;border-radius:50%;background:#febc2e;box-shadow:inset 0 0 0 0.5px rgba(0,0,0,.2)"></span>
            <span style="width:12px;height:12px;border-radius:50%;background:#28c840;box-shadow:inset 0 0 0 0.5px rgba(0,0,0,.2)"></span>
          </div>
          <div style="flex:1;text-align:center;font-size:13px;font-weight:600;color:#222;">Open File</div>
          <div style="width:54px"></div>
        </div>
        <div style="flex:1;display:flex;min-height:0;">
          <aside style="width:168px;background:#e4e4e4;border-right:1px solid #d0d0d0;padding:12px 8px;font-size:12px;color:#333;">
            <div style="font-size:10px;color:#777;letter-spacing:.04em;margin:4px 8px 6px;">Favorites</div>
            ${['Recents', 'Applications', 'Desktop', 'Documents', 'Downloads'].map((n, i) =>
              `<div style="padding:5px 8px;border-radius:6px;${i === 3 ? 'background:#0a84ff;color:#fff;font-weight:600;' : ''}">${n}</div>`,
            ).join('')}
          </aside>
          <div style="flex:1;display:flex;flex-direction:column;background:#f7f7f7;">
            <div style="padding:8px 12px;border-bottom:1px solid #ddd;display:flex;gap:8px;align-items:center;">
              <div style="flex:1;background:#fff;border:1px solid #ccc;border-radius:6px;padding:5px 10px;font-size:12px;color:#555;">Documents ▸ engagement-packs</div>
            </div>
            <div id="mac-file-list" style="flex:1;padding:8px 10px;overflow:auto;">
              <div style="display:grid;grid-template-columns:18px 1fr 90px 70px;gap:8px;padding:4px 8px;font-size:11px;color:#777;border-bottom:1px solid #e5e5e5;">
                <span></span><span>Name</span><span>Date Modified</span><span>Size</span>
              </div>
              ${rows.map(([name, date, size], idx) => `
                <div data-row="${idx}" style="display:grid;grid-template-columns:18px 1fr 90px 70px;gap:8px;align-items:center;padding:7px 8px;border-radius:6px;font-size:12px;color:#1a1a1a;">
                  <span style="font-size:14px;">📄</span>
                  <span style="font-weight:500;">${name}</span>
                  <span style="opacity:.85;font-size:11px;">${date}</span>
                  <span style="opacity:.85;font-size:11px;">${size}</span>
                </div>`).join('')}
            </div>
            <div style="padding:10px 14px;border-top:1px solid #ddd;background:#ececec;display:flex;justify-content:flex-end;gap:8px;">
              <button style="border:1px solid #c8c8c8;background:#fff;border-radius:6px;padding:5px 16px;font-size:13px;">Cancel</button>
              <button id="mac-open-btn" style="border:0;background:#b0b0b0;color:#fff;border-radius:6px;padding:5px 18px;font-size:13px;font-weight:600;">Open</button>
            </div>
          </div>
        </div>
      </div>`;
    document.body.appendChild(wrap);
  }, filename);
  await sleep(page, 1200);
  // Human-like: pause on the folder, then select the PDF
  await page.evaluate(() => {
    const row = document.querySelector('#mac-file-list [data-row="1"]');
    if (!row) return;
    row.style.background = '#0a84ff';
    row.style.color = '#fff';
    const name = row.querySelector('span:nth-child(2)');
    if (name) name.style.fontWeight = '600';
    const btn = document.getElementById('mac-open-btn');
    if (btn) btn.style.background = '#0a84ff';
  });
  await sleep(page, 2200);
  // Flash Open button press
  await page.evaluate(() => {
    const btn = document.getElementById('mac-open-btn');
    if (btn) btn.style.filter = 'brightness(.88)';
  });
  await sleep(page, 450);
}

async function showMacDownload(page, filename) {
  await page.evaluate((fn) => {
    document.getElementById('demo-download')?.remove();
    const el = document.createElement('div');
    el.id = 'demo-download';
    el.style.cssText =
      'position:fixed;right:18px;top:14px;z-index:85;width:320px;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif';
    el.innerHTML = `
      <div style="background:rgba(40,40,42,.92);color:#f5f5f7;border-radius:12px;padding:12px 14px;box-shadow:0 12px 40px rgba(0,0,0,.4);backdrop-filter:blur(18px);border:1px solid rgba(255,255,255,.12);">
        <div style="display:flex;gap:10px;align-items:flex-start;">
          <div style="width:36px;height:44px;border-radius:4px;background:linear-gradient(#ff6b5a,#c0392b);display:flex;align-items:flex-end;justify-content:center;color:#fff;font:700 9px/1.2 sans-serif;padding-bottom:4px;">PDF</div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${fn}</div>
            <div id="dl-status" style="font-size:11px;color:#a1a1a6;margin-top:2px;">Downloading…</div>
            <div style="margin-top:8px;height:4px;background:rgba(255,255,255,.15);border-radius:99px;overflow:hidden;">
              <div id="dl-bar" style="height:100%;width:8%;background:#0a84ff;border-radius:99px;transition:width .35s ease;"></div>
            </div>
          </div>
        </div>
      </div>`;
    document.body.appendChild(el);
  }, filename);
  for (const w of [18, 42, 68, 88, 100]) {
    await page.evaluate((width) => {
      const bar = document.getElementById('dl-bar');
      if (bar) bar.style.width = `${width}%`;
      if (width === 100) {
        const s = document.getElementById('dl-status');
        if (s) s.textContent = 'Downloaded to Downloads';
      }
    }, w);
    await sleep(page, 320);
  }
  await sleep(page, 2200);
  await page.evaluate(() => document.getElementById('demo-download')?.remove());
}

async function showChatGPTHandoff(page, filename, reply) {
  await page.evaluate((fn) => {
    document.getElementById('demo-chatgpt-card')?.remove();
    const card = document.createElement('div');
    card.id = 'demo-chatgpt-card';
    card.style.cssText =
      'position:fixed;inset:0;z-index:70;display:flex;align-items:center;justify-content:center;padding:24px;background:rgba(0,0,0,.55);backdrop-filter:blur(8px);font-family:-apple-system,BlinkMacSystemFont,sans-serif';
    card.innerHTML = `
      <div style="width:min(680px,100%);background:#212121;color:#ececec;border-radius:16px;padding:22px;box-shadow:0 24px 80px rgba(0,0,0,.5);">
        <div style="font-size:13px;color:#9b9b9b;margin-bottom:14px;">ChatGPT · new chat</div>
        <div id="cg-attach" style="display:inline-flex;align-items:center;gap:10px;background:#2f2f2f;border:1px solid #3a3a3a;border-radius:10px;padding:10px 12px;margin-bottom:14px;opacity:0;transition:opacity .35s;">
          <span style="width:28px;height:34px;border-radius:3px;background:linear-gradient(#ff6b5a,#c0392b);display:inline-flex;align-items:flex-end;justify-content:center;color:#fff;font:700 8px/1 sans-serif;padding-bottom:3px;">PDF</span>
          <div><div style="font-size:13px;font-weight:700;">${fn}</div>
          <div style="font-size:11px;color:#9b9b9b;">Uploading anonymized PDF…</div></div>
        </div>
        <div id="cg-prompt" style="background:#2f2f2f;border-radius:12px;padding:14px 16px;font-size:14px;line-height:1.5;color:#d0d0d0;margin-bottom:12px;opacity:0;transition:opacity .35s;"></div>
        <div id="cg-reply" style="background:#2f2f2f;border-radius:12px;padding:14px 16px;font-size:14px;line-height:1.5;color:#d0d0d0;opacity:0;transition:opacity .35s;max-height:180px;overflow:auto;"></div>
      </div>`;
    document.body.appendChild(card);
  }, filename);
  await sleep(page, 350);
  await page.evaluate(() => {
    const a = document.getElementById('cg-attach');
    if (a) a.style.opacity = '1';
  });
  await sleep(page, 1400);
  await page.evaluate(() => {
    const a = document.getElementById('cg-attach');
    if (a) a.querySelector('div div:last-child').textContent = 'Attached · from Privilege';
  });
  await sleep(page, 800);
  await page.evaluate(() => {
    const p = document.getElementById('cg-prompt');
    if (p) {
      p.textContent =
        'Summarize depot cost structure and list operating-committee questions. Do not identify the client.';
      p.style.opacity = '1';
    }
  });
  await sleep(page, 2000);
  await page.evaluate((r) => {
    const box = document.getElementById('cg-reply');
    if (box) {
      box.textContent = r;
      box.style.opacity = '1';
    }
  }, reply.slice(0, 520));
  await sleep(page, 4800);
  await page.evaluate(() => document.getElementById('demo-chatgpt-card')?.remove());
}

async function main() {
  mkdirSync(MEDIA, { recursive: true });
  rmSync(TMP, { recursive: true, force: true });
  mkdirSync(TMP, { recursive: true });

  const t0 = Date.now();
  const beats = [];
  const beat = (label) => {
    const s = (Date.now() - t0) / 1000;
    beats.push({ s, label });
    console.log(`[${s.toFixed(1)}s] ${label}`);
  };

  const context = await launchContext();
  const page = context.pages()[0] || (await context.newPage());

  beat('open Privilege');
  const res = await page.goto(BASE, { waitUntil: 'networkidle' });
  if (!res || !res.ok()) throw new Error(`Server not reachable at ${BASE}`);
  await sleep(page, 900);

  beat('intro — problem over live UI');
  const archB64 = existsSync(ARCH) ? readFileSync(ARCH).toString('base64') : '';
  await showOverlay(page, {
    id: 'demo-intro',
    ms: 10000,
    dim: 'rgba(12,10,8,.62)',
    html: `
      <div style="width:min(820px,100%);display:grid;grid-template-columns:${archB64 ? '1.05fr .95fr' : '1fr'};gap:22px;align-items:stretch;">
        <div style="background:rgba(28,24,20,.88);border:1px solid rgba(245,166,35,.28);border-radius:16px;padding:26px 28px;box-shadow:0 20px 60px rgba(0,0,0,.35);">
          <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#f5a623;margin-bottom:14px;">Engagement confidentiality</div>
          <div style="font-size:26px;font-weight:750;letter-spacing:-0.03em;line-height:1.22;margin-bottom:14px;color:#f7f2e8;">
            The leak isn’t always the name.<br/>It’s the mosaic.
          </div>
          <p style="font-size:14.5px;line-height:1.55;color:#c9c0b2;margin:0 0 12px;">
            Three harmless facts can still let a frontier model re-identify a client.
            Entity redaction doesn’t see that. Privilege does — locally — before anything leaves the laptop.
          </p>
          <p style="font-size:13px;color:#f5a623;margin:0;font-weight:600;letter-spacing:.01em;">
            Mask → GPT-5.6 attacks → anonymized PDF → restore
          </p>
        </div>
        ${
          archB64
            ? `<div style="border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.1);background:#111;display:flex;align-items:center;justify-content:center;padding:10px;">
          <img alt="" src="data:image/png;base64,${archB64}" style="width:100%;height:100%;object-fit:contain;max-height:280px;" />
        </div>`
            : ''
        }
      </div>`,
  });

  beat('Step 1 — policy');
  await page.selectOption('#template', 'restructuring');
  await sleep(page, 700);
  await typeSlow(page, '#name', 'Northwind Freight', { delay: 18 });
  await sleep(page, 400);
  await page.fill('#protected', 'Northwind Freight\nBaltic corridor');
  await page.locator('#protected').dispatchEvent('input');
  await sleep(page, 600);
  await page.evaluate(() => {
    const adv = [...document.querySelectorAll('details.adv')].find((d) =>
      (d.querySelector('summary')?.textContent || '').includes('Aliases'),
    );
    if (adv) adv.open = true;
  });
  await page.fill('#aliases', 'Northwind = Northwind Freight');
  await page.locator('#aliases').dispatchEvent('input');
  await page.fill(
    '#rules',
    'Northwind Freight withdrawing from the Baltic corridor is protected until the client announces it',
  );
  await page.locator('#rules').dispatchEvent('input');
  await sleep(page, 1200);

  beat('Create engagement');
  await page.click('#create');
  await page.waitForFunction(() => !document.getElementById('step-2')?.classList.contains('locked'), {
    timeout: 15000,
  });
  await sleep(page, 1000);

  beat('Step 2 — macOS Open dialog');
  await page.locator('#filebtn').scrollIntoViewIfNeeded();
  await page.locator('#filebtn').evaluate((el) => {
    el.style.outline = '2px solid #f5a623';
    el.style.outlineOffset = '3px';
  });
  await sleep(page, 1000);
  await showMacOpenDialog(page, 'client-brief.pdf');
  await page.evaluate(() => document.getElementById('demo-picker')?.remove());
  await sleep(page, 400);
  await page.locator('#filebtn').evaluate((el) => {
    el.style.outline = '';
    el.style.outlineOffset = '';
  });

  beat('Step 2 — upload + attest');
  await page.setInputFiles('#file', FIXTURE);
  await page.waitForSelector('#file-selected.show', { timeout: 20000 });
  await page.locator('#file-selected').scrollIntoViewIfNeeded();
  await sleep(page, 1800);
  await page.waitForSelector('#attest-box', { state: 'visible', timeout: 20000 });
  await page.locator('#attest-box').scrollIntoViewIfNeeded();
  await sleep(page, 1400);
  await page.check('#attest-check');
  await sleep(page, 600);
  await page.click('#attest-document');
  await page.waitForFunction(() => !document.getElementById('step-3')?.classList.contains('locked'), {
    timeout: 15000,
  });
  await sleep(page, 900);

  beat('Step 3 — Transform');
  await page.click('#export-safe');
  await page.waitForSelector('#export-result', { state: 'visible', timeout: 30000 });
  await page.waitForFunction(
    () => (document.getElementById('decision-badge')?.textContent || '').includes('Transform'),
    { timeout: 30000 },
  );
  await sleep(page, 4800);

  async function downloadPdf(label) {
    beat(label);
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 15000 }),
      page.locator('#download-pdf').click(),
    ]);
    const suggested = download.suggestedFilename() || 'privilege-anonymized.pdf';
    await page.waitForSelector('#dl-toast.show', { timeout: 5000 }).catch(() => {});
    const tmpPath = join(TMP, suggested);
    await download.saveAs(tmpPath);
    await showMacDownload(page, suggested);
    return { suggested, tmpPath };
  }

  const dl1 = await downloadPdf('Download PDF v1');
  // Brief Preview.app-style glance (not a full-screen black modal)
  await page.evaluate((filename) => {
    document.getElementById('demo-pdf-preview')?.remove();
    const text = (document.getElementById('sanitized')?.textContent || '').trim().slice(0, 420);
    const card = document.createElement('div');
    card.id = 'demo-pdf-preview';
    card.style.cssText =
      'position:fixed;right:24px;bottom:24px;z-index:72;width:min(420px,46vw);background:#1c1a17;color:#f2eee6;border-radius:12px;overflow:hidden;border:1px solid rgba(245,166,35,.25);box-shadow:0 18px 50px rgba(0,0,0,.45);font-family:-apple-system,BlinkMacSystemFont,sans-serif';
    card.innerHTML = `
      <div style="padding:10px 12px;background:rgba(255,255,255,.04);border-bottom:1px solid rgba(255,255,255,.08);display:flex;gap:8px;align-items:center;">
        <span style="width:22px;height:28px;border-radius:2px;background:linear-gradient(#ff6b5a,#c0392b);display:inline-flex;align-items:flex-end;justify-content:center;color:#fff;font:700 7px/1 sans-serif;padding-bottom:2px;">PDF</span>
        <div style="font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${filename}</div>
      </div>
      <pre style="margin:0;padding:12px;font:11px/1.45 ui-monospace,Menlo,monospace;white-space:pre-wrap;max-height:200px;overflow:auto;color:#d5cfc4;">${text.replace(/</g, '&lt;')}</pre>`;
    document.body.appendChild(card);
  }, dl1.suggested);
  await sleep(page, 3600);
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
  await sleep(page, 3500);

  const dl2 = await downloadPdf('Download PDF v2');
  await sleep(page, 600);

  let reply = FALLBACK_REPLY;
  let usedLive = false;
  const snap = await page.evaluate(() => ({
    engagementId: state.engagementId,
    engagementName: state.engagementName,
    documentId: state.documentId,
    documentTitle: state.documentTitle,
    documentAttested: state.documentAttested,
    exportPass: state.exportPass,
  }));

  if (MODE === 'live' || MODE === 'auto') {
    try {
      beat('ChatGPT — live');
      const live = await runLiveChatGPTOnPage(page, dl2.tmpPath, { beat, sleep });
      reply = live.reply;
      usedLive = true;
    } catch (err) {
      console.warn('Live ChatGPT failed:', err.message);
      if (MODE === 'live') throw err;
      beat('ChatGPT — staged handoff');
    }
  }

  if (!usedLive) {
    beat('ChatGPT — staged PDF handoff');
    // Stay on Privilege page for continuous video; show staged ChatGPT UI.
    await showChatGPTHandoff(page, dl2.suggested, reply);
  } else {
    beat('Back to Privilege');
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await sleep(page, 800);
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
    }, snap);
  }

  // Ensure step 4 active for sim path too
  await page.evaluate((s) => {
    if (!state.engagementId && s.engagementId) {
      state.engagementId = s.engagementId;
      state.engagementName = s.engagementName;
      state.documentId = s.documentId;
      state.documentTitle = s.documentTitle;
      state.documentAttested = s.documentAttested;
      state.exportPass = s.exportPass || 2;
    }
    for (let i = 1; i <= 3; i++) {
      const el = document.getElementById('step-' + i);
      el.classList.remove('locked', 'active');
      el.classList.add('complete');
    }
    const s4 = document.getElementById('step-4');
    s4.classList.remove('locked', 'complete');
    s4.classList.add('active');
  }, snap);

  beat('Step 4 — restore');
  const replyForRestore = reply.length > 1400 ? `${reply.slice(0, 1400)}\n…` : reply;
  await page.fill('#model-reply', replyForRestore);
  await sleep(page, 1400);
  await page.click('#rehydrate');
  await page.waitForSelector('#restored-box', { state: 'visible', timeout: 20000 });
  await page.locator('#step-4').scrollIntoViewIfNeeded();
  await sleep(page, 4200);

  beat('Architecture');
  if (existsSync(ARCH)) {
    const b64 = readFileSync(ARCH).toString('base64');
    await showOverlay(page, {
      id: 'demo-arch',
      ms: 8000,
      dim: 'rgba(12,10,8,.72)',
      html: `
        <div style="max-width:1080px;width:100%;background:rgba(22,20,18,.92);border:1px solid rgba(245,166,35,.22);border-radius:16px;padding:18px 20px 16px;box-shadow:0 24px 70px rgba(0,0,0,.4);">
          <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#f5a623;margin-bottom:6px;">Trust boundary</div>
          <div style="font-size:20px;font-weight:750;margin-bottom:12px;letter-spacing:-0.02em;">Raw stays local. OpenAI sees sanitized text only.</div>
          <img alt="Architecture" src="data:image/png;base64,${b64}"
            style="width:100%;max-height:480px;object-fit:contain;border-radius:10px;border:1px solid rgba(255,255,255,.08);background:#0e0d0c;" />
        </div>`,
    });
  }

  beat('Codex');
  const codex = join(CODEX_DIR, 'codex-session-gpt56.png');
  if (existsSync(codex)) {
    const b64 = readFileSync(codex).toString('base64');
    await showOverlay(page, {
      id: 'demo-codex',
      ms: 7500,
      dim: 'rgba(12,10,8,.72)',
      html: `
        <div style="max-width:1080px;width:100%;background:rgba(22,20,18,.92);border:1px solid rgba(245,166,35,.22);border-radius:16px;padding:18px 20px 16px;box-shadow:0 24px 70px rgba(0,0,0,.4);">
          <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#f5a623;margin-bottom:6px;">Built in Codex · GPT-5.6</div>
          <div style="font-size:18px;font-weight:750;margin-bottom:12px;letter-spacing:-0.02em;">Vault, sanitizer, attack loop — GPT-5.6 is the attacker at runtime.</div>
          <img alt="Codex" src="data:image/png;base64,${b64}"
            style="width:100%;max-height:460px;object-fit:contain;border-radius:10px;border:1px solid rgba(255,255,255,.08);" />
        </div>`,
    });
  }

  beat('End');
  await showOverlay(page, {
    id: 'demo-end',
    ms: 7500,
    dim: 'rgba(12,10,8,.7)',
    html: `
      <div style="max-width:560px;background:rgba(28,24,20,.9);border:1px solid rgba(245,166,35,.28);border-radius:16px;padding:28px 30px;box-shadow:0 20px 60px rgba(0,0,0,.4);">
        <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#f5a623;margin-bottom:12px;">Privilege</div>
        <div style="font-size:24px;font-weight:750;letter-spacing:-0.03em;line-height:1.25;margin-bottom:12px;">Attack the draft. Ship only what survives.</div>
        <p style="color:#c9c0b2;font-size:14.5px;line-height:1.55;margin:0 0 18px;">
          Local PDF preflight · consultant attestation · GPT-5.6 as attacker · anonymized PDF for any AI.
        </p>
        <p style="color:#f5a623;font:700 15px -apple-system,BlinkMacSystemFont,sans-serif;margin:0;">github.com/prasadt1/privilege</p>
      </div>`,
  });

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
  const dur = Number(probe);
  console.log('Wrote', mp4Out, `duration ${dur.toFixed(1)}s`, `ChatGPT=${usedLive ? 'live' : 'staged'}`);
  console.log('BEATS');
  for (const b of beats) console.log(`  ${b.s.toFixed(1)}\t${b.label}`);

  // Soft-cap if somehow over 2:58
  if (dur > 178) {
    const capped = join(MEDIA, 'privilege-pdf-lifecycle-cap.mp4');
    execFileSync('ffmpeg', ['-y', '-i', mp4Out, '-t', '00:02:55', '-c', 'copy', capped], {
      stdio: 'inherit',
    });
    copyFileSync(capped, mp4Out);
    rmSync(capped, { force: true });
    console.log('Trimmed hard to 2:55');
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
