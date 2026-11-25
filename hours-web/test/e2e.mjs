// Test całej aplikacji w przeglądarce (ekran iPhone'a 13, strefa Nowego Jorku).
// Uruchomienie: TZ=America/New_York node test/e2e.mjs  [katalog-na-zrzuty]
import { createRequire } from 'node:module';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import assert from 'node:assert/strict';
import * as C from '../core.js';

const { chromium, devices } = createRequire(import.meta.url)('playwright');

const ROOT = new URL('..', import.meta.url).pathname;
const SHOTS = process.argv[2] || join(ROOT, 'test', 'screenshots');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.webmanifest': 'application/manifest+json' };

const server = createServer(async (req, res) => {
  const path = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname)).replace(/^(\.\.[/\\])+/, '');
  const file = path.endsWith('/') ? path + 'index.html' : path;
  try {
    const body = await readFile(join(ROOT, file));
    res.writeHead(200, { 'content-type': TYPES[extname(file)] || 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404); res.end(); }
}).listen(0);
const URL0 = `http://localhost:${server.address().port}/`;

const browser = await chromium.launch();
const ctx = await browser.newContext({ ...devices['iPhone 13'], timezoneId: 'America/New_York', locale: 'pl-PL', acceptDownloads: true });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
await mkdir(SHOTS, { recursive: true });
const db = () => page.evaluate(() => window.__godziny.db());
const set = (sel, v) => page.locator(sel).evaluate((el, val) => { el.value = val; el.dispatchEvent(new Event('change')); }, v);
let step = 0;
const ok = msg => console.log(`ok ${++step} - ${msg}`);

try {
  await page.goto(URL0);
  assert.equal(await page.title(), 'Godziny Pracy');
  assert.equal(await page.textContent('#rateBtn'), '$34.00/h  ✎');
  ok('start: tytuł i stawka $34');

  await page.click('#clockBtn');
  assert.equal(await page.textContent('#clockBtn'), 'Clock Out');
  assert.equal((await db()).entries.length, 1);
  await page.click('#clockBtn');
  assert.equal((await db()).entries.length, 0);
  assert.match(await page.textContent('#toast'), /krótsza niż minuta/);
  ok('Clock In → Clock Out po chwili: zmiana < 1 min nie jest zapisywana');

  // Wpis ręczny: wczoraj 08:00–16:30, przerwa 30 min ⇒ 8:00 h = $272.00
  const now = Date.now();
  const y = C.addDays(C.dayStart(now), -1);
  await page.click('#addEntry');
  await set('#fDate', C.fmtISO(y));
  await set('#fStart', '08:00');
  await set('#fEnd', '16:30');
  await page.click('#breakRow [data-break="30"]');
  assert.match(await page.textContent('#fSummary'), /^8:00 h {2}· {2}\$272\.00/);
  await page.screenshot({ path: join(SHOTS, 'edycja.png') });
  await page.click('#fSave');
  let e = (await db()).entries[0];
  assert.deepEqual([e.start, e.end, e.breakMin, e.manual], [C.atTime(y, 8, 0), C.atTime(y, 16, 30), 30, true]);
  assert.match(await page.textContent('#entryList'), /08:00 – 16:30.*przerwa 0:30; dodano ręcznie/s);
  ok('dodanie wpisu ręcznie z przerwą: 8:00 h, $272.00');

  await page.click(`#entryList .row[data-id="${e.id}"]`);
  await page.click('#adjustRow [data-delta="-15"]');
  await page.click('#fSave');
  e = (await db()).entries[0];
  assert.equal(C.minutes(e, 0), 7 * 60 + 45);
  assert.equal(await page.textContent('#weekPay'), '$263.50');
  ok('edycja −15 min: 7:45 h, tydzień $263.50');

  // Raport miesiąca (miesiąc wpisu)
  await page.click('#monthReportBtn');
  if ((await page.textContent('#repLabel')) !== C.monthLabel(C.monthStart(y))) await page.click('#repPrev');
  const month = await page.textContent('#reportText');
  assert.match(month, /^RAPORT MIESIĘCZNY — GODZINY PRACY/);
  assert.match(month, new RegExp(`${C.fmtDM(y)}  08:00–16:15    7:45 h    \\$263\\.50`));
  assert.match(month, /DO WYPŁATY: {2}\$263\.50 brutto/);
  await page.screenshot({ path: join(SHOTS, 'raport-miesiac.png') });
  await page.click('#repClose');
  ok('raport miesiąca: wiersz wpisu i suma $263.50');

  // Usunięcie dnia i „Cofnij”
  await page.click('#entryList .dayhead');
  await page.click('#dayDelete');
  assert.equal((await db()).entries.length, 0);
  assert.equal(await page.isVisible('#undoBar'), true);
  await page.click('#undoBtn');
  assert.equal((await db()).entries.length, 1);
  ok('usuń dzień → Cofnij przywraca wpis');

  // Kopia CSV: eksport (pobranie w Chromium) i przywrócenie z tego samego pliku
  await page.click('#rateBtn');
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#sExport')]);
  const csvPath = join(SHOTS, 'kopia.csv');
  await dl.saveAs(csvPath);
  const parsed = C.csvParse(await readFile(csvPath, 'utf8'));
  assert.equal(parsed.entries.length, 1);
  assert.equal(parsed.entries[0].breakMin, 30);
  await page.setInputFiles('#sFile', csvPath);          // „Przywróć” w tym samym oknie
  await page.click('#askYes');
  assert.equal((await db()).entries.length, 1);
  ok('eksport CSV i przywrócenie z pliku');

  // Ustawienia: stawka $40 tylko od bieżącego tygodnia, motyw ciemny
  await page.click('#rateBtn');
  await page.fill('#sRate', '40');
  await page.click('#sTheme input[value="dark"]');
  await page.click('#settingsForm button[type="submit"]');
  assert.equal(await page.textContent('#rateBtn'), '$40.00/h  ✎');
  assert.equal(await page.getAttribute('html', 'data-theme'), 'dark');
  const expectRate = C.weekStart(y, 1) === C.weekStart(now, 1) ? 4000 : 3400;
  assert.equal((await db()).entries[0].rateCents, expectRate);
  ok('zmiana stawki nie rusza poprzednich tygodni; motyw ciemny');

  // Trwająca zmiana do zrzutu ekranu
  await page.click('#clockBtn');
  await page.evaluate(() => { const d = window.__godziny.db(); d.entries.find(x => x.end === 0).start -= 2 * 3600e3 + 14 * 60e3; });
  await page.click('#thisWeek').catch(() => {});
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.waitForTimeout(1100);
  await page.screenshot({ path: join(SHOTS, 'ekran-ciemny.png'), fullPage: true });
  await page.click('#rateBtn');
  await page.click('#sTheme input[value="light"]');
  await page.click('#settingsForm button[type="submit"]');
  await page.screenshot({ path: join(SHOTS, 'ekran.png'), fullPage: true });
  ok('zrzuty ekranu');

  // Tryb offline po zainstalowaniu service workera
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await ctx.setOffline(true);
  await page.reload();
  assert.equal(await page.title(), 'Godziny Pracy');
  assert.equal((await db()).entries.length, 2);
  await ctx.setOffline(false);
  ok('działa offline i dane zostają po ponownym uruchomieniu');

  assert.deepEqual(errors, []);
  ok('brak błędów JavaScript');
  console.log(`\n# ${step} kroków, wszystkie zaliczone`);
} catch (err) {
  await page.screenshot({ path: join(SHOTS, 'blad.png'), fullPage: true }).catch(() => {});
  console.error(err);
  if (errors.length) console.error('Błędy strony:', errors);
  process.exitCode = 1;
} finally {
  await browser.close();
  server.close();
}
