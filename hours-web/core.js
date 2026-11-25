// Godziny Pracy — logika bez interfejsu (przeglądarka i Node).
// Odpowiednik WorkMath / Report / Csv z aplikacji na Androida: te same reguły, te same
// teksty raportów i ten sam format CSV (kopia z Androida wczytuje się tutaj i odwrotnie).
// Czas lokalny urządzenia; całe minuty i centy, bez liczb zmiennoprzecinkowych w kwotach.

export const MINUTE = 60_000;
export const HOUR = 60 * MINUTE;
export const MAX_ENTRY = 24 * HOUR;
export const DEFAULT_RATE_CENTS = 3400;

export const DAYS = ['Nd', 'Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb'];                 // indeks = Date.getDay()
export const DAYS_FULL = ['niedziela', 'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota'];
export const MONTHS = ['styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec', 'lipiec',
  'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień'];

const p2 = n => String(n).padStart(2, '0');

// ------------------------------------------------------------ wpis

/** Wpis: end === 0 to zmiana w trakcie. origStart/origEnd — godziny z zegara. */
export function entry(id, start, end, breakMin = 0, rateCents = DEFAULT_RATE_CENTS,
                      origStart = start, origEnd = end, manual = false) {
  return { id, start, end, breakMin: Math.max(0, breakMin | 0), rateCents, origStart, origEnd, manual: !!manual };
}

export const isRunning = e => e.end === 0;
export const endOr = (e, now) => (isRunning(e) ? Math.max(now, e.start) : e.end);

export function isEdited(e) {
  if (e.manual) return true;
  if (e.start !== e.origStart) return true;
  return !isRunning(e) && e.end !== e.origEnd;
}

export function isValid(e) {
  return Number.isSafeInteger(e.id) && e.start > 0 && e.end >= 0 && (e.end === 0 || e.end >= e.start)
    && e.rateCents > 0 && e.breakMin >= 0;
}

// ------------------------------------------------------------ czas kalendarzowy

export function dayStart(t) {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function addDays(t, n) {
  const d = new Date(t);
  d.setDate(d.getDate() + n);
  return d.getTime();
}

export const addWeeks = (t, n) => addDays(t, 7 * n);

/** Północ pierwszego dnia tygodnia roboczego (firstDay: 0 = niedziela … 6 = sobota). */
export function weekStart(t, firstDay) {
  const d = new Date(dayStart(t));
  d.setDate(d.getDate() - ((d.getDay() - firstDay + 7) % 7));
  return d.getTime();
}

export function atTime(t, h, m) {
  const d = new Date(dayStart(t));
  d.setHours(h, m, 0, 0);
  return d.getTime();
}

/** Koniec o h:m:s liczony od początku: ten sam dzień, a gdy wypada przed początkiem — następny. */
export function endAfter(start, h, m, s) {
  const d = new Date(start);
  d.setHours(h, m, s, 0);
  if (d.getTime() <= start) d.setDate(d.getDate() + 1);
  return d.getTime();
}

export function monthStart(t) {
  const d = new Date(dayStart(t));
  d.setDate(1);
  return d.getTime();
}

export function addMonths(ms, n) {
  const d = new Date(ms);
  d.setMonth(d.getMonth() + n);
  return d.getTime();
}

export const monthLabel = ms => `${MONTHS[new Date(ms).getMonth()]} ${new Date(ms).getFullYear()}`;
export const dayShort = t => DAYS[new Date(t).getDay()];
export const fmtHM = t => { const d = new Date(t); return `${p2(d.getHours())}:${p2(d.getMinutes())}`; };
export const fmtDM = t => { const d = new Date(t); return `${p2(d.getDate())}.${p2(d.getMonth() + 1)}`; };
export const fmtDMY = t => `${fmtDM(t)}.${new Date(t).getFullYear()}`;
export const fmtISO = t => { const d = new Date(t); return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`; };

export const weekLabel = ws => `${fmtDM(ws)} – ${fmtDMY(addDays(ws, 6))}`;

export function inRange(all, from, to) {
  return all.filter(e => e.start >= from && e.start < to).sort((a, b) => a.start - b.start);
}

export const running = all => all.find(isRunning) || null;

// ------------------------------------------------------------ czas i pieniądze

export const grossMinutes = (e, now) => Math.floor(Math.max(0, endOr(e, now) - e.start) / MINUTE);
export const minutes = (e, now) => Math.max(0, grossMinutes(e, now) - e.breakMin);

/** Dzielenie z zaokrągleniem połówek w górę (liczby nieujemne, całkowite). */
export const divRound = (a, b) => Math.floor((a + Math.floor(b / 2)) / b);
export const payCents = (min, rate) => divRound(min * rate, 60);

export function summarize(list, now) {
  let total = 0, centMinutes = 0;
  const days = new Set(), rates = new Set();
  for (const e of list) {
    const m = minutes(e, now);
    total += m;
    centMinutes += m * e.rateCents;
    days.add(dayStart(e.start));
    rates.add(e.rateCents);
  }
  return {
    minutes: total,
    payCents: divRound(centMinutes, 60),
    averageRateCents: total === 0 ? 0 : divRound(centMinutes, total),
    mixedRates: rates.size > 1,
    days: days.size,
  };
}

export const formatHm = min => `${Math.floor(min / 60)}:${p2(min % 60)}`;
export function formatHms(ms) {
  const s = Math.floor(Math.max(0, ms) / 1000);
  return `${p2(Math.floor(s / 3600))}:${p2(Math.floor(s / 60) % 60)}:${p2(s % 60)}`;
}
export function formatDecimalHours(min) {
  const h = divRound(min * 100, 60);
  return `${Math.floor(h / 100)}.${p2(h % 100)}`;
}
export function formatMoney(cents) {
  const c = Math.abs(cents);
  const dollars = String(Math.floor(c / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${cents < 0 ? '-' : ''}$${dollars}.${p2(c % 100)}`;
}
export const plainMoney = cents => `${Math.floor(cents / 100)}.${p2(cents % 100)}`;

/** "34", "34,5", "$34.50" → centy; -1 gdy błędne. */
export function parseRate(text) {
  if (text == null) return -1;
  const t = String(text).trim().replace(',', '.').replace('$', '');
  if (!/^\d{1,5}(\.\d{0,2})?$/.test(t)) return -1;
  const [d, c = ''] = t.split('.');
  const v = Number(d) * 100 + (c === '' ? 0 : Number(c.length === 1 ? c + '0' : c));
  return v > 0 ? v : -1;
}
export const rateForInput = c => (c % 100 === 0 ? String(c / 100) : plainMoney(c));

// ------------------------------------------------------------ edycja

/** Skrócenie (delta < 0) albo wydłużenie: zakończony wpis — koniec, trwający — początek. */
export function adjust(start, end, deltaMs, now) {
  if (end === 0) {
    const s = start - deltaMs;
    return s > now - MINUTE ? null : [s, 0];
  }
  const e = end + deltaMs;
  return e - start < MINUTE || e > now ? null : [start, e];
}

export function validate(all, selfId, start, end, breakMin, now) {
  if (start > now) return 'Początek nie może być w przyszłości.';
  const realEnd = end === 0 ? now : end;
  if (end !== 0 && end <= start) return 'Koniec musi być po początku.';
  if (end !== 0 && end > now + MINUTE) return 'Koniec nie może być w przyszłości.';
  if (realEnd - start > MAX_ENTRY) return 'Wpis nie może być dłuższy niż 24 godziny.';
  if (end !== 0 && breakMin > 0 && Math.floor((end - start) / MINUTE) - breakMin < 1) {
    return 'Przerwa nie może być dłuższa niż cały wpis.';
  }
  for (const o of all) {
    if (o.id === selfId) continue;
    const oEnd = endOr(o, now);
    if (start < oEnd && o.start < realEnd) {
      const f = t => `${fmtDM(t)} ${fmtHM(t)}`;
      return `Nakłada się na inny wpis: ${f(o.start)} – ${isRunning(o) ? 'teraz' : f(oEnd)}.`;
    }
  }
  return null;
}

// ------------------------------------------------------------ raporty (tekst jak na Androidzie)

const padL = (s, w) => s.padStart(w, ' ');

export function notes(e) {
  const parts = [];
  if (e.breakMin > 0) parts.push(`przerwa ${formatHm(e.breakMin)}`);
  if (e.manual) parts.push('dodano ręcznie');
  else if (isEdited(e)) {
    parts.push(`poprawiono, zegar: ${fmtHM(e.origStart)}–${e.origEnd === 0 ? 'brak Clock Out' : fmtHM(e.origEnd)}`);
  }
  return parts.join('; ');
}

function rows(list, now) {
  let out = '', lastDay = -1;
  for (const e of list) {
    const d = dayStart(e.start);
    const label = d === lastDay ? '        ' : `${dayShort(e.start)} ${fmtDM(e.start)}`;
    lastDay = d;
    const m = minutes(e, now);
    out += `${label}  ${fmtHM(e.start)}–${isRunning(e) ? 'teraz' : fmtHM(e.end)}`
      + `  ${padL(formatHm(m) + ' h', 8)}  ${padL(formatMoney(payCents(m, e.rateCents)), 9)}`;
    if (isRunning(e)) out += '  (w trakcie)';
    const n = notes(e);
    if (n) out += `  [${n}]`;
    out += '\n';
  }
  return out;
}

function totals(list, now) {
  const s = summarize(list, now);
  let out = '\n';
  out += `Dni pracy:   ${s.days}\n`;
  out += `Razem:       ${formatHm(s.minutes)} h (${formatDecimalHours(s.minutes)} h)\n`;
  if (list.length) {
    out += `${s.mixedRates ? 'Śr. stawka:  ' : 'Stawka:      '}${formatMoney(s.averageRateCents)}/h`
      + (s.mixedRates ? ' (różne stawki)\n' : '\n');
  }
  out += `DO WYPŁATY:  ${formatMoney(s.payCents)} brutto\n`;
  return out;
}

export function weekReport(week, ws, now) {
  let out = 'RAPORT TYGODNIOWY — GODZINY PRACY\n';
  out += `Tydzień: ${weekLabel(ws)}\n`;
  out += `Początek tygodnia: ${DAYS_FULL[new Date(ws).getDay()]}, 00:00\n\n`;
  if (!week.length) out += 'Brak wpisów w tym tygodniu.\n';
  return out + rows(week, now) + totals(week, now);
}

export function monthReport(all, ms, firstDay, now) {
  const me = addMonths(ms, 1);
  const month = inRange(all, ms, me);
  let out = 'RAPORT MIESIĘCZNY — GODZINY PRACY\n';
  out += `Miesiąc: ${monthLabel(ms)} (${fmtDM(ms)} – ${fmtDMY(addDays(me, -1))})\n`;
  if (!month.length) out += '\nBrak wpisów w tym miesiącu.\n';
  for (let ws = weekStart(ms, firstDay); ws < me; ws = addWeeks(ws, 1)) {
    const we = addWeeks(ws, 1);
    const part = inRange(month, ws, we);
    if (!part.length) continue;
    out += `\nTydzień ${fmtDM(Math.max(ws, ms))} – ${fmtDM(addDays(Math.min(we, me), -1))}\n`;
    out += rows(part, now);
    const s = summarize(part, now);
    out += `          razem tygodnia: ${formatHm(s.minutes)} h  ${formatMoney(s.payCents)}\n`;
  }
  return out + totals(month, now);
}

// ------------------------------------------------------------ CSV (format wspólny z Androidem)

export const CSV_HEADER = ['data', 'dzien', 'poczatek', 'koniec', 'przerwa_min', 'minuty_platne',
  'godziny_dziesietnie', 'stawka_usd', 'kwota_usd', 'zrodlo', 'zegar_poczatek', 'zegar_koniec',
  'id', 'start_ms', 'end_ms', 'zegar_start_ms', 'zegar_koniec_ms'];

export function csvExport(all, now) {
  const list = [...all].sort((a, b) => a.start - b.start);
  let out = CSV_HEADER.join(',') + '\n';
  for (const e of list) {
    const m = minutes(e, now);
    const src = e.manual ? 'reczny' : isEdited(e) ? 'zegar+poprawka' : 'zegar';
    out += [fmtISO(e.start), dayShort(e.start), fmtHM(e.start), isRunning(e) ? '' : fmtHM(e.end),
      e.breakMin, m, formatDecimalHours(m), plainMoney(e.rateCents), plainMoney(payCents(m, e.rateCents)),
      src, e.manual ? '' : fmtHM(e.origStart), e.manual || e.origEnd === 0 ? '' : fmtHM(e.origEnd),
      e.id, e.start, e.end, e.origStart, e.origEnd].join(',') + '\n';
  }
  return out;
}

/** Wynik: { entries } albo { error }. */
export function csvParse(text) {
  if (text == null || !String(text).trim()) return { error: 'Plik jest pusty.' };
  const lines = String(text).replace(/\r/g, '').split('\n');
  const head = lines[0].charCodeAt(0) === 0xFEFF ? lines[0].slice(1) : lines[0];
  const col = {};
  head.split(',').forEach((n, i) => { col[n.trim()] = i; });
  for (const need of ['id', 'start_ms', 'end_ms', 'przerwa_min', 'stawka_usd', 'zrodlo', 'zegar_start_ms', 'zegar_koniec_ms']) {
    if (!(need in col)) return { error: `To nie jest kopia z tej aplikacji (brak kolumny ${need}).` };
  }
  const int = s => { const t = String(s ?? '').trim(); if (!/^-?\d+$/.test(t)) throw new Error(); return Number(t); };
  const out = [], ids = new Set();
  let runningCount = 0;
  for (let n = 1; n < lines.length; n++) {
    if (!lines[n].trim()) continue;
    const p = lines[n].split(',');
    const where = `Wiersz ${n + 1}: `;
    let e;
    try {
      const rate = parseRate(p[col.stawka_usd]);
      if (rate <= 0) return { error: where + 'błędna stawka.' };
      e = entry(int(p[col.id]), int(p[col.start_ms]), int(p[col.end_ms]), int(p[col.przerwa_min]), rate,
        int(p[col.zegar_start_ms]), int(p[col.zegar_koniec_ms]), String(p[col.zrodlo]).trim() === 'reczny');
    } catch {
      return { error: where + 'nie da się odczytać.' };
    }
    if (!isValid(e)) return { error: where + 'błędne godziny.' };
    if (e.end !== 0 && e.end - e.start > MAX_ENTRY) return { error: where + 'wpis dłuższy niż 24 h.' };
    if (ids.has(e.id)) return { error: where + 'powtórzony identyfikator.' };
    ids.add(e.id);
    if (isRunning(e) && ++runningCount > 1) return { error: where + 'więcej niż jedna trwająca zmiana.' };
    out.push(e);
  }
  return { entries: out };
}
