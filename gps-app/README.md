# Moja pozycja GPS (Android)

Prosta aplikacja na Androida, która pokazuje aktualną pozycję telefonu.

- szerokość i długość geograficzna (stopnie dziesiętne oraz stopnie, minuty i sekundy)
- dokładność, wysokość, prędkość, kierunek ruchu
- liczba satelitów (używane / widoczne)
- źródło pozycji (GPS albo sieć) i czas pomiaru, odświeżane co sekundę
- przyciski: **Otwórz w mapach**, **Kopiuj**, **Udostępnij** (link do Map Google)

### Gdzie zaparkowałem?

- **Zapisz miejsce parkowania** jednym przyciskiem, z opcjonalną notatką (np. „poziom -2, sektor B”).
  Miejsce zostaje zapamiętane także po zamknięciu aplikacji.
- **Strzałka z kompasem** pokazuje, w którą stronę iść do auta (z poprawką na deklinację
  magnetyczną). Gdy telefon nie ma kompasu, strzałka pokazuje kierunek względem północy.
- **Odległość do auta** i kierunek (np. „350 m, na Pn-Wsch”), a obok auta: „Jesteś przy aucie”.
- **Prowadź**: nawigacja piesza w Mapach Google (albo innej aplikacji map, albo w przeglądarce).
- **Skrót na ikonie:** przytrzymaj ikonę aplikacji i wybierz „Zapisz parking”.
  Aplikacja poczeka na aktualną pozycję i od razu zaproponuje zapis (Android 7.1+).
- Ostrzega, gdy zapisywana pozycja jest niedokładna albo nieaktualna.

### Automatyczne zapisywanie parkowania (Bluetooth auta)

Włącz przełącznik **„Zapisuj parking automatycznie”** i wskaż radio albo zestaw głośnomówiący
swojego auta (można kilka; przycisk **Wybierz Bluetooth auta**). Od tej pory:

1. **Połączenie** telefonu z Bluetooth auta = początek jazdy: startuje usługa z powiadomieniem
   „Jedziesz”, która śledzi GPS (GPS działa tylko wtedy).
2. **Rozłączenie** (wyłączenie silnika) = zapis parkingu z pozycji **z chwili rozłączenia**,
   gdy telefon był jeszcze w aucie. Powiadomienie ma przycisk **Prowadź**.
3. Chwilowe zerwanie Bluetooth w trakcie jazdy (auto jedzie) jest ignorowane.
4. Bez rozłączenia o końcu jazdy decyduje `DrivePolicy`: połączony z autem = jazda trwa
   (korek), chyba że bez ruchu przez godzinę; po zerwaniu Bluetooth w trasie zapis 5 minut
   po zatrzymaniu; bez jazdy przez 20 minut = fałszywy alarm.

Aplikacja korzysta **wyłącznie z danych Bluetooth** (bez rozpoznawania aktywności i bez usług
Google Play), więc nie ma fałszywych alarmów w autobusie i działa na każdym telefonie z Androidem 7.0+.

Zasada (za projektem ParKing, patrz niżej): **pozycja ustalona po fakcie to miejsce, gdzie stoi
kierowca, a nie auto.** Dlatego pozycje zapamiętane przez system są brane pod uwagę tylko z okolic
zdarzenia (do 60 s przed). Jeśli takiej pozycji brak, aplikacja prosi o ręczny zapis zamiast
zapisywać zgadywane miejsce.

Kolejność wyboru miejsca (`DrivingService`, `ParkingDetector`):
1. ostatni dokładny pomiar GPS sprzed rozłączenia (najwyżej 30 s wcześniej),
2. pierwszy postój (poniżej ok. 3,6 km/h) po ostatnim odcinku jazdy powyżej ok. 15 km/h;
   gdy GPS zniknie (garaż podziemny), ostatni punkt jazdy,
3. pozycja zapamiętana przez system z okolic zdarzenia,
4. nowy pomiar zaraz po rozłączeniu (oznaczony jako przybliżony).

Wymagane uprawnienia: lokalizacja „Zezwalaj zawsze”, „Urządzenia w pobliżu” (Bluetooth)
i (opcjonalnie) powiadomienia. Zalecane: wyłączenie optymalizacji baterii, bo inaczej Android
może zablokować start śledzenia w tle.

### Adres i historia

- Po zapisie aplikacja ustala **adres** miejsca (systemowy Geocoder, wymaga internetu)
  i pokazuje go na karcie i w powiadomieniu.
- **Historia parkowań** (przycisk pod kartami): 30 ostatnich miejsc. Dotknięcie otwiera mapę,
  przytrzymanie pozwala **przywrócić miejsce jako aktualne** albo je usunąć.

Aplikacja nie ma żadnych zewnętrznych bibliotek (tylko systemowe API Androida).
Działa na Androidzie 7.0 lub nowszym (minSdk 24, targetSdk 36).

## Budowanie

Wymagane: JDK 17+ i Android SDK (platforma 36).

```bash
cd gps-app
echo "sdk.dir=/ścieżka/do/android-sdk" > local.properties   # Android Studio robi to samo
./gradlew assembleDebug               # APK do testów: app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease             # APK do instalacji (wymaga klucza, patrz niżej)
./gradlew testDebugUnitTest           # testy jednostkowe (bez telefonu)
./gradlew connectedDebugAndroidTest   # testy na podłączonym telefonie / emulatorze
```

Można też po prostu otworzyć katalog `gps-app` w Android Studio.

## Klucz podpisu (ważne)

Android pozwala zainstalować aktualizację tylko wtedy, gdy jest podpisana **tym samym kluczem**
co zainstalowana wersja. Dlatego wersje do instalacji (release) podpisujemy stałym kluczem
`moja-pozycja-gps-release.jks`. **Klucza nie ma w repozytorium i nie może tam trafić**
(`.gitignore` blokuje `*.jks` i `keystore.properties`). Zgubienie klucza oznacza, że kolejną
wersję trzeba będzie instalować po odinstalowaniu poprzedniej (z utratą danych).

Lokalnie: utwórz `gps-app/keystore.properties`:

```properties
storeFile=/pełna/ścieżka/moja-pozycja-gps-release.jks
storePassword=...
keyAlias=mojapozycja
keyPassword=...
```

Albo ustaw zmienne środowiskowe `SIGNING_STORE_FILE`, `SIGNING_STORE_PASSWORD`,
`SIGNING_KEY_ALIAS`, `SIGNING_KEY_PASSWORD`. Bez klucza `assembleRelease` tworzy APK niepodpisany.

Wersja release jest zoptymalizowana przez R8 (ok. 60 KB).

## CI (GitHub Actions)

`.github/workflows/gps-app.yml` przy każdej zmianie w `gps-app/`:

1. uruchamia testy jednostkowe i lint, buduje APK debug,
2. jeśli są ustawione sekrety klucza, buduje **podpisany APK release** (artefakt `MojaPozycjaGPS-release`),
3. uruchamia testy na emulatorze z Androidem 14.

Sekrety (Settings → Secrets and variables → Actions → New repository secret):

| Sekret | Wartość |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | plik `.jks` zakodowany w base64 (`base64 -w0 moja-pozycja-gps-release.jks`) |
| `ANDROID_KEYSTORE_PASSWORD` | hasło do pliku |
| `ANDROID_KEY_ALIAS` | `mojapozycja` |
| `ANDROID_KEY_PASSWORD` | hasło klucza (to samo co do pliku) |

Gotowy APK pobierzesz z zakładki **Actions** → wybrany przebieg → **Artifacts**.

## Wydanie nowej wersji

1. Podbij `versionCode` i `versionName` w `app/build.gradle` i opisz zmiany w `CHANGELOG.md`.
2. Actions → **„Android – wydanie wersji”** → **Run workflow**.
3. Workflow zbuduje podpisany APK i opublikuje go w GitHub Releases (tag `gps-vX.Y`).
   Najnowsza wersja jest zawsze pod stałym linkiem:
   `https://github.com/krzoskarol-beep/FDSFWDSFASD/releases/latest/download/MojaPozycjaGPS.apk`

## Inspiracje (open source)

Rozwiązania sprawdzone w innych projektach, zaimplementowane tu od nowa (te projekty nie mają
licencji open source, więc kod nie był kopiowany, tylko pomysły):

- [cssnr/parking-android](https://github.com/cssnr/parking-android) (ParKing): wyzwalacz
  Bluetooth auta, zasada „nie ustalaj pozycji po fakcie”, historia, adres, alert przy braku
  pozycji, wydania APK w GitHub Releases.
- [marinolabtech/CarDash](https://github.com/marinolabtech/CarDash): automatyczny zapis po
  zatrzymaniu po jeździe powyżej 15 km/h (ten sam próg co w `ParkingDetector`), ostrzeżenie
  o słabym sygnale GPS przed zapisem, kompas do auta.

## Diagnostyka

Na dole ekranu głównego jest przycisk **Diagnostyka**: stan uprawnień, optymalizacji baterii
i Bluetooth oraz dziennik zdarzeń z tła (wykrycie jazdy, start usługi, zapis parkingu, błędy).
Dziennik jest przechowywany tylko w telefonie (ostatnie ok. 500 wpisów); przycisk
**Udostępnij** pozwala go wysłać, np. przy zgłaszaniu problemu.

## Instalacja na telefonie

1. Skopiuj APK (najlepiej release) na telefon.
2. Otwórz plik i zezwól na instalację z nieznanych źródeł.
3. Przy pierwszym uruchomieniu zezwól na dostęp do lokalizacji (najlepiej „dokładnej”).

Pierwszy pomiar GPS pod gołym niebem trwa zwykle od kilku do kilkudziesięciu sekund.
W budynku GPS może nie złapać sygnału, wtedy aplikacja pokazuje mniej dokładną pozycję z sieci.

Wersje do 1.2 były podpisane tymczasowym kluczem debug. Przejście na 1.3 (klucz release)
wymaga jednorazowego odinstalowania starej wersji.
