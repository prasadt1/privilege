#!/usr/bin/env node
/**
 * One-time ChatGPT login for the Privilege demo recorder.
 *
 * Opens Chrome with a dedicated profile. Log in to chatgpt.com, open a blank
 * chat, then press Enter in this terminal (or close the browser window).
 *
 *   cd tools/devpost-gallery
 *   node setup-chatgpt-profile.mjs
 *
 * Profile path (gitignored): tools/devpost-gallery/.chrome-profile
 * Override: CHROME_PROFILE=/path/to/dir
 */
import { mkdirSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROFILE =
  process.env.CHROME_PROFILE || join(__dirname, '.chrome-profile');

async function main() {
  mkdirSync(PROFILE, { recursive: true });
  console.log('Chrome profile:', PROFILE);
  console.log('1) Log into https://chatgpt.com in the window that opens');
  console.log('2) Dismiss any onboarding / cookie banners');
  console.log('3) Leave a blank new chat ready');
  console.log('4) Return here and press Enter (or close the browser)\n');

  let context;
  try {
    context = await chromium.launchPersistentContext(PROFILE, {
      channel: 'chrome',
      headless: false,
      viewport: { width: 1280, height: 800 },
      args: ['--disable-blink-features=AutomationControlled'],
    });
  } catch (chromeErr) {
    console.warn('System Chrome failed, trying Playwright Chromium…');
    try {
      context = await chromium.launchPersistentContext(PROFILE, {
        headless: false,
        viewport: { width: 1280, height: 800 },
      });
    } catch (chromiumErr) {
      console.error('Could not launch a browser.');
      console.error('Run: npx playwright install chromium');
      console.error(chromeErr.message.split('\n')[0]);
      console.error(chromiumErr.message.split('\n')[0]);
      process.exit(1);
    }
  }

  const page = context.pages()[0] || (await context.newPage());
  await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded', timeout: 120000 });

  await new Promise((resolveWait) => {
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    rl.question('Press Enter when ChatGPT login looks good… ', () => {
      rl.close();
      resolveWait();
    });
  });

  await context.close();
  console.log('\nProfile saved. Next:');
  console.log('  ./run-full-demo.sh');
  console.log('or:');
  console.log('  CHATGPT_MODE=live node record-pdf-lifecycle.mjs');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
