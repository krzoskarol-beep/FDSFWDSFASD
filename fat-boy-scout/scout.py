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
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import geo  # noqa: E402
CONFIG_PATH = BASE / "config.json"
STATE_PATH = BASE / "state.json"
REPORTS_DIR = BASE / "reports"

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


def family(listing: dict) -> str | None:
    """Rodzina modelu używana do kryteriów i cen referencyjnych."""
    text = f"{listing.get('model', '')} {listing.get('code', '')}".lower()
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
    text = f"{listing.get('model', '')} {listing.get('code', '')}".upper()
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
    if price is None:
        return False, "brak ceny"
    if price <= config["placeholder_price_max"]:
        return False, f"cena-wypełniacz ({fmt_price(price)})"
    if price > config["max_price_usd"]:
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
    return True, "ok"


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


def merge(state: dict, run: dict, config: dict) -> tuple[dict, dict]:
    """Zwraca (nowy_stan, diff). diff: new, drops, gone, active, unverified, rejected."""
    today = run["date"]
    first = not state["runs"]
    diff = {"new": [], "drops": [], "gone": [], "active": [], "unverified_new": [], "unverified_all": [],
            "rejected_now": [], "first": first}
    seen_ids = set()
    eligible_ids = set()
    checked = set(run.get("sources_checked", []))
    si = config.get("self_improve", {})
    qlist = run.get("queries", [])
    ok_q = [q for q in qlist if int(q.get("results", 0)) > 0]
    # skan jest „udany”, gdy co najmniej 3 zapytania i połowa z nich zwróciła wyniki – tylko wtedy liczymy zniknięcia
    scan_ok = not qlist or (len(ok_q) >= 3 and len(ok_q) >= len(qlist) / 2)
    diff["scan_ok"] = scan_ok

    for raw in run.get("listings", []):
        if raw.get("is_payment"):
            # kwota to rata/zaliczka – nie wiemy, czy cała cena mieści się w limicie
            w = {k: raw.get(k) for k in ("id", "model", "miles", "city", "state", "url")}
            w["note"] = f"kwota w ogłoszeniu to rata/zaliczka ({fmt_price(raw.get('price'))}), cena całkowita nieznana"
            run.setdefault("watchlist_unpriced", []).append(w)
            continue
        l = normalize(raw, config)
        lid = l["id"]
        seen_ids.add(lid)
        ok, reason = eligibility(l, config)
        prev = state["listings"].get(lid)
        if not ok:
            if prev and prev.get("status") == "active":
                prev["status"] = "gone" if l.get("active") is False else "dropped"
                prev["status_reason"] = reason
                prev["last_seen"] = today
                diff["gone"].append(prev)
            state["rejected"][lid] = {"id": lid, "model": l.get("model"), "price": l.get("price"),
                                      "year": l.get("year"), "family": l.get("family"), "source": l.get("source"),
                                      "location": ", ".join(x for x in (l.get("city"), l.get("state")) if x) or "lokalizacja: brak danych",
                                      "reason": reason,
                                      "url": l.get("url"), "date": today}
            diff["rejected_now"].append(state["rejected"][lid])
            continue
        state["rejected"].pop(lid, None)
        eligible_ids.add(lid)
        l["score"] = score(l, config)
        l["missing_runs"] = 0
        if prev is None:
            l.update(first_seen=today, last_seen=today, status="active", shown=True,
                     price_history=[{"date": today, "price": l["price"]}])
            state["listings"][lid] = l
            (diff["new"] if l.get("verified", True) else diff["unverified_new"]).append(l)
        else:
            old_price = prev.get("price")
            hist = prev.get("price_history", [])
            if old_price != l["price"]:
                hist.append({"date": today, "price": l["price"]})
            merged = {**prev, **l, "price_history": hist, "last_seen": today, "status": "active",
                      "first_seen": prev.get("first_seen") or today}
            # zweryfikowana wcześniej oferta nie traci statusu przez obserwację z indeksu
            merged["verified"] = bool(prev.get("verified")) or bool(l.get("verified", True))
            state["listings"][lid] = merged
            if old_price is not None and l["price"] < old_price:
                merged["old_price"] = old_price
                diff["drops"].append(merged)
            elif prev.get("verified") is False and merged["verified"]:
                diff["new"].append(merged)  # oferta z Facebooka potwierdzona – pokaż jako nową zweryfikowaną
        target = state["listings"][lid]
        (diff["active"] if target.get("verified", True) else diff["unverified_all"]).append(target)

    for lid, l in state["listings"].items():
        if lid in seen_ids or l.get("status") != "active":
            continue
        if l.get("source") not in checked:
            continue
        if l.get("verified", True):
            l["status"] = "gone"
            l["status_reason"] = "nie ma jej już w wynikach"
            diff["gone"].append(l)
        else:
            # indeks wyszukiwarki jest niekompletny – oferta znika dopiero po kilku UDANYCH skanach bez niej
            if not scan_ok:
                continue
            l["missing_runs"] = l.get("missing_runs", 0) + 1
            limit = si.get("gone_after_missing_runs", 3)
            if l["missing_runs"] >= limit:
                l["status"] = "gone"
                l["status_reason"] = (f"niewidziana od {pl_date(l['last_seen'])} ({limit} udane skany bez niej) – "
                                      "to nie musi znaczyć, że jest sprzedana")
                diff["gone"].append(l)

    diff["watch_new"] = []
    wl = state.setdefault("watchlist", {})
    for w in run.get("watchlist_unpriced", []):
        if w["id"] not in wl:
            wl[w["id"]] = dict(w, first_seen=today)
            diff["watch_new"].append(wl[w["id"]])
        wl[w["id"]]["last_seen"] = today

    mark_duplicates([l for l in state["listings"].values() if l.get("status") == "active"])

    # statystyki zapytań – paliwo dla `scout.py improve`.
    # Liczą się trafienia UNIKALNE: oferta pasująca, której w tym przebiegu nie znalazło żadne inne zapytanie.
    qs = state.setdefault("query_stats", {})
    found_by: dict[str, int] = {}
    for q in run.get("queries", []):
        for c in set(q.get("candidates", [])) & eligible_ids:
            found_by[c] = found_by.get(c, 0) + 1
    for q in run.get("queries", []):
        rec = qs.setdefault(q["q"], {"runs": 0, "results": 0, "match_hits": 0, "zero_streak": 0,
                                     "origin": q.get("origin", "config"), "first_run": today})
        cand = set(q.get("candidates", []))
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
        if q.get("origin"):
            rec["origin"] = q["origin"]
    diff["queries"] = run.get("queries", [])

    state["runs"].append(today)
    return state, diff


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


def render(diff: dict, run: dict, config: dict, report_no: int) -> list[str]:
    first = diff["first"]
    show = diff["active"] if first else diff["new"]
    show = sorted(show, key=lambda l: region_key(l, config))
    by_cat = {c: [l for l in show if l.get("category") == c] for c in config["categories"]}
    unverified = sorted(diff["unverified_all"] if first else diff["unverified_new"], key=lambda l: region_key(l, config))

    blocks: list[str] = []
    head = f"# Fat Boy Scout – raport nr {report_no} ({pl_date(run['date'])})"
    fb_only = "cycletrader" not in config.get("sources", ["cycletrader", "facebook"])
    n_new = len(unverified) if fb_only else len(show)
    summary = (f"Pasujące oferty: {n_new}" if first else
               f"Nowe: {n_new} · spadki cen: {len(diff['drops'])} · zniknęły: {len(diff['gone'])}")
    if not fb_only:
        summary += f" · Facebook do weryfikacji: {len(unverified)}"
    if diff.get("watch_new"):
        summary += f" · bez ceny: {len(diff['watch_new'])}"
    blocks.append(f"{head}\n{summary}")

    verified_sources = [s for s in config.get("sources", ["cycletrader", "facebook"]) if s != "facebook"]
    pool = diff["active"] + diff["unverified_all"]
    ranked = sorted([l for l in pool if l.get("price")], key=lambda l: rank_key(l, config))
    if ranked:
        r = config.get("ranking", {})
        tr = r.get("transport", {})
        rate = f"{r.get('usd_per_mile', 0.10):.2f}".replace(".", ",")
        trate = f"{tr.get('usd_per_mile', 0.6):.2f}".replace(".", ",")
        lines = [f"## Ranking: koszt całkowity = cena + {rate} USD za milę przebiegu + dowóz ~{trate} USD za milę "
                 "odległości (oferty bez przebiegu na końcu)"]
        ranked = [l for l in ranked if not l.get("dup_of")]
        for i, l in enumerate(ranked[:r.get("top", 10)], 1):
            loc = ", ".join(x for x in (l.get("city"), l.get("state")) if x) or "lokalizacja: brak danych"
            tag = "" if l.get("verified", True) else " [FB, nieotwarte]"
            tot = total_cost(l, config)
            d, est = distance_of(l)
            d_txt = f"{'~' if est else ''}{fmt_int(d)} mi od Des Plaines" if d is not None else "odległość nieznana"
            tot_txt = f"razem ~{fmt_price(tot)}" if tot is not None else "przebieg do ustalenia"
            lines.append(f"{i}. {l.get('model')} – {fmt_price(l['price'])} – {fmt_miles(l.get('miles'))} – "
                         f"{d_txt} – {tot_txt} – {loc}{tag}\n   {l.get('url') or 'link: brak'}")
        blocks.append("\n".join(lines))
        top = ranked[:r.get("next_steps_top", 3)]
        if top:
            blocks.append(next_steps(top, config))

    for cat, rules in (config["categories"].items() if verified_sources else []):
        items = by_cat.get(cat, [])
        title = f"## {rules['label']}" + ("" if first else " – nowe")
        if items:
            blocks.append(title)
            blocks.extend(block(l, config=config) for l in items)
        else:
            blocks.append(f"{title}\nBrak{'' if first else ' nowych'} ofert spełniających kryteria.")

    if diff["drops"]:
        blocks.append("## Spadki cen")
        for l in sorted(diff["drops"], key=lambda l: region_key(l, config)):
            pct = (l["old_price"] - l["price"]) / l["old_price"] * 100
            blocks.append(block(l, f" (było {fmt_int(l['old_price'])}, −{pct:.1f}%)".replace(".", ","), config=config))

    labels = " / ".join(r["label"] for r in config["categories"].values())
    fb_title = f"## {labels} – Facebook Marketplace" + ("" if first else " – nowe")
    fb_note = ("Oferty pochodzą z indeksu wyszukiwarki. Facebook wymaga logowania, więc ogłoszeń nie otwierano: "
               "cenę, aktywność i title sprawdź po kliknięciu.")
    if unverified:
        blocks.append(f"{fb_title}\n{fb_note}")
        blocks.extend(block(l, config=config) for l in unverified)
    elif not verified_sources:
        blocks.append(f"{fb_title}\nBrak{'' if first else ' nowych'} ofert spełniających kryteria.")

    if diff.get("watch_new"):
        blocks.append("## Facebook – obserwowane bez ceny\nPasujący model, ale indeks nie podaje ceny. Sprawdź je ręcznie.")
        for w in diff["watch_new"]:
            loc = ", ".join(x for x in (w.get("city"), w.get("state")) if x) or "lokalizacja: brak danych"
            line = f"{w['model']} | cena: brak danych | {fmt_miles(w.get('miles'))} | {loc} | title: brak danych"
            blocks.append(f"{line}\n{w['url']}" + (f"\nUwaga: {w['note']}" if w.get("note") else ""))

    if diff["gone"]:
        lines = ["## Niewidziane lub poza kryteriami"]
        for l in diff["gone"]:
            lines.append(f"- {l.get('model')} – {fmt_price(l.get('price'))} – "
                         f"{l.get('city')}, {l.get('state')} – {l.get('status_reason', '')}\n"
                         f"  {l.get('url') or 'link: brak'}")
        blocks.append("\n".join(lines))

    if diff["rejected_now"] and first:
        # oferty powyżej limitu ceny nie są pokazywane wcale – tylko ich liczba
        over = [r for r in diff["rejected_now"] if r["reason"].startswith("cena >")]
        rest = [r for r in diff["rejected_now"] if r not in over]
        lines = ["## Sprawdzone i odrzucone (do 11 000 USD, ale niespełniające innych kryteriów)"]
        lines += [f"- {r['model']} – {fmt_price(r.get('price'))} – {r['location']} – {r['reason']}\n"
                  f"  {r.get('url') or 'link: brak'}" for r in rest]
        if over:
            lines.append(f"Pominięto {len(over)} ofert z ceną powyżej {fmt_int(config['max_price_usd'])} USD.")
        blocks.append("\n".join(lines))

    if not diff.get("scan_ok", True):
        blocks.append("## Uwaga: skan niepełny\nMało zapytań zwróciło wyniki, więc liczniki zniknięć wstrzymano w tym przebiegu.")

    if diff.get("queries"):
        qm = diff.get("query_matches", {})
        hits = sum(1 for v in qm.values() if v)
        blocks.append(f"## Wyszukiwanie\nZapytań: {len(diff['queries'])}, w tym z pasującą ofertą: {hits}. "
                      "Statystyki zapytań są w state.json → query_stats, zmiany planu w improvements.md.")

    cov = run.get("coverage")
    if cov:
        blocks.append("## Zakres\n" + ("\n".join(f"- {c}" for c in cov) if isinstance(cov, list) else cov))
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
    if run["date"] in state["runs"] and not args.dry_run:
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
        (REPORTS_DIR / f"{run['date']}.md").write_text(text + "\n", encoding="utf-8")
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
    today = state["runs"][-1] if state["runs"] else date.today().isoformat()
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
    pa = sub.add_parser("parse", help="wyciągnij oferty z wyników wyszukiwania (JSON: url, title, description)")
    pa.add_argument("file")
    pa.set_defaults(func=cmd_parse)
    rc = sub.add_parser("recall", help="test skuteczności: ile z Twoich ręcznie znalezionych ofert Scout widział")
    rc.add_argument("file", help="plik z linkami (po jednym w linii)")
    rc.set_defaults(func=cmd_recall)
    im = sub.add_parser("improve", help="samodoskonalenie: zapytania i ceny referencyjne")
    im.add_argument("--apply", action="store_true", help="zapisz zmiany w config.json i improvements.md")
    im.set_defaults(func=cmd_improve)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
