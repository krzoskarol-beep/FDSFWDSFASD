# Pozycja: Polska

Aplikacja na Androida, która ustawia lokalizację telefonu w wybranym miejscu w Polsce.
Korzysta z oficjalnego mechanizmu Androida: **aplikacji do pozorowania lokalizacji**
(Opcje programisty). Root nie jest potrzebny.

## Co potrafi

- **12 gotowych miast**: Warszawa (domyślnie), Kraków, Gdańsk, Wrocław, Poznań, Łódź,
  Katowice, Szczecin, Lublin, Białystok, Rzeszów, Zakopane.
- **Własne współrzędne**: wklej np. `52.2297, 21.0122` skopiowane z Map Google
  (działa też przecinek dziesiętny i link z `@lat,lon`). Ostrzega, gdy punkt leży poza Polską.
- **Działa w tle**: usługa pierwszoplanowa co sekundę podaje pozycję dostawcom GPS,
  sieci i (od Androida 12) „fused”. Pozycja lekko „pływa” (±3 m), jak prawdziwy GPS.
  Wyłączysz ją z powiadomienia.
- **Sprawdzenie**: przycisk „Sprawdź, co widzi telefon” pyta system o pozycję tak,
  jak robią to inne aplikacje, i mówi, czy to jest w Polsce.

## Konfiguracja (jednorazowo)

1. Ustawienia → Informacje o telefonie → stuknij 7 razy „Numer kompilacji”
   (włącza Opcje programisty).
2. Opcje programisty → „Wybierz aplikację do pozorowania lokalizacji” → „Pozycja: Polska”.
3. Otwórz aplikację, wybierz miasto i stuknij „Włącz”.

Uwaga: to nie jest „Wybierz aplikację do debugowania” (Select debug app).

### Gdy telefon nie ma tej opcji

Część producentów ukrywa wybór aplikacji do pozorowania lokalizacji. Zgodę nadaje się wtedy
raz z komputera (zostaje po restarcie): włącz „Debugowanie USB”, podłącz telefon i wpisz

```bash
adb shell appops set pl.pozycja.polska android:mock_location allow
```

Aplikacja pokazuje to polecenie z przyciskiem „Kopiuj polecenie”.

## Ograniczenia

- Zmienia **lokalizację GPS**, a nie adres IP. Serwisy, które ustalają kraj po IP
  (np. streaming), wymagają VPN.
- Android oznacza taką pozycję jako pozorowaną. Część aplikacji (banki, niektóre gry)
  to wykrywa i odrzuca.
- Usługi Google mogą przez chwilę mieszać pozycję z Wi-Fi; jeśli mapy „skaczą”,
  wyłącz w ustawieniach lokalizacji „Skanowanie Wi-Fi” i „Dokładność lokalizacji Google”.

## Uprawnienia

- `ACCESS_MOCK_LOCATION` – podstawianie pozycji,
- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION` – tylko dla przycisku „Sprawdź”
  (aplikacja pyta o nie dopiero wtedy),
- `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE`, `POST_NOTIFICATIONS` – praca w tle.

Brak dostępu do internetu. Aplikacja niczego nie wysyła.

## Budowanie

Projekt samodzielny (Java, minSdk 24, targetSdk 36, bez bibliotek), niezależny od
`gps-app/` i `eq-app/`.

```bash
cd mock-app
./gradlew testDebugUnitTest lintDebug assembleDebug
./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'   # PNG w mock-app/screenshots/
```

Test na urządzeniu `MockEngineTest` (CI, emulator Android 14) nadaje zgodę poleceniem
`appops` i sprawdza, że system naprawdę zwraca pozycję w Warszawie oznaczoną jako pozorowana.

Podpisany release: zmienne `SIGNING_STORE_FILE`, `SIGNING_STORE_PASSWORD`,
`SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD` albo plik `mock-app/keystore.properties`
(oba poza repozytorium).
