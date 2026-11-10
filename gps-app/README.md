# Moja pozycja GPS (Android)

Prosta aplikacja na Androida, która pokazuje aktualną pozycję telefonu.

- szerokość i długość geograficzna (stopnie dziesiętne oraz stopnie, minuty i sekundy)
- dokładność, wysokość, prędkość, kierunek ruchu
- liczba satelitów (używane / widoczne)
- źródło pozycji (GPS albo sieć) i czas pomiaru, odświeżane co sekundę
- przyciski: **Otwórz w mapach**, **Kopiuj**, **Udostępnij** (link do Map Google)

Korzysta tylko z systemowego `LocationManager`, bez Google Play Services, więc działa
także na telefonach bez usług Google. Nie ma żadnych zewnętrznych bibliotek.
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
