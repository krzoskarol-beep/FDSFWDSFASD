# Zasady liczenia i weryfikacja

Aplikacja liczy wypłatę godzinową **bez nadgodzin**: każda przepracowana minuta jest płatna
według stawki zapisanej przy wpisie (domyślnie $34/h). Kwoty są **brutto** (bez podatków).

| Reguła w aplikacji | Podstawa |
|---|---|
| Tydzień roboczy = stałe 7 dni od wybranego dnia, 00:00 (nie musi być od poniedziałku) | jak u pracodawcy; por. 29 CFR 778.105 |
| Bezpłatna przerwa na posiłek nie jest czasem pracy | 29 CFR 785.19 („Bona fide meal periods are not worktime”) |
| Brak zaokrąglania — czas co do minuty | 29 CFR 785.48(b): zaokrąglanie dopuszczalne tylko, gdy „averages out” |
| Stawka zapisana przy wpisie — zmiana stawki nie przelicza wstecz | zasada aplikacji |

Teksty przepisów pobrano z eCFR (https://www.ecfr.gov/current/title-29, stan na 20.11.2026).
Nadgodziny (np. federalne ×1.5 ponad 40 h) zostały celowo usunięte z aplikacji.

## Jak liczy aplikacja (bez liczb zmiennoprzecinkowych)

- minuty wpisu = ⌊(koniec − początek) / 1 min⌋ − przerwa,
- do wypłaty = Σ minuty × stawka wpisu / 60, zaokrąglone raz, do centa,
- średnia stawka (przy kilku stawkach w tygodniu) = do wypłaty / godziny.

## Dowody jakości (poza samym kodem)

1. **Testy z przykładami liczbowymi** (`WorkMathTest`): $12 × 46 h = $552, 30 h × $12 + 15 h × $15
   = $585 (średnio $13/h), $34 × 42 h = $1,428.00, oraz sprawdzenie „minuty × stawka / 60”
   dla ~570 długości tygodnia.
2. **Niezależne przeliczenie** (`tools/sprawdz_csv.py`, Python + `Decimal`, bez kodu aplikacji):
   CI generuje próbkę 12 tygodni (różne stawki, przerwy, zmiany nocne, przejście na czas
   zimowy, tygodnie ponad 40 h), eksportuje CSV i porównuje sumy skryptu z sumami aplikacji
   co do minuty i centa. Różnica ⇒ czerwone CI.
3. **Ślad zmian**: każdy wpis pamięta godziny z zegara; raport i CSV pokazują, co poprawiono ręcznie.
4. **Twój pasek wypłaty (najmocniejszy dowód)** — porównaj dla 2–3 tygodni:
   „Hours” ↔ „Razem”, „Gross pay” ↔ „DO WYPŁATY … brutto”. Jeśli pasek pokazuje „Overtime”,
   kwoty będą się różnić o dopłatę, której aplikacja nie liczy. Jeśli pracodawca zaokrągla
   czas (np. do 15 min), różnice będą małe i systematyczne.

Własny plik możesz przeliczyć tak samo:

```bash
python3 tools/sprawdz_csv.py godziny-pracy-2026-11-24.csv --tydzien-od pn
```
