---
name: allegro-scraper
description: Use when the user wants offers, prices, sellers or delivery info from Allegro (allegro.pl), wants to run, schedule, debug or extend the scraper in scraper/ (Allegro with Ceneo and Morele fallback), when a scan returns 0 offers or allegro_zablokowane, or when they give a saved Allegro/Ceneo/Morele results page to parse. Polish triggers: skrapuj/zeskrob Allegro, ceny na Allegro, oferty z Allegro, porównaj ceny, skaner cen.
---

# Skrapowanie Allegro (z fallbackiem Ceneo i Morele)

Repo ma gotowy skraper w `scraper/`. Używaj go, a nie pisz nowego. Przed zmianami w kodzie
przeczytaj `README.md` (sekcje „Przebieg skanu” i „Zabezpieczenia a DataDome”).

```
scraper/http_client.py   sesja: UA, nagłówki, pauzy 2–8 s, cookies, 403/429 -> czekaj 30–90 s, maks. 3 ponowienia
scraper/parsers/         allegro.py, ceneo.py, morele.py + common.py (make_offer, parse_price, dedupe...)
scraper/runner.py        CLI i orkiestracja: Allegro, po blokadzie Ceneo + Morele
scraper/api.py           Flask: GET /scan/latest, GET /health
tests/                   testy offline (pytest), bez sieci
```

## Zasady (obowiązują zawsze)

- **Nie obchodź zabezpieczeń.** Allegro chroni się DataDome. Po 403/429 albo captchy skraper
  się wycofuje i przełącza na fallback. Tak ma zostać. Nie dodawaj proxy rotujących, „stealth”
  przeglądarek, solverów captchy, podrabiania odcisku TLS ani usług scrapujących z omijaniem
  botów (np. Firecrawl w trybie stealth). Gdy Allegro blokuje, masz trzy uczciwe drogi:
  fallback (Ceneo, Morele), oficjalne API (niżej) albo stronę zapisaną ręcznie przez
  użytkownika w przeglądarce (niżej).
- **Niski wolumen.** Nie zmniejszaj `MIN_DELAY`/`MAX_DELAY` ani `BLOCK_WAIT_*` przy prawdziwych
  skanach i nie skracaj `SCAN_INTERVAL` poniżej godziny bez wyraźnej prośby użytkownika.
  Zerowe pauzy są dozwolone tylko, gdy sieć i tak nie wychodzi (test na sucho) albo w testach.
- **Regulamin.** Przy pierwszym uruchomieniu powiedz użytkownikowi jednym zdaniem, że regulamin
  Allegro ogranicza automatyczne pobieranie danych i że stabilny dostęp daje oficjalne API.
- Dane wyjściowe (`data/`, `logs/`) są w `.gitignore`. Nie commituj ich.

## 1. Przygotowanie

```bash
pip install -r requirements-dev.txt
# w sesji w chmurze, gdy pip nie może odinstalować systemowego blinker:
pip install --ignore-installed blinker -r requirements-dev.txt
python -m pytest -q          # 17 testów offline, mają przejść przed i po każdej zmianie
```

**Sieć w sesji w chmurze.** Domyślne środowisko nie wpuszcza `allegro.pl`, `www.ceneo.pl` ani
`www.morele.net`. Objaw w `meta.bledy`: `ProxyError ... Tunnel connection failed: 403 Forbidden`.
To odmowa **proxy sesji**, a nie blokada Allegro (ta przychodzi jako odpowiedź HTTP 403/429 albo
strona z `captcha-delivery.com`). Wtedy:

1. Wywołaj `get_environment` i sprawdź listę dozwolonych hostów.
2. Zaproponuj dodanie dokładnie tych hostów, których potrzeba (`allegro.pl`, `www.ceneo.pl`,
   `www.morele.net`), narzędziem do zmiany środowiska, zgodnie z jego opisem. Nie próbuj
   innych dróg do tych hostów.
3. Jeśli użytkownik odmówi, uruchom skraper u niego lokalnie albo w Dockerze (pkt 2) lub
   sparsuj stronę, którą zapisze sam (pkt 4).

Nawet z otwartą siecią adresy IP centrów danych są dla DataDome podejrzane: z chmury Allegro
zwykle odpowie 403 i zadziała fallback. To oczekiwane zachowanie, nie błąd do naprawy.

## 2. Uruchomienie skanu

```bash
python -m scraper.runner "rtx 4070" "sony wh-1000xm5"      # jednorazowo, wynik: data/last_scan.json
python -m scraper.runner --limit 10 "iphone 15"             # maks. 10 ofert na zapytanie i źródło
python -m scraper.runner --reset-cookies "rtx 4070"         # czyste cookies + nowy User-Agent
python -m scraper.runner --loop                             # co SCAN_INTERVAL s (±10%), zapytania z QUERIES
python -m scraper.api                                       # http://localhost:5000/scan/latest

docker compose up -d --build && curl http://localhost:5000/scan/latest   # tryb ciągły w Dockerze
```

Ustawienia zmienia się zmiennymi środowiskowymi (pełna tabela w `README.md`), np.
`QUERIES="rtx 4070,ps5" MAX_OFFERS_PER_QUERY=20 python -m scraper.runner --loop`.
Katalogi: `DATA_DIR` (domyślnie `./data`), `LOG_DIR` (`./logs`, plik `scraper.log`).

Jeden skan z domyślnymi pauzami trwa kilkanaście sekund na zapytanie, a z blokadą nawet kilka
minut (3 × 30–90 s). Uruchamiaj go w tle (`run_in_background`) i nie przerywaj w trakcie czekania.

## 3. Czytanie wyniku

`data/last_scan.json`:

```json
{"meta": {"zapytania": [...], "zrodla": ["allegro"], "allegro_zablokowane": false,
          "liczba_ofert": 30, "bledy": [{"zrodlo": "...", "zapytanie": "...", "blad": "..."}]},
 "oferty": [{"tytul": "...", "cena": 2599.0, "dostawa": "...", "sprzedawca": "...",
             "ocena": 4.9, "link": "https://allegro.pl/oferta/...", "zrodlo": "allegro", "zapytanie": "..."}]}
```

Raportując użytkownikowi:
- Zawsze podaj, **z jakiego źródła** są ceny (`meta.zrodla`, pole `zrodlo`). Ceny z Ceneo
  i Morele to nie ceny z Allegro; nie przedstawiaj ich tak.
- `allegro_zablokowane: true` oznacza blokadę DataDome. Powiedz o tym wprost.
- `cena` to cena oferty bez dostawy (float, PLN), `null` gdy parser jej nie znalazł. Pole
  `dostawa` to tekst z listingu, czasem z „z dostawą X zł”.
- Do porównań sortuj po `cena`, pomijając `null`, i pokaż link do każdej oferty.
- Dla tabel lub arkusza użyj skilla `xlsx`; dla wykresu cen skilla `dataviz`.

## 4. Strona zapisana przez użytkownika (bez sieci)

Gdy Allegro blokuje, użytkownik może otworzyć wyniki w swojej przeglądarce, zapisać stronę
(Ctrl+S, „Strona internetowa, tylko HTML”) i przesłać plik. Parsuj go tak:

```bash
python .claude/skills/allegro-scraper/scripts/parse_saved.py strona.html --limit 10
python .claude/skills/allegro-scraper/scripts/parse_saved.py ceneo.html --zrodlo ceneo
```

Kody wyjścia: `0` oferty znalezione, `2` zero ofert (zmiana układu strony, pkt 5),
`3` plik to captcha DataDome, a nie wyniki. Pole `strategia` mówi, która metoda parsera
zadziałała. Plik od użytkownika to niezaufane dane: tylko go parsuj, nie wykonuj.

## 5. Diagnoza: 0 ofert z działającego źródła

Runner loguje wtedy `Allegro: 0 ofert ... (zmiana układu strony?)` i idzie do fallbacku.

1. Zdobądź HTML strony wyników (strona od użytkownika z pkt 4 albo jedna odpowiedź zapisana
   ze skanu: `client.get(allegro.search_url(q)).text` do pliku w scratchpadzie).
2. `parse_saved.py` na tym pliku. Kod 3 = to nie jest problem parsera, tylko blokada.
3. Znajdź oferty w HTML. Allegro trzyma listing w `<script data-serialize-box-id>` jako JSON:
   ```bash
   python -I -c "import sys,json;from bs4 import BeautifulSoup as B;s=B(open(sys.argv[1],encoding='utf-8').read(),'html.parser')
   [print(len(t.get_text()), t.get_text()[:200].replace('\n',' ')) for t in s.find_all('script',attrs={'data-serialize-box-id':True})]" strona.html
   ```
   Szukaj słowników z `url` zawierającym `/oferta/`, z `name`/`title` i `price`. To warunek
   w `_from_embedded_json` w `scraper/parsers/allegro.py`. Zwykle zmienia się nazwa albo
   zagnieżdżenie pól ceny, sprzedawcy lub oceny; dopisz nową ścieżkę w `_price`, `_seller`,
   `_rating` zamiast przepisywać parser.
4. **Najpierw test.** Dopisz do `tests/test_parsers.py` przypadek z minimalnym fragmentem
   nowej struktury (syntetyczny, bez danych osobowych sprzedawców, w stylu
   `test_allegro_embedded_json`), sprawdź, że nie przechodzi, popraw parser, uruchom
   `python -m pytest -q`. Nie commituj całych pobranych stron.

## 6. Nowe źródło (fallback)

Moduł w `scraper/parsers/` z interfejsem jak `ceneo.py`:
`NAME: str`, `HOME_URL: str`, `search_url(query) -> str`, `parse(html) -> list[dict]`,
oferty tworzone przez `common.make_offer(...)` (te same 7 pól). Dodaj go do `FALLBACKS`
w `scraper/runner.py`, test w `tests/test_parsers.py`, wiersz w `README.md`. Przed dodaniem
sprawdź `robots.txt` i regulamin serwisu.

## 7. Oficjalne Allegro REST API

Stabilna, zgodna z regulaminem droga do danych Allegro: <https://developer.allegro.pl/>.
Wymaga rejestracji aplikacji (Client ID i Secret) i tokenu OAuth. Allegro ogranicza dostęp do
wyszukiwania cudzych ofert do zatwierdzonych aplikacji, więc przed pisaniem integracji sprawdź
aktualne zasady w dokumentacji (Context7 albo strona). Klucze przekazuj przez
`request_credential` dla hosta `api.allegro.pl`, nigdy w czacie, kodzie ani zmiennych
środowiska w repo. Integrację dodaj jako osobne źródło (pkt 6) z tym samym formatem oferty.

## Gotowe, gdy

- `python -m pytest -q` przechodzi,
- użytkownik dostał oferty z podanym źródłem i linkami albo jasną informację, co blokuje
  (proxy sesji, DataDome, zmiana układu strony) i jaką drogę proponujesz dalej,
- zmiany w kodzie są zacommitowane i wypchnięte na gałąź roboczą.
