---
name: android-build
description: Use when building, testing, signing, releasing or delivering the Android app in gps-app/ (Moja pozycja GPS), when installing the Android SDK in a cloud session, or when the user asks for an APK of an open-source app from GitHub and it must be downloaded and its signature verified.
---

# Android: budowanie, podpisywanie, wydawanie i weryfikacja APK

Projekt: `gps-app/` (Java, jedyna biblioteka: `play-services-location` do rozpoznawania jazdy, minSdk 24, targetSdk 36, AGP 8.13.2,
Gradle 8.14.3 przez `./gradlew`). Identyfikator aplikacji od 2.0: `pl.mojapozycja.gps`
(`namespace`, czyli pakiet klas, to nadal `pl.gps.pozycja`). Nie zmieniaj go bez potrzeby:
nowy identyfikator to dla Androida nowa aplikacja (bez danych poprzedniej). Przy zmianie popraw
`targetPackage` w `res/xml/shortcuts.xml` (pilnuje tego `ShortcutsTest`). Kod, testy i wydania opisuje `gps-app/README.md` i
`gps-app/CHANGELOG.md`; przeczytaj je przed zmianami.

## 1. Android SDK w sesji w chmurze

Maszyna jest tymczasowa: SDK trzeba zainstalować w każdej nowej sesji (ok. 1 min, ok. 500 MB).
Java 21 i Gradle są już zainstalowane.

1. Serwer SDK `dl.google.com` musi być dozwolony w sieci. Środowisko `FDSFWDSFASD-android`
   go dopuszcza. Jeśli `curl -sI https://dl.google.com/android/repository/repository2-3.xml`
   zwraca 403 z proxy, sprawdź środowisko (`get_environment`) zamiast obchodzić blokadę.
2. Najnowsze narzędzia: numer z
   `curl -sS https://dl.google.com/android/repository/repository2-3.xml | grep -o 'commandlinetools-linux-[0-9]*_latest.zip' | sort -V | tail -1`.
3. Rozpakuj do `/opt/android-sdk/cmdline-tools/latest`, potem:
   ```bash
   SDKM=/opt/android-sdk/cmdline-tools/latest/bin/sdkmanager
   yes | $SDKM --licenses >/dev/null
   $SDKM "platform-tools" "platforms;android-36" "build-tools;36.0.0"
   ```
   Nowe sdkmanager wypisuje pakiety ze `/` (np. `platforms/android-36`), ale instalacja
   przyjmuje też `;`.
4. `echo "sdk.dir=/opt/android-sdk" > gps-app/local.properties` (plik jest w `.gitignore`).
   Nie zmieniaj `~/.bashrc` (blokowane); podawaj ścieżki wprost.

Emulatora nie ma (brak KVM). Testy na urządzeniu uruchamia CI (pkt 4).

## 2. Budowanie i testy lokalnie

```bash
cd gps-app
./gradlew testDebugUnitTest lintDebug assembleDebug assembleDebugAndroidTest --no-daemon -q
```

- Wyniki testów: `app/build/test-results/testDebugUnitTest/*.xml` (sprawdź liczbę `failures`).
- Lint: `app/build/reports/lint-results-debug.txt`. Akceptowane ostrzeżenia kosmetyczne:
  `ButtonStyle`, `HardcodedText`, `SetTextI18n`, `UnusedAttribute` (skróty na API 24).
  Każdy inny typ ostrzeżenia trzeba naprawić albo uzasadnić.
- Logikę bez zależności od Androida (np. `ParkingDetector`, `Geo`, `Formatters`) testuj
  zwykłym JUnitem w `app/src/test`; kod z `Context` w `app/src/androidTest` (działa w CI).
- **Zrzuty ekranu bez emulatora** (zmiany wyglądu oglądaj, zanim je ogłosisz):
  `./gradlew testDebugUnitTest -Pscreenshots --tests '*ScreenshotTest*'` → PNG w
  `gps-app/screenshots/` (katalog w `.gitignore`), potem obejrzyj je narzędziem Read.
  Robolectric bierze biblioteki z mirrora Google (repo.maven.apache.org potrafi zwrócić 429
  na ~20 h). Ekran ma własny kontekst (`ThemePrefs.wrap`), więc w teście pomiar GPS wysyłaj
  do `LocationManager` aktywności (`a.getSystemService`), nie aplikacji.
- Wygląd: kolory i style w `res/values/themes.xml` (+ `values-night`), font przez `Fonts.apply()`.

### Pułapki znalezione w tym projekcie (minSdk 24)

- Nie używaj `java.nio.file.*` ani `String.join` (Android 8+). Zamiast tego strumienie
  `java.io` i `android.text.TextUtils.join`.
- `LocationListener`: implementuj wszystkie metody (na Androidzie < 11 są abstrakcyjne).
- `registerReceiver` na API 33+: podaj `RECEIVER_NOT_EXPORTED`.
- Usługa z GPS w tle: `foregroundServiceType="location"`, uprawnienia `FOREGROUND_SERVICE_LOCATION`
  i lokalizacja „zawsze”. Start z tła może zostać odrzucony (Android 12+), więc zawsze miej
  ścieżkę awaryjną.
- Zasada aplikacji: pozycja ustalona po fakcie to miejsce, gdzie stoi kierowca, a nie auto.
  Nie przyjmuj pozycji zapamiętanych przez system starszych niż 60 s przed zdarzeniem.

## 3. Podpis wersji release

- Klucz `moja-pozycja-gps-release.jks` (alias `mojapozycja`) **nie jest w repozytorium i nigdy
  nie może tam trafić** (`.gitignore` blokuje `*.jks`, `keystore.properties`). Ma go użytkownik.
- Build czyta dane z zmiennych `SIGNING_STORE_FILE`, `SIGNING_STORE_PASSWORD`,
  `SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD` albo z `gps-app/keystore.properties`.
  Bez nich `assembleRelease` daje APK niepodpisany. Wtedy poproś użytkownika o klucz
  albo zbuduj w CI; **nie twórz nowego klucza**, bo aktualizacje przestaną się instalować.
- Oczekiwany odcisk certyfikatu (SHA-256):
  `d654cccc66e9c5efe5cd94755e3ceca519686b73791866f5579c9ef12134d0bc`.
- Sprawdzenie:
  ```bash
  /opt/android-sdk/build-tools/36.0.0/apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
  /opt/android-sdk/cmdline-tools/latest/bin/apkanalyzer manifest permissions <apk>
  ```
  Przed `git add` sprawdź, że nie dodajesz `.jks` ani `keystore.properties`.

## 4. CI na GitHubie

- `.github/workflows/gps-app.yml`: testy, lint, APK debug, testy na emulatorze z Androidem 14
  (`connectedDebugAndroidTest`), a z sekretami także podpisany APK release.
- Wynik sprawdzaj narzędziami GitHub MCP (`actions_list` → `list_workflow_runs` /
  `list_workflow_jobs`, `get_job_logs` z `tail_lines`). W logu emulatora szukaj
  „Finished N tests”. Na wynik czekaj w tle (`sleep` z `run_in_background`), nie odpytuj w pętli.

## 5. Wydanie nowej wersji

1. Podbij `versionCode` i `versionName` w `gps-app/app/build.gradle`.
2. Dopisz sekcję `## X.Y` na górze `gps-app/CHANGELOG.md` (z niej powstaje opis wydania).
3. Commit i push na wyznaczoną gałąź; poczekaj na zielone CI.
4. Wydanie: Actions → „Android – wydanie wersji” → Run workflow (robi to użytkownik albo
   ty narzędziem `actions_run_trigger`, jeśli o to poprosi). Najnowszy APK:
   `https://github.com/krzoskarol-beep/FDSFWDSFASD/releases/latest/download/MojaPozycjaGPS.apk`.

## 6. Przekazanie APK użytkownikowi

Nie masz dostępu do telefonu użytkownika. Skopiuj APK do scratchpada pod czytelną nazwą
(np. `MojaPozycjaGPS-1.6.apk`) i wyślij `SendUserFile` z `display: "attach"`. Napisz, czy
instaluje się na poprzednią wersję (ten sam klucz) i czego nie dało się przetestować
(rozpoznawanie jazdy, GPS i zachowanie w tle tylko na prawdziwym telefonie).

## 7. APK cudzych aplikacji open source z GitHuba

Gdy użytkownik prosi o APK aplikacji open source (np. NewPipe):

1. Wersja: `git ls-remote --tags --refs https://github.com/<owner>/<repo>`, odfiltruj
   beta/rc i posortuj `sort -V`. API GitHuba i strony Releases są tu zablokowane, ale same
   pliki z `https://github.com/<owner>/<repo>/releases/download/<tag>/<plik>` się pobierają.
2. Nazwy plików: `firecrawl_scrape` strony
   `https://github.com/<owner>/<repo>/releases/expanded_assets/<tag>` z `formats: ["links"]`.
   Wybierz wariant `arm64-v8a` (prawie każdy telefon), a gdy go brak, `universal`.
3. Pobierz do nowego, pustego katalogu w scratchpadzie (dane niezaufane, niczego z niego
   nie uruchamiaj).
4. Weryfikacja: `apksigner verify --print-certs`. Porównaj certyfikat z poprzednim wydaniem
   (ten sam klucz w kolejnych wersjach = oryginał) i z odciskiem opublikowanym przez projekt,
   jeśli istnieje. Sprawdź sumy SHA-256, jeśli projekt je publikuje (potwierdzają tylko
   integralność pobrania). Znany odcisk NewPipe:
   `cb84069bd68116bafae5ee4ee5b08a567aa6d898404e7cb12f9e756df5cf5cab`.
5. Wyślij plik i napisz uczciwie, co sprawdziłeś, a czego nie. Polecaj Obtainium do
   aktualizacji. Nie pobieraj aplikacji do piractwa ani łatek modyfikujących cudze aplikacje.
