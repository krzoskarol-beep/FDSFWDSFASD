"""Testy silnika Fat Boy Scout: python3 -m unittest fat-boy-scout/test_scout.py"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scout  # noqa: E402

REAL = json.loads((Path(__file__).resolve().parent / "config.json").read_text(encoding="utf-8"))
# Testy reguł ogólnych używają stałego, szerokiego profilu (niezależnego od bieżących ustawień użytkownika)
CONFIG = dict(REAL, scope="midwest", sources=["cycletrader", "facebook"], categories={
    "main": {"label": "Fat Boy 114 / Fat Bob 114", "min_year": 2018, "require_engine": "114",
             "families": ["Fat Boy 114", "Fat Bob 114", "Fat Boy", "Fat Bob"]},
    "challenger": {"label": "Indian Challenger", "min_year": 2020},
    "honda-deal": {"label": "Okazje Honda", "deal_only": True}})
CONFIG["market_reference"] = {"Fat Boy 114": {"2018": 12500, "2019": 13000, "2020": 14000},
                              "Fat Bob 114": {"2018": 12000, "2019": 12500},
                              "Africa Twin": {"2017": 8000}}
# Profil bieżący: tylko Fat Boy, tylko Facebook, cała USA
FB = dict(REAL, scope="usa", sources=["facebook"],
          categories={"main": {"label": "Fat Boy (2018+)", "min_year": 2018, "exclude_engines": ["107"],
                               "families": ["Fat Boy 114", "Fat Boy"]}})


def L(**kw):
    base = {"id": "ct-1", "source": "cycletrader", "category": "main", "model": "2018 Harley-Davidson Fat Bob 114",
            "code": "FXFBS", "year": 2018, "price": 10500, "miles": 9000, "city": "Elmhurst", "state": "IL",
            "url": "https://example.test/1", "verified": True, "active": True}
    base.update(kw)
    return base


def run(listings, d="2026-11-12", sources=("cycletrader",)):
    return {"date": d, "sources_checked": list(sources), "listings": listings}


class VinTests(unittest.TestCase):
    def test_fat_bob_114(self):
        v = scout.decode_vin("1HD1YLK18JC024906", CONFIG)
        self.assertEqual((v["engine"], v["code"], v["year"]), ("114", "FXFBS", 2018))

    def test_fat_bob_107(self):
        self.assertEqual(scout.decode_vin("1HD1YKJ11JC038349", CONFIG)["engine"], "107")

    def test_fat_boy_114(self):
        v = scout.decode_vin("1HD1YGK18M6040539", CONFIG)
        self.assertEqual((v["code"], v["year"]), ("FLFBS", 2021))

    def test_garbage(self):
        self.assertIsNone(scout.decode_vin("123", CONFIG))


class EligibilityTests(unittest.TestCase):
    def check(self, **kw):
        return scout.eligibility(scout.normalize(L(**kw), CONFIG), CONFIG)

    def test_ok(self):
        self.assertEqual(self.check(), (True, "ok"))

    def test_price_limit_inclusive(self):
        self.assertTrue(self.check(price=11000)[0])
        self.assertFalse(self.check(price=11001)[0])

    def test_no_price_and_placeholder(self):
        self.assertFalse(self.check(price=None)[0])
        self.assertFalse(self.check(price=1234)[0])

    def test_region(self):
        self.assertIn("poza regionem", self.check(state="MO")[1])

    def test_107_by_code_and_vin(self):
        self.assertEqual(self.check(model="2018 Harley-Davidson Fat Bob", code="FXFB")[1], "wersja 107")
        self.assertEqual(self.check(model="2018 Harley-Davidson Fat Bob", code=None,
                                    vin="1HD1YKJ11JC038349")[1], "wersja 107")

    def test_year(self):
        self.assertFalse(self.check(year=2017)[0])

    def test_unconfirmed_engine_is_kept_with_flag(self):
        l = scout.normalize(L(model="2019 Harley-Davidson Fat Boy", code=None), CONFIG)
        self.assertTrue(scout.eligibility(l, CONFIG)[0])
        self.assertIn("114 niepotwierdzone", scout.score(l, CONFIG)["flags"])

    def test_honda_needs_deal(self):
        h = dict(category="honda-deal", model="2017 Honda Africa Twin", code=None, year=2017)
        self.assertFalse(self.check(**h, price=7900)[0])
        self.assertTrue(self.check(**h, price=5999)[0])
        self.assertTrue(self.check(**h, price=7900, deal=True)[0])

    def test_sold(self):
        self.assertFalse(self.check(active=False)[0])


class ScopeTests(unittest.TestCase):
    def test_usa_scope(self):
        cfg = dict(CONFIG, scope="usa")
        l = scout.normalize(L(state="FL", city="Tampa", distance_mi=1025), cfg)
        self.assertTrue(scout.eligibility(l, cfg)[0])
        self.assertFalse(scout.eligibility(l, CONFIG)[0])
        near = scout.normalize(L(state="OH", city="Medina", distance_mi=319), cfg)
        far_close = scout.normalize(L(state="KY", city="Georgetown", distance_mi=317), cfg)
        self.assertLess(scout.region_key(near, cfg), scout.region_key(far_close, cfg))

    def test_usa_rejects_non_us(self):
        cfg = dict(CONFIG, scope="usa")
        self.assertFalse(scout.eligibility(scout.normalize(L(state="ON"), cfg), cfg)[0])


class ScoreTests(unittest.TestCase):
    def test_salvage_flag_and_penalty(self):
        clean = scout.score(scout.normalize(L(price=9000), CONFIG), CONFIG)
        salv = scout.score(scout.normalize(L(price=9000, title="Rebuilt"), CONFIG), CONFIG)
        self.assertLess(salv["discount"], clean["discount"])
        self.assertTrue(any("Rebuilt" in f for f in salv["flags"]))

    def test_suspicious(self):
        s = scout.score(scout.normalize(L(price=4000), CONFIG), CONFIG)
        self.assertTrue(any("podejrzanie" in f for f in s["flags"]))


class MergeTests(unittest.TestCase):
    def test_first_report_shows_all_then_only_changes(self):
        st = scout.empty_state()
        st, d1 = scout.merge(st, run([L(id="a"), L(id="b", price=10900)]), CONFIG)
        self.assertTrue(d1["first"])
        self.assertEqual(len(d1["active"]), 2)

        st, d2 = scout.merge(st, run([L(id="a", price=9900), L(id="b", price=10900), L(id="c")],
                                     d="2026-11-19"), CONFIG)
        self.assertFalse(d2["first"])
        self.assertEqual([l["id"] for l in d2["new"]], ["c"])
        self.assertEqual([(l["id"], l["old_price"]) for l in d2["drops"]], [("a", 10500)])
        self.assertEqual(len(st["listings"]["a"]["price_history"]), 2)

        st, d3 = scout.merge(st, run([L(id="c")], d="2026-11-26"), CONFIG)
        self.assertEqual(sorted(l["id"] for l in d3["gone"]), ["a", "b"])

    def test_gone_only_for_checked_sources(self):
        st = scout.empty_state()
        st, _ = scout.merge(st, run([L(id="a")]), CONFIG)
        st, d = scout.merge(st, run([], d="2026-11-19", sources=("facebook",)), CONFIG)
        self.assertEqual(d["gone"], [])

    def test_price_rise_above_limit_drops_out(self):
        st = scout.empty_state()
        st, _ = scout.merge(st, run([L(id="a")]), CONFIG)
        st, d = scout.merge(st, run([L(id="a", price=11500)], d="2026-11-19"), CONFIG)
        self.assertEqual([l["id"] for l in d["gone"]], ["a"])
        self.assertIn("a", st["rejected"])

    def test_rejected_then_price_drop_becomes_new(self):
        st = scout.empty_state()
        st, _ = scout.merge(st, run([L(id="a", price=12000)]), CONFIG)
        st, d = scout.merge(st, run([L(id="a", price=10800)], d="2026-11-19"), CONFIG)
        self.assertEqual([l["id"] for l in d["new"]], ["a"])
        self.assertNotIn("a", st["rejected"])

    def test_facebook_unverified_then_verified(self):
        st = scout.empty_state()
        fb = L(id="fb-1", source="facebook", verified=False)
        st, d = scout.merge(st, run([fb], sources=("cycletrader", "facebook")), CONFIG)
        self.assertEqual(len(d["unverified_all"]), 1)
        st, d = scout.merge(st, run([dict(fb, verified=True)], d="2026-11-19"), CONFIG)
        self.assertEqual([l["id"] for l in d["new"]], ["fb-1"])


class RenderTests(unittest.TestCase):
    def test_two_line_format_and_sorting(self):
        st = scout.empty_state()
        ls = [L(id="oh", city="Medina", state="OH", distance_mi=319),
              L(id="chi", city="Elmhurst", state="IL", distance_mi=12),
              L(id="wi", city="Big Bend", state="WI", distance_mi=61)]
        st, d = scout.merge(st, run(ls), CONFIG)
        text = "\n".join(scout.render(d, run(ls), CONFIG, 1))
        text = text[text.index("## Fat Boy 114"):]
        self.assertLess(text.index("Elmhurst, IL"), text.index("Big Bend, WI"))
        self.assertLess(text.index("Big Bend, WI"), text.index("Medina, OH"))
        line = next(x for x in text.splitlines() if "Elmhurst, IL |" in x)
        self.assertEqual(line.count(" | "), 4)
        nxt = text.splitlines()[text.splitlines().index(line) + 1]
        self.assertTrue(nxt.startswith("https://"))

    def test_every_offer_has_link(self):
        st = scout.empty_state()
        ls = [L(id="a"), L(id="rej", state="MO", url="https://example.test/rej"),
              L(id="fb", source="facebook", verified=False, url="https://example.test/fb")]
        st, d = scout.merge(st, run(ls), CONFIG)
        text = "\n".join(scout.render(d, run(ls), CONFIG, 1))
        self.assertIn("https://example.test/rej", text)
        self.assertIn("https://example.test/fb", text)
        rank = text[text.index("## Ranking"):text.index("## Fat Boy 114")]
        self.assertIn("https://example.test/1", rank)
        st, d = scout.merge(st, run([], d="2026-11-19"), CONFIG)
        self.assertIn("https://example.test/1", "\n".join(scout.render(d, run([]), CONFIG, 2)))

    def test_split_parts(self):
        parts = scout.split_parts(["x" * 100] * 10, 350)
        self.assertGreater(len(parts), 1)
        self.assertTrue(parts[0].startswith("**Część 1/"))
        self.assertTrue(all(len(p) < 450 for p in parts))

    def test_over_limit_never_listed(self):
        st = scout.empty_state()
        ls = [L(id="a"), L(id="drogi", price=12500, url="https://example.test/drogi")]
        st, d = scout.merge(st, run(ls), CONFIG)
        text = "\n".join(scout.render(d, run(ls), CONFIG, 1))
        self.assertNotIn("https://example.test/drogi", text)
        self.assertNotIn("12\u00a0500", text)
        self.assertIn("Pominięto 1 ofert", text)

    def test_header_not_orphaned(self):
        parts = scout.split_parts(["# T", "## Sekcja", "x" * 300 + " https://a"], 320)
        self.assertTrue(all(not p.rstrip().endswith("## Sekcja") for p in parts))
        self.assertTrue(any("## Sekcja\n\nxxx" in p for p in parts))

    def test_migrate_v1(self):
        v1 = {"last_report": "2026-11-12",
              "shown": [{"id": "ct-x", "model": "2018 Harley-Davidson Fat Bob 114 (FXFBS)", "url": "u",
                         "location": "Elmhurst, IL", "miles": 1, "price_history": [{"date": "2026-11-12", "price": 10999}]}],
              "rejected": [{"id": "r", "model": "m", "location": "x", "price": 1, "reason": "107"}]}
        st = scout.migrate(copy.deepcopy(v1))
        self.assertEqual(st["listings"]["ct-x"]["state"], "IL")
        self.assertEqual(st["listings"]["ct-x"]["price"], 10999)
        self.assertIn("r", st["rejected"])


class FacebookOnlyTests(unittest.TestCase):
    def fb(self, **kw):
        base = dict(id="fb-1", source="facebook", verified=False, model="2018 Harley-Davidson Fat Boy 114",
                    code=None, state="TX", city="Forney")
        base.update(kw)
        return L(**base)

    def test_fat_bob_rejected_fat_boy_ok(self):
        self.assertTrue(scout.eligibility(scout.normalize(self.fb(), FB), FB)[0])
        bob = scout.normalize(self.fb(model="2018 Harley-Davidson Fat Bob 114"), FB)
        self.assertIn("inny model", scout.eligibility(bob, FB)[1])

    def test_engine_by_year(self):
        self.assertEqual(scout.normalize(self.fb(model="2021 Harley-Davidson Fat Boy", year=2021), FB)["engine"], "114")
        l2020 = scout.normalize(self.fb(model="2020 Harley-Davidson Fat Boy", year=2020), FB)
        self.assertIsNone(l2020.get("engine"))
        self.assertIn("114 niepotwierdzone", scout.score(l2020, FB)["flags"])
        self.assertEqual(scout.normalize(self.fb(model="2018 Harley-Davidson FLFBS Fatboy", year=2018), FB)["engine"], "114")
        self.assertEqual(scout.normalize(self.fb(model="2018 Harley-Davidson FLFB Fat Boy", year=2018), FB)["engine"], "107")
        l = scout.normalize(self.fb(model="2025 Harley-Davidson Fat Boy", year=2025), FB)
        self.assertEqual(l["engine"], "117")
        self.assertEqual(scout.eligibility(l, FB)[1], "ok")  # bez górnej granicy rocznika
        self.assertIsNone(scout.normalize(self.fb(model="2018 Harley-Davidson Fat Boy", year=2018), FB).get("engine"))

    def test_report_lists_fb_offers_as_main_section(self):
        st, d = scout.merge(scout.empty_state(), run([self.fb()], sources=("facebook",)), FB)
        text = "\n".join(scout.render(d, run([self.fb()]), FB, 1))
        self.assertIn("Pasujące oferty: 1", text)
        self.assertIn("## Fat Boy (2018+) – Facebook Marketplace", text)
        self.assertIn("[FB, nieotwarte]", text)

    def test_fb_gone_after_missing_runs(self):
        good = [{"q": f"q{i}", "results": 10, "candidates": []} for i in range(4)]
        st, _ = scout.merge(scout.empty_state(), run([self.fb()], sources=("facebook",)), FB)
        for d in ("2026-11-19", "2026-11-26"):
            st, diff = scout.merge(st, dict(run([], d=d, sources=("facebook",)), queries=good), FB)
            self.assertEqual(diff["gone"], [])
        st, diff = scout.merge(st, dict(run([], d="2026-12-03", sources=("facebook",)), queries=good), FB)
        self.assertEqual([l["id"] for l in diff["gone"]], ["fb-1"])
        self.assertIn("niewidziana od 12.11.2026", diff["gone"][0]["status_reason"])

    def test_failed_scan_does_not_count(self):
        bad = [{"q": f"q{i}", "results": 0, "candidates": []} for i in range(4)]
        st, _ = scout.merge(scout.empty_state(), run([self.fb()], sources=("facebook",)), FB)
        for d in ("2026-11-19", "2026-11-26", "2026-12-03", "2026-12-10"):
            st, diff = scout.merge(st, dict(run([], d=d, sources=("facebook",)), queries=bad), FB)
            self.assertEqual(diff["gone"], [])
            self.assertFalse(diff["scan_ok"])

    def test_payment_goes_to_watchlist(self):
        st, d = scout.merge(scout.empty_state(), run([self.fb(price=299, is_payment=True)], sources=("facebook",)), FB)
        self.assertEqual(st["listings"], {})
        self.assertIn("rata/zaliczka", d["watch_new"][0]["note"])

    def test_unique_hits(self):
        r = dict(run([self.fb()], sources=("facebook",)), queries=[
            {"q": "a", "results": 5, "candidates": ["fb-1"]}, {"q": "b", "results": 5, "candidates": ["fb-1"]}])
        st, _ = scout.merge(scout.empty_state(), r, FB)
        self.assertEqual(st["query_stats"]["a"]["unique_hits"], 0)
        self.assertEqual(st["query_stats"]["a"]["match_hits"], 1)


class MileageLimitTests(unittest.TestCase):
    def test_max_miles(self):
        cfg = dict(FB, categories={"main": dict(FB["categories"]["main"], max_miles=15000)})
        mk = lambda m: scout.normalize(L(id="m", source="facebook", verified=False, model="2018 Harley-Davidson Fat Boy 114",
                                         code=None, state="TX", miles=m), cfg)
        self.assertTrue(scout.eligibility(mk(15000), cfg)[0])
        self.assertEqual(scout.eligibility(mk(15001), cfg)[1], "przebieg > 15\u00a0000 mi")
        self.assertTrue(scout.eligibility(mk(None), cfg)[0])  # nieznany przebieg zostaje z flagą


class RankingTests(unittest.TestCase):
    def test_price_and_miles(self):
        a = dict(price=10500, miles=2000)    # 10 700
        b = dict(price=10000, miles=20000)   # 12 000
        c = dict(price=9000, miles=None)     # bez przebiegu – na końcu
        order = sorted([b, c, a], key=lambda l: scout.rank_key(l, FB))
        self.assertEqual(order, [a, b, c])
        self.assertEqual(scout.effective_price(a, FB), 10700)


class GeoAndCostTests(unittest.TestCase):
    def test_distance_estimates(self):
        import geo
        self.assertEqual(geo.estimate_road_miles("IL", metro=True), 15)
        self.assertLess(geo.estimate_road_miles("WI"), geo.estimate_road_miles("TX"))
        self.assertGreater(geo.estimate_road_miles("OR"), 1800)
        self.assertEqual(geo.state_code("Florida"), "FL")

    def test_transport_changes_ranking(self):
        cfg = dict(FB, ranking={"usd_per_mile": 0.10, "transport": {"usd_per_mile": 0.6, "free_within_mi": 300}})
        near = scout.normalize(L(id="n", model="2018 Harley-Davidson Fat Boy 114", price=10500, miles=5000,
                                 state="WI", city="Caledonia", distance_mi=60), cfg)
        far = scout.normalize(L(id="f", model="2018 Harley-Davidson Fat Boy 114", price=10000, miles=5000,
                                state="OR", city="Brookings"), cfg)
        self.assertEqual(scout.transport_cost(near, cfg), 0)
        self.assertGreater(scout.transport_cost(far, cfg), 1000)
        self.assertEqual(sorted([far, near], key=lambda l: scout.rank_key(l, cfg))[0]["id"], "n")

    def test_duplicates(self):
        a = dict(id="fb-a", year=2018, state="CT", price=9000, miles=9900)
        b = dict(id="fb-b", year=2018, state="CT", price=9000, miles=9900)
        c = dict(id="fb-c", year=2018, state="CT", price=9000, miles=20000)
        scout.mark_duplicates([a, b, c])
        self.assertEqual(b["dup_of"], "fb-a")
        self.assertNotIn("dup_of", c)


class ParserTests(unittest.TestCase):
    def test_pattern_a_title(self):
        o = scout.parse_snippet("2018 Harley-Davidson FAT BOY - $9995, Used, in Ormond Beach, Florida. Browse similar",
                                "https://www.facebook.com/marketplace/item/1687282615899659/")
        self.assertEqual(len(o), 1)
        self.assertEqual((o[0]["id"], o[0]["price"], o[0]["state"]), ("fb-1687282615899659", 9995, "FL"))

    def test_pattern_b_related_with_miles(self):
        s = ("Harley Davidson for sale in Kellogg, Idaho. 2018 Harley-Davidson fat boy 114 flfbs for sale - Used - "
             "$10,500 in Rathdrum. Price drop. $10,500. 2018 Harley-Davidson fat boy 114 flfbs. 1K miles. Rathdrum, ID")
        o = scout.parse_snippet(s, "https://www.facebook.com/marketplace/kellogg-id/harley-davidson/")
        self.assertEqual((o[0]["price"], o[0]["miles"], o[0]["state"]), (10500, 1000, "ID"))
        self.assertTrue(o[0]["price_drop"])
        self.assertEqual(o[0]["id"], "fb-rathdrum-id-2018")

    def test_pattern_c_listed(self):
        o = scout.parse_snippet("2018 Harley-Davidson Fat Boy 114 - Motorcycles & Scooters - 2018 Harley-Davidson Fat Boy 114. "
                                "$12,999. Listed 11 hours ago · Defiance, OH ...",
                                "https://www.facebook.com/marketplace/item/891120917356759/")
        self.assertEqual((o[0]["id"], o[0]["price"], o[0]["city"], o[0]["state"], o[0]["listed"]),
                         ("fb-891120917356759", 12999, "Defiance", "OH", "11 hours ago"))

    def test_miles_formats(self):
        self.assertEqual(scout._miles("6.3K miles"), 6300)
        self.assertEqual(scout._miles("Driven 31,000 miles."), 31000)
        self.assertEqual(scout._miles("9800 miles. Must see"), 9800)


class RecallTests(unittest.TestCase):
    def test_item_id(self):
        self.assertEqual(scout.item_id("https://www.facebook.com/marketplace/item/123/?ref=x"), "fb-123")


class ImproveTests(unittest.TestCase):
    def cfg(self):
        c = json.loads(json.dumps(FB))
        c["searches"]["facebook_index"] = [{"q": "seed-q", "origin": "seed", "status": "active"},
                                           {"q": "auto-dead", "origin": "auto", "status": "active"}]
        c["market_reference"] = {"Fat Boy 114": {"2018": 12500}}
        c["self_improve"] = dict(c["self_improve"], min_samples_for_price=3)
        return c

    def test_query_stats_prune_and_promote(self):
        cfg = self.cfg()
        st = scout.empty_state()
        listing = dict(id="fb-x", source="facebook", category="main", model="2018 Harley-Davidson Fat Boy 114",
                       year=2018, price=10000, city="Hartford", state="MI", verified=False, url="u")
        r = {"date": "2026-11-12", "sources_checked": ["facebook"], "listings": [listing], "queries": [
            {"q": "seed-q", "results": 5, "candidates": []},
            {"q": "auto-dead", "results": 5, "candidates": []},
            {"q": "exp-good", "results": 3, "candidates": ["fb-x"], "origin": "experiment"}]}
        st, _ = scout.merge(st, r, cfg)
        for d in ("2026-11-19", "2026-11-26"):
            st, _ = scout.merge(st, dict(r, date=d, queries=r["queries"][:2]), cfg)
        new, log = scout.improve(st, cfg, "2026-11-26")
        status = {q["q"]: q["status"] for q in new["searches"]["facebook_index"]}
        self.assertEqual(status["auto-dead"], "retired")
        self.assertEqual(status["seed-q"], "active")
        self.assertEqual(status["exp-good"], "active")
        self.assertIn('site:facebook.com/marketplace "Fat Boy" "Hartford"', status)

    def test_price_calibration(self):
        cfg = self.cfg()
        st = scout.empty_state()
        st["rejected"] = {str(i): {"id": str(i), "family": "Fat Boy 114", "year": 2018, "price": p,
                                   "location": f"miasto{i}", "reason": "cena > 11 000 USD"}
                          for i, p in enumerate([11500, 12000, 14500])}
        new, log = scout.improve(st, cfg, "2026-11-12")
        self.assertEqual(new["market_reference"]["Fat Boy 114"]["2018"], 12250)  # (12500 + 12000) / 2
        self.assertTrue(any("Cena referencyjna" in x for x in log))

    def test_107_not_used_for_calibration(self):
        cfg = self.cfg()
        st = scout.empty_state()
        st["rejected"] = {str(i): {"family": "Fat Boy", "year": 2018, "price": 5000, "reason": "wersja 107"} for i in range(5)}
        new, _ = scout.improve(st, cfg, "2026-11-12")
        self.assertEqual(new["market_reference"]["Fat Boy 114"]["2018"], 12500)


if __name__ == "__main__":
    unittest.main()
