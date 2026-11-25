// Testy logiki wersji webowej. Uruchamiać ze strefą Nowego Jorku (jak próbka z Androida):
//   TZ=America/New_York node --test test/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as C from '../core.js';

const fx = name => readFileSync(new URL(`./fixtures/${name}`, import.meta.url), 'utf8');
const t = (y, mo, d, h, mi) => new Date(y, mo - 1, d, h, mi).getTime();
const { HOUR: H, MINUTE: M } = C;

test('strefa czasowa testów', () => {
  assert.equal(Intl.DateTimeFormat().resolvedOptions().timeZone, 'America/New_York');
});

test('tydzień od poniedziałku, niedzieli i dowolnego dnia', () => {
  const wed = t(2026, 11, 25, 14, 30);
  assert.equal(C.weekStart(wed, 1), t(2026, 11, 23, 0, 0));
  assert.equal(C.weekStart(wed, 0), t(2026, 11, 22, 0, 0));
  assert.equal(C.weekStart(wed, 4), t(2026, 11, 19, 0, 0));          // od czwartku
  assert.equal(C.weekStart(t(2026, 11, 29, 23, 59), 1), t(2026, 11, 23, 0, 0));
});

test('dodawanie tygodni przez zmianę czasu (USA, 1.11.2026)', () => {
  const w = C.weekStart(t(2026, 10, 28, 12, 0), 1);
  assert.equal(C.addWeeks(w, 1), t(2026, 11, 2, 0, 0));
  assert.equal(C.addWeeks(w, 1) - w, 169 * H);
});

test('wypłata $34/h i zaokrąglenia', () => {
  assert.equal(C.payCents(60, 3400), 3400);
  assert.equal(C.payCents(510, 3400), 28900);
  assert.equal(C.payCents(1, 3400), 57);
  assert.equal(C.formatMoney(109650), '$1,096.50');
  assert.equal(C.formatMoney(57), '$0.57');
  assert.equal(C.formatHm(485), '8:05');
  assert.equal(C.formatHms(3_723_000), '01:02:03');
  assert.equal(C.formatDecimalHours(485), '8.08');
});

test('podsumowanie: bez nadgodzin, dwie stawki, przerwa', () => {
  const week = (hours, rate, id0) => {
    const out = []; let left = Math.round(hours * 60);
    for (let d = 0; left > 0; d++) {
      const m = Math.min(left, 600), s = t(2026, 11, 23 + d, 6, 0);
      out.push(C.entry(id0 + d, s, s + m * M, 0, rate)); left -= m;
    }
    return out;
  };
  assert.equal(C.summarize(week(46, 1200, 1), 0).payCents, 55200);
  assert.equal(C.summarize(week(42, 3400, 1), 0).payCents, 142800);
  const two = [...week(30, 1200, 1), ...week(15, 1500, 100).map(e => ({ ...e, start: e.start + 12 * H, end: e.end + 12 * H }))];
  const s = C.summarize(two, 0);
  assert.deepEqual([s.minutes, s.payCents, s.averageRateCents, s.mixedRates], [2700, 58500, 1300, true]);
  const b = C.entry(1, t(2026, 11, 24, 8, 0), t(2026, 11, 24, 17, 0), 30);
  assert.equal(C.minutes(b, 0), 510);
});

test('stawka wpisana przez użytkownika', () => {
  assert.equal(C.parseRate('34'), 3400);
  assert.equal(C.parseRate('34,5'), 3450);
  assert.equal(C.parseRate(' $34.05 '), 3405);
  for (const bad of ['', '0', 'abc', '34.555']) assert.equal(C.parseRate(bad), -1);
  assert.equal(C.rateForInput(3450), '34.50');
});

test('edycja: koniec przez północ, odejmowanie czasu, walidacja', () => {
  const s = t(2026, 11, 23, 22, 0);
  assert.equal(C.endAfter(s, 6, 0, 0), t(2026, 11, 24, 6, 0));
  assert.equal(C.endAfter(s, 23, 30, 0), t(2026, 11, 23, 23, 30));
  const now = s + 12 * H;
  assert.deepEqual(C.adjust(s, s + 8 * H, -15 * M, now), [s, s + 7 * H + 45 * M]);
  assert.equal(C.adjust(s, s + 10 * M, -H, now), null);
  assert.deepEqual(C.adjust(s, 0, -H, s + 3 * H), [s + H, 0]);
  const one = [C.entry(7, s, s + 8 * H)];
  assert.match(C.validate(one, -1, s + H, s + 2 * H, 0, now), /^Nakłada się/);
  assert.equal(C.validate(one, 7, s + H, s + 2 * H, 0, now), null);
  assert.equal(C.validate([], -1, s, s + 20 * M, 30, now), 'Przerwa nie może być dłuższa niż cały wpis.');
  assert.equal(C.validate([], -1, now + H, 0, 0, now), 'Początek nie może być w przyszłości.');
});

// ------------------------------------------------------------ zgodność z Androidem

test('CSV z Androida: wczytanie i sumy tygodni co do minuty i centa', () => {
  const r = C.csvParse(fx('probka.csv'));
  assert.equal(r.error, undefined);
  assert.ok(r.entries.length > 50);
  for (const line of fx('oczekiwane.txt').trim().split('\n')) {
    const [date, min, cents] = line.split(' ');
    const [y, m, d] = date.split('-').map(Number);
    const ws = new Date(y, m - 1, d).getTime();
    const s = C.summarize(C.inRange(r.entries, ws, C.addWeeks(ws, 1)), 0);
    assert.deepEqual([s.minutes, s.payCents], [Number(min), Number(cents)], date);
  }
});

test('CSV: eksport webowy = eksport Androida (bajt w bajt)', () => {
  const android = fx('probka.csv').replace(/^﻿/, '');
  assert.equal(C.csvExport(C.csvParse(android).entries, 0), android);
});

test('raport tygodnia i miesiąca: identyczny tekst jak na Androidzie', () => {
  const all = C.csvParse(fx('probka.csv')).entries;
  const ws = C.weekStart(new Date(2026, 10, 9, 12).getTime(), 1);
  assert.equal(C.weekReport(C.inRange(all, ws, C.addWeeks(ws, 1)), ws, 0), fx('raport-tydzien.txt'));
  assert.equal(C.monthReport(all, C.monthStart(new Date(2026, 9, 15).getTime()), 1, 0), fx('raport-miesiac.txt'));
});

test('CSV: odrzuca obce i uszkodzone pliki', () => {
  assert.ok(C.csvParse('').error);
  assert.ok(C.csvParse('a,b\n1,2\n').error);
  const good = fx('probka.csv');
  const lines = good.split('\n');
  assert.match(C.csvParse(good + lines[1] + '\n').error, /powtórzony/);
  assert.match(C.csvParse(good.replace(',34.00,', ',abc,')).error, /^Wiersz \d+: /);
});

test('raport miesiąca: przycięcie do miesiąca i grupy tygodni', () => {
  const all = [
    C.entry(1, t(2026, 10, 30, 8, 0), t(2026, 10, 30, 16, 0)),
    C.entry(2, t(2026, 11, 1, 9, 0), t(2026, 11, 1, 13, 0)),
    C.entry(3, t(2026, 11, 30, 7, 0), t(2026, 11, 30, 17, 0)),
    C.entry(4, t(2026, 12, 1, 7, 0), t(2026, 12, 1, 15, 0)),
  ];
  const r = C.monthReport(all, t(2026, 11, 1, 0, 0), 1, 0);
  assert.match(r, /Miesiąc: listopad 2026 \(01\.11 – 30\.11\.2026\)/);
  assert.match(r, /Tydzień 01\.11 – 01\.11\nNd 01\.11/);
  assert.match(r, /Tydzień 30\.11 – 30\.11\n/);
  assert.doesNotMatch(r, /30\.10|01\.12/);
  assert.match(r, /DO WYPŁATY: {2}\$476\.00 brutto/);               // 14 h × $34
});
