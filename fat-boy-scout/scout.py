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
    if l.get("state") not in config["states_priority"]:
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
        if l.get("engine") == "107":
            return False, "wersja 107"
        if l.get("family") not in ("Fat Boy 114", "Fat Bob 114", "Fat Boy", "Fat Bob"):
            return False, "inny model"
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


# ---------------------------------------------------------------- region
def region_key(l: dict, config: dict) -> tuple:
    st = l.get("state")
    prio = config["states_priority"]
    city = (l.get("city") or "").lower()
    dist = l.get("distance_mi")
    metro = (st == "IL") and (city in config["metro_cities"] or (dist is not None and dist <= config["metro_radius_mi"]))
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
    checked = set(run.get("sources_checked", []))

    for raw in run.get("listings", []):
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
                                      "location": f"{l.get('city')}, {l.get('state')}", "reason": reason,
                                      "url": l.get("url"), "date": today}
            diff["rejected_now"].append(state["rejected"][lid])
            continue
        state["rejected"].pop(lid, None)
        l["score"] = score(l, config)
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
        if l.get("source") in checked and l.get("verified", True):
            l["status"] = "gone"
            l["status_reason"] = "nie ma jej już w wynikach"
            diff["gone"].append(l)

    diff["watch_new"] = []
    wl = state.setdefault("watchlist", {})
    for w in run.get("watchlist_unpriced", []):
        if w["id"] not in wl:
            wl[w["id"]] = dict(w, first_seen=today)
            diff["watch_new"].append(wl[w["id"]])
        wl[w["id"]]["last_seen"] = today

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


def score_line(l: dict) -> str | None:
    s = l.get("score") or {}
    parts = []
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


def block(l: dict, price_note: str = "", with_score: bool = True) -> str:
    out = offer_lines(l, price_note)
    sl = score_line(l) if with_score else None
    return f"{out}\n{sl}" if sl else out


def render(diff: dict, run: dict, config: dict, report_no: int) -> list[str]:
    first = diff["first"]
    show = diff["active"] if first else diff["new"]
    show = sorted(show, key=lambda l: region_key(l, config))
    by_cat = {c: [l for l in show if l.get("category") == c] for c in config["categories"]}
    unverified = sorted(diff["unverified_all"] if first else diff["unverified_new"], key=lambda l: region_key(l, config))

    blocks: list[str] = []
    head = f"# Fat Boy Scout – raport nr {report_no} ({pl_date(run['date'])})"
    summary = (f"Pasujące oferty: {len(show)}" if first else
               f"Nowe: {len(show)} · spadki cen: {len(diff['drops'])} · zniknęły: {len(diff['gone'])}")
    summary += f" · Facebook do weryfikacji: {len(unverified)}"
    if diff.get("watch_new"):
        summary += f" · bez ceny: {len(diff['watch_new'])}"
    blocks.append(f"{head}\n{summary}")

    ranked = [l for l in diff["active"] if (l.get("score") or {}).get("discount") is not None]
    ranked.sort(key=lambda l: -l["score"]["discount"])
    if ranked:
        lines = ["## Ranking okazji (wszystkie aktywne, zweryfikowane)"]
        for i, l in enumerate(ranked[:5], 1):
            s = l["score"]
            loc = ", ".join(x for x in (l.get("city"), l.get("state")) if x)
            lines.append(f"{i}. {l.get('model')} – {fmt_price(l['price'])} – {loc} – {s['label']} "
                         f"({round(s['discount'] * 100):+d}%)\n   {l.get('url') or 'link: brak'}")
        blocks.append("\n".join(lines))

    for cat, rules in config["categories"].items():
        items = by_cat.get(cat, [])
        title = f"## {rules['label']}" + ("" if first else " – nowe")
        if items:
            blocks.append(title)
            blocks.extend(block(l) for l in items)
        else:
            blocks.append(f"{title}\nBrak{'' if first else ' nowych'} ofert spełniających kryteria.")

    if diff["drops"]:
        blocks.append("## Spadki cen")
        for l in sorted(diff["drops"], key=lambda l: region_key(l, config)):
            pct = (l["old_price"] - l["price"]) / l["old_price"] * 100
            blocks.append(block(l, f" (było {fmt_int(l['old_price'])}, −{pct:.1f}%)".replace(".", ",")))

    if unverified:
        blocks.append("## Facebook – do ręcznej weryfikacji\nTe oferty pochodzą z indeksu wyszukiwarki. "
                      "Nie zostały otwarte, więc aktywność, cena i title NIE są potwierdzone.")
        blocks.extend(block(l) for l in unverified)

    if diff.get("watch_new"):
        blocks.append("## Facebook – obserwowane bez ceny\nPasujący model, ale indeks nie podaje ceny. Sprawdź je ręcznie.")
        for w in diff["watch_new"]:
            loc = ", ".join(x for x in (w.get("city"), w.get("state")) if x) or "lokalizacja: brak danych"
            line = f"{w['model']} | cena: brak danych | {fmt_miles(w.get('miles'))} | {loc} | title: brak danych"
            blocks.append(f"{line}\n{w['url']}" + (f"\nUwaga: {w['note']}" if w.get("note") else ""))

    if diff["gone"]:
        lines = ["## Zniknęły lub wypadły z kryteriów"]
        for l in diff["gone"]:
            lines.append(f"- {l.get('model')} – {fmt_price(l.get('price'))} – "
                         f"{l.get('city')}, {l.get('state')} – {l.get('status_reason', '')}\n"
                         f"  {l.get('url') or 'link: brak'}")
        blocks.append("\n".join(lines))

    if diff["rejected_now"] and first:
        lines = ["## Sprawdzone i odrzucone"]
        lines += [f"- {r['model']} – {fmt_price(r.get('price'))} – {r['location']} – {r['reason']}\n"
                  f"  {r.get('url') or 'link: brak'}" for r in diff["rejected_now"]]
        blocks.append("\n".join(lines))

    cov = run.get("coverage")
    if cov:
        blocks.append("## Zakres\n" + ("\n".join(f"- {c}" for c in cov) if isinstance(cov, list) else cov))
    return split_parts(blocks, config["report_max_chars"])


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


def cmd_vin(args) -> int:
    print(json.dumps(decode_vin(args.vin, load_json(CONFIG_PATH)), ensure_ascii=False))
    return 0


def cmd_plan(args) -> int:
    cfg = load_json(CONFIG_PATH)
    for s in cfg["searches"]["cycletrader"]:
        print(f"[CT/{s['category']}] {s['name']}{' (+&page=N)' if s.get('paged') else ''}\n  {s['url']}")
    for q in cfg["searches"]["facebook_index"]:
        print(f"[FB-index] {q}")
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
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
