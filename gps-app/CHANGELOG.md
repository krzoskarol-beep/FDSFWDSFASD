# Zmiany – Moja pozycja GPS

## 2.0

- **Nowy identyfikator aplikacji: `pl.mojapozycja.gps`** (wcześniej `pl.gps.pozycja`).
  Wersja 2.0 instaluje się jako nowa aplikacja, bez konfliktu z poprzednimi instalacjami
  (wersje 1.0–1.2 były podpisane innym kluczem i blokowały aktualizację: „App not installed”).
  Starą aplikację można po instalacji 2.0 odinstalować. Zapisane miejsca nie są przenoszone.
- Skrót „Zapisz parking” wskazuje na nowy identyfikator (test `ShortcutsTest`).
- Funkcje bez zmian względem 1.7.

## 1.7

- **Przełącznik motywu:** karta „Wygląd” na dole ekranu głównego z wyborem Systemowy / Jasny /
  Ciemny. Wybór działa na wszystkich ekranach i niezależnie od ustawienia telefonu
  (wcześniej tryb ciemny włączał się tylko razem z ciemnym motywem systemu).

## 1.6

- **Poprawka: korek nie jest już parkingiem.** Gdy telefon jest połączony z Bluetooth auta,
  długi postój (korek, czekanie z włączonym silnikiem) nie kończy jazdy. Wcześniej po 20 minutach
  postoju aplikacja zapisywała złe miejsce i przestawała śledzić jazdę.
- **Poprawka: zerwanie Bluetooth w trasie.** Gdy połączenie z autem zerwie się w trakcie jazdy
  i nie wróci, parking zapisuje się 5 minut po zatrzymaniu (wcześniej po 20).
- Połączony z autem, ale bez jazdy przez godzinę (np. radio grające po zgaszeniu silnika):
  zapis miejsca postoju i wyłączenie GPS.
- **Niezawodność w tle:** wyłączenie optymalizacji baterii jest krokiem konfiguracji
  automatycznego zapisu, a gdy Android zablokuje śledzenie, pojawia się powiadomienie
  (najwyżej raz na dobę).
- **Podpowiedź kierunku** obok strzałki: „prosto”, „w prawo”, „za Tobą”…, czytana też przez TalkBack.
- **Tryb ciemny** razem z ciemnym motywem systemu.

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
