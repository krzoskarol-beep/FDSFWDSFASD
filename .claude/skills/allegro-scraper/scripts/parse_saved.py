"""Parsuje zapisaną stronę wyników (HTML z dysku) parserem skrapera, bez sieci.

Użycie (z katalogu głównego repozytorium):
    python .claude/skills/allegro-scraper/scripts/parse_saved.py strona.html
    python .claude/skills/allegro-scraper/scripts/parse_saved.py strona.html --zrodlo ceneo --limit 5

Wypisuje JSON {"zrodlo", "liczba_ofert", "strategia", "oferty"} na stdout.
Kod wyjścia 2, gdy parser nie znalazł żadnej oferty (sygnał: zmienił się układ strony
albo plik to strona z captchą).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from scraper.http_client import DATADOME_CHALLENGE_MARKERS  # noqa: E402
from scraper.parsers import allegro, ceneo, morele  # noqa: E402
from scraper.parsers.common import dedupe  # noqa: E402

SOURCES = {"allegro": allegro, "ceneo": ceneo, "morele": morele}


def allegro_strategy(html: str) -> str:
    """Która strategia parsera Allegro dała wynik: osadzony JSON, HTML czy JSON-LD."""
    soup = BeautifulSoup(html, "html.parser")
    if dedupe(allegro._from_embedded_json(soup)):
        return "osadzony JSON (data-serialize-box-id)"
    if dedupe(allegro._from_html(soup)):
        return "HTML (<article>)"
    return "JSON-LD albo brak"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plik", type=Path, help="zapisany plik HTML strony wyników")
    ap.add_argument("--zrodlo", choices=sorted(SOURCES), default="allegro")
    ap.add_argument("--limit", type=int, default=None, help="ile ofert wypisać")
    args = ap.parse_args()

    html = args.plik.read_text(encoding="utf-8", errors="replace")
    if any(marker in html for marker in DATADOME_CHALLENGE_MARKERS):
        print("To strona z captchą DataDome, nie lista ofert.", file=sys.stderr)
        return 3

    offers = SOURCES[args.zrodlo].parse(html)
    out = {
        "zrodlo": args.zrodlo,
        "liczba_ofert": len(offers),
        "strategia": allegro_strategy(html) if args.zrodlo == "allegro" else None,
        "oferty": offers[: args.limit] if args.limit else offers,
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if offers else 2


if __name__ == "__main__":
    raise SystemExit(main())
