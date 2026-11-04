# Skraper Allegro z fallbackiem Ceneo / Morele

Python + `requests.Session`, bez płatnych bibliotek, bez Apify, bez proxy.

```
scraper/
  config.py          # ustawienia (nadpisywalne zmiennymi środowiskowymi)
  http_client.py     # sesja: UA z puli 10, nagłówki, opóźnienia, cookies, 403 -> retry
  parsers/           # allegro.py, ceneo.py, morele.py + common.py
  runner.py          # orkiestracja skanu i fallbacku, CLI, tryb pętli
  api.py             # Flask: GET /scan/latest
tests/               # testy offline (pytest)
```

## Uruchomienie

```bash
# Docker
docker compose up -d --build
curl http://localhost:5000/scan/latest

# Lokalnie
pip install -r requirements-dev.txt
python -m scraper.runner "rtx 4070" "sony wh-1000xm5"
python -m scraper.runner --loop          # skan co SCAN_INTERVAL s (±10%)
python -m scraper.runner --reset-cookies # czyste cookies + nowy User-Agent
python -m scraper.api                    # http://localhost:5000/scan/latest
pytest -q
```

Volume `scraper-data` (`/data`) trzyma `cookies.json` i `last_scan.json`, a `scraper-logs` (`/logs`) trzyma
`scraper.log`, `api-access.log` i `api-error.log`. Podgląd: `docker compose exec scraper tail -f /logs/scraper.log`.

## Przebieg skanu

1. Dla każdego zapytania: strona główna Allegro (tylko gdy nie ma cookies), potem listing.
2. Przed każdym żądaniem jest losowa pauza 2–8 s.
3. Po 403/429 albo stronie z captchą DataDome skrypt czeka 30–90 s i ponawia, maksymalnie 3 razy.
4. Gdy ponowienia się skończą, rzucany jest `BlockedError`. Allegro jest wtedy pomijane do końca skanu,
   a to samo zapytanie (i kolejne) idzie do Ceneo i Morele.
5. Wynik trafia atomowo do `last_scan.json`:

```json
{
  "meta": {"zapytania": ["rtx 4070"], "zrodla": ["ceneo", "morele"], "allegro_zablokowane": true, "liczba_ofert": 42, "bledy": [...]},
  "oferty": [
    {"tytul": "...", "cena": 2599.0, "dostawa": "Darmowa dostawa", "sprzedawca": "...", "ocena": 4.8,
     "link": "https://...", "zrodlo": "ceneo", "zapytanie": "rtx 4070"}
  ]
}
```

## Zmienne środowiskowe

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `QUERIES` | 2 przykładowe | zapytania rozdzielone przecinkiem |
| `MIN_DELAY` / `MAX_DELAY` | 2 / 8 | losowa pauza przed żądaniem (s) |
| `BLOCK_WAIT_MIN` / `BLOCK_WAIT_MAX` | 30 / 90 | pauza po 403/429 (s) |
| `MAX_RETRIES` | 3 | ponowienia po blokadzie |
| `SHUFFLE_HEADERS` | 1 | mieszanie kolejności nagłówków |
| `SCAN_INTERVAL` | 3600 | odstęp skanów w trybie `--loop` (s) |
| `MAX_OFFERS_PER_QUERY` | 30 | limit ofert na zapytanie i źródło |
| `DATA_DIR` / `LOG_DIR` | `./data` / `./logs` | w Dockerze `/data` i `/logs` |

## Zabezpieczenia a DataDome: co dają i gdzie się kończą

- **Losowe opóźnienia 2–8 s.** DataDome ocenia tempo i regularność żądań z jednego IP. Stały, szybki rytm to
  najprostszy sygnał bota, a losowa pauza go usuwa.
- **Czekanie 30–90 s po 403 i najwyżej 3 ponowienia.** Natychmiastowe ponawianie po blokadzie tylko potwierdza
  klasyfikację „bot” i może przedłużyć ban IP. Limit ponowień chroni przed pętlą, która nigdy się nie kończy.
- **Cookies w pliku.** Cookie `datadome` niesie historię oceny klienta. Powracający klient z ważnym cookie wygląda
  lepiej niż anonimowy gość przy każdym uruchomieniu. Uwaga: jeśli cookie zostało oznaczone jako bot, utrwala
  blokadę. Wtedy pomaga `--reset-cookies`.
- **User-Agent z puli 10.** UA jest losowany raz i zapisywany razem z cookies, a nie przy każdym żądaniu. Zmiana UA
  przy tym samym cookie i IP to dla DataDome mocny sygnał niespójności. Nagłówki (`Sec-CH-UA` tylko dla Chromium)
  są dopasowane do wylosowanej przeglądarki.
- **Losowa kolejność nagłówków.** Jest zrobiona zgodnie ze specyfikacją, ale prawdziwe przeglądarki wysyłają
  nagłówki w stałej, charakterystycznej kolejności. Losowa kolejność jest więc raczej sygnałem bota niż kamuflażem.
  Można ją wyłączyć przez `SHUFFLE_HEADERS=0`.
- **Twardy limit tej architektury.** `requests` ma odcisk TLS/HTTP (JA3/JA4, brak HTTP/2), który wyraźnie różni się
  od przeglądarki, i nie wykonuje wyzwania JavaScript DataDome. Na Allegro trzeba więc liczyć się z tym, że
  przeważnie skończy się na 403. Dlatego istnieje fallback. Stabilny dostęp do danych Allegro daje oficjalne
  [Allegro REST API](https://developer.allegro.pl/).

Przed uruchomieniem sprawdź regulaminy i `robots.txt` serwisów. Trzymaj niski wolumen zapytań. Selektory w
parserach opierają się na układzie stron, który się zmienia. Gdy źródło zwraca 0 ofert, zacznij diagnozę od nich.
