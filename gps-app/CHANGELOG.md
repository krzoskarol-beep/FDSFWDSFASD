# Zmiany – Moja pozycja GPS

## 1.5

- **Tylko Bluetooth auta:** automatyczne zapisywanie korzysta wyłącznie z połączenia
  z Bluetooth samochodu. Usunięto rozpoznawanie aktywności (usługi Google Play)
  i uprawnienie „Aktywność fizyczna”.
- Aplikacja nie ma już żadnych zewnętrznych bibliotek i działa na telefonach bez usług
  Google; APK zmalał z ok. 340 KB do ok. 60 KB.
- Włączanie automatu prowadzi krok po kroku: lokalizacja → „Urządzenia w pobliżu” →
  wybór auta → lokalizacja w tle.
- Diagnostyka pokazuje stan Bluetooth i wybrane auto.

## 1.4

- **Bluetooth auta jako wyzwalacz:** połączenie z radiem / zestawem głośnomówiącym auta
  rozpoczyna śledzenie jazdy, a rozłączenie (wyłączenie silnika) zapisuje parking dokładnie
  w miejscu postoju. Bez fałszywych alarmów w autobusie i bez wymogu usług Google Play.
  Chwilowe zerwanie Bluetooth w trakcie jazdy jest ignorowane.
- **Poprawka:** zapis awaryjny nie używa już pozycji sprzed kilku minut (mogła pochodzić
  z trasy, nawet kilometry od parkingu). Pozycja musi pochodzić z okolic zdarzenia; jeśli jej
  brak, aplikacja prosi o ręczny zapis zamiast zgadywać.
- **Adres parkingu** (np. „Marszałkowska 10, Warszawa”) na karcie i w powiadomieniu.
- **Historia parkowań** (30 ostatnich): otwieranie w mapach, przywracanie jako aktualne
  miejsce (np. po fałszywym alarmie), usuwanie.
- CI: wydania w GitHub Releases ze stałym linkiem do najnowszej wersji; nowsze wersje akcji.

## 1.3

- Stały klucz podpisu wersji release, R8 (APK ok. 0,3 MB).
- Ekran „Diagnostyka” z dziennikiem zdarzeń z tła.
- CI: testy jednostkowe, lint, testy na emulatorze z Androidem 14.

## 1.2

- Automatyczne zapisywanie parkowania: wykrywanie jazdy w tle (usługi Google),
  śledzenie GPS tylko w trakcie jazdy, wybór miejsca postoju.

## 1.1

- „Gdzie zaparkowałem?”: zapis miejsca z notatką, strzałka z kompasem, odległość,
  nawigacja piesza, skrót na ikonie aplikacji.

## 1.0

- Aktualna pozycja GPS: współrzędne, dokładność, wysokość, prędkość, kierunek, satelity.
