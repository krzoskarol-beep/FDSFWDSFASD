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
  usunąć. „+ Dodaj wpis ręcznie” dodaje zapomnianą zmianę. Aplikacja nie pozwala
  zapisać wpisów nakładających się na siebie, dłuższych niż 24 h ani w przyszłości.
- **Raport tygodnia** — czytelne zestawienie dzień po dniu z sumą godzin i wypłatą;
  można je skopiować albo udostępnić (SMS, e-mail, WhatsApp…).
- **Ustawienia** (przycisk ze stawką): stawka godzinowa, początek tygodnia
  (poniedziałek albo niedziela) i wygląd.
- **Tryb ciemny** — domyślnie aplikacja jest jasna albo ciemna tak jak telefon;
  w Ustawieniach można wymusić motyw jasny lub ciemny.

## Zasady liczenia

- Czas wpisu liczony jest w pełnych minutach; wypłata tygodnia = suma minut × stawka / 60,
  zaokrąglona do centa. Dzięki temu godziny i kwota w raporcie zawsze do siebie pasują.
- Zmiana przez północ (np. 22:00–06:00) należy do dnia, w którym się zaczęła.
- Zmiana krótsza niż minuta (przypadkowe Clock In → Clock Out) nie jest zapisywana.
- Nadgodziny (np. ×1.5 powyżej 40 h) **nie** są liczone osobno.

## Prywatność

Aplikacja nie ma żadnych uprawnień: bez internetu, lokalizacji i plików.
Dane są tylko w pamięci telefonu (kopia zapasowa Androida je obejmuje).

## Budowanie

Projekt samodzielny (Java, bez bibliotek, minSdk 24, targetSdk 36), w układzie jak `eq-app/`.

```bash
cd hours-app
./gradlew testDebugUnitTest lintDebug assembleDebug
./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'   # godziny.png i godziny-ciemny.png w hours-app/screenshots/
```

Logika (tydzień, wypłata, walidacja, raport) jest w `WorkMath` i `Report` i ma testy JUnit.
Podpis wersji release: zmienne `SIGNING_*` albo `hours-app/keystore.properties` (poza repozytorium).
