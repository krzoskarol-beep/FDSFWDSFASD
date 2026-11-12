#!/usr/bin/env python3
"""Fat Boy Scout – deterministyczny silnik raportów.

Agent szuka i weryfikuje ogłoszenia, a potem zapisuje obserwacje z danego przebiegu
w pliku runs/RRRR-MM-DD.json. Ten skrypt:
  * ponownie sprawdza kryteria (cena, region, rocznik, silnik 114, VIN),
  * scala obserwacje z historią w state.json (nowe oferty, spadki cen, zniknięcia),
  * ocenia okazje względem orientacyjnych cen rynkowych i oznacza ryzyka,
  * składa raport w formacie dwóch linii na ofertę i dzieli go na części.

Użycie:
  python3 scout.py run runs/2026-11-19.json [--dry-run]
  python3 scout.py vin 1HD1YLK18JC024906
  python3 scout.py plan
  python3 scout.py status
Tylko biblioteka standardowa.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import geo  # noqa: E402
# FBS_DATA_DIR pozwala uruchomić symulację na osobnych danych (stan, przebiegi, raporty) bez ruszania prawdziwych
DATA = Path(os.environ.get("FBS_DATA_DIR", BASE))
CONFIG_PATH = Path(os.environ.get("FBS_CONFIG", BASE / "config.json"))
STATE_PATH = DATA / "state.json"
REPORTS_DIR = DATA / "reports"
RUNS_DIR = DATA / "runs"

# potwierdzenie modelu: tytuł, kod modelu albo cytat z opisu ogłoszenia
MODEL_RE = re.compile(r"fat\s*boy|fatboy|\bflfbs?\b", re.I)
OTHER_MODEL_RE = re.compile(r"\b(?:fat\s*bob|street\s*bob|softail\s+(?:slim|standard|deluxe)|heritage|breakout|low\s*rider|"
                            r"sport\s*glide|fxbbs?|fxst|flsl|flhcs?|fxbrs?|fxlrs?|flsb|fxfbs?)\b", re.I)
DIRECT_LINK_RE = re.compile(r"facebook\.com/marketplace/item/\d+|cycletrader\.com/listing/")

TITLE_BAD = ("salvage", "rebuilt", "rebuild", "flood", "lemon", "bonded", "no title", "parts only")
SCAM_WORDS = ("shipping only", "deposit", "zelle", "gift card", "out of state", "ebay motors protection",
              "military", "deployed", "escrow")


# ---------------------------------------------------------------- utils
def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fmt_int(n) -> str:
    """12 345 – format polski z twardą spacją jako separatorem tysięcy."""
    return f"{int(round(n)):,}".replace(",", " ")


def fmt_price(p) -> str:
    return f"{fmt_int(p)} USD" if p is not None else "cena: brak danych"


def fmt_miles(m) -> str:
    return f"{fmt_int(m)} mi" if m is not None else "przebieg: brak danych"


def pl_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


# ---------------------------------------------------------------- model / VIN
def decode_vin(vin: str | None, config: dict) -> dict | None:
    if not vin:
        return None
    vin = vin.strip().upper()
    if len(vin) != 17 or not vin.startswith(("1HD", "5HD")):
        return None
    info = config["vin_model_codes"].get(vin[4:6])
    if not info:
        return {"code": vin[4:6], "known": False}
    out = dict(info, known=True)
    year_chars = "ABCDEFGHJKLMNPRSTVWXY123456789"
    yc = vin[9]
    if yc in year_chars:
        idx = year_chars.index(yc)
        # cykl 30 lat; wybierz rok >= 2010 (A=2010)
        out["year"] = 2010 + idx
    return out


def evidence_text(listing: dict) -> str:
    """Dosłowne cytaty z opisu ogłoszenia zapisane przez agenta (pole evidence)."""
    ev = listing.get("evidence") or []
    if isinstance(ev, str):
        return ev
    return " ".join(str(e.get("quote", "")) if isinstance(e, dict) else str(e) for e in ev)


def model_text(listing: dict) -> str:
    # listing_title = tytuł ogłoszenia (np. „2018 Harley Softail”); pole title to stan dokumentu (clean/salvage)
    return f"{listing.get('model') or ''} {listing.get('code') or ''} {listing.get('listing_title') or ''} {evidence_text(listing)}"


def family(listing: dict) -> str | None:
    """Rodzina modelu używana do kryteriów i cen referencyjnych."""
    text = model_text(listing).lower()
    if "challenger" in text:
        return "Indian Challenger"
    if "africa twin" in text or "crf1000" in text or "crf1100" in text:
        return "Africa Twin"
    if "gold wing" in text or "goldwing" in text or "gl1800" in text:
        return "Gold Wing"
    if re.search(r"fat\s*boy|fatboy|flfb", text):
        return "Fat Boy 114" if engine_of(listing) == "114" else "Fat Boy"
    if re.search(r"fat\s*bob|fxfb", text):
        return "Fat Bob 114" if engine_of(listing) == "114" else "Fat Bob"
    return None


def engine_of(listing: dict) -> str | None:
    if listing.get("engine"):
        return str(listing["engine"])
    text = model_text(listing).upper()
    if "FLFBS" in text or "FXFBS" in text or re.search(r"\b114\b", text):
        return "114"
    if re.search(r"\bFLFB\b|\bFXFB\b|\b107\b", text):
        return "107"
    if re.search(r"FAT\s*BOY|FATBOY", text):
        # FLFB (107) w USA: 2018–2019; w 2020 dokumentacja H-D wymienia jeszcze oba kody, więc 2020 bez kodu = do potwierdzenia.
        # 2021–2024 to wyłącznie FLFBS 114, od 2025 – 117.
        y = listing.get("year")
        if y and 2021 <= y <= 2024:
            return "114"
        if y and y >= 2025:
            return "117"
    return None


def normalize(listing: dict, config: dict) -> dict:
    l = dict(listing)
    l["state"] = (l.get("state") or "").upper().strip() or None
    v = decode_vin(l.get("vin"), config)
    if v and v.get("known"):
        l["engine"] = v["engine"]
        l.setdefault("code", v["code"])
        l["vin_check"] = f"VIN {v['code']} = {v['model']}"
    elif not l.get("engine"):
        e = engine_of(l)
        if e:
            l["engine"] = e
    l["family"] = family(l)
    vin_fat_boy = bool(v and v.get("known") and "Fat Boy" in v.get("model", ""))
    l["model_confirmed"] = bool(MODEL_RE.search(model_text(l))) or vin_fat_boy
    l.pop("model_provisional", None)
    if l["family"] is None and l.get("basis") and not OTHER_MODEL_RE.search(evidence_text(l)):
        # szeroki tytuł („2018 Harley Softail”) + konkretna podstawa (np. pełne koła Lakester w opisie) → do sprawdzenia
        l["family"] = "Fat Boy"
        l["model_provisional"] = True
    if l.get("state") and len(l["state"]) > 2:
        l["state"] = geo.state_code(l["state"]) or l["state"]
    if l.get("distance_mi") is None:
        city = (l.get("city") or "").lower()
        metro = l.get("state") == "IL" and city in config.get("metro_cities", [])
        est = geo.estimate_road_miles(l.get("state"), metro)
        if est is not None:
            l["distance_est"] = est
    return l


# ---------------------------------------------------------------- kryteria
def eligibility(l: dict, config: dict) -> tuple[bool, str]:
    if l.get("active") is False:
        return False, "nieaktywne (sprzedane/usunięte)"
    if l.get("is_part") or l.get("is_payment"):
        return False, "część/rata/zaliczka"
    price = l.get("price")
    if price is not None and price > config["max_price_usd"]:
        return False, f"cena > {fmt_int(config['max_price_usd'])} USD"
    allowed = config["us_states"] if config.get("scope") == "usa" else config["states_priority"]
    if l.get("state") not in allowed:
        return False, f"poza regionem ({l.get('state') or 'stan nieznany'})"
    cat = l.get("category")
    rules = config["categories"].get(cat)
    if not rules:
        return False, f"nieznana kategoria {cat!r}"
    year = l.get("year")
    # Nazwa „Fat Boy 114”/„Fat Bob 114” istnieje dopiero od rocznika 2018, więc brak rocznika nie dyskwalifikuje
    implied_2018 = l.get("family") in ("Fat Boy 114", "Fat Bob 114")
    if rules.get("min_year"):
        if year is None and not implied_2018:
            return False, "rocznik nieznany"
        if year is not None and year < rules["min_year"]:
            return False, f"rocznik < {rules['min_year']}"
    if cat == "main":
        excluded = rules.get("exclude_engines", ["107", "117"])
        if l.get("engine") in excluded:
            return False, f"wersja {l['engine']}"
        if rules.get("max_miles") and l.get("miles") is not None and l["miles"] > rules["max_miles"]:
            return False, f"przebieg > {fmt_int(rules['max_miles'])} mi"
        families = rules.get("families", ["Fat Boy 114", "Fat Bob 114", "Fat Boy", "Fat Bob"])
        if l.get("family") is None and not OTHER_MODEL_RE.search(model_text(l)) and \
                re.search(r"softail|harley", model_text(l), re.I):
            # sam tytuł „Softail” nie wystarcza – zachowujemy trop do dalszego wyszukania
            return False, "trop: szerokie trafienie bez potwierdzenia modelu Fat Boy"
        if l.get("family") not in families:
            return False, f"inny model (szukamy: {rules['label']})"
    if cat == "challenger" and l.get("family") != "Indian Challenger":
        return False, "inny model"
    if cat == "honda-deal":
        if l.get("family") not in ("Africa Twin", "Gold Wing"):
            return False, "inny model"
        s = score(l, config)
        if not l.get("deal") and (s["discount"] is None or s["discount"] < config["deal_thresholds"]["okazja"]):
            return False, "Honda bez wyjątkowej ceny"
    # brak ceny sprawdzamy na końcu: „brak ceny” oznacza, że wszystkie znane kryteria są spełnione
    if price is None:
        return False, "brak ceny"
    if price <= config["placeholder_price_max"]:
        return False, f"cena-wypełniacz ({fmt_price(price)})"
    return True, "ok"


def is_direct_link(url: str | None) -> bool:
    return bool(url and DIRECT_LINK_RE.search(url))


def missing_info(l: dict, config: dict) -> tuple[list[str], list[str]]:
    """(ustalono, brakuje) – dla sekcji „Do sprawdzenia” i dla decyzji, czy oferta jest w pełni potwierdzona."""
    known, missing = [], []
    ev = evidence_text(l)
    if l.get("model_provisional"):
        missing.append("potwierdzenie modelu Fat Boy (tytuł jest ogólny)")
        known.append(f"podstawa: {l.get('basis')}")
    elif l.get("model_confirmed"):
        src = "VIN" if l.get("vin_check") else ("opis ogłoszenia" if MODEL_RE.search(ev) else "tytuł")
        known.append(f"model Fat Boy ({src})")
    if l.get("engine") in ("114", "117"):
        known.append(f"silnik {l['engine']}" + (" (opis)" if re.search(r"114|117|flfbs", ev, re.I) else ""))
    else:
        missing.append("potwierdzenie silnika 114 (rocznik 2018–2020 mógł mieć 107)")
    if l.get("year"):
        known.append(f"rocznik {l['year']}")
    else:
        missing.append("rocznik")
    price = l.get("price")
    if price is None or price <= config["placeholder_price_max"]:
        missing.append("cena")
    else:
        known.append(f"cena {fmt_price(price)}")
    rules = config["categories"].get(l.get("category") or "main", {})
    if l.get("miles") is None:
        missing.append(f"przebieg (limit {fmt_int(rules.get('max_miles', 0))} mi)" if rules.get("max_miles") else "przebieg")
    else:
        known.append(f"przebieg {fmt_miles(l['miles'])}")
    if l.get("state"):
        known.append(", ".join(x for x in (l.get("city"), l.get("state")) if x))
    if not is_direct_link(l.get("url")):
        missing.append("bezpośredni link (jest tylko strona wyników)")
    return known, missing


# ---------------------------------------------------------------- ocena okazji
def reference_price(l: dict, config: dict) -> int | None:
    fam = l.get("family")
    if fam in ("Fat Boy", "Fat Bob"):  # silnik niepotwierdzony – zakładamy 114
        fam += " 114"
    table = config["market_reference"].get(fam or "")
    year = l.get("year")
    if not table or not year:
        return None
    years = sorted(int(y) for y in table)
    nearest = min(years, key=lambda y: abs(y - year))
    return table[str(nearest)]


def score(l: dict, config: dict) -> dict:
    ref = reference_price(l, config)
    flags: list[str] = []
    title = (l.get("title") or "").lower()
    if any(w in title for w in TITLE_BAD):
        flags.append(f"title: {l.get('title')}")
    notes = (l.get("notes") or "").lower()
    if any(w in notes for w in SCAM_WORDS):
        flags.append("sygnały oszustwa w opisie")
    if l.get("category") == "main" and l.get("engine") is None:
        flags.append("114 niepotwierdzone")
    if l.get("category") == "main" and l.get("miles") is None:
        flags.append("przebieg do ustalenia")
    if l.get("category") == "main" and not l.get("year"):
        flags.append("rocznik nieznany (nazwa 114 oznacza 2018+)")
    if l.get("fees"):
        flags.append(f"dopłaty dealera: {l['fees']}")
    if ref is None or l.get("price") is None:
        return {"ref": ref, "discount": None, "label": "brak oceny", "flags": flags}
    price = l["price"]
    discount = (ref - price) / ref
    miles, year = l.get("miles"), l.get("year")
    if miles is not None and year:
        age = max(1, date.today().year - year)
        expected = age * config["expected_miles_per_year"]
        adj = max(-0.10, min(0.10, (expected - miles) / expected * 0.10))
        discount += adj
    if flags and any(f.startswith("title:") for f in flags):
        discount -= 0.25
    th = config["deal_thresholds"]
    if (ref - price) / ref >= th["podejrzanie_tanio"]:
        flags.append("podejrzanie tanio – sprawdź, czy to nie oszustwo")
    if discount >= th["okazja"]:
        label = "OKAZJA"
    elif discount >= th["dobra_cena"]:
        label = "dobra cena"
    elif discount >= th["drogo"]:
        label = "cena rynkowa"
    else:
        label = "drogo"
    return {"ref": ref, "discount": discount, "label": label, "flags": flags}


# ---------------------------------------------------------------- ranking: cena + przebieg
def effective_price(l: dict, config: dict) -> float | None:
    """Cena „efektywna”: cena ogłoszenia + koszt przebiegu (domyślnie 0,10 USD za milę)."""
    if l.get("price") is None or l.get("miles") is None:
        return None
    return l["price"] + config.get("ranking", {}).get("usd_per_mile", 0.10) * l["miles"]


def distance_of(l: dict) -> tuple[int | None, bool]:
    """(mile, czy_szacunek): odległość od Des Plaines – podana przez agenta albo oszacowana ze środka stanu."""
    if l.get("distance_mi") is not None:
        # dokładna tylko z serwisu (Cycle Trader podaje „X mi away”); odległość wpisana przez agenta to szacunek
        return int(l["distance_mi"]), l.get("source") != "cycletrader"
    if l.get("distance_est") is not None:
        return int(l["distance_est"]), True
    return None, True


def transport_cost(l: dict, config: dict) -> float:
    t = config.get("ranking", {}).get("transport", {})
    d, _ = distance_of(l)
    if not t or d is None or d <= t.get("free_within_mi", 0):
        return 0.0
    return max(t.get("min_usd", 0), t.get("usd_per_mile", 0.6) * d)


def total_cost(l: dict, config: dict) -> float | None:
    """Koszt całkowity = cena + koszt przebiegu + szacunkowy dowóz do Des Plaines."""
    eff = effective_price(l, config)
    return None if eff is None else eff + transport_cost(l, config)


def rank_key(l: dict, config: dict) -> tuple:
    tot = total_cost(l, config)
    # najpierw oferty ze znanym przebiegiem (wg kosztu całkowitego), potem bez przebiegu (wg ceny + dowóz)
    if tot is not None:
        return (0, tot)
    return (1, (l.get("price") or 0) + transport_cost(l, config))


# ---------------------------------------------------------------- region
def region_key(l: dict, config: dict) -> tuple:
    st = l.get("state")
    prio = config["states_priority"]
    city = (l.get("city") or "").lower()
    dist, _ = distance_of(l)
    metro = (st == "IL") and (city in config["metro_cities"] or (dist is not None and dist <= config["metro_radius_mi"]))
    if config.get("scope") == "usa":
        # najpierw Des Plaines/Chicago, potem stany priorytetowe, potem reszta kraju; w grupie według odległości
        group = 0 if metro else (1 if st in prio else 2)
        return (group, dist if dist is not None else 9999, l.get("price") or 0)
    state_rank = prio.index(st) + 1 if st in prio else 99
    return (0 if metro else state_rank, dist if dist is not None else 9999, l.get("price") or 0)


# ---------------------------------------------------------------- stan
def empty_state() -> dict:
    return {"version": 2, "runs": [], "listings": {}, "rejected": {}}


def migrate(state: dict | None) -> dict:
    if not state:
        return empty_state()
    if state.get("version") == 2:
        return state
    new = empty_state()
    if state.get("last_report"):
        new["runs"].append(state["last_report"])
    for s in state.get("shown", []):
        hist = s.get("price_history", [])
        city, _, st = (s.get("location") or "").partition(",")
        year = int(m.group()) if (m := re.match(r"\d{4}", s.get("model", ""))) else None
        new["listings"][s["id"]] = {
            "id": s["id"], "source": s.get("source", "cycletrader"), "category": s.get("category", "main"),
            "model": s.get("model"), "year": year, "price": hist[-1]["price"] if hist else None,
            "miles": s.get("miles"), "city": city.strip() or None, "state": st.strip() or None,
            "title": s.get("title"), "seller": s.get("seller"), "url": s.get("url"), "notes": s.get("notes"),
            "verified": True, "price_history": hist, "first_seen": s.get("first_seen"),
            "last_seen": s.get("last_seen"), "status": s.get("status", "active"), "shown": True,
        }
    for f in state.get("facebook_unverified", []):
        city, _, st = (f.get("location") or "").partition(",")
        year = int(m.group()) if (m := re.match(r"\d{4}", f.get("model", ""))) else None
        d = f.get("first_seen")
        new["listings"][f["id"]] = {
            "id": f["id"], "source": "facebook", "category": "challenger" if "Challenger" in f.get("model", "") else "main",
            "model": f.get("model"), "year": year, "price": f.get("price"), "miles": f.get("miles"),
            "city": city.strip() or None, "state": (st.strip()[:2] or None) if st else None, "url": f.get("url"),
            "notes": f.get("note"), "verified": False,
            "price_history": [{"date": d, "price": f["price"]}] if f.get("price") else [],
            "first_seen": d, "last_seen": d, "status": "active", "shown": True,
        }
    for r in state.get("rejected", []):
        new["rejected"][r["id"]] = {k: v for k, v in r.items()}
    return new


def _norm_mods(mods) -> set:
    if not mods:
        return set()
    if isinstance(mods, str):
        mods = re.split(r"[,;/]| and ", mods)
    return {re.sub(r"[^a-z0-9]+", " ", m.lower()).strip() for m in mods if m and m.strip()}


def same_bike(new: dict, old: dict, config: dict) -> tuple[str, list[str]] | None:
    """Czy dwa ogłoszenia to ten sam motocykl? ('vin'|'prawdopodobnie', powody) albo None.
    Identyczny pełny VIN = pewność. Bez VIN-u co najmniej N zgodnych cech charakterystycznych.
    Sam rocznik, kolor albo zdjęcie katalogowe nigdy nie wystarczają."""
    rl = config.get("relist", {})
    v1, v2 = (new.get("vin") or "").strip().upper(), (old.get("vin") or "").strip().upper()
    if len(v1) == 17 and len(v2) == 17:
        return ("vin", [f"identyczny VIN {v1}"]) if v1 == v2 else None   # różne VIN-y = różne motocykle
    if new.get("year") and old.get("year") and new["year"] != old["year"]:
        return None
    feats = []
    p1, p2 = new.get("photo_fingerprint"), old.get("photo_fingerprint")
    if p1 and p2 and p1 == p2 and not new.get("photo_is_stock") and not old.get("photo_is_stock"):
        feats.append("te same charakterystyczne zdjęcia")
    s1, s2 = (new.get("seller_name") or "").strip().lower(), (old.get("seller_name") or "").strip().lower()
    if s1 and s1 == s2:
        feats.append(f"ten sam sprzedawca ({new.get('seller_name')})")
    if new.get("city") and old.get("city") and new["city"].lower() == old["city"].lower() and new.get("state") == old.get("state"):
        feats.append(f"ta sama miejscowość ({new['city']}, {new.get('state')})")
    m1, m2 = new.get("miles"), old.get("miles")
    if m1 is not None and m2 is not None:
        tol = rl.get("miles_tolerance_pct", 5) / 100 * max(m2, 1000)
        if m2 - tol <= m1 <= m2 + rl.get("miles_max_increase", 1500):
            feats.append(f"zgodny przebieg ({fmt_miles(m2)} → {fmt_miles(m1)})")
    shared = _norm_mods(new.get("mods")) & _norm_mods(old.get("mods"))
    if shared:
        feats.append("te same modyfikacje: " + ", ".join(sorted(shared)))
    if len(feats) >= rl.get("min_features", 3):
        return "prawdopodobnie", feats
    return None


def find_same_bike(l: dict, state: dict, config: dict):
    """Szuka w całej historii (aktywne, wygasłe, odrzucone – także powyżej limitu). Zwraca (rekord, magazyn, rodzaj, powody)."""
    best = None
    for store in ("listings", "rejected"):
        for rid, rec in state.get(store, {}).items():
            if rid == l["id"]:
                continue
            m = same_bike(l, rec, config)
            if m and (best is None or m[0] == "vin" or len(m[1]) > len(best[3])):
                best = (rec, store, m[0], m[1])
                if m[0] == "vin":
                    return best
    return best


def _add_price(rec: dict, price, today: str, run_key: str) -> None:
    """Dopisuje obserwację ceny. Ten sam przebieg nie dopisze drugi raz (wznowienie, ponowne scalanie)."""
    if price is None:
        return
    hist = rec.setdefault("price_history", [])
    if any(h.get("run") == run_key for h in hist):
        return
    if hist and hist[-1].get("price") == price:
        hist[-1]["last_seen"] = today
        return
    hist.append({"date": today, "price": price, "run": run_key})


def _urls(*recs) -> list[str]:
    out: list[str] = []
    for r in recs:
        if not r:
            continue
        for u in (r.get("urls") or []) + [r.get("url")]:
            if u and u not in out:
                out.append(u)
    return out


def merge(state: dict, run: dict, config: dict) -> tuple[dict, dict]:
    """Zwraca (nowy_stan, diff). Scala obserwacje z historią, łączy ponownie wystawione motocykle,
    wykrywa spadki cen (także z ceny powyżej limitu), liczy pokrycie stanów i zniknięcia."""
    today = run["date"]
    run_key = run.get("run_id") or today
    first = not state["runs"]
    diff = {"new": [], "drops": [], "gone": [], "active": [], "unverified_new": [], "unverified_all": [],
            "rejected_now": [], "relists": [], "leads_new": [], "first": first}
    seen_ids, eligible_ids = set(), set()
    checked = set(run.get("sources_checked", []))
    si = config.get("self_improve", {})
    qlist = run.get("queries", [])
    ok_q = [q for q in qlist if q.get("status", "ok") != "error" and int(q.get("results", 0)) > 0]
    scan_ok = not qlist or (len(ok_q) >= 3 and len(ok_q) >= len([q for q in qlist if q.get("status") != "error"]) / 2)
    diff["scan_ok"] = scan_ok
    aliases = state.setdefault("aliases", {})
    state.setdefault("leads", {})
    wl = state.setdefault("watchlist", {})
    diff["watch_new"] = []
    max_price = config["max_price_usd"]

    observed_states: dict[str, dict] = {}
    for raw in run.get("listings", []):
        if raw.get("is_payment"):
            w = {k: raw.get(k) for k in ("id", "model", "miles", "city", "state", "url", "year")}
            w["note"] = f"kwota w ogłoszeniu to rata/zaliczka ({fmt_price(raw.get('price'))}), cena całkowita nieznana"
            run.setdefault("watchlist_unpriced", []).append(w)
            continue
        l = normalize(raw, config)
        orig_id = l["id"]
        lid = aliases.get(orig_id, orig_id)
        l["id"] = lid
        if lid in seen_ids:
            continue  # ta sama sztuka już przetworzona w tym przebiegu (np. wpis zdublowany przy wznowieniu)
        seen_ids.add(lid)
        st_rec = observed_states.setdefault(l.get("state") or "?", {"seen": 0, "match": 0})
        st_rec["seen"] += 1

        prev_store = "listings" if lid in state["listings"] else ("rejected" if lid in state["rejected"] else None)
        prev = state[prev_store][lid] if prev_store else None
        relist = None
        if prev is None:
            hit = find_same_bike(l, state, config)
            if hit:
                rec, store, kind, reasons = hit
                relist = {"kind": kind, "reasons": reasons, "previous_id": rec["id"], "previous_url": rec.get("url"),
                          "new_id": orig_id, "new_url": l.get("url"), "date": today}
                aliases[orig_id] = rec["id"]
                lid = l["id"] = rec["id"]
                prev, prev_store = rec, store
                seen_ids.add(lid)

        ok, reason = eligibility(l, config)
        if not ok and reason.startswith("trop:"):
            lead = state["leads"].get(orig_id)
            state["leads"][orig_id] = dict(l, id=orig_id, reason=reason, first_seen=(lead or {}).get("first_seen", today),
                                           last_seen=today)
            if not lead:
                diff["leads_new"].append(state["leads"][orig_id])
            continue
        if not ok and (reason == "brak ceny" or reason.startswith("cena-wypełniacz")):
            # pasujący model bez (prawdziwej) ceny → „Do sprawdzenia”, nie odrzucamy
            w = wl.get(lid)
            wl[lid] = dict(w or {}, **{k: v for k, v in l.items() if v is not None},
                           note=l.get("notes") or reason, first_seen=(w or {}).get("first_seen", today), last_seen=today)
            if not w:
                diff["watch_new"].append(wl[lid])
            continue

        hist_before = list((prev or {}).get("price_history") or [])
        last = hist_before[-1] if hist_before else None
        if not ok:
            if prev_store == "listings" and prev.get("status") == "active":
                prev["status"] = "gone" if l.get("active") is False else "dropped"
                prev["status_reason"] = reason
                prev["last_seen"] = today
                diff["gone"].append(prev)
            old = state["rejected"].get(lid) or (prev if prev_store == "listings" else None) or {}
            rec = {**old, **{k: v for k, v in l.items() if v is not None}, "id": lid, "reason": reason, "date": today,
                   "location": ", ".join(x for x in (l.get("city"), l.get("state")) if x) or "lokalizacja: brak danych",
                   "urls": _urls(old, l), "price_history": list(old.get("price_history") or [])}
            _add_price(rec, l.get("price"), today, run_key)   # cena zapamiętana także powyżej limitu
            if relist:
                rec["relist"] = relist
            state["rejected"][lid] = rec
            if prev_store != "listings":
                diff["rejected_now"].append(rec)
            continue

        st_rec["match"] += 1
        eligible_ids.add(lid)
        l["score"] = score(l, config)
        l["missing_runs"] = 0
        base = prev or {}
        merged = {**base, **{k: v for k, v in l.items() if v is not None}, "id": lid,
                  "urls": _urls(base, l), "url": l.get("url") or base.get("url"),
                  "price_history": hist_before, "last_seen": today, "status": "active",
                  "first_seen": base.get("first_seen") or today}
        for k in ("status_reason", "reason", "old_price", "old_date", "into_limit", "dup_of"):
            merged.pop(k, None)
        merged["verified"] = bool(base.get("verified")) or bool(l.get("verified", True))
        _add_price(merged, l["price"], today, run_key)
        if relist:
            merged["relist"] = relist
            diff["relists"].append(merged)
        if prev_store == "rejected":
            state["rejected"].pop(lid, None)
        state["listings"][lid] = merged
        if last and l["price"] < last["price"] and last.get("run") != run_key:
            merged.update(old_price=last["price"], old_date=last.get("last_seen") or last.get("date"),
                          into_limit=last["price"] > max_price)
            diff["drops"].append(merged)
        elif prev is None or prev_store == "rejected" or base.get("status") != "active":
            (diff["new"] if merged.get("verified", True) else diff["unverified_new"]).append(merged)
        elif base.get("verified") is False and merged["verified"]:
            diff["new"].append(merged)
        (diff["active"] if merged.get("verified", True) else diff["unverified_all"]).append(merged)

    cov = coverage(run, config, observed_states)
    diff["coverage"] = cov
    covered = {s for s, c in cov["states"].items() if c["status"] in ("found", "zero")}
    for lid, l in state["listings"].items():
        if lid in seen_ids or l.get("status") != "active":
            continue
        if l.get("source") not in checked:
            continue
        if l.get("state") and l["state"] not in covered:
            l["region_note"] = f"region nie sprawdzony w przebiegu {run_key} – ostatni znany status z {pl_date(l['last_seen'])}"
            (diff["active"] if l.get("verified", True) else diff["unverified_all"]).append(l)
            continue
        l.pop("region_note", None)
        if l.get("verified", True):
            l["status"] = "gone"
            l["status_reason"] = "nie ma jej już w wynikach"
            diff["gone"].append(l)
            continue
        if not scan_ok:
            (diff["unverified_all"]).append(l)
            continue
        if l.get("last_missing_run") != run_key:
            l["missing_runs"] = l.get("missing_runs", 0) + 1
            l["last_missing_run"] = run_key
        limit = si.get("gone_after_missing_runs", 3)
        if l["missing_runs"] >= limit:
            l["status"] = "gone"
            l["status_reason"] = (f"niewidziana od {pl_date(l['last_seen'])} ({limit} udane skany bez niej) – "
                                  "to nie musi znaczyć, że jest sprzedana")
            diff["gone"].append(l)
        else:
            diff["unverified_all"].append(l)   # nadal pokazywana – ostatni znany status

    for w in run.get("watchlist_unpriced", []):
        wid = aliases.get(w["id"], w["id"])
        if wid not in wl:
            wl[wid] = dict(w, id=wid, first_seen=today)
            diff["watch_new"].append(wl[wid])
        wl[wid]["last_seen"] = today
    for wid in list(wl):
        if wid in state["listings"] and state["listings"][wid].get("status") == "active":
            wl.pop(wid)   # dostała cenę i pasuje – jest już na liście ofert

    mark_duplicates([l for l in state["listings"].values() if l.get("status") == "active"])

    # statystyki zapytań – liczą się trafienia UNIKALNE
    qs = state.setdefault("query_stats", {})
    found_by: dict[str, int] = {}
    for q in qlist:
        for c in {aliases.get(c, c) for c in q.get("candidates", [])} & eligible_ids:
            found_by[c] = found_by.get(c, 0) + 1
    for q in qlist:
        if q.get("status") == "error":
            continue
        rec = qs.setdefault(q["q"], {"runs": 0, "results": 0, "match_hits": 0, "zero_streak": 0,
                                     "origin": q.get("origin", "config"), "first_run": today})
        if rec.get("last_run_id") == run_key:
            continue
        cand = {aliases.get(c, c) for c in q.get("candidates", [])}
        m = len(cand & eligible_ids)
        u = sum(1 for c in cand & eligible_ids if found_by.get(c) == 1)
        rec["runs"] += 1
        rec["results"] += int(q.get("results", 0))
        rec["match_hits"] += m
        rec["unique_hits"] = rec.get("unique_hits", 0) + u
        rec["zero_streak"] = 0 if u else rec["zero_streak"] + 1
        rec["last_matches"] = m
        diff.setdefault("query_matches", {})[q["q"]] = m
        rec["last_run"] = today
        rec["last_run_id"] = run_key
        if q.get("origin"):
            rec["origin"] = q["origin"]
    diff["queries"] = qlist
    diff["credits"] = run.get("credits_used")

    diff["watch_all"] = [w for w in wl.values() if w.get("status", "active") == "active"]
    diff["leads_all"] = list(state["leads"].values())
    if run_key not in state["runs"]:
        state["runs"].append(run_key)
    state["last_run_date"] = today
    return state, diff


# ---------------------------------------------------------------- pokrycie stanów
def query_states(q: dict, config: dict) -> list[str] | None:
    """Stany, których dotyczy zapytanie; None = zapytanie ogólnokrajowe."""
    if q.get("states"):
        return [geo.state_code(s) or s for s in q["states"]]
    for p in config["searches"].get("facebook_index", []):
        if isinstance(p, dict) and p.get("q") == q.get("q") and p.get("states"):
            return [geo.state_code(s) or s for s in p["states"]]
    return None


def coverage(run: dict, config: dict, observed: dict | None = None) -> dict:
    """Status każdego stanu: found (znaleziono oferty), zero (sprawdzono, zero trafień), error (błąd/blokada),
    unchecked (jeszcze nie sprawdzono). Stan liczy się jako sprawdzony tylko wtedy, gdy wyniki źródła
    faktycznie go zawierały albo zapytanie dotyczyło wyłącznie tego stanu – samo wpisanie stanu
    do zapytania grupowego nie wystarcza."""
    observed = observed or {}
    states = config.get("us_states", [])
    seen_in_results: set[str] = set()
    errors: dict[str, list[str]] = {}
    grouped_only: set[str] = set()
    single_ok: set[str] = set()
    for q in run.get("queries", []):
        qs = query_states(q, config)
        if q.get("status") == "error":
            for s in (qs or ["*"]):
                errors.setdefault(s, []).append(q.get("error") or "błąd")
            continue
        rs = {geo.state_code(s) or s for s in q.get("result_states", [])}
        seen_in_results |= rs
        if qs and len(qs) == 1 and int(q.get("results", 0)) >= 0:
            single_ok.add(qs[0])
        elif qs:
            grouped_only |= set(qs) - rs
    out = {}
    for s in states:
        o = observed.get(s, {"seen": 0, "match": 0})
        if o["seen"]:
            out[s] = {"status": "found", "seen": o["seen"], "match": o["match"]}
        elif s in seen_in_results or s in single_ok:
            out[s] = {"status": "zero"}
        elif s in errors or "*" in errors:
            out[s] = {"status": "error", "detail": "; ".join(sorted(set(errors.get(s, []) + errors.get("*", []))))}
        else:
            out[s] = {"status": "unchecked", "detail": "było w zapytaniu grupowym, ale wyniki nie zawierały tego stanu"
                      if s in grouped_only else "żadne zakończone zapytanie nie objęło tego stanu"}
    sources = {}
    for src in config.get("sources", ["facebook"]):
        mine = [q for q in run.get("queries", []) if q.get("source", "facebook") == src]
        sources[src] = {"queries": len(mine), "errors": sum(1 for q in mine if q.get("status") == "error"),
                        "with_results": sum(1 for q in mine if q.get("status") != "error" and int(q.get("results", 0)) > 0)}
    return {"states": out, "sources": sources}


# ---------------------------------------------------------------- raport
def offer_lines(l: dict, price_note: str = "") -> str:
    model = l.get("model") or "Model: brak danych"
    if l.get("year") and not str(model).startswith(str(l["year"])):
        model = f"{l['year']} {model}"
    if l.get("code") and l["code"] not in model:
        model += f" ({l['code']})"
    loc = ", ".join(x for x in (l.get("city"), l.get("state")) if x) or "lokalizacja: brak danych"
    title = f"title: {l['title']}" if l.get("title") else "title: brak danych"
    if l.get("seller"):
        title += f" ({'prywatny sprzedawca' if l['seller'] == 'private' else 'dealer'})"
    line1 = f"{model} | {fmt_price(l.get('price'))}{price_note} | {fmt_miles(l.get('miles'))} | {loc} | {title}"
    return f"{line1}\n{l.get('url') or 'link: brak'}"


def score_line(l: dict, config: dict | None = None) -> str | None:
    s = l.get("score") or {}
    parts = []
    if config is not None:
        d, est = distance_of(l)
        if d is not None:
            tc = transport_cost(l, config)
            parts.append(f"{'~' if est else ''}{fmt_int(d)} mi od Des Plaines" + (f", dowóz ~{fmt_price(tc)}" if tc else ""))
    if l.get("dup_of"):
        parts.append(f"Możliwy duplikat oferty {l['dup_of']} (ten sam rocznik, cena i przebieg)")
    ev = evidence_text(l)
    if ev:
        parts.append(f"Potwierdzenie z opisu ogłoszenia: „{ev[:200]}”")
    if l.get("listed"):
        parts.append(f"Wystawiona: {l['listed']}")
    if s.get("discount") is not None:
        pct = round(s["discount"] * 100)
        parts.append(f"Ocena: {s['label']} ({'+' if pct >= 0 else ''}{pct}% vs rynek ≈ {fmt_price(s['ref'])})")
    if s.get("flags"):
        parts.append("Uwaga: " + "; ".join(s["flags"]))
    if l.get("notes"):
        parts.append(f"Notatka: {l['notes']}")
    if l.get("why"):
        parts.append(f"Dlaczego: {l['why']}")
    if l.get("vin_check"):
        parts.append(l["vin_check"])
    return " · ".join(parts) if parts else None


def block(l: dict, price_note: str = "", with_score: bool = True, config: dict | None = None) -> str:
    out = offer_lines(l, price_note)
    sl = score_line(l, config) if with_score else None
    return f"{out}\n{sl}" if sl else out


STATUS_LABELS = {"found": "znaleziono oferty", "zero": "sprawdzono, zero trafień",
                 "error": "błąd lub blokada", "unchecked": "jeszcze nie sprawdzono"}


def _loc(l: dict) -> str:
    return ", ".join(x for x in (l.get("city"), l.get("state")) if x) or "lokalizacja: brak danych"


def change_line(l: dict, config: dict) -> str:
    """Opis zmiany: spadek ceny (z datami i wejściem w limit) albo ponowne wystawienie."""
    parts = []
    if l.get("old_price") is not None:
        d = l["old_price"] - l["price"]
        last = (l.get("price_history") or [{}])[-1]
        txt = (f"Poprzednio {fmt_price(l['old_price'])} ({pl_date(l['old_date'])}), teraz {fmt_price(l['price'])} "
               f"({pl_date(last.get('date', l['last_seen']))}). Spadek o {fmt_price(d)}.")
        if l.get("into_limit"):
            txt += " Oferta weszła w Twój limit."
        parts.append(txt)
    rl = l.get("relist")
    if rl:
        label = "Ten sam motocykl (identyczny VIN)" if rl["kind"] == "vin" else "Prawdopodobnie ten sam motocykl"
        parts.append(f"{label} co wcześniejsze ogłoszenie – powód: {'; '.join(rl['reasons'])}. "
                     f"Wcześniejszy link: {rl.get('previous_url') or 'brak'} · nowy link: {rl.get('new_url') or 'brak'}")
    return " ".join(parts)


def render(diff: dict, run: dict, config: dict, report_no: int) -> list[str]:
    first = diff["first"]
    pool, seen = [], set()
    for l in diff["active"] + diff["unverified_all"]:
        # duplikaty zostają w raporcie (z adnotacją) – każda znaleziona oferta ma być widoczna z linkiem
        if l["id"] not in seen:
            seen.add(l["id"])
            pool.append(l)
    confirmed = sorted([l for l in pool if not missing_info(l, config)[1]], key=lambda l: rank_key(l, config))
    to_check = sorted([l for l in pool if missing_info(l, config)[1]], key=lambda l: rank_key(l, config))
    state_watch = [w for w in diff.get("watch_all", []) if w["id"] not in seen]
    new_ids = {l["id"] for l in diff["new"] + diff["unverified_new"]}
    drop_ids = {l["id"] for l in diff["drops"]}

    blocks: list[str] = []
    head = f"# Fat Boy Scout – raport nr {report_no} ({pl_date(run['date'])}, przebieg {run.get('run_id', run['date'])})"
    summary = (f"Potwierdzone oferty: {len(confirmed)} · do sprawdzenia: {len(to_check) + len(state_watch)} · "
               f"nowe: {len(new_ids)} · tańsze: {len(drop_ids)} · ponownie wystawione: {len(diff.get('relists', []))} · "
               f"niewidziane: {len(diff['gone'])}")
    blocks.append(f"{head}\n{summary}")

    changes = [l for l in pool if l["id"] in drop_ids or l.get("relist", {}).get("date") == run["date"]]
    if changes:
        lines = ["## Zmiany od poprzedniego przebiegu"]
        for l in changes:
            lines.append(f"- {l.get('model')} – {_loc(l)}\n  {change_line(l, config)}\n  {l.get('url') or 'link: brak'}")
        blocks.append("\n".join(lines))

    r = config.get("ranking", {})
    rate = f"{r.get('usd_per_mile', 0.10):.2f}".replace(".", ",")
    trate = f"{r.get('transport', {}).get('usd_per_mile', 0.6):.2f}".replace(".", ",")
    note = (f"Wszystkie oferty spełniające kryteria z potwierdzonym modelem, silnikiem, ceną, przebiegiem i bezpośrednim linkiem. "
            f"Kolejność: koszt całkowity = cena + {rate} USD/milę przebiegu + dowóz ~{trate} USD/milę. "
            "Dane z indeksu wyszukiwarki – dostępność sprawdź po kliknięciu.")
    if confirmed:
        blocks.append(f"## Potwierdzone – spełniają wszystkie kryteria ({len(confirmed)})\n{note}")
        for l in confirmed:
            tag = " [NOWA]" if l["id"] in new_ids else (" [TANIEJ]" if l["id"] in drop_ids else "")
            b = block(l, tag, config=config)
            ch = change_line(l, config)
            blocks.append(b + (f"\nZmiana: {ch}" if ch else "") + (f"\n{l['region_note']}" if l.get("region_note") else ""))
        blocks.append(next_steps(confirmed[:r.get("next_steps_top", 3)], config))
    else:
        blocks.append("## Potwierdzone – spełniają wszystkie kryteria (0)\nBrak ofert z kompletem potwierdzonych danych.")

    if to_check or state_watch:
        blocks.append(f"## Do sprawdzenia ({len(to_check) + len(state_watch)})\n"
                      "Są podstawy, żeby uznać motocykl za pasujący, ale czegoś brakuje. Nic tu nie łamie znanych kryteriów.")
        for l in to_check + state_watch:
            known, missing = missing_info(l, config)
            tag = " [NOWA]" if l["id"] in new_ids else ""
            lines = [f"{l.get('model') or 'Fat Boy'}{tag} – {fmt_price(l.get('price'))} – {fmt_miles(l.get('miles'))} – {_loc(l)}",
                     l.get("url") or "link: brak",
                     f"Ustalono: {'; '.join(known) or 'nic poza modelem'}",
                     f"Brakuje: {'; '.join(missing)}"]
            ev = evidence_text(l)
            if ev:
                lines.append(f"Cytat z opisu: „{ev[:200]}”")
            if l.get("dup_of"):
                lines.append(f"Możliwy duplikat oferty {l['dup_of']} (ten sam rocznik, cena, przebieg i stan) – sprawdź oba linki")
            if l.get("notes") or l.get("note"):
                lines.append(f"Notatka: {l.get('notes') or l.get('note')}")
            ch = change_line(l, config)
            if ch:
                lines.append(f"Zmiana: {ch}")
            if l.get("region_note"):
                lines.append(l["region_note"])
            blocks.append("\n".join(lines))

    if diff["gone"]:
        lines = ["## Niewidziane lub poza kryteriami"]
        for l in diff["gone"]:
            lines.append(f"- {l.get('model')} – {fmt_price(l.get('price'))} – {_loc(l)} – {l.get('status_reason', '')}\n"
                         f"  {l.get('url') or 'link: brak'}")
        blocks.append("\n".join(lines))

    if diff["rejected_now"]:
        over = [x for x in diff["rejected_now"] if x["reason"].startswith("cena >")]
        rest = [x for x in diff["rejected_now"] if x not in over]
        lines = ["## Sprawdzone i odrzucone (do 11 000 USD, ale niespełniające innych kryteriów)"]
        lines += [f"- {x.get('model')} – {fmt_price(x.get('price'))} – {x['location']} – {x['reason']}\n"
                  f"  {x.get('url') or 'link: brak'}" for x in rest]
        if over:
            lines.append(f"Pominięto {len(over)} ofert z ceną powyżej {fmt_int(config['max_price_usd'])} USD "
                         "(ceny zapamiętane – jeśli spadną do limitu, raport to pokaże).")
        blocks.append("\n".join(lines))

    leads = diff.get("leads_all", [])
    if leads:
        blocks.append(f"## Tropy do dalszego wyszukania ({len(leads)})\nSzerokie trafienia (np. „2018 Harley Softail”) bez "
                      "potwierdzenia, że to Fat Boy. Nie są ofertami – są na liście `scout.py todo`.")

    cov = diff.get("coverage")
    if cov:
        groups: dict[str, list[str]] = {k: [] for k in STATUS_LABELS}
        for s, c in sorted(cov["states"].items()):
            label = s
            if c["status"] == "found":
                label += f" ({c['match']} pasujących z {c['seen']})"
            groups[c["status"]].append(label)
        lines = ["## Pokrycie – co faktycznie sprawdzono"]
        for k, lab in STATUS_LABELS.items():
            lines.append(f"- {lab.capitalize()} ({len(groups[k])}): {', '.join(groups[k]) or '—'}")
        for src, sc in cov["sources"].items():
            lines.append(f"- Źródło {src}: {sc['queries']} zapytań, z wynikami {sc['with_results']}, błędów {sc['errors']}")
        for src in ("cycletrader",):
            if src not in config.get("sources", []):
                lines.append(f"- Źródło {src}: wyłączone w konfiguracji – nie sprawdzano")
        lines.append("Stan z zapytania grupowego liczy się jako sprawdzony tylko wtedy, gdy wyniki go zawierały.")
        blocks.append("\n".join(lines))

    if not diff.get("scan_ok", True):
        blocks.append("## Uwaga: skan niepełny\nMało zapytań zwróciło wyniki, więc liczniki zniknięć wstrzymano w tym przebiegu.")
    if diff.get("queries"):
        qm = diff.get("query_matches", {})
        cr = diff.get("credits")
        blocks.append(f"## Wyszukiwanie\nZapytań: {len(diff['queries'])}, w tym z pasującą ofertą: {sum(1 for v in qm.values() if v)}"
                      + (f", błędów: {sum(1 for q in diff['queries'] if q.get('status') == 'error')}" )
                      + (f". Kredyty Firecrawl: {cr}." if cr is not None else ". Kredyty Firecrawl: nie zmierzono."))
    cvg = run.get("coverage")
    if cvg:
        blocks.append("## Zakres\n" + ("\n".join(f"- {c}" for c in cvg) if isinstance(cvg, list) else cvg))
    return split_parts(blocks, config["report_max_chars"])


def next_steps(top: list[dict], config: dict) -> str:
    """Gotowa wiadomość do sprzedawcy i lista kontrolna dla najlepszych ofert."""
    home = config.get("home", {})
    lines = ["## Następne kroki – najlepsze oferty"]
    for i, l in enumerate(top, 1):
        loc = ", ".join(x for x in (l.get("city"), l.get("state")) if x)
        lines.append(f"{i}. {l.get('model')} – {fmt_price(l.get('price'))} – {loc} – {l.get('url') or 'link: brak'}")
    lines.append("Wiadomość do sprzedawcy (wklej w Messengerze):\n"
                 "„Hi! Is your Fat Boy still available? Could you send me the VIN, a photo of the odometer and of the "
                 "title (clean and in your name?), and tell me about service history and any drops or accidents? "
                 f"I'm in the {home.get('city', 'Des Plaines')}, {home.get('state', 'IL')} area. Thanks!”")
    lines.append("Do sprawdzenia przed jazdą lub przelewem:")
    lines.append("- VIN: `python3 fat-boy-scout/scout.py vin <VIN>` pokaże silnik (YG = FLFBS 114, FLFB = 107) i rocznik.")
    lines.append("- Title: clean, na nazwisko sprzedawcy; nie salvage, rebuilt ani bonded.")
    lines.append("- Zdjęcie licznika potwierdza przebieg do 15 000 mil; poproś też o zdjęcie VIN na ramie.")
    lines.append("- Nigdy nie wpłacaj zaliczki „za trzymanie” przed obejrzeniem; uważaj na „wysyłka tylko z depozytem”.")
    return "\n".join(lines)


def mark_duplicates(listings: list[dict]) -> None:
    """Ta sama oferta pod różnymi linkami/miastami: ten sam rocznik, cena (±1%), przebieg (±5%) i stan."""
    seen: list[dict] = []
    for l in sorted(listings, key=lambda x: x["id"]):
        l.pop("dup_of", None)
        for s in seen:
            if (l.get("year") == s.get("year") and l.get("state") == s.get("state") and l.get("price") and s.get("price")
                    and abs(l["price"] - s["price"]) <= 0.01 * s["price"]
                    and l.get("miles") is not None and s.get("miles") is not None
                    and abs(l["miles"] - s["miles"]) <= 0.05 * max(1, s["miles"])):
                l["dup_of"] = s["id"]
                break
        else:
            seen.append(l)


def split_parts(blocks: list[str], max_chars: int) -> list[str]:
    # nagłówek sekcji (z ewentualnym wstępem, bez linku) skleja się z następnym blokiem,
    # żeby nie został sam na końcu części
    glued: list[str] = []
    for b in blocks:
        if glued and glued[-1].startswith("## ") and "http" not in glued[-1] and not glued[-1].startswith("## Zakres"):
            glued[-1] = f"{glued[-1]}\n\n{b}"
        else:
            glued.append(b)
    blocks = glued
    parts, cur = [], ""
    for b in blocks:
        if cur and len(cur) + len(b) + 2 > max_chars:
            parts.append(cur)
            cur = b
        else:
            cur = f"{cur}\n\n{b}" if cur else b
    if cur:
        parts.append(cur)
    if len(parts) > 1:
        parts = [f"**Część {i}/{len(parts)}**\n\n{p}" for i, p in enumerate(parts, 1)]
    return parts


# ---------------------------------------------------------------- CLI
def cmd_run(args) -> int:
    config = load_json(CONFIG_PATH)
    run = load_json(Path(args.run_file))
    run.setdefault("date", date.today().isoformat())
    state = migrate(load_json(STATE_PATH))
    run.setdefault("run_id", run["date"])
    errors, warnings = validate_run(run, config)
    for w in warnings:
        print(f"OSTRZEŻENIE: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"BŁĄD: {e}", file=sys.stderr)
        print("Popraw plik przebiegu (scout.py check pokaże to samo) i uruchom ponownie.", file=sys.stderr)
        return 1
    if run["run_id"] in state["runs"] and not args.dry_run:
        print(f"Przebieg {run['date']} jest już w state.json – użyj --dry-run albo innej daty.", file=sys.stderr)
        return 2
    report_no = len(state["runs"]) + 1
    state, diff = merge(state, run, config)
    parts = render(diff, run, config, report_no)
    text = "\n\n---\n\n".join(parts)
    print(text)
    if not args.dry_run:
        state["last_run"] = run["date"]
        save_json(STATE_PATH, state)
        REPORTS_DIR.mkdir(exist_ok=True)
        (REPORTS_DIR / f"{run['run_id']}.md").write_text(text + "\n", encoding="utf-8")
    return 0


def improve(state: dict, config: dict, today: str) -> tuple[dict, list[str]]:
    """Samodoskonalenie: przycina martwe zapytania, dodaje skuteczne eksperymenty i zapytania z miast
    z trafieniami, kalibruje ceny referencyjne na podstawie obserwacji. Zwraca (nowy_config, log)."""
    cfg = json.loads(json.dumps(config))
    si = cfg.get("self_improve", {})
    log: list[str] = []
    queries = cfg["searches"]["facebook_index"]
    by_q = {q["q"]: q for q in queries}
    stats = state.get("query_stats", {})

    # a) przycinanie
    for q in queries:
        st = stats.get(q["q"])
        if not st or q.get("status") != "active":
            continue
        if st["zero_streak"] >= si.get("drop_after_zero_runs", 3):
            if q.get("origin") == "seed":
                if not q.get("flagged"):
                    q["flagged"] = today
                    log.append(f"Zapytanie startowe bez trafień od {st['zero_streak']} przebiegów (zostaje, oznaczone): {q['q']}")
            else:
                q["status"] = "retired"
                q["retired"] = today
                log.append(f"Wycofano zapytanie bez trafień od {st['zero_streak']} przebiegów: {q['q']}")

    def add(qtext: str, origin: str, why: str) -> None:
        active = [x for x in queries if x.get("status") == "active"]
        if qtext in by_q or len(active) >= si.get("max_queries", 25):
            return
        item = {"q": qtext, "origin": origin, "added": today, "status": "active", "why": why}
        queries.append(item)
        by_q[qtext] = item
        log.append(f"Dodano zapytanie ({origin}): {qtext} – {why}")

    # b) eksperymenty, które dały trafienia, wchodzą do stałego planu
    for qtext, st in stats.items():
        if st.get("origin") == "experiment" and st.get("unique_hits", 0) > 0:
            add(qtext, "auto", f"eksperyment z {st['unique_hits']} unikalnymi trafieniami")

    # c) zapytania dla miast, w których znaleziono pasujące oferty
    tmpl = si.get("city_query_template", 'site:facebook.com/marketplace "Fat Boy" "{city}"')
    for l in state.get("listings", {}).values():
        if l.get("status") == "active" and l.get("city") and l.get("state"):
            city = re.sub(r"\s*\(.*?\)", "", l["city"]).strip()
            add(tmpl.format(city=city, state=l["state"]), "auto", f"miasto z trafieniem ({city}, {l['state']})")

    # d) kalibracja cen referencyjnych z obserwacji (także ofert powyżej limitu)
    obs: dict[tuple[str, int], list[int]] = {}
    seen_bikes: set = set()
    for rec in list(state.get("listings", {}).values()) + list(state.get("rejected", {}).values()):
        bike = (rec.get("year"), (rec.get("city") or rec.get("location") or "").lower(), rec.get("price"))
        if rec.get("id") in seen_bikes or (bike[1] and bike in seen_bikes):
            continue
        seen_bikes.update({rec.get("id"), bike})
        fam, year, price = rec.get("family"), rec.get("year"), rec.get("price")
        if fam in ("Fat Boy", "Fat Bob"):
            fam += " 114"
        if not fam or not year or not price or price <= cfg["placeholder_price_max"]:
            continue
        if "107" in str(rec.get("reason", "")) or "117" in str(rec.get("reason", "")):
            continue
        obs.setdefault((fam, int(year)), []).append(int(price))
    for (fam, year), prices in sorted(obs.items()):
        if len(prices) < si.get("min_samples_for_price", 3):
            continue
        prices.sort()
        n = len(prices)
        med = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        table = cfg["market_reference"].setdefault(fam, {})
        old = table.get(str(year))
        blend = si.get("price_blend", 0.5)
        new = int(round((med if old is None else blend * old + (1 - blend) * med) / 50.0) * 50)
        if old != new:
            table[str(year)] = new
            log.append(f"Cena referencyjna {fam} {year}: {fmt_price(old) if old else 'brak'} → {fmt_price(new)} "
                       f"(mediana {fmt_price(med)} z {n} ofert)")
    return cfg, log


def cmd_improve(args) -> int:
    config = load_json(CONFIG_PATH)
    state = migrate(load_json(STATE_PATH))
    today = state.get("last_run_date") or (state["runs"][-1][:10] if state["runs"] else date.today().isoformat())
    new_cfg, log = improve(state, config, today)
    if not log:
        print("Brak zmian – plan i ceny referencyjne są aktualne.")
        return 0
    print("\n".join(f"- {x}" for x in log))
    if args.apply:
        save_json(CONFIG_PATH, new_cfg)
        path = BASE / "improvements.md"
        prev = path.read_text(encoding="utf-8") if path.exists() else "# Dziennik samodoskonalenia Fat Boy Scout\n"
        path.write_text(prev.rstrip() + f"\n\n## {today}\n" + "\n".join(f"- {x}" for x in log) + "\n", encoding="utf-8")
        print("Zapisano config.json i improvements.md")
    return 0


PRICE_RE = r"(?:US)?\$\s?(?P<price>\d{1,3}(?:[.,\s\u00a0]\d{3})+|\d{4,6})"


def _num(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def _miles(s: str) -> int | None:
    m = re.search(r"(?P<n>\d+(?:[.,]\d+)?)\s?(?P<k>[Kk]|tys\.?|t\.)?\s?(?:miles|mi\b)", s)
    if not m:
        m = re.search(r"Driven (?P<n>[\d,]+) miles", s)
        return _num(m.group("n")) if m else None
    n = float(m.group("n").replace(",", ".")) if m.group("k") else _num(m.group("n"))
    return int(round(n * 1000)) if m.group("k") else int(n)


def parse_snippet(text: str, url: str | None = None) -> list[dict]:
    """Wyciąga oferty Fat Boy z fragmentu wyniku wyszukiwania Facebooka. Zwraca kandydatów do przejrzenia."""
    out = []
    # A: „2018 Harley-Davidson Fat Boy - $9995, Used, in Ormond Beach, Florida.”
    for m in re.finditer(r"(?P<title>(?P<year>20\d\d)[^\n]{0,60}?fat\s?boy[^\n]{0,40}?) - " + PRICE_RE +
                         r",(?: Used,)? in (?P<city>[A-Z][\w .'-]+?), (?P<state>[A-Z][a-zA-Z ]+?)[.\s]", text, re.I):
        out.append({"model": m.group("title").strip(), "year": int(m.group("year")), "price": _num(m.group("price")),
                    "city": m.group("city").strip(), "state": geo.state_code(m.group("state"))})
    # B: „2018 Harley-Davidson fat boy 114 flfbs for sale - Used - $10,500 in Rathdrum. ... 1K miles. Rathdrum, ID”
    for m in re.finditer(r"(?P<title>(?P<year>20\d\d)[^\n]{0,60}?fat\s?boy[^\n]{0,40}?) for sale - Used(?: - [\w ]+?)? - "
                         + PRICE_RE + r"(?P<rest>.{0,160})", text, re.I):
        rest = m.group("rest")
        locs = list(re.finditer(r"((?:[A-Z][a-z'.-]+ ?){1,3}), ([A-Z]{2})\b", rest))
        loc = locs[0] if locs else None
        out.append({"model": m.group("title").strip(), "year": int(m.group("year")), "price": _num(m.group("price")),
                    "miles": _miles(rest), "city": loc.group(1).strip() if loc else None,
                    "state": loc.group(2) if loc else None, "price_drop": "price drop" in rest.lower()})
    # C: „2018 Harley-Davidson Fat Boy 114. $12,999. Listed 11 hours ago · Defiance, OH”
    if not out:
        for m in re.finditer(r"(?P<title>(?P<year>20\d\d)[^\n]{0,60}?fat\s?boy[^.\n$]{0,30})\.\s*" + PRICE_RE +
                             r"\.?(?P<rest>.{0,140})", text, re.I):
            rest = m.group("rest")
            loc = re.search(r"·\s*((?:[A-Z][a-z'.-]+ ?){1,3}), ([A-Z]{2})\b", rest)
            out.append({"model": m.group("title").strip(), "year": int(m.group("year")), "price": _num(m.group("price")),
                        "miles": _miles(rest), "city": loc.group(1).strip() if loc else None,
                        "state": loc.group(2) if loc else None})
            break
    listed = re.search(r"Listed ([\w ]+? ago|on \w+)", text)
    for o in out:
        if listed and len(out) == 1:
            o["listed"] = listed.group(1)
        if o.get("miles") is None and len(out) == 1:
            o["miles"] = _miles(text)
        o.update(source="facebook", category="main", verified=False, url=url)
        if len(out) == 1 and re.search(r"dealer|stock\s*(?:#|number)|we finance|processing fee|doc fee|no hidden fees|"
                                         r"financing|trades? welcome", text, re.I):
            o["seller"] = "dealer"
        iid = item_id(url or "")
        o["id"] = iid if iid.startswith("fb-") and len(out) == 1 and text.lstrip().startswith(str(o["year"])) else \
            f"fb-{(o.get('city') or 'x').lower().replace(' ', '')}-{(o.get('state') or 'xx').lower()}-{o['year']}"
    return out


def cmd_parse(args) -> int:
    """Wejście: plik JSON z listą {url, title, description} (wyniki wyszukiwania). Wyjście: kandydaci do pliku przebiegu."""
    items = json.loads(Path(args.file).read_text(encoding="utf-8"))
    found: dict[str, dict] = {}
    for it in items:
        text = f"{it.get('title', '')} - {it.get('description', '')}" if " - $" not in it.get("title", "") else \
            f"{it.get('title', '')}. {it.get('description', '')}"
        for o in parse_snippet(text, it.get("url")):
            found.setdefault(o["id"], o)
    print(json.dumps(list(found.values()), ensure_ascii=False, indent=2))
    return 0


def validate_run(run: dict, config: dict) -> tuple[list[str], list[str]]:
    """Sprawdza plik przebiegu przed scaleniem. Zwraca (błędy, ostrzeżenia)."""
    err, warn = [], []
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(run.get("date", ""))):
        err.append("pole 'date' musi mieć format RRRR-MM-DD")
    if not run.get("sources_checked"):
        warn.append("brak 'sources_checked' – zniknięcia nie będą liczone")
    ids = [l.get("id") for l in run.get("listings", [])]
    dups = {i for i in ids if ids.count(i) > 1}
    if dups:
        err.append(f"zdublowane ID: {', '.join(sorted(map(str, dups)))}")
    states = set(config.get("us_states", []))
    for l in run.get("listings", []):
        lid = l.get("id") or "?"
        if not re.fullmatch(r"(fb|ct)-[\w-]+", str(l.get("id", ""))):
            err.append(f"{lid}: ID musi mieć postać fb-<numer> albo fb-<miasto>-<stan>-<rocznik>")
        if l.get("category") not in config["categories"]:
            err.append(f"{lid}: nieznana kategoria {l.get('category')!r}")
        for k in ("year", "price", "miles", "distance_mi"):
            if l.get(k) is not None and not isinstance(l[k], int):
                err.append(f"{lid}: '{k}' musi być liczbą całkowitą albo null (jest {l[k]!r})")
        st = l.get("state")
        if st is not None and st.upper() not in states and not geo.state_code(st):
            warn.append(f"{lid}: nieznany stan {st!r} (oferta spoza USA zostanie odrzucona)")
        if not l.get("url"):
            err.append(f"{lid}: brak linku 'url' – każda oferta musi mieć link")
        if l.get("source") == "facebook" and l.get("verified") is not False:
            warn.append(f"{lid}: oferta z Facebooka powinna mieć \"verified\": false")
        if isinstance(l.get("price"), int) and l["price"] <= config["max_price_usd"] and l.get("distance_mi") is None:
            warn.append(f"{lid}: brak 'distance_mi' – silnik użyje środka stanu")
    known = set(ids) | {w.get("id") for w in run.get("watchlist_unpriced", [])}
    for q in run.get("queries", []):
        if "q" not in q or not isinstance(q.get("results", 0), int):
            err.append(f"zapytanie bez tekstu 'q' albo z nieliczbowym 'results': {q}")
        for c in q.get("candidates", []):
            if c not in known:
                warn.append(f"zapytanie {q.get('q', '?')[:40]!r}: kandydat {c} nie występuje w listings/watchlist")
    for q in run.get("queries", []):
        if q.get("status") not in (None, "ok", "zero", "error"):
            err.append(f"zapytanie {q.get('q', '?')[:40]!r}: status musi być ok, zero albo error")
    for l in run.get("listings", []):
        if l.get("basis") is not None and not isinstance(l.get("basis"), str):
            err.append(f"{l.get('id')}: 'basis' musi być tekstem (dlaczego to może być Fat Boy)")
        ev = l.get("evidence")
        if ev is not None and not (isinstance(ev, list) and all(isinstance(e, dict) and e.get("quote") for e in ev)):
            err.append(f"{l.get('id')}: 'evidence' musi być listą {{quote, url}} z dosłownym cytatem z opisu")
    if not run.get("queries"):
        warn.append("brak 'queries' – samodoskonalenie nie dostanie danych")
    return err, warn


def cmd_check(args) -> int:
    run = load_json(Path(args.run_file))
    errors, warnings = validate_run(run, load_json(CONFIG_PATH))
    for w in warnings:
        print(f"OSTRZEŻENIE: {w}")
    for e in errors:
        print(f"BŁĄD: {e}")
    print("OK – plik przebiegu jest poprawny." if not errors else f"{len(errors)} błędów.")
    return 1 if errors else 0


def todo_items(state: dict, config: dict) -> list[str]:
    """Lista braków w aktywnych ofertach i gotowe zapytania, które je uzupełnią."""
    out = []
    for l in sorted(state.get("listings", {}).values(), key=lambda l: rank_key(l, config)):
        if l.get("status") != "active" or l.get("dup_of"):
            continue
        city, st, y = l.get("city") or "", l.get("state") or "", l.get("year") or ""
        base = f'"{y} Harley-Davidson Fat Boy" {city} {st}'.strip()
        gaps = []
        if l.get("model_provisional"):
            gaps.append(("potwierdzenie modelu Fat Boy", f'"{l.get("listing_title") or l.get("model")}" {city} {st} "Fat Boy" OR FLFBS'))
        if l.get("miles") is None:
            gaps.append(("przebieg", f"{base} miles facebook marketplace"))
        if l.get("engine") is None and l.get("year") and l["year"] <= 2020:
            gaps.append(("silnik 107/114", f"{base} FLFBS OR 114 OR 107"))
        if "/marketplace/item/" not in (l.get("url") or ""):
            gaps.append(("bezpośredni link", f'site:facebook.com/marketplace/item {base}'))
        if l.get("distance_mi") is None:
            gaps.append(("odległość", "wpisz distance_mi z własnej wiedzy o geografii"))
        for what, q in gaps:
            out.append(f"{l['id']} ({l.get('model')}, {fmt_price(l.get('price'))}, {city} {st}) – brak: {what}\n    → {q}")
    for ld in state.get("leads", {}).values():
        iid = re.search(r"marketplace/item/(\d+)", ld.get("url") or "")
        q = (f'"marketplace/item/{iid.group(1)}" OR "{ld.get("listing_title") or ld.get("model")}" {ld.get("city") or ""} Fat Boy'
             if iid else f'"{ld.get("listing_title") or ld.get("model")}" {ld.get("city") or ""} {ld.get("state") or ""} "Fat Boy" description')
        out.append(f"{ld['id']} (trop: {ld.get('listing_title') or ld.get('model')}, {fmt_price(ld.get('price'))}, "
                   f"{ld.get('city') or ''} {ld.get('state') or ''}) – brak: potwierdzenie modelu w opisie\n    → {q.strip()}")
    for w in state.get("watchlist", {}).values():
        mq = re.split(r"[(,]", w.get("model", ""))[0].strip()
        where = " ".join(x for x in (w.get("city"), w.get("state")) if x)
        out.append(f"{w['id']} ({w.get('model')}) – brak: cena\n    → \"{mq}\" {where} price facebook marketplace".rstrip())
    return out


def cmd_todo(args) -> int:
    items = todo_items(migrate(load_json(STATE_PATH)), load_json(CONFIG_PATH))
    print("\n".join(items) if items else "Brak braków – wszystkie aktywne oferty są kompletne.")
    return 0


def item_id(s: str) -> str:
    m = re.search(r"marketplace/item/(\d+)", s)
    return f"fb-{m.group(1)}" if m else s.strip()


def cmd_recall(args) -> int:
    """Test skuteczności: plik z linkami ofert znalezionych ręcznie → ile z nich Scout widział."""
    state = migrate(load_json(STATE_PATH))
    known = set(state["listings"]) | set(state["rejected"]) | set(state.get("watchlist", {}))
    lines = [x for x in Path(args.file).read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
    found = [x for x in lines if item_id(x) in known]
    missed = [x for x in lines if item_id(x) not in known]
    print(f"Skuteczność: {len(found)}/{len(lines)} ({round(100 * len(found) / max(1, len(lines)))}%)")
    for x in missed:
        print(f"  przeoczona: {x.strip()}")
    return 0


# ---------------------------------------------------------------- przebieg krok po kroku (wznawialny)
def save_json_atomic(path: Path, data) -> None:
    """Zapis przez plik tymczasowy + rename: przerwany proces nie zostawi uszkodzonego pliku."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def states_in_text(text: str) -> set[str]:
    """Stany USA widoczne w tekście wyników: „, TX”, „Texas” itp."""
    found = {m.group(1) for m in re.finditer(r",\s([A-Z]{2})\b", text) if m.group(1) in geo.STATE_CENTROIDS}
    low = text.lower()
    for name, code in geo.STATE_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", low):
            found.add(code)
    return found


def unfinished_runs() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted(p for p in RUNS_DIR.glob("*.json") if (load_json(p) or {}).get("status") == "in_progress")


def plan_queries(config: dict) -> list[dict]:
    return [dict(q) for q in config["searches"].get("facebook_index", [])
            if isinstance(q, dict) and q.get("status", "active") == "active"]


def remaining_queries(run: dict) -> list[dict]:
    done = {q["q"] for q in run.get("queries", []) if q.get("status") in ("ok", "zero")}
    return [q for q in run.get("plan", []) if q["q"] not in done]


def begin_run(config: dict, today: str | None = None, hour: str | None = None) -> tuple[dict, bool]:
    """Zwraca (przebieg, czy_wznowiony). Niedokończony przebieg jest zawsze wznawiany; po zakończonym – nowy."""
    open_runs = unfinished_runs()
    if open_runs:
        return load_json(open_runs[-1]), True
    today = today or date.today().isoformat()
    state = migrate(load_json(STATE_PATH))
    run_id = today
    if run_id in state["runs"] or (RUNS_DIR / f"{run_id}.json").exists():
        run_id = f"{today}-{hour or __import__('datetime').datetime.now().strftime('%H%M')}"
    run = {"date": today, "run_id": run_id, "status": "in_progress", "sources_checked": list(config.get("sources", [])),
           "plan": plan_queries(config), "queries": [], "listings": [], "watchlist_unpriced": [], "coverage": [],
           "credits_used": 0, "started_at": __import__("datetime").datetime.now().isoformat(timespec="seconds")}
    save_json_atomic(RUNS_DIR / f"{run_id}.json", run)
    return run, False


def _upsert(items: list[dict], new: dict) -> bool:
    """Wstawia albo uzupełnia wpis o tym samym ID. Zwraca True, gdy wpis był nowy."""
    for it in items:
        if it.get("id") == new.get("id"):
            it.update({k: v for k, v in new.items() if v is not None})
            return False
    items.append(dict(new))
    return True


def record_query(run: dict, payload: dict, config: dict) -> dict:
    """Zapisuje JEDNO zakończone zapytanie z jego wynikami. Ponowne zapisanie tego samego zapytania nie dubluje danych."""
    q = {"q": payload["q"], "origin": payload.get("origin") or next(
        (p.get("origin", "seed") for p in run.get("plan", []) if p["q"] == payload["q"]), "experiment"),
        "source": payload.get("source", "facebook")}
    plan_item = next((p for p in run.get("plan", []) if p["q"] == payload["q"]), {})
    if plan_item.get("states"):
        q["states"] = plan_item["states"]
    if payload.get("status") == "error":
        q.update(status="error", error=payload.get("error") or "błąd", results=0, candidates=[])
    else:
        raw = payload.get("raw") or []
        parsed: dict[str, dict] = {}
        rstates: set[str] = set(payload.get("result_states") or [])
        for it in raw:
            text = f"{it.get('title', '')} - {it.get('description', '')}"
            rstates |= states_in_text(text)
            for o in parse_snippet(text, it.get("url")):
                parsed.setdefault(o["id"], o)
        listings = list(parsed.values())
        for l in payload.get("listings") or []:      # dane poprawione/uzupełnione przez agenta mają pierwszeństwo
            _upsert(listings, l)
        for l in listings:
            if l.get("state"):
                rstates.add(geo.state_code(l["state"]) or l["state"])
        results = int(payload.get("results", len(raw)))
        q.update(status="ok" if results else "zero", results=results, candidates=[l["id"] for l in listings],
                 result_states=sorted(rstates))
        for l in listings:
            _upsert(run["listings"], l)
        for w in payload.get("watchlist_unpriced") or []:
            _upsert(run["watchlist_unpriced"], w)
    run["credits_used"] = int(run.get("credits_used") or 0) + int(payload.get("credits") or 0)
    replaced = False
    for i, old in enumerate(run["queries"]):
        if old["q"] == q["q"]:
            if old.get("status") in ("ok", "zero") and q.get("status") == "error":
                return run   # udany wynik nie zostaje nadpisany późniejszym błędem
            run["queries"][i] = q
            replaced = True
    if not replaced:
        run["queries"].append(q)
    if payload.get("coverage_note"):
        run.setdefault("coverage", []).append(payload["coverage_note"])
    return run


def finish_run(run: dict, config: dict, partial: bool = False) -> tuple[int, str]:
    """Scala przebieg z historią i pisze raport. Bez --partial odmawia, gdy zostały niewykonane zapytania z planu."""
    left = remaining_queries(run)
    if left and not partial:
        return 3, (f"Zostało {len(left)} niewykonanych zapytań z planu – przebieg zostaje otwarty. "
                   "Uruchom kolejne /fat-boy-scout, żeby je dokończyć, albo użyj --partial.")
    state = migrate(load_json(STATE_PATH))
    if run["run_id"] in state["runs"]:
        run["status"] = "done"
        save_json_atomic(RUNS_DIR / f"{run['run_id']}.json", run)
        return 0, f"Przebieg {run['run_id']} był już scalony – nic nie dodano drugi raz."
    errors, _ = validate_run(run, config)
    if errors:
        return 1, "BŁĘDY w pliku przebiegu:\n" + "\n".join(errors)
    if left:
        run.setdefault("coverage", []).append(f"Przebieg zamknięty częściowo: {len(left)} zapytań z planu nie wykonano.")
    report_no = len(state["runs"]) + 1
    state, diff = merge(state, run, config)
    text = "\n\n---\n\n".join(render(diff, run, config, report_no))
    state["last_run"] = run["date"]
    save_json_atomic(STATE_PATH, state)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{run['run_id']}.md").write_text(text + "\n", encoding="utf-8")
    run["status"] = "done"
    run["finished_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    save_json_atomic(RUNS_DIR / f"{run['run_id']}.json", run)
    return 0, text


def _run_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.json"


def cmd_begin(args) -> int:
    run, resumed = begin_run(load_json(CONFIG_PATH), args.date)
    left = remaining_queries(run)
    print(json.dumps({"run_id": run["run_id"], "resumed": resumed, "done": len(run["queries"]),
                      "remaining": [q["q"] for q in left], "credits_used_so_far": run.get("credits_used", 0)},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_record(args) -> int:
    path = _run_path(args.run_id)
    run = load_json(path)
    if not run or run.get("status") != "in_progress":
        print(f"Brak otwartego przebiegu {args.run_id}.", file=sys.stderr)
        return 1
    payload = load_json(Path(args.payload))
    for p in (payload if isinstance(payload, list) else [payload]):
        run = record_query(run, p, load_json(CONFIG_PATH))
    save_json_atomic(path, run)
    print(f"Zapisano. Wykonane zapytania: {len(run['queries'])}, pozostało z planu: {len(remaining_queries(run))}, "
          f"ofert w przebiegu: {len(run['listings'])}, kredyty: {run.get('credits_used', 0)}")
    return 0


def cmd_remaining(args) -> int:
    run = load_json(_run_path(args.run_id))
    for q in remaining_queries(run):
        print(q["q"])
    return 0


def cmd_finish(args) -> int:
    run = load_json(_run_path(args.run_id))
    code, text = finish_run(run, load_json(CONFIG_PATH), args.partial)
    print(text)
    return code


def cmd_vin(args) -> int:
    print(json.dumps(decode_vin(args.vin, load_json(CONFIG_PATH)), ensure_ascii=False))
    return 0


def cmd_plan(args) -> int:
    cfg = load_json(CONFIG_PATH)
    usa = cfg.get("scope") == "usa"
    print(f"Zasięg: {'cała USA (radius=' + str(cfg['searches']['usa_radius']) + ')' if usa else 'Midwest (radius=500)'}")
    for s in (cfg["searches"].get("cycletrader", []) if "cycletrader" in cfg.get("sources", ["cycletrader"]) else []):
        url = s["url"].replace("radius=500", f"radius={cfg['searches']['usa_radius']}") if usa else s["url"]
        print(f"[CT/{s['category']}] {s['name']}{' (+&page=N)' if s.get('paged') else ''}\n  {url}")
    for q in cfg["searches"]["facebook_index"]:
        if isinstance(q, str):
            print(f"[FB-index] {q}")
        elif q.get("status") == "active":
            print(f"[FB-index/{q.get('origin', 'seed')}] {q['q']}")
    return 0


def cmd_status(args) -> int:
    state = migrate(load_json(STATE_PATH))
    act = [l for l in state["listings"].values() if l.get("status") == "active"]
    print(f"Przebiegi: {len(state['runs'])} (ostatni: {state['runs'][-1] if state['runs'] else '—'})")
    print(f"Aktywne śledzone: {len(act)} · odrzucone: {len(state['rejected'])}")
    for l in sorted(act, key=lambda l: l.get("price") or 0):
        v = "" if l.get("verified", True) else " [FB, niezweryfikowane]"
        print(f"- {l['id']}: {l.get('model')} {fmt_price(l.get('price'))} {l.get('city')}, {l.get('state')}{v}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fat Boy Scout – silnik raportów")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="scal obserwacje z przebiegu i wygeneruj raport")
    r.add_argument("run_file")
    r.add_argument("--dry-run", action="store_true", help="nie zapisuj stanu ani raportu")
    r.set_defaults(func=cmd_run)
    v = sub.add_parser("vin", help="dekoduj model/silnik z VIN Harleya")
    v.add_argument("vin")
    v.set_defaults(func=cmd_vin)
    sub.add_parser("plan", help="pokaż plan wyszukiwań").set_defaults(func=cmd_plan)
    sub.add_parser("status", help="pokaż śledzone oferty").set_defaults(func=cmd_status)
    ck = sub.add_parser("check", help="sprawdź plik przebiegu przed uruchomieniem")
    ck.add_argument("run_file")
    ck.set_defaults(func=cmd_check)
    sub.add_parser("todo", help="braki w aktywnych ofertach i zapytania, które je uzupełnią").set_defaults(func=cmd_todo)
    pa = sub.add_parser("parse", help="wyciągnij oferty z wyników wyszukiwania (JSON: url, title, description)")
    pa.add_argument("file")
    pa.set_defaults(func=cmd_parse)
    rc = sub.add_parser("recall", help="test skuteczności: ile z Twoich ręcznie znalezionych ofert Scout widział")
    rc.add_argument("file", help="plik z linkami (po jednym w linii)")
    rc.set_defaults(func=cmd_recall)
    bg = sub.add_parser("begin", help="zacznij nowy przebieg albo wznów niedokończony")
    bg.add_argument("--date", default=None)
    bg.set_defaults(func=cmd_begin)
    rd = sub.add_parser("record", help="zapisz jedno zakończone zapytanie (JSON: q, status, raw, listings, credits)")
    rd.add_argument("run_id")
    rd.add_argument("payload")
    rd.set_defaults(func=cmd_record)
    rm = sub.add_parser("remaining", help="zapytania z planu, których jeszcze nie wykonano")
    rm.add_argument("run_id")
    rm.set_defaults(func=cmd_remaining)
    fi = sub.add_parser("finish", help="scal przebieg i zrób raport (odmawia, gdy zostały zapytania)")
    fi.add_argument("run_id")
    fi.add_argument("--partial", action="store_true")
    fi.set_defaults(func=cmd_finish)
    im = sub.add_parser("improve", help="samodoskonalenie: zapytania i ceny referencyjne")
    im.add_argument("--apply", action="store_true", help="zapisz zmiany w config.json i improvements.md")
    im.set_defaults(func=cmd_improve)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
