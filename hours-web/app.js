// Godziny Pracy (web/iPhone) — ekran. Logika obliczeń jest w core.js (wspólna z testami).
import * as C from './core.js';

const VERSION = '1.7';
const KEY = 'godziny-pracy-v1';
const FORGOTTEN_AFTER = 12 * C.HOUR;
const WEEK_DAYS = [1, 2, 3, 4, 5, 6, 0];   // kolejność na liście (od poniedziałku), wartości Date.getDay()

const $ = id => document.getElementById(id);
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

// ------------------------------------------------------------ dane (tylko w tym telefonie)

let db = { entries: [], nextId: 1, rateCents: C.DEFAULT_RATE_CENTS, firstDay: 1, theme: 'system' };
try {
  const raw = localStorage.getItem(KEY);
  if (raw) db = { ...db, ...JSON.parse(raw) };
  db.entries = (db.entries || []).filter(C.isValid);
} catch { /* brak pamięci — działa do zamknięcia */ }
navigator.storage?.persist?.().catch(() => {});

function save() {
  try { localStorage.setItem(KEY, JSON.stringify(db)); } catch { toast('Nie udało się zapisać danych w telefonie.'); }
}
const all = () => db.entries.slice();
function add(start, end, breakMin, manual) {
  const e = C.entry(db.nextId++, start, end, breakMin, db.rateCents, start, end, manual);
  db.entries.push(e); save(); return e;
}
function update(e) { db.entries = db.entries.map(o => (o.id === e.id ? e : o)); save(); }
function removeIds(ids) { db.entries = db.entries.filter(e => !ids.includes(e.id)); save(); }
function restore(list) {
  let n = 0, hasRun = !!C.running(db.entries);
  for (const e of list) {
    if (db.entries.some(o => o.id === e.id) || (C.isRunning(e) && hasRun)) continue;
    db.entries.push(e); n++;
  }
  save(); return n;
}

// ------------------------------------------------------------ stan ekranu

let weekStart = C.weekStart(Date.now(), db.firstDay);
const currentWeek = () => C.weekStart(Date.now(), db.firstDay);
let lastMinute = -1;

function applyTheme() {
  const r = document.documentElement;
  if (db.theme === 'light' || db.theme === 'dark') r.dataset.theme = db.theme; else delete r.dataset.theme;
}

function render() {
  const now = Date.now();
  const list = all();
  const run = C.running(list);
  $('rateBtn').textContent = `${C.formatMoney(db.rateCents)}/h  ✎`;

  const status = $('status');
  status.className = 'status';
  if (run) {
    status.textContent = `W pracy od ${C.fmtHM(run.start)}`
      + (C.dayStart(run.start) === C.dayStart(now) ? '' : ` (${C.dayShort(run.start)} ${C.fmtDM(run.start)})`);
    status.classList.add('on');
    if (now - run.start > FORGOTTEN_AFTER) {
      status.textContent = `Ponad 12 h od Clock In (${C.fmtHM(run.start)}). Zapomniany Clock Out? Dotknij wpis, aby ustawić koniec.`;
      status.className = 'status warn';
    }
    $('timer').textContent = C.formatHms(now - run.start);
    $('timer').classList.remove('idle');
    $('earned').textContent = C.formatMoney(C.payCents(C.minutes(run, now), run.rateCents));
    $('earned').hidden = $('earnedLabel').hidden = false;
    $('clockBtn').textContent = 'Clock Out';
    $('clockBtn').className = 'big out';
  } else {
    status.textContent = 'Nie jesteś w pracy';
    $('timer').textContent = '00:00:00';
    $('timer').classList.add('idle');
    $('earned').hidden = $('earnedLabel').hidden = true;
    $('clockBtn').textContent = 'Clock In';
    $('clockBtn').className = 'big in';
  }

  const current = weekStart === currentWeek();
  $('weekLabel').textContent = C.weekLabel(weekStart);
  $('thisWeek').hidden = current;
  $('nextWeek').disabled = current;

  const week = C.inRange(list, weekStart, C.addWeeks(weekStart, 1));
  const s = C.summarize(week, now);
  $('weekHours').textContent = `${C.formatHm(s.minutes)} h`;
  $('weekHoursDec').textContent = `= ${C.formatDecimalHours(s.minutes)} h`;
  $('weekPay').textContent = C.formatMoney(s.payCents);
  $('weekDays').textContent = `brutto · dni pracy: ${s.days}`;

  const box = $('entryList');
  box.replaceChildren();
  $('emptyMsg').hidden = week.length > 0;
  $('editHint').hidden = week.length === 0;
  let day = -1;
  for (const e of week) {
    const d = C.dayStart(e.start);
    if (d !== day) {
      day = d;
      const dayEntries = week.filter(o => C.dayStart(o.start) === d);
      let dm = 0, dp = 0;
      for (const o of dayEntries) { const m = C.minutes(o, now); dm += m; dp += C.payCents(m, o.rateCents); }
      const h = el('button', 'dayhead');
      h.dataset.day = String(d);
      h.setAttribute('aria-label', `Dzień ${C.dayShort(e.start)} ${C.fmtDM(e.start)}: usuń albo dodaj wpis`);
      h.append(el('b', null, `${C.dayShort(e.start)} ${C.fmtDM(e.start)}  ⋯`), el('span', null, `${C.formatHm(dm)} h · ${C.formatMoney(dp)}`));
      h.onclick = () => openDay(d);
      box.append(h);
    }
    const m = C.minutes(e, now);
    let range = `${C.fmtHM(e.start)} – ${C.isRunning(e) ? 'teraz' : C.fmtHM(e.end)}`;
    if (!C.isRunning(e) && C.dayStart(e.end) !== d) range += ' (+1)';
    const row = el('button', 'row');
    row.dataset.id = String(e.id);
    const left = el('span');
    left.append(el('span', 'range' + (C.isRunning(e) ? ' live' : ''), range));
    const n = C.notes(e);
    if (n) left.append(el('span', 'note', (C.isEdited(e) ? '✎ ' : '') + n));
    row.append(left, el('span', 'dur', `${C.formatHm(m)} h`), el('span', 'pay', C.formatMoney(C.payCents(m, e.rateCents))));
    row.onclick = () => openEntry(e);
    box.append(row);
  }
}

function tick() {
  const run = C.running(db.entries);
  if (!run) return;
  const now = Date.now();
  $('timer').textContent = C.formatHms(now - run.start);
  const m = C.minutes(run, now);
  $('earned').textContent = C.formatMoney(C.payCents(m, run.rateCents));
  if (m !== lastMinute) { lastMinute = m; render(); }
}

// ------------------------------------------------------------ Clock In / Out

function toggleClock() {
  const now = Date.now();
  const run = C.running(db.entries);
  if (run) {
    if (now - run.start < C.MINUTE) {
      removeIds([run.id]);
      toast('Zmiana krótsza niż minuta — nie zapisano.');
    } else {
      const done = { ...run, end: now, origEnd: now };
      update(done);
      const m = C.minutes(done, now);
      toast(`Zapisano: ${C.formatHm(m)} h · ${C.formatMoney(C.payCents(m, done.rateCents))}`);
    }
  } else {
    const err = C.validate(db.entries, -1, now, 0, 0, now);
    if (err) { toast(err); return; }
    add(now, 0, 0, false);
    weekStart = currentWeek();
  }
  lastMinute = -1;
  render();
}

// ------------------------------------------------------------ okna

const show = d => { if (!d.open) d.showModal(); };
const hide = d => d.close();
for (const d of document.querySelectorAll('dialog')) {
  d.addEventListener('click', ev => { if (ev.target === d) d.close(); });   // dotknięcie tła zamyka
}

function ask(title, text, yes = 'OK') {
  return new Promise(resolve => {
    $('askTitle').textContent = title;
    $('askText').textContent = text;
    $('askYes').textContent = yes;
    $('askNo').hidden = yes === null;
    if (yes === null) $('askYes').textContent = 'OK';
    const done = v => { hide($('askDlg')); $('askYes').onclick = $('askNo').onclick = null; resolve(v); };
    $('askYes').onclick = () => done(true);
    $('askNo').onclick = () => done(false);
    show($('askDlg'));
  });
}

let toastTimer;
function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3000);
}

// ------------------------------------------------------------ edycja wpisu

const ed = {};
const hhmm = t => C.fmtHM(t);
const parseHM = v => v.split(':').map(Number);

function openEntry(entry, presetDay = -1) {
  const now = Date.now();
  ed.entry = entry;
  if (entry) {
    Object.assign(ed, { start: entry.start, end: entry.end, running: C.isRunning(entry), brk: entry.breakMin, rate: entry.rateCents });
  } else {
    const we = C.addWeeks(weekStart, 1);
    const day = presetDay >= 0 ? presetDay : (now >= weekStart && now < we ? C.dayStart(now) : weekStart);
    let s = C.atTime(day, 8, 0), e = C.atTime(day, 16, 0);
    if (e > now) { e = now - (now % C.MINUTE); s = Math.max(C.dayStart(now), e - 8 * C.HOUR); }
    Object.assign(ed, { start: s, end: e, running: false, brk: 0, rate: db.rateCents });
  }
  $('entryTitle').textContent = entry ? 'Edytuj wpis' : 'Nowy wpis';
  $('fDelete').hidden = !entry;
  $('fDate').max = C.fmtISO(now);
  const c = $('fClock');
  c.hidden = !(entry && !entry.manual);
  if (entry && !entry.manual) {
    c.textContent = `Z zegara: ${C.fmtHM(entry.origStart)} – ${entry.origEnd === 0 ? (C.isRunning(entry) ? 'trwa' : 'brak Clock Out') : C.fmtHM(entry.origEnd)}  (zachowane w raporcie)`;
  }
  fillEntry();
  show($('entryDlg'));
}

function keepEnd() {
  if (ed.running) return;
  const o = new Date(ed.end);
  ed.end = C.endAfter(ed.start, o.getHours(), o.getMinutes(), o.getSeconds());
}

function fillEntry() {
  const now = Date.now();
  $('fDate').value = C.fmtISO(ed.start);
  $('fStart').value = hhmm(ed.start);
  $('fEnd').hidden = ed.running;
  $('fEndRunning').hidden = !ed.running;
  if (!ed.running) $('fEnd').value = hhmm(ed.end);
  const probe = C.entry(-1, ed.start, ed.running ? 0 : ed.end, ed.brk, ed.rate);
  const m = C.minutes(probe, now);
  $('fSummary').textContent = `${C.formatHm(m)} h  ·  ${C.formatMoney(C.payCents(m, ed.rate))}   (${C.formatMoney(ed.rate)}/h)`;
  for (const b of document.querySelectorAll('#breakRow button')) b.classList.toggle('on', Number(b.dataset.break) === ed.brk);
  const hint = $('fHint');
  if (ed.running) {
    hint.textContent = 'Zmiana trwa. Odejmowanie czasu przesuwa początek. Ustaw koniec, aby zakończyć zmianę.';
    hint.hidden = false;
  } else if (C.dayStart(ed.end) !== C.dayStart(ed.start)) {
    hint.textContent = `Koniec następnego dnia: ${C.dayShort(ed.end)} ${C.fmtDM(ed.end)} (zmiana przez północ)`;
    hint.hidden = false;
  } else hint.hidden = true;
  $('fError').hidden = true;
}

function entryError(msg) { $('fError').textContent = msg; $('fError').hidden = false; }

$('fDate').addEventListener('change', () => {
  if (!$('fDate').value) return;
  const [y, mo, d] = $('fDate').value.split('-').map(Number);
  const s = new Date(ed.start);
  s.setFullYear(y, mo - 1, d);
  ed.start = s.getTime();
  keepEnd(); fillEntry();
});
$('fStart').addEventListener('change', () => {
  if (!$('fStart').value) return;
  const [h, m] = parseHM($('fStart').value);
  const s = new Date(ed.start);
  s.setHours(h, m, 0, 0);
  ed.start = s.getTime();
  keepEnd(); fillEntry();
});
$('fEnd').addEventListener('change', () => {
  if (!$('fEnd').value) return;
  const [h, m] = parseHM($('fEnd').value);
  ed.end = C.endAfter(ed.start, h, m, 0);
  ed.running = false;
  fillEntry();
});
$('fEndRunning').onclick = () => {
  const n = new Date();
  ed.end = C.endAfter(ed.start, n.getHours(), n.getMinutes(), 0);
  ed.running = false;
  fillEntry();
  $('fEnd').focus();
};
for (const b of document.querySelectorAll('#adjustRow button')) {
  b.onclick = () => {
    const delta = Number(b.dataset.delta) * C.MINUTE;
    const r = C.adjust(ed.start, ed.running ? 0 : ed.end, delta, Date.now());
    if (!r) { entryError(delta < 0 ? 'Nie można odjąć więcej, niż trwa wpis.' : 'Koniec nie może być w przyszłości.'); return; }
    ed.start = r[0];
    if (!ed.running) ed.end = r[1];
    fillEntry();
  };
}
for (const b of document.querySelectorAll('#breakRow button')) {
  b.onclick = () => { ed.brk = Number(b.dataset.break); fillEntry(); };
}
$('fCancel').onclick = () => hide($('entryDlg'));
$('entryForm').addEventListener('submit', ev => {
  ev.preventDefault();
  const end = ed.running ? 0 : ed.end;
  const err = C.validate(db.entries, ed.entry ? ed.entry.id : -1, ed.start, end, ed.brk, Date.now());
  if (err) { entryError(err); return; }
  if (ed.entry) update({ ...ed.entry, start: ed.start, end, breakMin: ed.brk });
  else add(ed.start, end, ed.brk, true);
  weekStart = C.weekStart(ed.start, db.firstDay);
  hide($('entryDlg'));
  lastMinute = -1;
  render();
});
$('fDelete').onclick = async () => {
  const e = ed.entry;
  if (!e) return;
  hide($('entryDlg'));
  if (await ask('Usunąć wpis?', `${C.dayShort(e.start)} ${C.fmtDM(e.start)} ${C.fmtHM(e.start)}`, 'Usuń')) {
    deleteWithUndo([e], `Usunięto wpis ${C.dayShort(e.start)} ${C.fmtDM(e.start)} ${C.fmtHM(e.start)}`);
  }
};

// ------------------------------------------------------------ dzień i „Cofnij”

let dayOpen = -1;
function openDay(day) {
  const now = Date.now();
  const list = C.inRange(db.entries, day, C.addDays(day, 1));
  if (!list.length) return;
  dayOpen = day;
  let m = 0, p = 0, text = '';
  for (const e of list) {
    const x = C.minutes(e, now);
    m += x; p += C.payCents(x, e.rateCents);
    text += `• ${C.fmtHM(e.start)} – ${C.isRunning(e) ? 'teraz (trwa)' : C.fmtHM(e.end)}   ${C.formatHm(x)} h\n`;
  }
  text += `\nRazem: ${C.formatHm(m)} h · ${C.formatMoney(p)}`;
  $('dayTitle').textContent = `${C.dayShort(day)} ${C.fmtDMY(day)}`;
  $('dayText').textContent = text;
  show($('dayDlg'));
}
$('dayCancel').onclick = () => hide($('dayDlg'));
$('dayAdd').onclick = () => { hide($('dayDlg')); openEntry(null, dayOpen); };
$('dayDelete').onclick = () => {
  const list = C.inRange(db.entries, dayOpen, C.addDays(dayOpen, 1));
  hide($('dayDlg'));
  deleteWithUndo(list, `Usunięto ${C.dayShort(dayOpen)} ${C.fmtDM(dayOpen)}: ${C.formatHm(C.summarize(list, Date.now()).minutes)} h`);
};

let lastDeleted = null, undoTimer;
function deleteWithUndo(list, msg) {
  removeIds(list.map(e => e.id));
  lastDeleted = list;
  $('undoText').textContent = msg;
  $('undoBar').hidden = false;
  clearTimeout(undoTimer);
  undoTimer = setTimeout(hideUndo, 15_000);
  lastMinute = -1;
  render();
}
function hideUndo() { lastDeleted = null; $('undoBar').hidden = true; }
$('undoBtn').onclick = () => {
  if (lastDeleted) {
    const n = restore(lastDeleted);
    toast(n === lastDeleted.length ? `Przywrócono (${n}).` : `Przywrócono ${n} z ${lastDeleted.length} — trwającej zmiany nie, bo trwa już nowa.`);
  }
  clearTimeout(undoTimer);
  hideUndo();
  lastMinute = -1;
  render();
};

// ------------------------------------------------------------ raporty

const rep = { mode: 'week', cursor: 0, text: '' };
function openReport(mode) {
  rep.mode = mode;
  const now = Date.now();
  rep.cursor = mode === 'week' ? weekStart
    : (weekStart === currentWeek() ? C.monthStart(now) : C.monthStart(weekStart));
  $('reportTitle').textContent = mode === 'week' ? 'Raport tygodnia' : 'Raport miesiąca';
  fillReport();
  show($('reportDlg'));
}
function fillReport() {
  const now = Date.now();
  if (rep.mode === 'week') {
    rep.text = C.weekReport(C.inRange(db.entries, rep.cursor, C.addWeeks(rep.cursor, 1)), rep.cursor, now);
    $('repLabel').textContent = C.weekLabel(rep.cursor);
    $('repNext').disabled = rep.cursor >= currentWeek();
  } else {
    rep.text = C.monthReport(db.entries, rep.cursor, db.firstDay, now);
    $('repLabel').textContent = C.monthLabel(rep.cursor);
    $('repNext').disabled = rep.cursor >= C.monthStart(now);
  }
  rep.text += `\nGodziny Pracy ${VERSION} (iPhone)\n`;
  $('reportText').textContent = rep.text;
}
const stepReport = n => {
  rep.cursor = rep.mode === 'week' ? C.addWeeks(rep.cursor, n) : C.addMonths(rep.cursor, n);
  fillReport();
};
$('repPrev').onclick = () => stepReport(-1);
$('repNext').onclick = () => stepReport(1);
$('repClose').onclick = () => hide($('reportDlg'));
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast('Skopiowano raport.'); }
  catch {
    const r = document.createRange();
    r.selectNodeContents($('reportText'));
    getSelection().removeAllRanges();
    getSelection().addRange(r);
    toast('Zaznaczono — wybierz „Kopiuj”.');
  }
}
$('repCopy').onclick = () => copyText(rep.text);
$('repShare').onclick = async () => {
  const title = `Godziny pracy ${$('repLabel').textContent}`;
  if (navigator.share) {
    try { await navigator.share({ title, text: rep.text }); } catch { /* anulowano */ }
  } else copyText(rep.text);
};

// ------------------------------------------------------------ ustawienia i kopia CSV

function openSettings() {
  $('version').textContent = `· wersja ${VERSION}`;
  $('sRate').value = C.rateForInput(db.rateCents);
  $('sRateWeek').checked = true;
  $('sError').hidden = true;
  const sel = $('sWeek');
  sel.replaceChildren(...WEEK_DAYS.map(d => {
    const o = el('option', null, `${C.DAYS_FULL[d]}, 00:00`);
    o.value = String(d);
    return o;
  }));
  sel.value = String(db.firstDay);
  for (const r of document.querySelectorAll('#sTheme input')) r.checked = r.value === db.theme;
  show($('settingsDlg'));
}
$('sCancel').onclick = () => hide($('settingsDlg'));
$('settingsForm').addEventListener('submit', ev => {
  ev.preventDefault();
  const cents = C.parseRate($('sRate').value);
  if (cents <= 0) { $('sError').textContent = 'Wpisz stawkę, np. 34 albo 34.50'; $('sError').hidden = false; return; }
  if (cents !== db.rateCents) {
    // Historia zostaje przy starej stawce; bieżący tydzień — według wyboru.
    const from = $('sRateWeek').checked ? currentWeek() : Infinity;
    db.entries = db.entries.map(e => (e.start >= from ? { ...e, rateCents: cents } : e));
    db.rateCents = cents;
  }
  db.firstDay = Number($('sWeek').value);
  db.theme = document.querySelector('#sTheme input:checked')?.value || 'system';
  weekStart = C.weekStart(weekStart, db.firstDay);
  save();
  applyTheme();
  hide($('settingsDlg'));
  render();
});
$('sExport').onclick = async () => {
  const name = `godziny-pracy-${C.fmtISO(Date.now())}.csv`;
  const csv = '﻿' + C.csvExport(db.entries, Date.now());
  const file = new File([csv], name, { type: 'text/csv' });
  if (navigator.canShare?.({ files: [file] })) {
    try { await navigator.share({ files: [file], title: name }); return; } catch (e) { if (e.name === 'AbortError') return; }
  }
  const a = el('a');
  a.href = URL.createObjectURL(file);
  a.download = name;
  document.body.append(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  toast(`Zapisano kopię: ${db.entries.length} wpisów.`);
};
$('sImport').onclick = () => $('sFile').click();
$('sFile').addEventListener('change', async () => {
  const f = $('sFile').files[0];
  $('sFile').value = '';
  if (!f) return;
  if (f.size > 5_000_000) { await ask('Nie przywrócono', 'Plik jest za duży.', null); return; }
  const r = C.csvParse(await f.text());
  hide($('settingsDlg'));
  if (r.error) { await ask('Nie przywrócono', r.error, null); return; }
  if (await ask('Przywrócić kopię?', `Obecne wpisy (${db.entries.length}) zostaną zastąpione ${r.entries.length} wpisami z pliku.`, 'Przywróć')) {
    db.entries = r.entries;
    db.nextId = Math.max(db.nextId, ...r.entries.map(e => e.id + 1), 1);
    save();
    lastMinute = -1;
    render();
    toast(`Przywrócono ${r.entries.length} wpisów.`);
  }
});

// ------------------------------------------------------------ start

$('clockBtn').onclick = toggleClock;
$('rateBtn').onclick = openSettings;
$('prevWeek').onclick = () => { weekStart = C.addWeeks(weekStart, -1); render(); };
$('nextWeek').onclick = () => { const t = C.addWeeks(weekStart, 1); if (t <= currentWeek()) { weekStart = t; render(); } };
$('thisWeek').onclick = () => { weekStart = currentWeek(); render(); };
$('addEntry').onclick = () => openEntry(null);
$('weekReportBtn').onclick = () => openReport('week');
$('monthReportBtn').onclick = () => openReport('month');
document.addEventListener('visibilitychange', () => { if (!document.hidden) { lastMinute = -1; render(); } });

const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
$('installHint').hidden = !(ios && !navigator.standalone && !matchMedia('(display-mode: standalone)').matches);

applyTheme();
render();
setInterval(tick, 1000);
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
window.__godziny = { db: () => db, VERSION };   // do testów e2e
