/**
 * Live ChatGPT.com helpers for the Privilege PDF lifecycle demo.
 *
 * Requires a Chrome persistent profile already logged into ChatGPT
 * (see setup-chatgpt-profile.mjs). UI selectors change; this tries several
 * strategies and returns null on failure so the recorder can fall back.
 */
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const CHATGPT_URL = process.env.CHATGPT_URL || 'https://chatgpt.com/';

const PROMPT =
  process.env.CHATGPT_PROMPT ||
  'Summarize the depot cost structure in the attached PDF and list questions the operating committee should ask. Do not try to identify the real client or company name.';

export async function openChatGPT(context, { beat = console.log, sleep }) {
  const page = await context.newPage();
  beat('ChatGPT — open');
  await page.goto(CHATGPT_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(page, 4000);

  // Cookie / consent banners
  for (const label of ['Accept all', 'Accept', 'Agree', 'Got it', 'OK']) {
    const btn = page.getByRole('button', { name: label, exact: false }).first();
    if (await btn.isVisible().catch(() => false)) {
      await btn.click().catch(() => {});
      await sleep(page, 1000);
    }
  }

  const composer = page.locator('#prompt-textarea, [data-testid="prompt-textarea"], div[contenteditable="true"]').first();
  try {
    await composer.waitFor({ state: 'visible', timeout: 45000 });
  } catch {
    const shot = 'docs/media/.chatgpt-login-needed.png';
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    throw new Error(
      `ChatGPT composer not found — profile may not be logged in. Screenshot: ${shot}`,
    );
  }

  // Prefer a fresh chat if the New chat control exists
  const newChat = page.getByRole('button', { name: /new chat/i }).first();
  if (await newChat.isVisible().catch(() => false)) {
    await newChat.click().catch(() => {});
    await sleep(page, 2000);
  }

  return page;
}

async function attachPdf(page, pdfPath, { beat, sleep }) {
  beat('ChatGPT — attach PDF');
  const fileInputs = page.locator('input[type="file"]');
  const count = await fileInputs.count();
  if (count > 0) {
    // Prefer an accept=* / broad input if present
    let target = fileInputs.first();
    for (let i = 0; i < count; i++) {
      const accept = (await fileInputs.nth(i).getAttribute('accept')) || '';
      if (!accept || accept.includes('pdf') || accept.includes('*') || accept.includes('.')) {
        target = fileInputs.nth(i);
        break;
      }
    }
    await target.setInputFiles(pdfPath);
  } else {
    const plus = page.locator(
      '[data-testid="composer-plus-btn"], button[aria-label*="Attach"], button[aria-label*="Upload"], button[aria-label*="Add photos"]',
    ).first();
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 15000 }),
      plus.click(),
    ]);
    await chooser.setFiles(pdfPath);
  }

  // Wait for upload / processing chip
  const name = pdfPath.split('/').pop() || 'pdf';
  await page.waitForFunction(
    (needle) => document.body?.innerText?.includes(needle),
    name.replace(/\.pdf$/i, ''),
    { timeout: 90000 },
  ).catch(() => {});
  // Clear uploading states if present
  await page.waitForFunction(
    () => {
      const busy = document.querySelector('[data-state="uploading"], [data-state="loading"], [aria-busy="true"]');
      const text = document.body?.innerText || '';
      return !busy && !/Uploading|Processing…|Processing\.\.\./i.test(text);
    },
    { timeout: 120000 },
  ).catch(() => {});
  await sleep(page, 2500);
}

async function typePrompt(page, text, { beat, sleep }) {
  beat('ChatGPT — type prompt');
  const composer = page.locator('#prompt-textarea, [data-testid="prompt-textarea"]').first();
  await composer.click({ timeout: 15000 });
  await sleep(page, 500);
  // contenteditable: type works more reliably than fill
  await page.keyboard.type(text, { delay: 12 });
  await sleep(page, 1500);
}

async function sendAndWait(page, { beat, sleep }) {
  beat('ChatGPT — send + wait for reply');
  const before = await page.locator('[data-message-author-role="assistant"]').count();

  const send = page.locator(
    'button[data-testid="send-button"], button[aria-label="Send prompt"], button[aria-label*="Send"]',
  ).first();
  if (await send.isEnabled().catch(() => false)) {
    await send.click();
  } else {
    await page.keyboard.press('Enter');
  }

  // Wait until a new assistant turn appears and streaming finishes
  await page.waitForFunction(
    (prev) => document.querySelectorAll('[data-message-author-role="assistant"]').length > prev,
    before,
    { timeout: 180000 },
  );

  // Stop button present while generating
  const stop = page.locator(
    'button[data-testid="stop-button"], button[aria-label*="Stop"]',
  ).first();
  await stop.waitFor({ state: 'visible', timeout: 30000 }).catch(() => {});
  await stop.waitFor({ state: 'hidden', timeout: 300000 }).catch(() => {});

  // Extra settle for late tokens
  await sleep(page, 4000);

  const assistants = page.locator('[data-message-author-role="assistant"]');
  const n = await assistants.count();
  if (!n) throw new Error('No assistant message found');
  const last = assistants.nth(n - 1);
  const text = ((await last.innerText()) || '').trim();
  if (text.length < 40) throw new Error(`Assistant reply too short (${text.length} chars)`);
  return text;
}

/**
 * Full live beat on the *same* Playwright page (keeps one continuous video).
 * Caller must re-open Privilege and restore SPA state afterward.
 */
export async function runLiveChatGPTOnPage(page, pdfPath, helpers) {
  const { beat, sleep } = helpers;
  beat('ChatGPT — open');
  await page.goto(CHATGPT_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(page, 4000);

  for (const label of ['Accept all', 'Accept', 'Agree', 'Got it', 'OK']) {
    const btn = page.getByRole('button', { name: label, exact: false }).first();
    if (await btn.isVisible().catch(() => false)) {
      await btn.click().catch(() => {});
      await sleep(page, 800);
    }
  }

  const composer = page.locator('#prompt-textarea, [data-testid="prompt-textarea"], div[contenteditable="true"]').first();
  try {
    await composer.waitFor({ state: 'visible', timeout: 45000 });
  } catch {
    const shot = joinMediaShot();
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    const err = new Error(`ChatGPT composer not found — log in via setup-chatgpt-profile.mjs. Screenshot: ${shot}`);
    err.screenshot = shot;
    throw err;
  }

  const newChat = page.getByRole('button', { name: /new chat/i }).first();
  if (await newChat.isVisible().catch(() => false)) {
    await newChat.click().catch(() => {});
    await sleep(page, 2000);
  }

  // Prefer a collapsed sidebar so personal history is less visible on camera.
  const closeSidebar = page.getByRole('button', { name: /close sidebar|hide sidebar/i }).first();
  if (await closeSidebar.isVisible().catch(() => false)) {
    await closeSidebar.click().catch(() => {});
    await sleep(page, 600);
  }

  try {
    await attachPdf(page, pdfPath, helpers);
    await typePrompt(page, PROMPT, helpers);
    const reply = await sendAndWait(page, helpers);
    beat(`ChatGPT — got reply (${reply.length} chars)`);
    await sleep(page, 8000);
    return { reply };
  } catch (err) {
    const shot = joinMediaShot();
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {});
    err.screenshot = shot;
    throw err;
  }
}

function joinMediaShot() {
  return join(dirname(fileURLToPath(import.meta.url)), '../../docs/media/.chatgpt-failed.png');
}

export const FALLBACK_REPLY =
  'Summary for the operating committee: prioritize lease-notice timing on [VALUE_2]. ' +
  'Flag empty-repositioning cost pressure before any footprint decision on [VALUE_1]. ' +
  'No public announcement is implied.';
