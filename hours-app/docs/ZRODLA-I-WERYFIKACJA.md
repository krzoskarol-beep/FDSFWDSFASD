# Źródła reguł i weryfikacja obliczeń

Aplikacja liczy wypłatę pracownika godzinowego w USA (stawka domyślna $34/h). Każda reguła
poniżej pochodzi z federalnych przepisów o płacy (FLSA). Teksty pobrano z eCFR
(stan na 20.11.2026, https://www.ecfr.gov/current/title-29).

| Reguła w aplikacji | Przepis | Cytat (skrót) |
|---|---|---|
| Tydzień roboczy = stałe 7 × 24 h od wybranego dnia, nie musi być od poniedziałku | 29 CFR 778.105 | „fixed and regularly recurring period of 168 hours… may begin on any day” |
| Nadgodziny: dopłata ½ stawki za każdą godzinę ponad 40 w tygodniu | 29 CFR 778.110(a) | „$12 hourly rate … 46 hours … total weekly wage of $588” |
| Różne stawki w tygodniu ⇒ stawka regularna = średnia ważona | 29 CFR 778.115 | „total earnings … divided by the total number of hours worked” |
| Bezpłatna przerwa na posiłek nie jest czasem pracy (zwykle ≥ 30 min) | 29 CFR 785.19 | „Bona fide meal periods are not worktime” |
| Brak zaokrąglania — czas co do minuty | 29 CFR 785.48(b) | zaokrąglanie jest dopuszczalne tylko, jeśli „averages out”; dokładne minuty są zawsze zgodne |

Nadgodziny można wyłączyć w Ustawieniach (np. pracownik zwolniony z FLSA albo umowa poza USA).
Nie są liczone przepisy stanowe (np. Kalifornia: nadgodziny dzienne > 8 h) ani podatki — kwoty są **brutto**.

## Jak liczy aplikacja (bez liczb zmiennoprzecinkowych)

- minuty wpisu = ⌊(koniec − początek) / 1 min⌋ − przerwa,
- podstawa = Σ minuty × stawka wpisu / 60 (zaokrąglenie do centa),
- stawka regularna = Σ minuty × stawka / Σ minuty,
- dopłata = ½ × stawka regularna × minuty ponad 2400 / 60,
- do wypłaty = podstawa + dopłata.

## Dowody jakości (poza samym kodem)

1. **Przykłady z przepisów jako testy** (`WorkMathTest`): $12 × 46 h = $588 (§ 778.110),
   średnia ważona $585 / 45 h = $13 ⇒ $617.50 (§ 778.115), $34 × 42 h = $1,462.00.
2. **Niezależne przeliczenie** (`tools/sprawdz_csv.py`, Python + `Decimal`, bez kodu aplikacji):
   CI generuje próbkę 12 tygodni (różne stawki, przerwy, zmiany nocne, przejście na czas
   zimowy, nadgodziny), eksportuje CSV i porównuje sumy skryptu z sumami aplikacji co do
   minuty i centa. Różnica ⇒ czerwone CI.
3. **Ślad zmian**: każdy wpis pamięta godziny z zegara; raport i CSV pokazują, co poprawiono ręcznie.
4. **Twój pasek wypłaty (najmocniejszy dowód)** — porównaj dla 2–3 tygodni:
   - „Hours” / „Regular” na pasku ↔ „Razem” i „zwykłe” w raporcie,
   - „Overtime” ↔ „nadgodziny”, kwota OT ↔ (podstawa za nadgodziny + dopłata),
   - „Gross pay” ↔ „DO WYPŁATY … brutto”.
   Jeśli pracodawca zaokrągla czas (np. do 15 min) albo inaczej wyznacza tydzień, różnice
   będą małe i systematyczne; ustaw w aplikacji ten sam dzień początku tygodnia.

Własny plik możesz przeliczyć tak samo:

```bash
python3 tools/sprawdz_csv.py godziny-pracy-2026-11-24.csv --tydzien-od pn
```
