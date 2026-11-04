"""Główna logika skanu: Allegro, a po blokadzie fallback na Ceneo i Morele.

Uruchomienie:
    python -m scraper.runner "rtx 4070" "sony wh-1000xm5"   # jednorazowy skan
    python -m scraper.runner --loop                          # skan co SCAN_INTERVAL s
    python -m scraper.runner --reset-cookies                 # nowa tożsamość, czyste cookies
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import requests

from . import config
from .http_client import BlockedError, PersistentSession
from .logging_setup import setup_logging
from .parsers import allegro, ceneo, morele

log = logging.getLogger(__name__)

PRIMARY: ModuleType = allegro
FALLBACKS: tuple[ModuleType, ...] = (ceneo, morele)


def build_client() -> PersistentSession:
    """Tworzy sesję HTTP z ustawieniami z config.py."""
    return PersistentSession(
        cookies_file=config.COOKIES_FILE,
        min_delay=config.MIN_DELAY,
        max_delay=config.MAX_DELAY,
        block_wait=(config.BLOCK_WAIT_MIN, config.BLOCK_WAIT_MAX),
        max_retries=config.MAX_RETRIES,
        timeout=config.REQUEST_TIMEOUT,
        shuffle_headers=config.SHUFFLE_HEADERS,
    )


def scrape_source(
    client: PersistentSession, source: ModuleType, query: str, limit: int
) -> list[dict[str, Any]]:
    """Pobiera i parsuje wyniki jednego serwisu dla jednego zapytania."""
    client.warm_up(source.HOME_URL)
    resp = client.get(source.search_url(query), referer=source.HOME_URL)
    offers = source.parse(resp.text)[:limit]
    for offer in offers:
        offer["zapytanie"] = query
    log.info("%s: %d ofert dla „%s”", source.NAME, len(offers), query)
    return offers


def run_scan(
    queries: list[str],
    client: PersistentSession | None = None,
    limit: int | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    """Wykonuje pełny skan i zapisuje wynik do pliku JSON."""
    client = client or build_client()
    limit = limit or config.MAX_OFFERS_PER_QUERY
    started = datetime.now(timezone.utc)

    offers: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    sources_used: set[str] = set()
    # Po blokadzie Allegro nie wracamy do niego w tym samym skanie —
    # każde kolejne żądanie tylko pogłębiałoby „podejrzenie”.
    primary_blocked = False

    for query in queries:
        if not primary_blocked:
            try:
                found = scrape_source(client, PRIMARY, query, limit)
                if found:
                    offers.extend(found)
                    sources_used.add(PRIMARY.NAME)
                    continue
                log.warning("Allegro: 0 ofert dla „%s” (zmiana układu strony?) — fallback", query)
            except BlockedError as exc:
                primary_blocked = True
                errors.append({"zrodlo": PRIMARY.NAME, "zapytanie": query, "blad": str(exc)})
                log.error("Allegro zablokowane: %s — przełączam na fallback", exc)
            except requests.RequestException as exc:
                errors.append({"zrodlo": PRIMARY.NAME, "zapytanie": query, "blad": str(exc)})
                log.error("Allegro: błąd %s — fallback dla „%s”", exc, query)

        # Fallback: te same zapytania w Ceneo i Morele.
        for source in FALLBACKS:
            try:
                offers.extend(scrape_source(client, source, query, limit))
                sources_used.add(source.NAME)
            except (BlockedError, requests.RequestException) as exc:
                errors.append({"zrodlo": source.NAME, "zapytanie": query, "blad": str(exc)})
                log.error("%s: błąd %s dla „%s”", source.NAME, exc, query)

    result = {
        "meta": {
            "rozpoczeto": started.isoformat(),
            "zakonczono": datetime.now(timezone.utc).isoformat(),
            "zapytania": queries,
            "zrodla": sorted(sources_used),
            "allegro_zablokowane": primary_blocked,
            "liczba_ofert": len(offers),
            "bledy": errors,
        },
        "oferty": offers,
    }
    save_json(result, output or config.LAST_SCAN_FILE)
    log.info("Skan zakończony: %d ofert, źródła: %s", len(offers), ", ".join(sorted(sources_used)) or "brak")
    return result


def save_json(data: dict[str, Any], path: Path) -> None:
    """Zapis atomowy — endpoint Flask nigdy nie przeczyta połowy pliku."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".scan-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Skraper Allegro z fallbackiem na Ceneo i Morele")
    parser.add_argument("queries", nargs="*", help="zapytania (domyślnie z env QUERIES)")
    parser.add_argument("--loop", action="store_true", help="skanuj w pętli co SCAN_INTERVAL sekund")
    parser.add_argument("--limit", type=int, default=None, help="maks. ofert na zapytanie i źródło")
    parser.add_argument("--reset-cookies", action="store_true", help="wyczyść cookies i wylosuj nowy UA")
    args = parser.parse_args(argv)

    setup_logging(config.LOG_DIR)
    queries = args.queries or config.QUERIES
    client = build_client()

    if args.reset_cookies:
        client.reset()
        if not args.queries and not args.loop:
            return 0

    if not args.loop:
        run_scan(queries, client=client, limit=args.limit)
        return 0

    while True:
        try:
            run_scan(queries, client=client, limit=args.limit)
        except Exception:  # pętla ma przetrwać każdy pojedynczy błąd
            log.exception("Nieoczekiwany błąd skanu")
        # Rozrzut ±10%, żeby skany nie startowały co do sekundy regularnie.
        pause = config.SCAN_INTERVAL * random.uniform(0.9, 1.1)
        log.info("Następny skan za %.0f s", pause)
        time.sleep(pause)


if __name__ == "__main__":
    raise SystemExit(main())
