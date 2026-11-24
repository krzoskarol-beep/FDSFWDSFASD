# Godziny Pracy

Prosta aplikacja na Androida do liczenia godzin pracy i wypłaty.
Stawka domyślna: **$34.00/h** (można zmienić).

## Co potrafi

- **Clock In / Clock Out** — jeden duży przycisk. Podczas zmiany widać licznik
  czasu (hh:mm:ss) i kwotę zarobioną na tej zmianie. Zmiana trwa także po
  zamknięciu aplikacji czy restarcie telefonu (zapisany jest tylko jej początek).
- **Podsumowanie tygodnia** — suma godzin (8:30 h oraz dziesiętnie 8.50 h),
  kwota do wypłaty i liczba dni pracy. Strzałkami przechodzisz do poprzednich tygodni.
- **Edycja wpisów** — dotknij wpisu, aby zmienić datę, początek lub koniec, albo go
  usunąć. Przyciski **−1 h / −15 min / +15 min / +1 h** szybko odejmują lub dodają czas
  (w zakończonej zmianie przesuwają koniec, w trwającej — początek). Trwającej zmianie
  można też ustawić koniec, co ją kończy. „+ Dodaj wpis ręcznie” dodaje zapomnianą zmianę. Aplikacja nie pozwala
  zapisać wpisów nakładających się na siebie, dłuższych niż 24 h ani w przyszłości.
- **Usuwanie całego dnia** — dotknij datę dnia na liście: podgląd wpisów i sumy, „Usuń dzień”
  albo „Dodaj” wpis w tym dniu. Po usunięciu (dnia lub wpisu) przez 15 s działa „Cofnij”.
- **Przerwa bezpłatna** (0/15/30/45/60 min) przy każdym wpisie — odejmowana od czasu.
- **Stawka zapisana przy wpisie** — zmiana stawki nie przelicza wstecz starych tygodni.
- **Ślad zmian** — każdy wpis pamięta godziny z zegara (Clock In/Out); lista, raport i CSV
  pokazują, co poprawiono ręcznie albo dodano ręcznie.
- **Kopia CSV** — eksport do Excela/Arkuszy i przywracanie z tego samego pliku (Ustawienia).
- **Ostrzeżenie** przy zmianie trwającej ponad 12 h (zapomniany Clock Out).
- **Raport tygodnia** — czytelne zestawienie dzień po dniu z sumą godzin i wypłatą;
  można je skopiować albo udostępnić (SMS, e-mail, WhatsApp…).
- **Ustawienia** (przycisk ze stawką): stawka godzinowa, dzień początku
  tygodnia roboczego (dowolny, jak u pracodawcy), wygląd, kopia CSV.
- **Tryb ciemny** — domyślnie aplikacja jest jasna albo ciemna tak jak telefon;
  w Ustawieniach można wymusić motyw jasny lub ciemny.

## Zasady liczenia

Reguły, ich podstawy i sposób weryfikacji opisuje
[docs/ZRODLA-I-WERYFIKACJA.md](docs/ZRODLA-I-WERYFIKACJA.md). W skrócie:

- czas wpisu w pełnych minutach, minus przerwa; bez zaokrąglania,
- wypłata = Σ minuty × stawka wpisu / 60 — **bez nadgodzin** (każda godzina po tej samej stawce),
- zmiana przez północ należy do dnia, w którym się zaczęła,
- zmiana krótsza niż minuta (przypadkowe Clock In → Clock Out) nie jest zapisywana,
- kwoty są brutto (bez podatków).

## Prywatność

Aplikacja nie ma żadnych uprawnień: bez internetu, lokalizacji i plików.
Dane są tylko w pamięci telefonu (kopia zapasowa Androida je obejmuje).

## Budowanie

Projekt samodzielny (Java, bez bibliotek, minSdk 24, targetSdk 36), w układzie jak `eq-app/`.

```bash
cd hours-app
./gradlew testDebugUnitTest lintDebug assembleDebug
./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'   # ekran główny i okno edycji (jasny i ciemny) w hours-app/screenshots/
```

Logika (tydzień, wypłata, walidacja, raport, CSV) jest w `WorkMath`, `Report` i `Csv` i ma testy JUnit.
Niezależne przeliczenie próbki (robi to też CI):

```bash
python3 tools/sprawdz_csv.py app/build/weryfikacja/probka.csv --porownaj app/build/weryfikacja/oczekiwane.txt
```
Podpis wersji release: zmienne `SIGNING_*` albo `hours-app/keystore.properties` (poza repozytorium).
