"""Testy silnika Fat Boy Scout: python3 -m unittest fat-boy-scout/test_scout.py"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scout  # noqa: E402

CONFIG = json.loads((Path(__file__).resolve().parent / "config.json").read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    unittest.main()
