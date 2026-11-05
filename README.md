# allegro_ceny — zbieranie i porównywanie cen ofert Allegro

Narzędzie terminalowe w Pythonie: pobiera wyniki wyszukiwania Allegro przeglądarką (Playwright + Chromium),
odczytuje oferty z DOM załadowanej strony, klasyfikuje je (pasuje / odrzucona / wymaga sprawdzenia),
zapisuje do SQLite razem z historią cen, liczy statystyki i eksportuje CSV / JSON / JSON dla AI.
Podstawowe działanie nie wymaga żadnego płatnego API.

> **Stan weryfikacji — przeczytaj przed użyciem.**
> Kod powstał w środowisku, które **nie miało dostępu do allegro.pl** (serwer proxy odrzucał połączenie:
> `CONNECT tunnel failed, response 403` / `net::ERR_TUNNEL_CONNECTION_FAILED`).
> **Selektorów nie sprawdzono na prawdziwej, aktualnej stronie Allegro.** Parser opiera się na stabilnych
> cechach semantycznych (opisanych niżej) i przeszedł testy na **syntetycznych** stronach testowych.
> Zanim zaufasz wynikom, wykonaj kroki z sekcji [Pierwsze uruchomienie: weryfikacja parsera](#pierwsze-uruchomienie-weryfikacja-parsera).

---

## Spis treści

1. [Dostęp do danych Allegro — ustalenia](#dostęp-do-danych-allegro--ustalenia)
2. [Instalacja](#instalacja)
3. [Szybki start](#szybki-start)
4. [Komendy](#komendy)
5. [Profil wyszukiwania](#profil-wyszukiwania)
6. [Dane oferty](#dane-oferty)
7. [Filtrowanie](#filtrowanie)
8. [Analiza](#analiza)
9. [Eksport i eksport dla AI](#eksport-i-eksport-dla-ai)
10. [Blokady i kompletność przebiegu](#blokady-i-kompletność-przebiegu)
11. [Tryb importu (gdy pobieranie nie działa)](#tryb-importu-gdy-pobieranie-nie-działa)
12. [Pierwsze uruchomienie: weryfikacja parsera](#pierwsze-uruchomienie-weryfikacja-parsera)
13. [Bezpieczeństwo i prywatność](#bezpieczeństwo-i-prywatność)
14. [Testy](#testy)
15. [Struktura projektu](#struktura-projektu)
16. [Raport: co działa, co sprawdzono, co pozostało niezweryfikowane](#raport-co-działa-co-sprawdzono-co-pozostało-niezweryfikowane)

---

## Dostęp do danych Allegro — ustalenia

- **Allegro REST API nie daje zwykłej aplikacji wyszukiwania cudzych ofert.** Endpoint `GET /offers/listing`
  (wyszukiwanie ofert) jest w dokumentacji oznaczony jako *„Access for verified applications only”*, a we
  wrześniu 2025 r. przedstawiciel Allegro napisał w repozytorium `allegro/allegro-api`, że dostęp dla nowych
  aplikacji jest niemożliwy, bo został *„zawieszony z przyczyn biznesowych”*
  ([issue #12257](https://github.com/allegro/allegro-api/issues/12257), komentarz z 22.09.2025).
  Ograniczenie dla niezweryfikowanych aplikacji obowiązuje od 15.03.2021.
  Strony `developer.allegro.pl` nie dało się otworzyć bezpośrednio z tego środowiska, więc ustalenie
  opiera się na wynikach wyszukiwania i wypowiedzi w oficjalnym repozytorium Allegro. Sprawdź aktualny stan przed decyzją.
- Dlatego narzędzie czyta **publiczną stronę wyników** w zwykłej przeglądarce, z niskim tempem
  (domyślnie 8 s między stronami, maks. 3 strony) i **bez obchodzenia zabezpieczeń**:
  - bez wtyczek „stealth”, bez ukrywania `navigator.webdriver`, bez podmiany User-Agenta i odcisku przeglądarki;
  - bez rotacji proxy, bez rozwiązywania CAPTCHA, bez prywatnych endpointów;
  - po wykryciu blokady pobieranie się kończy, przebieg jest oznaczany jako **niepełny**.
- Sprawdź samodzielnie regulamin Allegro i `https://allegro.pl/robots.txt` (z tego środowiska nie dało
  się ich odczytać) i używaj narzędzia z umiarem, do własnych potrzeb.
- Program **nie** kupuje, **nie** kontaktuje się ze sprzedawcami, **nie** loguje się.

## Instalacja

Wymagany Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # playwright, beautifulsoup4
python -m playwright install chromium
pip install -r requirements-dev.txt  # opcjonalnie: pytest
```

Jeśli Chromium jest już zainstalowany w nietypowym miejscu, wskaż go zmienną
`ALLEGRO_CENY_CHROMIUM=/ścieżka/do/chrome`.

## Szybki start

```bash
# 1. Pobierz wyniki (otworzy się widoczne okno przeglądarki)
python -m allegro_ceny pobierz --profil profile/stihl_ms391.toml

# 2. Statystyki ostatniego przebiegu
python -m allegro_ceny analiza --profil profile/stihl_ms391.toml

# 3. Eksport CSV + JSON + JSON dla AI do katalogu eksport/
python -m allegro_ceny eksport --profil profile/stihl_ms391.toml

# 4. Zmiany cen między przebiegami
python -m allegro_ceny historia --profil profile/stihl_ms391.toml
```

Bez profilu (ad hoc):

```bash
python -m allegro_ceny pobierz --nazwa husq_455 --fraza "husqvarna 455 rancher" --marka Husqvarna --model 455
python -m allegro_ceny pobierz --profil profile/stihl_ms391.toml --url "https://allegro.pl/listing?string=stihl%20ms391&stan=używane"
```

Dane robocze trafiają do `dane/` (baza `dane/allegro_ceny.sqlite`, log, diagnostyka). Katalog jest w `.gitignore`.

## Komendy

| Komenda | Co robi |
|---|---|
| `pobierz` | Pobiera strony wyników przeglądarką. Opcje: `--headless`, `--max-stron`, `--max-ofert`, `--odstep`, `--zapisz-html`, `--fraza`, `--url`, `--marka`, `--model`, `--cena-min`, `--cena-max`, `--testowe`. |
| `importuj PLIKI…` | Importuje zapisane strony `.html`/`.htm` oraz `.csv`/`.json`. `--testowe` oznacza dane jako testowe. |
| `analiza` | Statystyki ostatniego przebiegu profilu (albo `--przebieg N`). |
| `eksport` | `--formaty csv json ai`, `--katalog eksport`, `--przebieg N`. |
| `historia` | Zmiany ceny tych samych ofert między przebiegami. |
| `przebiegi` | Lista przebiegów: tryb, status, powód zakończenia. |
| `diagnozuj PLIK.html` | Pokazuje, co parser widzi na zapisanej stronie (do weryfikacji selektorów). |

Opcje globalne (przed nazwą komendy): `--katalog-danych dane`, `--baza ścieżka.sqlite`, `-v`.

Kody wyjścia: `0` OK, `2` błąd konfiguracji, `3` przebieg niepełny, `4` `diagnozuj` nie znalazł ofert.

## Profil wyszukiwania

Profile to pliki TOML w `profile/` — osobny plik na każdy produkt. Wzór: [`profile/stihl_ms391.toml`](profile/stihl_ms391.toml).

| Klucz | Znaczenie |
|---|---|
| `nazwa` | Identyfikator profilu (historia cen jest per profil). |
| `[wyszukiwanie] fraza` / `url` | Fraza albo gotowy adres wyników (adres ma pierwszeństwo). Filtry Allegro (stan, cena, kategoria) najpewniej ustawisz w przeglądarce i wkleisz adres. |
| `[produkt] marka`, `model` | Oczekiwana marka i model. Model `MS391` dopasuje „MS 391”, „MS-391”, „ms391”, ale **nie** MS39, MS3910, MS 3911; „MS391C” trafi do sprawdzenia. |
| `aliasy_modelu` | Dodatkowe zapisy, np. `"STIHL 391"`. |
| `akceptowane_marki` | Lista marek dopuszczonych (domyślnie = `marka`). |
| `slowa_produktu` | Słowa oznaczające kompletny produkt („pilarka”, „piła spalinowa”). |
| `frazy_neutralne` | Frazy usuwane przed szukaniem części („piła łańcuchowa” ≠ „łańcuch”). |
| `[filtry] stany` | `nowe`, `używane`, `uszkodzone`. |
| `cena_min`, `cena_max` | Zakres ceny pełnej. Poza zakresem → odrzucona z opisem. |
| `cena_podejrzana_ponizej` | Próg oznaczania podejrzanie niskich cen w analizie. |
| `slowa_czesci`, `slowa_opakowania`, `marki_czesci` | Słownik części, opakowań/dokumentów i marek osprzętu. |
| `slowa_niekompletny` | Sygnały braków („bez prowadnicy”) → do sprawdzenia. |
| `wykluczone_slowa` | Twarde wykluczenia (np. „wynajem”). |
| `[pobieranie] max_stron`, `max_ofert`, `odstep_s`, `limit_czasu_s`, `ponowienia` | Limity. `odstep_s` ≥ 2 s; ponowienia (0–5) tylko przy błędach przejściowych. |

Słowa dopasowywane są bez wielkości liter i polskich znaków, jako **rdzenie od początku słowa**
(„łańcuch” trafi w „łańcucha”). Słowo zakończone `=` musi wystąpić dokładnie (`"pila="` nie trafi w „pilarka”).

## Dane oferty

| Pole | Opis |
|---|---|
| `offer_id`, `id_pewne` | ID z linku `/oferta/…-<ID>`. Gdy linku z ID brak: identyfikator zastępczy `x-…`, `id_pewne=false`. |
| `url` | Bezpośredni link bez parametrów śledzących (także dla linków reklamowych `…/events/clicks?redirect=…`). |
| `tytul` | Tekst sprzedawcy (dane niezaufane). |
| `marka`, `model`, `ean` | Marka z tytułu (`nieustalona`, gdy nie rozpoznano — to **nie** znaczy no-name), model z dopasowania, EAN tylko z poprawną sumą kontrolną. |
| `cena`, `waluta`, `cena_rodzaj` | Pełna cena produktu. `pelna` albo `od` (najniższa z wariantów — nieporównywalna). **Nigdy rata.** |
| `koszt_dostawy` | Tylko gdy podany dokładnie (np. „dostawa 19,99 zł” albo bezwarunkowa „darmowa dostawa” → 0). |
| `koszt_dostawy_od` | „dostawa od 9,99 zł” — dolna granica, **nie** koszt. |
| `cena_z_dostawa`, `…_zrodlo` | `strona` (podana przez Allegro) albo `obliczona` (cena + dokładny koszt dostawy). Inaczej `null`. |
| `smart` | Widoczne oznaczenie Smart. **Nie** oznacza darmowej dostawy dla każdego — koszt pozostaje `null`. |
| `stan`, `stan_zrodlo` | `nowy` / `używany` / `uszkodzony` / inny tekst; z parametru „Stan” albo z tytułu. |
| `sprzedawca` | Login z linku `/uzytkownik/…`, jeśli jest. |
| `sponsorowana` | `true` = wykryto „Sponsorowane” lub link reklamowy; `false` = nie wykryto oznaczenia. |
| `pobrano` | Czas ze strefą (`2026-11-05T01:21:28+01:00`); `null` przy imporcie bez czasu. |
| `fraza`, `profil`, `decyzja`, `powod`, `uwagi`, `ostrzezenia_parsera`, `wystapienia` | Kontekst i wynik filtra. |

Zasady: brak danych = `null` (pusta komórka w CSV), nigdy 0 ani wartość wymyślona. Kwoty liczone na `Decimal`,
w bazie jako grosze (`INTEGER`). Raty, ceny referencyjne („najniższa cena z 30 dni”) i ceny „z dostawą” są
rozpoznawane po tekście bezpośrednio przy kwocie i nie są mylone z ceną.

## Filtrowanie

Każda oferta dostaje decyzję i powód:

- **pasuje** — zgodny model, akceptowana marka, akceptowany stan, znana pełna cena;
- **odrzucona** — np. „część zamienna: „prowadnic””, „inny model: MS362”, „inna marka: Husqvarna”,
  „produkt uszkodzony / na części”, „zamiennik / nie oryginał (fraza „typu ms 391”)”, „opakowanie / dokumenty”,
  „cena … poniżej minimum profilu”;
- **wymaga_sprawdzenia** — „brak pewności co do modelu”, „marka nieustalona”, „w tytule kilka modeli”,
  „możliwy inny wariant modelu”, „możliwie niekompletny”, „cena „od””, „brak ceny”.

Kontekst ma znaczenie: „**Pilarka** STIHL MS391 + łańcuch gratis” → *pasuje* (część po nazwie produktu =
wyposażenie, z uwagą), „**Łańcuch** Oregon do STIHL MS391” → *odrzucona*. Przy wątpliwości program wybiera
„wymaga sprawdzenia”, a nie odrzucenie. Filtr widzi tylko tytuł i dane z listy wyników (nie pełny opis oferty).

Duplikaty: ta sama oferta (to samo ID) w jednym przebiegu jest zapisywana raz (`wystapienia` liczy powtórzenia,
np. pozycja sponsorowana + zwykła). Różne oferty tego samego modelu są zachowane. Kolejne przebiegi dopisują
**obserwacje** (historię ceny) zamiast nowych rekordów oferty.

## Analiza

`analiza` pokazuje dla ofert *pasuje* z pełną ceną: liczby (pasuje/odrzucone/do sprawdzenia), min, Q1, medianę,
Q3, max — łącznie, osobno dla stanów (nowy/używany/…) i osobno dla ceny z dostawą (z pokryciem, np. `4/6`),
najtańsze oferty z linkami, podejrzanie niskie ceny (poniżej Q1 − 1,5·IQR, poniżej 60% mediany lub progu
z profilu) oraz główne powody odrzuceń. Kwartyle liczone są od n ≥ 4; przy n < 5 wyświetlane jest
ostrzeżenie o małej próbie. `historia` pokazuje zmiany cen tych samych ofert.

To **ceny ofertowe**, nie potwierdzone ceny sprzedaży. Zniknięcie oferty z wyników nie oznacza sprzedaży
(może to być zakończenie, zmiana pozycji, limit stron) — eksport AI opisuje to wprost.

## Eksport i eksport dla AI

`eksport` tworzy w `eksport/`:

- `…_przebiegN.csv` — UTF-8 z BOM (polskie znaki poprawnie w Excelu), separator `;`, przecinek dziesiętny,
  pusta komórka = brak danych;
- `…_przebiegN.json` — pełne dane przebiegu i ofert, kwoty jako tekst `"1299.00"`;
- `…_przebiegN_ai.json` — do przekazania modelowi AI: `kryteria`, `pobranie` (zakres, status, `kompletny`,
  powód zakończenia), `statystyki`, `oferty_pasujace`, `oferty_do_sprawdzenia`, podsumowanie odrzuconych,
  `zmiany_cen`, `niewidziane_w_tym_przebiegu`, `braki_i_ograniczenia` oraz `instrukcja_dla_ai`.

Teksty od sprzedawców (tytuł, login, opis dostawy) są wyłącznie w polach `tekst_sprzedawcy`, opisanych jako
dane niezaufane — nawet jeśli tytuł zawiera „polecenie”, program i eksport traktują je jako zwykły tekst.

Przykłady w [`przyklady/`](przyklady/) mają prefiks `TESTOWE_` — **powstały z syntetycznych stron testowych,
nie są aktualnymi ofertami** (pole `dane_testowe: true`). Odtworzenie: `./przyklady/generuj.sh`.
Rzeczywistych eksportów w repozytorium nie ma, bo z tego środowiska nie było dostępu do Allegro.

## Blokady i kompletność przebiegu

Każdy przebieg ma status i zapisany powód zakończenia (`przebiegi`, eksport `pobranie`):

| Powód | Status | Znaczenie |
|---|---|---|
| `brak_wynikow` | pelny | Strona pokazała komunikat o braku wyników. |
| `koniec_wynikow`, `powtorzona_strona`, `brak_nowych_ofert` | pelny | Koniec wyników; zapętlenie tej samej strony jest wykrywane (te same ID lub przekierowanie na inny numer strony). |
| `limit_stron`, `limit_ofert` | ograniczony_limitem | Zatrzymano na limicie z profilu. |
| `blokada` | **niepelny** | HTTP 401/403/407/429, iframe CAPTCHA, komunikat „potwierdź, że jesteś człowiekiem” lub przekierowanie na obcą domenę. |
| `blad_sieci`, `blad_http` | **niepelny** | Timeout / błąd sieci / 5xx po wyczerpaniu ponowień. |
| `nieznany_uklad_strony` | **niepelny** | Brak ofert **i** brak komunikatu o braku wyników — możliwa zmiana układu. **To nie jest „brak ofert”.** |
| `przerwane`, `blad_wewnetrzny` | **niepelny** | Ctrl+C albo błąd programu. |
| `import` | import | Dane z plików — kompletność nieznana. |

Przy blokadzie: pobieranie się zatrzymuje (brak kolejnych żądań), oferty z wcześniejszych stron zostają
w bazie (zapis po każdej stronie), w `dane/diagnostyka/przebieg_N/` zapisywany jest zrzut ekranu, a w bazie
diagnostyka strony: kod HTTP, oczyszczony adres, tytuł strony, wykryte znaczniki, statystyki parsera.
Diagnostyka nie zawiera cookies ani nagłówków. Program nie próbuje ponawiać po blokadzie.
Status jest zapisywany do bazy, zanim przeglądarka zostanie zamknięta.

## Tryb importu (gdy pobieranie nie działa)

```bash
python -m allegro_ceny importuj --profil profile/stihl_ms391.toml wyniki_s1.html wyniki_s2.html moje_oferty.csv
```

- **HTML**: otwórz wyniki w zwykłej przeglądarce, przewiń do końca, zapisz jako „Strona internetowa, kompletna”
  (wersja „tylko HTML” może nie zawierać ofert doładowanych skryptem). Każdy plik = jedna strona.
- **CSV** (`;` lub `,`, UTF-8) / **JSON** (lista albo `{"oferty": [...]}`, przyjmuje też własny eksport AI):
  rozpoznawane kolumny m.in. `id`/`offer_id`, `tytul`/`title`, `cena`/`price`, `dostawa`/`koszt_dostawy`,
  `cena_z_dostawa`, `stan`, `link`/`url`, `sprzedawca`, `sponsorowana`, `ean`, `pobrano`.

**Ograniczenia importu:** zakres wyników i kompletność są nieznane (status `import`, `kompletny: false`);
czas pobrania jest `null`, jeśli plik go nie zawiera; dane z CSV/JSON nie są weryfikowane z Allegro;
zapisana strona z CAPTCHA zostanie wykryta i oznaczy przebieg jako niepełny.

## Pierwsze uruchomienie: weryfikacja parsera

Ponieważ selektorów nie dało się sprawdzić na żywej stronie, zrób to raz u siebie:

1. `python -m allegro_ceny pobierz --profil profile/stihl_ms391.toml --max-stron 1 --zapisz-html`
2. Porównaj wynik w terminalu z tym, co widać w oknie przeglądarki.
3. `python -m allegro_ceny diagnozuj dane/strony/przebieg_1/strona_1.html --ile 20` — sprawdź dla kilku ofert:
   ID i tytuł, cenę (czy to nie rata/„z dostawą”), koszt dostawy, stan, sponsorowanie.
4. W wyniku `diagnozuj` zwróć uwagę na `strategia` (oczekiwane `dom_article`), `kontenery` vs
   `linki_ofert_na_stronie` (podobne liczby) i `braki_pol`.

Jak działa parser (`allegro_ceny/parse.py`): kontener oferty = element `<article>` z linkiem `/oferta/…-<ID>`
(zapasowo: najwyższy przodek linku z kwotą i jednym ID); tytuł z `h2`/`h3`; cena z `aria-label` zawierającego
„cena” albo z tekstu, gdzie każda kwota jest klasyfikowana po etykiecie przylegającej z lewej/prawej;
uzupełnienia z JSON osadzonego w `<script type="application/json|ld+json">`. Klasy CSS nie są używane.

**Gdy parser nie widzi ofert** (`nieznany_uklad_strony`, `diagnozuj` zwraca kod 4): obejrzyj zrzut z
`dane/diagnostyka/`. Jeśli to zgoda na cookies — kliknij ją w otwartym oknie przy kolejnym przebiegu albo
zignoruj (oferty i tak są w DOM pod spodem). Jeśli oferty są widoczne, a parser ich nie znajduje, układ
strony się zmienił — dopasuj `_containers` / `_title` / `_prices` w `parse.py` i dodaj zapisany HTML jako
test w `tests/fixtures/` (usuń z niego wcześniej ewentualne dane osobowe).

## Bezpieczeństwo i prywatność

- Każde uruchomienie to nowy, pusty kontekst przeglądarki; cookies istnieją tylko w pamięci do zamknięcia
  okna i nie są zapisywane na dysk (sprawdza to test `tests/test_browser.py`).
- Logi i diagnostyka zawierają tylko oczyszczone adresy wyszukiwania (`string`, `p`, …), bez nagłówków i cookies.
- `--zapisz-html` zapisuje pełny HTML do `dane/strony/` — może zawierać techniczne tokeny strony; katalog
  jest w `.gitignore`, nie udostępniaj go.
- Brak logowania, zakupów i kontaktu ze sprzedawcami.

## Testy

```bash
pip install -r requirements-dev.txt
python -m pytest -q                 # 125 testów, ok. 10 s
python -m pytest -q -m "not browser"  # bez uruchamiania Chromium
```

- `test_money.py` — polskie formaty cen (spacje, twarde spacje, kropki tysięcy, ceny rozbite na elementy), `null` zamiast 0, Decimal.
- `test_parse.py` — rata vs cena, „z dostawą”, „dostawa od”, Smart bez założenia darmowej dostawy, cena „od”, cena z 30 dni, sponsorowane i linki śledzące, duplikaty, strategie zapasowe, CAPTCHA vs skrypt pomiarowy, brak wyników vs nieznany układ.
- `test_filtering.py` — produkt vs część/opakowanie/zamiennik, wzmianka o części w kompletnym produkcie, warianty zapisu modelu i podobne numery, marki, stany, uszkodzenia, niekompletność.
- `test_storage_pipeline.py` — deduplikacja, historia cen, `null` w bazie, paginacja i zapętlenie, blokada w trakcie (dane zachowane, brak kolejnych żądań), błąd sieci, nieznany układ, Ctrl+C, błąd programu, import, status zapisany przed zamknięciem przeglądarki.
- `test_analysis_export.py` — kwartyle, mała próba, podejrzanie niskie ceny, rozdział stanów i dostawy, CSV UTF-8 z polskimi znakami, struktura eksportu AI, „polecenie” w tytule jako dane.
- `test_browser.py` — **prawdziwy Chromium** na lokalnym serwerze z syntetycznymi stronami: paginacja i zapętlenie, blokada 403 + CAPTCHA (zatrzymanie, zrzut ekranu, zachowane dane), ponowienie po 503, brak zapisu cookies, `navigator.webdriver === true` (automatyzacja nie jest ukrywana), zamknięcie przeglądarki.

Wszystkie dane w `tests/fixtures/` są **syntetyczne** (fikcyjne ID `99…`, sprzedawcy `sprzedawca_testowy_N`).

## Struktura projektu

```
allegro_ceny/
  cli.py         interfejs terminalowy (argparse)
  config.py      profile TOML i walidacja
  fetch.py       pobieranie: Playwright/Chromium, limity czasu, ponowienia, zamykanie
  blocking.py    rozpoznawanie blokady/CAPTCHA, braku wyników, banera zgód
  parse.py       parsowanie DOM strony wyników -> oferty
  urls.py        adresy wyników, paginacja, ID oferty, czyszczenie linków
  money.py       kwoty: polskie formaty, Decimal, grosze
  textnorm.py    normalizacja tekstu, dopasowanie fraz, EAN
  filtering.py   decyzje filtra z uzasadnieniem
  storage.py     SQLite: przebiegi, oferty, obserwacje (historia)
  analysis.py    statystyki, podejrzane ceny, zmiany cen
  export.py      CSV / JSON / JSON dla AI
  importers.py   import HTML / CSV / JSON
  pipeline.py    przebieg: pobieranie/import -> parsowanie -> filtr -> zapis
profile/stihl_ms391.toml   przykładowy profil
przyklady/                 przykładowe eksporty TESTOWE (syntetyczne) + generuj.sh
tests/                     testy i syntetyczne strony testowe
```

## Raport: co działa, co sprawdzono, co pozostało niezweryfikowane

**Sprawdzone (w tym środowisku):**
- 125 testów automatycznych przechodzi, w tym 4 z prawdziwym Chromium 153 (Playwright 1.63) na lokalnym serwerze.
- Parser, filtr, analiza i eksport na syntetycznych stronach: rozróżnianie ceny/raty/ceny z dostawą/kosztu
  dostawy/ceny referencyjnej, części vs produkt, modele, deduplikacja, historia cen (wykryta zmiana 2 899 → 2 749 zł
  w przykładzie).
- Mechanika przeglądarki: paginacja, wykrycie zapętlenia, zatrzymanie przy 403 + CAPTCHA z zachowaniem danych
  i zrzutem ekranu, ponowienie po 503, brak zapisu cookies, poprawne zamykanie.
- **Próba na prawdziwym Allegro:** `pobierz --max-stron 1` → proxy środowiska odrzuciło połączenie
  (`net::ERR_TUNNEL_CONNECTION_FAILED`). Program wykonał 3 próby, zakończył przebieg statusem **niepełny /
  blad_sieci** i nie zgłosił tego jako „brak ofert”. Przy tej próbie wykryto i naprawiono zawieszanie się
  zamykania przeglądarki na stronie błędu Chromium.

**Niezweryfikowane:**
- Działanie selektorów na **aktualnej stronie Allegro** (struktura DOM, etykiety cen/dostawy/stanu,
  oznaczenie „Sponsorowane”, linki sprzedawców, komunikat o braku wyników, parametr `p` paginacji).
  Testowe strony odwzorowują założenia, nie są kopią Allegro.
- Zachowanie mechanizmów antybotowych Allegro wobec zwykłej przeglądarki sterowanej przez Playwright —
  możliwe, że blokada pojawi się od razu; program wtedy zatrzyma się i oznaczy przebieg jako niepełny.
- Aktualna treść dokumentacji Allegro API, regulaminu i `robots.txt` (strony niedostępne z tego środowiska).
- Uruchomienie w trybie z widocznym oknem (środowisko nie ma ekranu; testy działają w trybie headless,
  kod obu trybów jest ten sam poza flagą `headless`).
