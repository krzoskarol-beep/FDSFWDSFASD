#!/usr/bin/env python3
"""Import ofert z ai-marketplace-monitor (aimm) do Fat Boy Scout.

aimm otwiera ogłoszenia Facebooka w zalogowanej przeglądarce na Twoim komputerze i zapisuje ich dane
(tytuł, cena, lokalizacja, opis, sprzedawca, zdjęcie, bezpośredni link) w pamięci podręcznej diskcache
(domyślnie ~/.ai-marketplace-monitor). Ten skrypt czyta tę pamięć i składa z niej plik przebiegu Fat Boy Scout,
który silnik scala z historią (spadki cen, ponowne wystawienia, raport).

Użycie (Pythonem, w którym zainstalowane jest aimm – ma on bibliotekę diskcache):
  python fat-boy-scout/aimm/import_aimm.py                    # tworzy runs/<data>-aimm.json i od razu scala
  python fat-boy-scout/aimm/import_aimm.py --dry-run          # tylko pokazuje raport, nic nie zapisuje
  python fat-boy-scout/aimm/import_aimm.py --aimm-home ŚCIEŻKA --out plik.json --no-merge
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
FBS = HERE.parent
sys.path.insert(0, str(FBS))
import geo  # noqa: E402
import scout  # noqa: E402

LISTING_KEY = "listing-details"
SENTENCE_RE = re.compile(r"[^.!?\n]*(?:fat\s*boy|fatboy|flfbs?|\b114\b|\b107\b|\b117\b|milwaukee[- ]eight)[^.!?\n]*", re.I)


def read_cache(home: Path) -> list[dict]:
    try:
        from diskcache import Cache  # type: ignore
    except ImportError:
        sys.exit("Brak biblioteki diskcache – uruchom ten skrypt Pythonem, w którym jest zainstalowane ai-marketplace-monitor.")
    if not home.exists():
        sys.exit(f"Nie ma katalogu aimm: {home}. Uruchom najpierw aimm albo podaj --aimm-home.")
    out = []
    with Cache(str(home)) as c:
        for key in c.iterkeys():
            if isinstance(key, tuple) and key and key[0] == LISTING_KEY:
                v = c.get(key)
                if isinstance(v, dict):
                    out.append(v)
    return out


def parse_price(p: str | None) -> int | None:
    if not p:
        return None
    m = re.search(r"\d[\d,.\s ]*", p)
    if not m:
        return None
    digits = re.sub(r"[^\d]", "", m.group())
    return int(digits) if digits else None


def to_fbs(l: dict, today: str) -> dict | None:
    """Jedno ogłoszenie aimm → oferta Fat Boy Scout. None, gdy to na pewno nie Harley."""
    title = (l.get("title") or "").strip()
    desc = (l.get("description") or "").strip()
    text = f"{title} {desc}"
    if not re.search(r"harley|h-d|fat\s*boy|fatboy|flfb|softail", text, re.I):
        return None
    url = (l.get("post_url") or "").split("?")[0]
    m = re.search(r"/marketplace/item/(\d+)", url)
    lid = f"fb-{m.group(1)}" if m else f"fb-aimm-{l.get('id')}"
    if url.startswith("/"):
        url = "https://www.facebook.com" + url
    city, state = None, None
    loc = (l.get("location") or "").strip()
    if "," in loc:
        city, st = [x.strip() for x in loc.rsplit(",", 1)]
        state = geo.state_code(st) or st
    year = None
    ym = re.search(r"\b(20[12]\d)\b", title) or re.search(r"\b(20[12]\d)\b", desc)
    if ym:
        year = int(ym.group(1))
    miles = scout._miles(desc) or scout._miles(title)
    quotes = [s.strip() for s in SENTENCE_RE.findall(desc) if 8 <= len(s.strip()) <= 220][:2]
    rec = {
        "id": lid, "source": "facebook", "category": "main", "verified": False,
        "model": title or "Harley-Davidson", "listing_title": title, "year": year,
        "price": parse_price(l.get("price")), "miles": miles, "city": city, "state": state, "url": url,
        "seller_name": (l.get("seller") or None), "photo_fingerprint": (l.get("image") or "").split("?")[0] or None,
        "opened_by": "aimm",
        "notes": f"dane z ogłoszenia otwartego przez aimm (zalogowana przeglądarka), import {today}"
                 + (f"; stan: {l.get('condition')}" if l.get("condition") else ""),
    }
    if quotes:
        rec["evidence"] = [{"quote": q, "url": url} for q in quotes]
    if re.search(r"\b(salvage|rebuilt|bonded)\b", desc, re.I):
        rec["title"] = re.search(r"\b(salvage|rebuilt|bonded)\b", desc, re.I).group(1).lower()
    elif re.search(r"clean\s+title", desc, re.I):
        rec["title"] = "clean"
    return rec


def build_run(listings: list[dict], today: str) -> dict:
    recs = [r for r in (to_fbs(l, today) for l in listings) if r]
    states = sorted({r["state"] for r in recs if r.get("state")})
    return {
        "date": today, "run_id": f"{today}-aimm", "sources_checked": ["facebook"],
        "coverage": [f"Import z ai-marketplace-monitor: {len(listings)} ogłoszeń w pamięci aimm, {len(recs)} z Harleyem. "
                     "Dane pochodzą z otwartych ogłoszeń (zalogowana przeglądarka na komputerze użytkownika). "
                     "Pokrycie dotyczy tylko stanów, w których aimm coś znalazł – pozostałe zachowują ostatni status."],
        "queries": [{"q": "aimm: pamięć ai-marketplace-monitor", "origin": "aimm", "source": "facebook", "status": "ok",
                     "results": len(listings), "candidates": [r["id"] for r in recs], "result_states": states}],
        "listings": recs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aimm-home", default=os.environ.get("AIMM_HOME") or str(Path.home() / ".ai-marketplace-monitor"))
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-merge", action="store_true", help="tylko zapisz plik przebiegu, nie scalaj")
    ap.add_argument("--dry-run", action="store_true", help="pokaż raport bez zapisywania stanu")
    a = ap.parse_args()
    run = build_run(read_cache(Path(a.aimm_home)), a.date)
    out = Path(a.out) if a.out else scout.RUNS_DIR / f"{run['run_id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Zapisano {out} – ofert z Harleyem: {len(run['listings'])}")
    if a.no_merge:
        return 0
    cmd = [sys.executable, str(FBS / "scout.py"), "run", str(out)] + (["--dry-run"] if a.dry_run else [])
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
