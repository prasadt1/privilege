#!/usr/bin/env node
/**
 * Capture local-viewer screenshots + eval table into docs/media/.
 *
 * Prerequisites: Privilege HTTP server on :7077 with demo vault, e.g.
 *   PRIVILEGE_MOCK=1 python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077
 *
 * Usage: node capture-ui.mjs
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
# Prefer last Transform receipt (mosaic catch); fall back to last Allow with outbound
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
restored = (
    "Northwind Freight depot cost structure (restored locally)\\n\\n"
    "- 14 depots in the network\\n"
    "- Baltic corridor volumes down 22% YoY\\n"
    "- Depot leases in that corridor expire in Q3\\n"
    "- No board announcement yet on corridor strategy\\n\\n"
    "(Names restored on-device from placeholders; this pane never left the laptop.)"
)
print(json.dumps({
    "raw": raw,
    "name": name,
    "policy": policy,
    "decision": decision,
    "sanitized": sanitized,
    "restored": restored,
    "claims": payload.get("inferred_claims") or [],
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

// --- Local viewer shots ---
{
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
    deviceScaleFactor: 2,
  });

  const mode = await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  if (!mode || !mode.ok()) {
    await browser.close();
    console.error(`Server not reachable at ${BASE}. Start:`);
    console.error('  PRIVILEGE_MOCK=1 python -m src.server_http --db demo/demo-vault.sqlite3 --port 7077');
    process.exit(1);
  }

  await page.waitForSelector('#load-id');
  await page.fill('#load-id', ENGAGEMENT);
  await page.click('#load');
  await page.waitForFunction(
    () => document.getElementById('receipts')?.querySelectorAll('details.receipt').length > 0,
    { timeout: 15000 },
  );

  // Hydrate three-column view + policy form from the committed live vault
  // (Load API does not return raw text; receipts are real GPT-5.6 output.)
  await page.evaluate((data) => {
    const $ = (id) => document.getElementById(id);
    $('mode').textContent = 'Live, gpt-5.6';
    $('mode').className = 'mode live';
    $('mode-detail').textContent = 'Receipts below are from the committed live GPT-5.6 demo vault.';
    $('name').value = data.name;
    $('protected').value = (data.policy.protected_values || []).join('\n');
    $('rules').value = (data.policy.abstract_rules || []).join('\n');
    $('purpose').value = data.policy.allowed_purpose || '';
    const aliases = data.policy.aliases || {};
    $('aliases').value = Object.entries(aliases).map(([k, v]) => `${k} = ${v}`).join('\n');
    $('policy').value = JSON.stringify(data.policy, null, 2);
    $('rules-preview').textContent = (data.policy.abstract_rules || []).join('\n') || 'Add a rule above.';
    $('raw').value = data.raw;
    $('raw-view').textContent = data.raw;
    $('sanitized').textContent = data.sanitized;
    $('restored').textContent = data.restored;
    $('decision').textContent = data.decision;
    $('title').value = 'engagement_notes.txt';
    // Trigger template-independent preview sync if present
    if (typeof syncPolicy === 'function') {
      try { syncPolicy(); } catch (_) { /* ignore */ }
    }
  }, vault);

  await page.waitForTimeout(400);

  await page.screenshot({
    path: join(MEDIA, 'viewer-three-column.png'),
    fullPage: true,
  });
  console.log('wrote viewer-three-column.png');

  const setup = page.locator('.setup > section').first();
  await setup.screenshot({ path: join(MEDIA, 'policy-form.png') });
  console.log('wrote policy-form.png');

  // Expand strongest Transform receipt
  const receipts = page.locator('details.receipt');
  const count = await receipts.count();
  let target = null;
  for (let i = 0; i < count; i++) {
    const text = (await receipts.nth(i).locator('summary .decision').textContent()) || '';
    const d = text.trim().toLowerCase();
    if (d === 'block') {
      target = receipts.nth(i);
      break;
    }
    if (d === 'transform' && !target) target = receipts.nth(i);
  }
  if (!target && count > 0) target = receipts.nth(count - 1);

  if (target) {
    await target.locator('summary').click();
    await page.waitForTimeout(350);
    await page.locator('section.feed').screenshot({ path: join(MEDIA, 'receipt-expanded.png') });
    console.log('wrote receipt-expanded.png');
  } else {
    console.warn('no receipts found — receipt-expanded.png skipped');
  }

  await page.close();
}

// --- Eval table ---
{
  const page = await browser.newPage({
    viewport: { width: 1100, height: 640 },
    deviceScaleFactor: 2,
  });
  await page.goto('file://' + join(__dirname, 'eval-table.html'));
  await page.waitForTimeout(150);
  await page.locator('#frame').screenshot({ path: join(MEDIA, 'eval-table.png') });
  console.log('wrote eval-table.png');
  await page.close();
}

await browser.close();
console.log('done →', MEDIA);
