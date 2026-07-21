#!/usr/bin/env node
/**
 * Capture local-viewer screenshots into docs/media/ for the Claude step UI.
 *
 * Prerequisites: Privilege HTTP server on :7077 with demo vault, e.g.
 *   PRIVILEGE_MOCK=1 python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077
 *
 * Usage: node capture-ui.mjs
 *
 * Outputs (filenames kept for GitHub/Devpost URL stability):
 *   viewer-three-column.png  — hero: step 3 export-result with green Allow badge
 *   receipt-expanded.png     — Transform receipt with mosaic inferences
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const MEDIA = join(ROOT, 'docs/media');
const BASE = process.env.PRIVILEGE_URL || 'http://127.0.0.1:7077';
const ENGAGEMENT = 'eng_2d90da2c94224fccad51a15fb398c3dc';
const DB = join(ROOT, 'demo/demo-vault.sqlite3');

function documentBody(payload) {
  const marker = '\n\nDocument:\n';
  if (payload.includes(marker)) return payload.split(marker, 1)[1];
  return payload;
}

function loadVault() {
  const py = `
import json, sqlite3
c = sqlite3.connect(${JSON.stringify(DB)})
raw = c.execute("select raw_text from documents where engagement_id=?", (${JSON.stringify(ENGAGEMENT)},)).fetchone()[0]
name, policy = c.execute("select name, policy_json from engagements where id=?", (${JSON.stringify(ENGAGEMENT)},)).fetchone()
policy = json.loads(policy)

def payload_text(row):
    decision, payload = row[0], json.loads(row[1])
    text = payload.get("final_outbound_payload") or payload.get("sanitized_candidate_preview") or ""
    marker = "\\n\\nDocument:\\n"
    if marker in text:
        text = text.split(marker, 1)[1]
    return decision, text, payload.get("inferred_claims") or []

allow = c.execute(
    "select decision, payload_json from receipts where engagement_id=? and decision='Allow' order by created_at asc limit 1",
    (${JSON.stringify(ENGAGEMENT)},),
).fetchone()
transform = c.execute(
    "select decision, payload_json from receipts where engagement_id=? and decision='Transform' order by created_at desc limit 1",
    (${JSON.stringify(ENGAGEMENT)},),
).fetchone()
allow_decision, allow_text, _ = payload_text(allow)
xform_decision, xform_text, claims = payload_text(transform) if transform else ("Allow", allow_text, [])
print(json.dumps({
    "raw": raw,
    "name": name,
    "policy": policy,
    "allow_decision": allow_decision,
    "allow_text": allow_text,
    "transform_decision": xform_decision,
    "transform_text": xform_text,
    "claims": claims,
}))
`;
  const out = execFileSync(join(ROOT, '.venv/bin/python'), ['-c', py], { encoding: 'utf8' });
  return JSON.parse(out);
}

async function launch() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return await chromium.launch();
  }
}

mkdirSync(MEDIA, { recursive: true });
const vault = loadVault();
const browser = await launch();

{
  const page = await browser.newPage({
    viewport: { width: 820, height: 1100 },
    deviceScaleFactor: 2,
  });

  const mode = await page.goto(BASE + '/?v=allow-hero', { waitUntil: 'networkidle' });
  if (!mode || !mode.ok()) {
    await browser.close();
    console.error(`Server not reachable at ${BASE}. Start:`);
    console.error('  PRIVILEGE_MOCK=1 python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077');
    process.exit(1);
  }

  // Confirm we are on the step UI, not a stale cached page.
  await page.waitForSelector('#step-3');
  await page.waitForSelector('#export-result', { state: 'attached' });
  await page.waitForSelector('#load-toggle');
  await page.click('#load-toggle');
  await page.fill('#load-id', ENGAGEMENT);
  await page.click('#load');
  await page.waitForFunction(
    () => document.getElementById('receipts')?.querySelectorAll('details.receipt').length > 0,
    { timeout: 15000 },
  );

  // Hero: finished export with green Allow badge — the strongest product moment.
  await page.evaluate((data) => {
    const $ = (id) => document.getElementById(id);
    $('mode').textContent = 'Live, gpt-5.6';
    $('mode').className = 'mode-badge live';
    $('mode').title = 'Receipts below are from the committed live GPT-5.6 demo vault.';
    $('name').value = data.name;
    $('protected').value = (data.policy.protected_values || []).join('\n');
    $('rules').value = (data.policy.abstract_rules || []).join('\n');
    $('purpose').value = data.policy.allowed_purpose || '';
    const aliases = data.policy.aliases || {};
    $('aliases').value = Object.entries(aliases).map(([k, v]) => `${k} = ${v}`).join('\n');
    $('policy').value = JSON.stringify(data.policy, null, 2);
    if (typeof syncPolicy === 'function') {
      try { syncPolicy(); } catch (_) { /* ignore */ }
    }
    $('raw').value = data.raw;
    $('raw-view').textContent = data.raw;
    $('title').value = 'engagement_notes.txt';
    $('s1-sub').textContent = `✓ ${data.name}`;
    $('s2-sub').textContent = '✓ engagement_notes.txt';

    for (let i = 1; i <= 4; i++) {
      const el = $('step-' + i);
      el.classList.remove('locked', 'active');
      el.classList.add('complete');
    }
    // Step 3 open on the Allow export result; step 4 unlocked as the next beat.
    $('step-3').classList.add('active');
    $('step-3').classList.remove('complete');
    $('step-4').classList.remove('locked');

    const decision = 'Allow';
    $('export-result').style.display = 'block';
    const badge = $('decision-badge');
    badge.textContent = `✓ ${decision}`;
    badge.className = 'decision-badge allow';
    $('sanitized').textContent = data.allow_text;
    $('export-actions').style.display = 'flex';
    $('pass-label').textContent = '· pass 2';
    $('trust').innerHTML =
      '<strong>Allow</strong> under this engagement policy. Download the anonymized PDF for ChatGPT, Claude, or another tool — then restore names from the reply.';

    $('notice').textContent = 'Allow. Download the anonymized PDF, then restore names from the reply.';
    $('receipts-fold').open = false;

    // Article crop: hide secondary chrome; keep the four-step story readable
    // without the tall full-page scroll that blows up Devpost embeds.
    $('ask-fold').style.display = 'none';
    $('receipts-fold').style.display = 'none';
    $('export-safe').style.display = 'none';
    const hint = document.querySelector('#step-3 > .step-body > .hint');
    if (hint) hint.style.display = 'none';
    $('notice').style.display = 'none';
    const brandP = document.querySelector('.brand p');
    if (brandP) brandP.style.display = 'none';
    const askToggle = $('ask-toggle');
    if (askToggle) askToggle.style.display = 'none';
    // Prefer a short, readable safe excerpt for the hero.
    $('sanitized').textContent =
      '[VALUE_1] operates 14 depots. [VALUE_2] volumes fell 22% year on year.\n' +
      'Depot leases in that corridor expire in Q3. The board has not yet announced any change.';
    $('sanitized').style.maxHeight = '4.8em';
    $('trust').innerHTML =
      '<strong>Allow</strong> under this engagement policy. Download the anonymized PDF for any external AI.';
  }, vault);

  await page.addStyleTag({
    content: `
      .wrap { max-width: 920px !important; padding: 18px 22px 20px !important; }
      header { margin-bottom: 10px !important; }
      .steps { gap: 10px !important; margin-top: 0 !important; }
      .step-head { padding: 12px 16px !important; gap: 10px !important; }
      .step-title { font-size: 16px !important; }
      .step-sub { font-size: 13px !important; }
      .num { width: 26px !important; height: 26px !important; font-size: 13px !important; }
      .step-body { padding: 0 16px 14px !important; }
      .safebox { margin-top: 10px !important; padding: 12px !important; }
      .safebox pre { font-size: 13px !important; line-height: 1.45 !important; }
      .trust { margin-top: 8px !important; font-size: 13px !important; }
      .row { margin-top: 8px !important; }
      .btn.small { padding: 7px 11px !important; font-size: 13px !important; }
      .decision-badge { font-size: 14px !important; padding: 5px 12px !important; }
    `,
  });

  await page.waitForTimeout(300);

  // Clip to header through step 4 — article-friendly height.
  const clip = await page.evaluate(() => {
    const wrap = document.querySelector('.wrap').getBoundingClientRect();
    const end = document.getElementById('step-4').getBoundingClientRect();
    const pad = 6;
    return {
      x: Math.max(0, wrap.left - pad),
      y: Math.max(0, wrap.top - pad),
      width: Math.ceil(wrap.width + pad * 2),
      height: Math.ceil(end.bottom - wrap.top + pad * 2),
    };
  });
  await page.screenshot({
    path: join(MEDIA, 'viewer-three-column.png'),
    clip,
  });
  console.log('wrote viewer-three-column.png (Allow export-result, article crop)');

  // Restore folds for the receipt shot.
  await page.evaluate(() => {
    document.getElementById('ask-fold').style.display = '';
    document.getElementById('receipts-fold').style.display = '';
    document.getElementById('receipts-fold').open = true;
  });
  await page.waitForTimeout(200);

  const receipts = page.locator('#receipts details.receipt');
  const count = await receipts.count();
  let target = null;
  for (let i = 0; i < count; i++) {
    const text = ((await receipts.nth(i).locator('summary .rd').textContent()) || '').trim().toLowerCase();
    if (text === 'transform') {
      target = receipts.nth(i);
      break;
    }
  }
  if (!target && count > 0) target = receipts.nth(0);

  if (target) {
    await target.locator('summary').click();
    await page.waitForTimeout(350);
    await page.locator('#receipts-fold').screenshot({ path: join(MEDIA, 'receipt-expanded.png') });
    console.log('wrote receipt-expanded.png');
  } else {
    console.warn('no receipts found — receipt-expanded.png skipped');
  }

  await page.close();
}

await browser.close();
console.log('done →', MEDIA);
