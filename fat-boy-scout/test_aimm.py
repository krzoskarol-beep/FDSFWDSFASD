"""Testy importu z ai-marketplace-monitor i poprawek z przeglądu kodu: python3 -m unittest fat-boy-scout/test_aimm.py"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "aimm"))
import import_aimm as ia  # noqa: E402
import scout  # noqa: E402
from test_scout import FB  # noqa: E402


def A(**kw):
    base = {"title": "2019 Harley-Davidson Fat Boy 114", "price": "$10,500", "location": "Joliet, IL",
            "post_url": "/marketplace/item/111222333/?ref=search", "id": "111222333",
            "description": "FLFBS Fat Boy 114, 8,200 miles, clean title.", "seller": "Mike", "image": ""}
    base.update(kw)
    return base


class PriceTests(unittest.TestCase):
    def test_reduced_price_two_amounts(self):
        self.assertEqual(ia.parse_price("$9,500 $10,000"), 9500)
        self.assertEqual(ia.parse_price("$9,500$10,000"), 9500)

    def test_cents_ignored(self):
        self.assertEqual(ia.parse_price("$10,500.00"), 10500)
        self.assertEqual(ia.parse_price("US$10500"), 10500)
        self.assertIsNone(ia.parse_price("Free"))


class TitleTests(unittest.TestCase):
    def test_negated_salvage_is_clean(self):
        self.assertEqual(ia.title_status("Clean title, never salvage or rebuilt."), "clean")
        self.assertEqual(ia.title_status("Not a rebuilt bike. Clean TX title"), "clean")

    def test_real_salvage(self):
        self.assertEqual(ia.title_status("Salvage title due to theft recovery."), "salvage")
        self.assertIsNone(ia.title_status("Runs great."))


class YearMilesTests(unittest.TestCase):
    def test_year_from_unrelated_description_ignored(self):
        self.assertIsNone(ia.year_of("Harley Fat Boy", "new tires in 2023, will deliver within 100 miles"))
        self.assertEqual(ia.year_of("Harley Fat Boy", "Selling my 2019 Harley, great shape"), 2019)

    def test_distance_is_not_mileage(self):
        self.assertIsNone(ia.miles_of("Harley Fat Boy", "Will deliver within 100 miles. 200 miles away from Chicago."))
        self.assertEqual(ia.miles_of("Harley Fat Boy", "Can deliver within 50 miles. Only 6,400 miles on it."), 6400)
        self.assertEqual(ia.miles_of("Fat Boy 114 - 12K miles", ""), 12000)


class ToFbsTests(unittest.TestCase):
    def test_full_listing(self):
        r = ia.to_fbs(A(), "2026-11-14")
        self.assertEqual(r["id"], "fb-111222333")
        self.assertEqual(r["url"], "https://www.facebook.com/marketplace/item/111222333/")
        self.assertEqual((r["price"], r["miles"], r["year"], r["state"], r["title"]), (10500, 8200, 2019, "IL", "clean"))
        self.assertTrue(any("FLFBS" in e["quote"] for e in r["evidence"]))

    def test_id_fallback_and_missing(self):
        r = ia.to_fbs(A(post_url="", id="999"), "2026-11-14")
        self.assertEqual(r["id"], "fb-999")
        self.assertIn("/marketplace/item/999/", r["url"])
        self.assertIsNone(ia.to_fbs(A(post_url="", id=None), "2026-11-14"))

    def test_duplicates_dropped_in_run(self):
        run = ia.build_run([A(), A(price="$10,200")], "2026-11-14")
        self.assertEqual(len(run["listings"]), 1)


class PartialImportTests(unittest.TestCase):
    """Import aimm to wycinek wyników – nie może oznaczać innych ofert jako zniknięte."""

    def test_aimm_import_does_not_mark_others_gone(self):
        fbl = {"id": "fb-555", "source": "facebook", "category": "main", "model": "2020 Harley-Davidson Fat Boy 114",
               "code": "FLFBS", "year": 2020, "price": 10800, "miles": 7000, "city": "Austin", "state": "TX",
               "url": "https://www.facebook.com/marketplace/item/555/", "verified": True}
        st, _ = scout.merge(scout.empty_state(), {"date": "2026-11-12", "sources_checked": ["facebook"],
                                                  "listings": [fbl]}, FB)
        other = A(location="Dallas, TX", post_url="/marketplace/item/777/", id="777")
        st, d = scout.merge(st, ia.build_run([other], "2026-11-14"), FB)
        self.assertEqual(d["gone"], [])
        self.assertEqual(st["listings"]["fb-555"]["status"], "active")


class ReviewFixTests(unittest.TestCase):
    def test_relist_history_keeps_all(self):
        st = scout.empty_state()
        st["listings"]["x"] = {"id": "x", "relist": {"date": "2026-11-01", "previous_id": "a"},
                               "relist_history": {"date": "2026-10-01", "previous_id": "z"}}
        st, _ = scout.merge(st, {"date": "2026-11-14", "sources_checked": [], "listings": []}, FB)
        self.assertEqual([h["previous_id"] for h in st["listings"]["x"]["relist_history"]], ["z", "a"])

    def test_drop_without_old_date_still_explained(self):
        txt = scout.change_line({"old_price": 11200, "price": 10700, "last_seen": "2026-11-14",
                                 "price_history": [{"price": 10700, "date": "2026-11-14"}]}, FB)
        self.assertIn("Poprzednio 11", txt)
        self.assertIn("Spadek o 500", txt.replace(" ", " "))


class WatchlistYearTests(unittest.TestCase):
    def test_year_and_engine_from_title(self):
        w = {"id": "fb-9", "model": "2021 Harley-Davidson Fat Boy 114", "url": "https://www.facebook.com/marketplace/item/9/"}
        known, missing = scout.missing_info(w, FB)
        self.assertIn("rocznik 2021", known)
        self.assertTrue(any(k.startswith("silnik 114") for k in known))
        self.assertNotIn("rocznik", missing)

    def test_2018_without_code_still_needs_engine(self):
        _, missing = scout.missing_info({"model": "2018 Harley-Davidson Fat Boy", "price": 10000}, FB)
        self.assertTrue(any("107" in m for m in missing))


class DashboardTests(unittest.TestCase):
    def sets(self, model="2019 Fat Boy 114"):
        l = scout.normalize({"id": "fb-1", "source": "facebook", "category": "main", "model": model, "code": "FLFBS",
                             "year": 2019, "price": 10000, "miles": 5000, "city": "Joliet", "state": "IL",
                             "url": "https://www.facebook.com/marketplace/item/1/", "verified": False}, FB)
        diff = {"active": [], "unverified_all": [l], "watch_all": [], "new": [], "unverified_new": [l], "drops": []}
        return scout.report_sets(diff, FB)

    def test_html_contains_offer_and_link(self):
        import dashboard
        html = dashboard.build_html(self.sets(), {"date": "2026-11-14", "run_id": "2026-11-14"}, FB, 3)
        self.assertIn("marketplace/item/1/", html)
        self.assertIn('"NOWA"', html)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))

    def test_script_injection_escaped(self):
        import dashboard
        html = dashboard.build_html(self.sets("2019 Fat Boy </script><b>x"), {"date": "2026-11-14"}, FB, 1)
        self.assertNotIn("</script><b>", html)


if __name__ == "__main__":
    unittest.main()
