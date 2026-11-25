# Lightpanda kontra Chromium

[Lightpanda](https://github.com/lightpanda-io/browser) to bezgłowa przeglądarka
napisana od zera w Zigu (bez Chromium i WebKita), przeznaczona dla automatyzacji
i agentów AI. Mówi protokołem CDP, więc steruje się nią zwykłym Puppeteerem
lub Playwrightem.

Ten folder uruchamia **ten sam skrypt Puppeteera** na obu przeglądarkach
i mierzy czas na stronę oraz szczytową pamięć.

```
site/          # strona testowa: lista 200 produktów budowana przez JS z products.json
scrape.mjs     # skrypt Puppeteera (connect do Lightpandy albo launch Chromium)
bench.sh       # pobiera Lightpandę, stawia stronę, uruchamia obie przeglądarki, mierzy RSS
```

## Uruchomienie

Wymagane: Node 20+, Python 3 (serwer strony testowej), Chromium/Chrome.

```bash
cd lightpanda-demo
./bench.sh                      # 50 załadowań, obie przeglądarki
./bench.sh 100 lightpanda       # tylko Lightpanda, 100 załadowań
CHROME_PATH=/usr/bin/chromium ./bench.sh
URL=https://example.com SELECTOR=h1 ./bench.sh 10   # własna strona zamiast demo
```

Przy pierwszym uruchomieniu `bench.sh` pobiera nocną binarkę Lightpandy do
`bin/` (Linux x86_64/aarch64, macOS) i instaluje `puppeteer-core`.
Telemetria Lightpandy jest wyłączona (`LIGHTPANDA_DISABLE_TELEMETRY=true`).

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `URL` | lokalna strona demo | adres do załadowania |
| `SELECTOR` | `li.product` | element, na który skrypt czeka |
| `CHROME_PATH` | `/opt/pw-browsers/chromium` | binarka Chromium |
| `LP_BIN` | `bin/lightpanda` | binarka Lightpandy |
| `SITE_PORT` / `LP_PORT` | 8811 / 9222 | porty strony demo i serwera CDP |

Sama Lightpanda bez Puppeteera:

```bash
bin/lightpanda fetch --wait-selector li.product --dump markdown http://127.0.0.1:8811/
bin/lightpanda serve --host 127.0.0.1 --port 9222   # serwer CDP
```

Na stronach doładowujących treść w tle trzeba podać `--wait-selector`
(albo w Puppeteerze `waitForSelector`), inaczej zrzut powstanie przed danymi.

## Wynik (listopad 2026, Lightpanda 1.1.0-nightly, Chromium 1243, kontener Linux)

50 załadowań strony demo, dwa przebiegi:

| | Lightpanda | Chromium | Różnica |
|---|---|---|---|
| Czas na stronę | 21–25 ms | 148–162 ms | ~7× szybciej |
| Szczytowa pamięć (RSS) | 25 MB | 846–878 MB | ~35× mniej |

Obie przeglądarki zwróciły identyczne dane (200 produktów, maks. 499.39, średnia 239.69).

Zastrzeżenia:

- Czas Chromium nie obejmuje jego uruchomienia.
- RSS Chromium to suma jego procesów; pamięć współdzielona liczy się kilka razy,
  więc to górne oszacowanie. Pomiar RSS działa tylko na Linuksie (`/proc`).
- Strona demo jest prosta. Na dużych serwisach przewaga maleje, a część stron
  może w Lightpandzie nie działać, bo nie implementuje ona całej platformy webowej.
