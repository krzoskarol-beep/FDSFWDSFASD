# Korektor

Globalny korektor dźwięku na Androida: stroi **cały** dźwięk telefonu (Spotify,
YouTube, odtwarzacz muzyki), a nie tylko to, co grałoby w samej aplikacji.

## Co potrafi

- **Korektor wielopasmowy** — liczba pasm i częstotliwości pochodzą z telefonu
  (zwykle 5 pasm, od ~60 Hz do ~14 kHz). Fadery jak w konsolecie studyjnej.
- **Zestawy (presety)** — gotowe ustawienia z systemu (Rock, Pop, Jazz…) oraz
  tryb „Własny”, gdy sam przesuniesz suwaki.
- **Wzmocnienie basu** i **efekt przestrzenny (surround)** — jeśli telefon je obsługuje.
- **Działa w tle** — gdy korektor jest włączony, efekty trzyma usługa
  pierwszoplanowa z powiadomieniem, więc muzyka w innej aplikacji jest strojona
  nawet przy zgaszonym ekranie. Wyłączenie zwalnia efekty.

## Prywatność i uprawnienia

Aplikacja prosi tylko o:

- `MODIFY_AUDIO_SETTINGS` — podłączenie efektów do dźwięku,
- `FOREGROUND_SERVICE` / `FOREGROUND_SERVICE_SPECIAL_USE` — utrzymanie efektów w tle,
- `POST_NOTIFICATIONS` — powiadomienie „Korektor aktywny”.

**Brak dostępu do internetu, lokalizacji, plików czy mikrofonu.** Niczego nie wysyła.

## Zastrzeżenia

Globalny korektor (sesja audio 0) działa na większości telefonów, ale część
producentów go ogranicza — wtedy aplikacja pokazuje komunikat zamiast zmieniać
dźwięk. Niektóre aplikacje z własnym silnikiem audio mogą go pomijać.

## Budowanie

Projekt jest samodzielny (Java, minSdk 24, targetSdk 36, Gradle przez `./gradlew`),
niezależny od `gps-app/`, ale używa tego samego klucza podpisu.

```bash
cd eq-app
./gradlew testDebugUnitTest lintDebug assembleDebug
```

Zrzut ekranu wyglądu (bez emulatora, Robolectric):

```bash
./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'   # PNG w eq-app/screenshots/
```

Podpisana wersja release wymaga klucza — przez zmienne `SIGNING_STORE_FILE`,
`SIGNING_STORE_PASSWORD`, `SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD` albo plik
`eq-app/keystore.properties` (oba poza repozytorium).
