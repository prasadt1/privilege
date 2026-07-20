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
 *   viewer-three-column.png  — full export-first step flow (name is historical)
 *   receipt-expanded.png     — Transform/Block receipt with inferences
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

function loadVault() {
  const py = `
import json, sqlite3
c = sqlite3.connect(${JSON.stringify(DB)})
raw = c.execute("select raw_text from documents where engagement_id=?", (${JSON.stringify(ENGAGEMENT)},)).fetchone()[0]
name, policy = c.execute("select name, policy_json from engagements where id=?", (${JSON.stringify(ENGAGEMENT)},)).fetchone()
policy = json.loads(policy)
row = c.execute(
    "select decision, payload_json from receipts where engagement_id=? and decision='Transform' order by created_at desc limit 1",
    (${JSON.stringify(ENGAGEMENT)},),
).fetchone()
if not row:
    row = c.execute(
        "select decision, payload_json from receipts where engagement_id=? order by created_at desc limit 1",
        (${JSON.stringify(ENGAGEMENT)},),
    ).fetchone()
decision, payload = row[0], json.loads(row[1])
sanitized = payload.get("final_outbound_payload") or payload.get("sanitized_candidate_preview") or ""
# Prefer the Document: body for the export-safe pane.
marker = "\\n\\nDocument:\\n"
if marker in sanitized:
    sanitized = sanitized.split(marker, 1)[1]
restored = (
    "Northwind Freight depot cost structure (restored locally)\\n\\n"
    "- 14 depots in the network\\n"
    "- Baltic corridor volumes down 22% YoY\\n"
    "- Depot leases in that corridor expire in Q3\\n"
    "- No board announcement yet on corridor strategy\\n\\n"
    "(Names restored on-device from placeholders; this never left the laptop.)"
)
print(json.dumps({
    "raw": raw,
    "name": name,
    "policy": policy,
    "decision": decision,
    "sanitized": sanitized,
    "restored": restored,
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
    viewport: { width: 820, height: 1200 },
    deviceScaleFactor: 2,
  });

  const mode = await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  if (!mode || !mode.ok()) {
    await browser.close();
    console.error(`Server not reachable at ${BASE}. Start:`);
    console.error('  PRIVILEGE_MOCK=1 python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077');
    process.exit(1);
  }

  await page.waitForSelector('#load-toggle');
  await page.click('#load-toggle');
  await page.fill('#load-id', ENGAGEMENT);
  await page.click('#load');
  await page.waitForFunction(
    () => document.getElementById('receipts')?.querySelectorAll('details.receipt').length > 0,
    { timeout: 15000 },
  );

  // Hydrate the step UI to a finished export + restore state for the hero shot.
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

    // Unlock all steps; leave step 3 open on the safe export (hero).
    for (let i = 1; i <= 4; i++) {
      const el = $('step-' + i);
      el.classList.remove('locked', 'active');
      el.classList.add('complete');
    }
    $('step-3').classList.add('active');
    $('step-3').classList.remove('complete');

    const decision = data.decision || 'Allow';
    $('export-result').style.display = 'block';
    const badge = $('decision-badge');
    const icon = decision === 'Block' ? '⛔' : decision === 'Transform' ? '✎' : '✓';
    badge.textContent = `${icon} ${decision}`;
    badge.className = 'decision-badge ' + decision.toLowerCase();
    $('sanitized').textContent = data.sanitized;
    $('export-actions').style.display = 'flex';
    $('trust').innerHTML = `<strong>${decision}</strong> — attack-verified against prior disclosures in this engagement. Copy for ChatGPT, Claude, or another tool.`;

    $('restored-box').style.display = 'block';
    $('restored').textContent = data.restored;
    $('model-reply').value = 'Recommendation: [VALUE_1] should delay corridor lease renewals pending board review.';

    $('receipts-fold').open = true;
  }, vault);

  await page.waitForTimeout(500);

  await page.locator('.wrap').screenshot({
    path: join(MEDIA, 'viewer-three-column.png'),
  });
  console.log('wrote viewer-three-column.png (export-first step flow)');

  // Expand strongest Transform/Block receipt for the mosaic beat.
  const receipts = page.locator('#receipts details.receipt');
  const count = await receipts.count();
  let target = null;
  for (let i = 0; i < count; i++) {
    const text = ((await receipts.nth(i).locator('summary .rd').textContent()) || '').trim().toLowerCase();
    if (text === 'block') {
      target = receipts.nth(i);
      break;
    }
    if (text === 'transform' && !target) target = receipts.nth(i);
  }
  if (!target && count > 0) target = receipts.nth(count - 1);

  if (target) {
    await target.locator('summary').click();
    await page.waitForTimeout(350);
    await page.locator('#receipts-fold').screenshot({ path: join(MEDIA, 'receipt-expanded.png') });
    console.log('wrote receipt-expanded.png');
  } else {
    console.warn('no receipts found — receipt-expanded.png skipped');
  }

  // Step-1 policy view for a secondary crop if needed — full hero already shows it collapsed.
  await page.close();
}

await browser.close();
console.log('done →', MEDIA);
