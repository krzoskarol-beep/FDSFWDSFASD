// Ten sam kod Puppeteera dla obu przeglądarek — różni się tylko sposób połączenia.
//
//   node scrape.mjs lightpanda [N]   # łączy się z `lightpanda serve` (LIGHTPANDA_WS)
//   node scrape.mjs chrome [N]       # uruchamia Chromium (CHROME_PATH)
//
// Zmienne: URL (domyślnie lokalna strona demo), SELECTOR (na co czekać, domyślnie li.product).
import puppeteer from 'puppeteer-core';

const mode = process.argv[2];
const N = Number(process.argv[3] ?? 20);
const URL = process.env.URL ?? 'http://127.0.0.1:8811/';
const SELECTOR = process.env.SELECTOR ?? 'li.product';

if (!['lightpanda', 'chrome'].includes(mode) || !(N > 0)) {
  console.error('użycie: node scrape.mjs <lightpanda|chrome> [liczba_załadowań]');
  process.exit(2);
}

const browser = mode === 'lightpanda'
  ? await puppeteer.connect({ browserWSEndpoint: process.env.LIGHTPANDA_WS ?? 'ws://127.0.0.1:9222' })
  : await puppeteer.launch({
      executablePath: process.env.CHROME_PATH ?? '/opt/pw-browsers/chromium',
      headless: true,
      args: ['--no-sandbox'],
    });

try {
  const t0 = performance.now();
  let result;
  for (let i = 0; i < N; i++) {
    const ctx = await browser.createBrowserContext();
    const page = await ctx.newPage();
    await page.goto(URL);
    await page.waitForSelector(SELECTOR);
    result = await page.evaluate((sel) => {
      const els = [...document.querySelectorAll(sel)];
      const prices = els.map((el) => Number(el.dataset.price)).filter(Number.isFinite);
      const out = { title: document.title, count: els.length };
      if (prices.length) {
        out.max = Math.max(...prices);
        out.avg = +(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2);
      }
      return out;
    }, SELECTOR);
    await page.close();
    await ctx.close();
  }
  const ms = performance.now() - t0;
  console.log(JSON.stringify({
    mode, url: URL, ...result, loads: N,
    total_ms: Math.round(ms), per_page_ms: +(ms / N).toFixed(1),
  }));
} finally {
  await (mode === 'lightpanda' ? browser.disconnect() : browser.close());
}
