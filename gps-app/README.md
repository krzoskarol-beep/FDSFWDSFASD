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

### Automatyczne zapisywanie parkowania (w tle)

Włącz przełącznik **„Zapisuj parking automatycznie”**. Od tej pory:

1. Rozpoznawanie aktywności z usług Google Play wykrywa, że jedziesz samochodem
   (działa w tle bez GPS, więc prawie nie zużywa baterii).
2. W trakcie jazdy działa usługa z powiadomieniem „Jedziesz”, która śledzi GPS.
3. Po zakończeniu jazdy aplikacja zapisuje **miejsce, w którym auto stanęło**
   (a nie to, do którego zdążyłeś dojść, zanim system zgłosił koniec jazdy)
   i pokazuje powiadomienie z przyciskiem **Prowadź**.

Jak wybierany jest punkt postoju (`ParkingDetector`): pierwszy pomiar z prędkością poniżej
ok. 3,6 km/h po ostatnim odcinku jazdy powyżej ok. 15 km/h. Postój na światłach kasuje się,
gdy auto znów rusza. Gdy GPS zniknie (garaż podziemny), zapisywany jest ostatni punkt jazdy.

Wymagane uprawnienia: lokalizacja „Zezwalaj zawsze”, „Aktywność fizyczna” i (opcjonalnie)
powiadomienia. Wymaga usług Google Play. Jazda autobusem czy pociągiem też jest rozpoznawana
jako jazda, więc w powiadomieniu „Jedziesz” jest przycisk **„To nie moje auto”**.

Pozycję odczytuje z systemowego `LocationManager`, więc podstawowe funkcje działają także
na telefonach bez usług Google. Tylko automatyczne zapisywanie parkowania korzysta
z biblioteki `play-services-location` (rozpoznawanie aktywności).
Działa na Androidzie 7.0 lub nowszym (minSdk 24, targetSdk 36).

## Budowanie

Wymagane: JDK 17+ i Android SDK (platforma 36).

```bash
cd gps-app
echo "sdk.dir=/ścieżka/do/android-sdk" > local.properties   # Android Studio robi to samo
./gradlew assembleDebug        # APK: app/build/outputs/apk/debug/app-debug.apk
./gradlew testDebugUnitTest    # testy jednostkowe
```

Można też po prostu otworzyć katalog `gps-app` w Android Studio.

## Instalacja na telefonie

1. Skopiuj `app-debug.apk` na telefon.
2. Otwórz plik i zezwól na instalację z nieznanych źródeł.
3. Przy pierwszym uruchomieniu zezwól na dostęp do lokalizacji (najlepiej „dokładnej”).

Pierwszy pomiar GPS pod gołym niebem trwa zwykle od kilku do kilkudziesięciu sekund.
W budynku GPS może nie złapać sygnału, wtedy aplikacja pokazuje mniej dokładną pozycję z sieci.

APK jest podpisany kluczem debug, więc nadaje się do instalacji ręcznej, ale nie do Google Play.
