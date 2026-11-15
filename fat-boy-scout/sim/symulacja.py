#!/usr/bin/env python3
"""SYMULACJA przebiegu /fat-boy-scout – te same polecenia CLI, których używa agent (begin → record → finish),
każde jako osobny proces. Dane są zmyślone (example.test / numery 9000xxx), zapisywane w osobnym katalogu
(FBS_DATA_DIR), więc prawdziwy stan w fat-boy-scout/state.json pozostaje nietknięty.

Scenariusz:
  przebieg A (05.11): VIN 1HD1YGK13JC012345 za 11 500 USD (powyżej limitu – cena zapamiętana)
  przebieg B (12.11): 10 zapytań (8 regionów + Softail + wariant). Przerwanie po 5 regionach
                      (ostatnie zapytanie kończy się błędem „brak kredytów”), wznowienie kolejnym
                      `begin`, dokończenie pozostałych, finish.
Użycie: python3 fat-boy-scout/sim/symulacja.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOUT = HERE.parent / "scout.py"
DATA = HERE / "_dane"
REAL_CFG = json.loads((HERE.parent / "config.json").read_text(encoding="utf-8"))

REGIONS = {"Midwest": ["IL", "WI", "IN", "MI", "IA", "OH", "MN", "MO"], "Plains i Góry": ["KS", "NE", "SD", "ND", "MT", "WY", "CO"],
           "Zachód": ["WA", "OR", "ID", "UT", "NV", "CA"], "Południowy zachód": ["TX", "OK", "NM", "AZ"],
           "Południe": ["LA", "MS", "AR", "AL", "TN", "KY"], "Południowy wschód": ["FL", "GA", "SC", "NC", "VA", "WV"],
           "Północny wschód": ["PA", "NY", "NJ", "CT", "MA", "MD", "DE"], "Nowa Anglia": ["ME", "NH", "VT", "RI"]}
NAMES = list(REGIONS)


def item(n):
    return f"https://www.facebook.com/marketplace/item/{n}/"


def fb(n, **kw):
    d = dict(id=f"fb-{n}", source="facebook", category="main", verified=False, model="2018 Harley-Davidson Fat Boy 114",
             code="FLFBS", year=2018, price=10000, miles=8000, url=item(n))
    d.update(kw)
    return d


def sh(*args):
    env = dict(os.environ, FBS_DATA_DIR=str(DATA), FBS_CONFIG=str(DATA / "config.json"))
    p = subprocess.run([sys.executable, str(SCOUT), *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def record(rid, payload):
    f = DATA / "payload.json"
    f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    code, out, err = sh("record", rid, str(f))
    print(f"  record {payload['q'][:48]:<48} → {out.strip() or err.strip()}")


def regional(name, offers, credits=8):
    s = REGIONS[name]
    raw = [{"url": "https://www.facebook.com/marketplace/x/harley-davidson/", "title": "Harley Davidson for sale",
            "description": "; ".join(f"2012 Harley-Davidson Road King. Town, {st}" for st in s)}]
    return {"q": f"[SYM] region {name}", "results": 30, "raw": raw, "listings": offers, "credits": credits}


def main():
    shutil.rmtree(DATA, ignore_errors=True)
    DATA.mkdir(parents=True)
    cfg = json.loads(json.dumps(REAL_CFG))
    cfg["searches"]["facebook_index"] = (
        [{"q": f"[SYM] region {n}", "origin": "seed", "status": "active", "region": n, "states": s} for n, s in REGIONS.items()]
        + [{"q": "[SYM] 2018 Harley Softail", "origin": "seed", "status": "active", "broad": True},
           {"q": "[SYM] Fatboy", "origin": "seed", "status": "active"}])
    (DATA / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    print("== Przebieg A (05.11.2026): wcześniejsza obserwacja powyżej limitu ==")
    code, out, _ = sh("begin", "--date", "2026-11-05")
    rid_a = json.loads(out)["run_id"]
    record(rid_a, regional("Midwest", [fb(9000100, vin="1HD1YGK13JC012345", price=11500, miles=6900,
                                          city="Naperville", state="IL", distance_mi=30)]))
    for n in NAMES[1:]:
        record(rid_a, regional(n, []))
    record(rid_a, {"q": "[SYM] 2018 Harley Softail", "results": 0, "raw": [], "credits": 2})
    record(rid_a, {"q": "[SYM] Fatboy", "results": 0, "raw": [], "credits": 2})
    code, out, err = sh("finish", rid_a)
    print(f"  finish → kod {code}")

    print("\n== Przebieg B (12.11.2026): przerwanie po 5 regionach ==")
    code, out, _ = sh("begin", "--date", "2026-11-12")
    b = json.loads(out)
    rid = b["run_id"]
    print(f"  begin → run_id {rid}, wznowiony: {b['resumed']}, do zrobienia: {len(b['remaining'])}")
    offers = {
        "Midwest": [fb(9000200, vin="1HD1YGK13JC012345", price=10700, miles=7050, city="Naperville", state="IL",
                       distance_mi=30, notes="nowy link, ten sam VIN co oferta z 05.11"),
                    fb(9000201, price=10900, miles=12400, city="Caledonia", state="WI", distance_mi=60),
                    fb(9000202, price=9500, miles=None, city="Hartford", state="MI", distance_mi=170, code=None,
                       model="2018 Harley-Davidson Fat Boy")],
        "Plains i Góry": [fb(9000210, price=10450, miles=3100, city="Denver", state="CO", distance_mi=1000)],
        "Zachód": [fb(9000220, price=10500, miles=1000, city="Rathdrum", state="ID", distance_mi=1700),
                   fb(9000221, price=12900, miles=2000, city="Boise", state="ID")],                  # powyżej limitu
        "Południowy zachód": [fb(9000230, price=11000, miles=2500, city="Forney", state="TX", distance_mi=960)],
        "Południe": [],
    }
    for n in NAMES[:5]:
        record(rid, regional(n, offers[n]))
    record(rid, {"q": "[SYM] region Południowy wschód", "status": "error", "error": "Firecrawl: brak kredytów (402)"})
    print("  *** symulowane przerwanie: brak kredytów, proces kończy się bez finish ***")
    code, out, _ = sh("finish", rid)
    print(f"  finish (przedwczesne) → kod {code}: {out.strip()[:110]}")

    print("\n== Kolejne /fat-boy-scout: wznowienie ==")
    code, out, _ = sh("begin", "--date", "2026-11-12")
    b = json.loads(out)
    print(f"  begin → run_id {b['run_id']}, wznowiony: {b['resumed']}, wykonane: {b['done']}, pozostało: {len(b['remaining'])}")
    for q in b["remaining"]:
        print(f"     - {q}")
    record(rid, regional("Południe", []))   # ponowny zapis zapytania sprzed przerwania – nie może dublować
    record(rid, regional("Południowy wschód", [fb(9000250, price=8900, miles=14800, city="Tampa", state="FL", distance_mi=1150)]))
    record(rid, regional("Północny wschód", [fb(9000260, price=9000, miles=9900, city="Madison", state="CT", distance_mi=900)]))
    record(rid, regional("Nowa Anglia", []))
    softail_raw = [{"url": item(9000270), "title": "2018 Harley Softail",
                    "description": "2018 Harley Softail - $10200, Used, in Rockford, Illinois. Garage kept."},
                   {"url": item(9000271), "title": "2019 Harley Softail",
                    "description": "2019 Harley Softail - $9800, Used, in Joliet, Illinois."},
                   {"url": item(9000272), "title": "2018 Harley Softail",
                    "description": "2018 Harley Softail - $9900, Used, in Peoria, Illinois."}]
    record(rid, {"q": "[SYM] 2018 Harley Softail", "results": 3, "raw": softail_raw, "credits": 8, "listings": [
        fb(9000270, model="2018 Harley Softail", listing_title="2018 Harley Softail", code=None, price=10200, miles=6200,
           city="Rockford", state="IL", distance_mi=75,
           evidence=[{"quote": "Selling my 2018 Fat Boy 114 (FLFBS), Milwaukee-Eight 114, 6,200 miles, clean title",
                      "url": item(9000270)}]),
        fb(9000271, model="2019 Harley Softail", listing_title="2019 Harley Softail", code=None, year=2019, price=9800, miles=8800,
           city="Joliet", state="IL", distance_mi=40,
           basis="opis: „solid Lakester wheels, 240 rear tire” – charakterystyczne dla Fat Boya; silnik niepodany"),
        fb(9000272, model="2018 Harley Softail", listing_title="2018 Harley Softail", code=None, price=9900, miles=None,
           city="Peoria", state="IL", distance_mi=160)]})
    record(rid, {"q": "[SYM] Fatboy", "results": 1, "credits": 8, "raw": [
        {"url": "https://www.facebook.com/marketplace/kellogg-id/harley-davidson/", "title": "Harley Davidson for sale in Kellogg, Idaho",
         "description": "2018 Harley-Davidson fat boy 114 flfbs for sale - Used - $10,500 in Rathdrum. Price drop. $10,500. "
                        "2018 Harley-Davidson fat boy 114 flfbs. 1K miles. Rathdrum, ID"}]})
    code, text, err = sh("finish", rid)
    print(f"  finish → kod {code}")
    (HERE / "przykladowy_raport.md").write_text("> **DANE SYMULOWANE** – zmyślone ogłoszenia do sprawdzenia działania "
                                                 "silnika. To nie są prawdziwe oferty.\n\n" + text, encoding="utf-8")
    st = json.loads((DATA / "state.json").read_text(encoding="utf-8"))
    dup_hist = {k: len(v["price_history"]) for k, v in st["listings"].items()}
    print("\n== Kontrola ==")
    print(f"  przebiegi w stanie: {st['runs']}")
    print(f"  oferty w historii: {len(st['listings'])}, odrzucone: {len(st['rejected'])}, tropy: {len(st['leads'])}")
    print(f"  wpisy historii cen na ofertę: {dup_hist}")
    run = json.loads((DATA / 'runs' / f'{rid}.json').read_text(encoding='utf-8'))
    print(f"  zapytania w przebiegu B: {len(run['queries'])} (błędów: {sum(q['status']=='error' for q in run['queries'])}), "
          f"kredyty (symulowane): {run['credits_used']}")
    code, out, _ = sh("begin", "--date", "2026-11-13")
    nb = json.loads(out)
    print(f"  kolejne begin po zakończeniu → wznowiony: {nb['resumed']} (nowy przebieg {nb['run_id']}, "
          f"do zrobienia {len(nb['remaining'])})")
    code, out, _ = sh("todo")
    print("  todo (fragment):\n    " + "\n    ".join(out.strip().splitlines()[:6]))


if __name__ == "__main__":
    main()
