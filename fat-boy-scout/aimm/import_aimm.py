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
import tempfile
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
FBS = HERE.parent
sys.path.insert(0, str(FBS))
import geo  # noqa: E402
import scout  # noqa: E402

LISTING_KEY = "listing-details"
DEFAULT_MAX_AGE_DAYS = 3
NEG_RE = re.compile(r"\b(no|not|never|non|without|isn'?t)\b[^.!?\n]{0,20}$", re.I)
DISTANCE_CTX_RE = re.compile(r"(within|deliver\w*|away|radius|trip|haul|from|ride to|drive)\W*(?:\w+\W*){0,2}$", re.I)
SENTENCE_RE = re.compile(r"[^.!?\n]*(?:fat\s*boy|fatboy|flfbs?|\b114\b|\b107\b|\b117\b|milwaukee[- ]eight)[^.!?\n]*", re.I)


def _store_time(c, key) -> float | None:
    """Kiedy aimm zapisał wpis (kolumna store_time w diskcache). None, gdy nie da się odczytać."""
    try:
        db_key, raw = c._disk.put(key)
        row = c._sql("SELECT store_time FROM Cache WHERE key = ? AND raw = ?", (db_key, raw)).fetchone()
        return float(row[0]) if row else None
    except Exception:
        return None


def read_cache(home: Path, max_age_days: float | None = DEFAULT_MAX_AGE_DAYS) -> tuple[list[dict], dict]:
    """Ogłoszenia z pamięci aimm. Pomija wpisy starsze niż max_age_days – ogłoszenie zapisane tygodnie temu
    mogło zniknąć, więc nie wolno go pokazywać jako widzianego dziś."""
    try:
        from diskcache import Cache  # type: ignore
    except ImportError:
        sys.exit("Brak biblioteki diskcache – uruchom ten skrypt Pythonem, w którym jest zainstalowane ai-marketplace-monitor.")
    if not home.exists():
        sys.exit(f"Nie ma katalogu aimm: {home}. Uruchom najpierw aimm albo podaj --aimm-home.")
    out, stats = [], {"all": 0, "stale": 0, "unknown_age": 0}
    now = time.time()
    with Cache(str(home)) as c:
        for key in c.iterkeys():
            if not (isinstance(key, tuple) and key and key[0] == LISTING_KEY):
                continue
            v = c.get(key)
            if not isinstance(v, dict):
                continue
            stats["all"] += 1
            st = _store_time(c, key)
            if st is None:
                stats["unknown_age"] += 1
            elif max_age_days is not None and now - st > max_age_days * 86400:
                stats["stale"] += 1
                continue
            out.append(v)
    return out, stats


def parse_price(p: str | None) -> int | None:
    """Pierwsza kwota w napisie aimm. „$9,500 $10,000” (obniżka) → 9500, „$10,500.00” → 10500."""
    if not p:
        return None
    m = re.search(r"\d{1,3}(?:,\d{3})+(?!\d)|\d+", p.replace("\u00a0", ""))
    return scout._num(m.group()) if m else None


def title_status(desc: str) -> str | None:
    """Rodzaj title z opisu. Zaprzeczenia („never salvage”, „not rebuilt”) nie liczą się jako salvage."""
    for m in re.finditer(r"\b(salvage|rebuilt|bonded)\b", desc, re.I):
        if not NEG_RE.search(desc[max(0, m.start() - 30):m.start()]):
            return m.group(1).lower()
    return "clean" if re.search(r"clean\s+(?:\w+\s+)?title", desc, re.I) else None


def year_of(title: str, desc: str) -> int | None:
    """Rocznik z tytułu; z opisu tylko wtedy, gdy stoi tuż przy nazwie modelu („2019 Harley…”, „2020 Fat Boy”)."""
    m = re.search(r"\b(20[12]\d)\b", title)
    if not m:
        m = re.search(r"\b(20[12]\d)\s+(?:harley|h-?d\b|fat\s*boy|fatboy|softail|flfbs?)", desc, re.I)
    return int(m.group(1)) if m else None


def miles_of(title: str, desc: str) -> int | None:
    """Przebieg; pomija odległości („deliver within 100 miles”, „200 miles away”)."""
    for text in (title, desc):
        for m in re.finditer(r"\d[\d,.]*\s?(?:[Kk]|tys\.?)?\s?(?:miles|mi\b)", text):
            before = text[max(0, m.start() - 30):m.start()]
            after = text[m.end():m.end() + 8]
            if DISTANCE_CTX_RE.search(before) or re.match(r"\s*(away|from|radius)", after, re.I):
                continue
            n = scout._miles(m.group())
            if n is not None:
                return n
    return None


def to_fbs(l: dict, today: str) -> dict | None:
    """Jedno ogłoszenie aimm → oferta Fat Boy Scout. None, gdy to na pewno nie Harley."""
    title = (l.get("title") or "").strip()
    desc = (l.get("description") or "").strip()
    text = f"{title} {desc}"
    if not re.search(r"harley|h-d|fat\s*boy|fatboy|flfb|softail", text, re.I):
        return None
    url = (l.get("post_url") or "").split("?")[0]
    if url.startswith("/"):
        url = "https://www.facebook.com" + url
    m = re.search(r"/marketplace/item/(\d+)", url)
    item = m.group(1) if m else (str(l["id"]) if str(l.get("id") or "").isdigit() else None)
    if not item:
        return None   # bez numeru ogłoszenia nie ma ani stabilnego ID, ani linku
    lid = f"fb-{item}"
    if not m:
        url = f"https://www.facebook.com/marketplace/item/{item}/"
    city, state = None, None
    loc = (l.get("location") or "").strip()
    if "," in loc:
        city, st = [x.strip() for x in loc.rsplit(",", 1)]
        state = geo.state_code(st) or st
    year = year_of(title, desc)
    miles = miles_of(title, desc)
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
    ts = title_status(desc)
    if ts:
        rec["title"] = ts
    return rec


def build_run(listings: list[dict], today: str, stats: dict | None = None) -> dict:
    recs, seen = [], set()
    for r in (to_fbs(l, today) for l in listings):
        if r and r["id"] not in seen:
            seen.add(r["id"])
            recs.append(r)
    states = sorted({r["state"] for r in recs if r.get("state")})
    st = stats or {}
    note = (f"Import z ai-marketplace-monitor: {len(listings)} świeżych ogłoszeń w pamięci aimm, {len(recs)} z Harleyem"
            + (f"; pominięto {st['stale']} starszych niż limit wieku" if st.get("stale") else "")
            + (f"; {st['unknown_age']} bez daty zapisu" if st.get("unknown_age") else "") + ". "
            "Dane pochodzą z otwartych ogłoszeń (zalogowana przeglądarka na komputerze użytkownika). "
            "To nie jest pełny skan – oferty, których aimm nie widział, zachowują ostatni status.")
    return {
        # sources_checked puste: pamięć aimm to wycinek wyników, więc brak oferty w imporcie
        # nie może oznaczać, że zniknęła z Marketplace
        "date": today, "run_id": f"{today}-aimm", "sources_checked": [], "partial_import": "aimm",
        "coverage": [note],
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
    ap.add_argument("--dry-run", action="store_true", help="pokaż raport, nic nie zapisuje w fat-boy-scout/")
    ap.add_argument("--max-age-days", type=float, default=DEFAULT_MAX_AGE_DAYS,
                    help=f"pomiń wpisy aimm starsze niż tyle dni (domyślnie {DEFAULT_MAX_AGE_DAYS}; 0 = bez limitu)")
    a = ap.parse_args()
    listings, stats = read_cache(Path(a.aimm_home), a.max_age_days or None)
    run = build_run(listings, a.date, stats)
    if a.dry_run and not a.out:
        out = Path(tempfile.mkdtemp(prefix="fbs-aimm-")) / f"{run['run_id']}.json"
    else:
        out = Path(a.out) if a.out else scout.RUNS_DIR / f"{run['run_id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Zapisano {out} – ofert z Harleyem: {len(run['listings'])}"
          + (f" (pominięto starych wpisów: {stats['stale']})" if stats.get("stale") else ""))
    if a.no_merge:
        return 0
    cmd = [sys.executable, str(FBS / "scout.py"), "run", str(out)] + (["--dry-run"] if a.dry_run else [])
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
