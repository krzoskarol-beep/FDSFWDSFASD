"""Testy importu z ai-marketplace-monitor i poprawek z przeglądu kodu: python3 -m unittest fat-boy-scout/test_aimm.py"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "aimm"))
import import_aimm as ia  # noqa: E402
import scout  # noqa: E402
from test_scout import FB, FBV  # noqa: E402


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


class SearchFeedbackTests(unittest.TestCase):
    """Ocena wyników dla firecrawl_search_feedback (zwrot 1 kredytu za wyszukiwanie)."""
    RAW = [{"url": "https://example.com/blog", "title": "Harley news", "description": "x"},
           {"url": "https://www.facebook.com/marketplace/item/123/", "title": "2019 Harley-Davidson Fat Boy 114",
            "description": "2019 Harley-Davidson Fat Boy 114 - $10,500, Used, in Joliet, IL. 8K miles"}]

    def test_valuable_position_is_one_indexed_web(self):
        fb = scout.search_feedback({"search_id": "abc", "raw": self.RAW},
                                   [{"url": "https://www.facebook.com/marketplace/item/123/", "price": 10500, "miles": 8000}])
        self.assertEqual(fb["searchId"], "abc")
        self.assertEqual(fb["rating"], "good")
        self.assertEqual([v["position"] for v in fb["valuableResults"]], [2])

    def test_no_listings_is_bad_with_missing_content(self):
        fb = scout.search_feedback({"search_id": "abc", "raw": self.RAW[:1]}, [])
        self.assertEqual(fb["rating"], "bad")
        self.assertTrue(fb["missingContent"])

    def test_no_search_id_no_feedback(self):
        self.assertIsNone(scout.search_feedback({"raw": self.RAW}, []))

    def test_record_keeps_search_id_and_report_shows_refund(self):
        run = {"run_id": "r", "date": "2026-11-14", "plan": [], "queries": [], "listings": [], "watchlist_unpriced": []}
        run = scout.record_query(run, {"q": "fat boy", "search_id": "abc", "raw": self.RAW, "results": 2, "credits": 7}, FB)
        self.assertEqual(run["queries"][0]["search_id"], "abc")
        self.assertEqual(run.pop("_last_feedback")["rating"], "good")
        run["credits_refunded"] = 1
        diff = {"queries": run["queries"], "query_matches": {}, "credits": 7}
        blocks = " ".join(scout.render(dict(diff, first=True, active=[], unverified_all=[], new=[], unverified_new=[],
                                            drops=[], gone=[], relists=[], rejected_now=[], leads_new=[]), run, FB, 1))
        self.assertIn("zwrot za oceny wyników: 1, netto 6", blocks)


class ScanFixTests(unittest.TestCase):
    """Błędy wykryte w przebiegu 2026-11-15."""

    def test_canadian_listing_is_non_us(self):
        o = scout.parse_snippet("2019 Harley-Davidson Fat Boy - $14888, Used, in Winnipeg, Manitoba.",
                                "https://www.facebook.com/marketplace/item/1793799569127594/")[0]
        self.assertTrue(o["non_us"])
        ok, reason = scout.eligibility(scout.normalize(dict(o, price=9000), FB), FB)
        self.assertFalse(ok)
        self.assertIn("poza USA", reason)

    def test_foreign_currency_is_non_us(self):
        out = scout.parse_snippet("2019 Harley-Davidson Fat Boy - CA$9,800, Used, in Calgary, AB.", None)
        out += scout.parse_snippet("2019 Harley-Davidson Fat Boy for sale - Used - $9,800 CA$ in Calgary. Calgary, AB", None)
        self.assertFalse([o for o in out if not o.get("non_us")])   # żadna nie przechodzi jako oferta z USA

    def test_related_items_get_distinct_ids_and_other_listing_flag(self):
        url = "https://www.facebook.com/marketplace/item/1620401672569465/?locale=te_IN"
        text = ("Related: 2020 Harley-Davidson Fat Boy - $27,000, Used, in Brooklyn, NY. "
                "2021 Harley-Davidson Fat Boy for sale - Used - $22,000 nice bike")
        out = scout.parse_snippet(text, url)
        ids = [o["id"] for o in out]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertFalse(any("xx" in i or "-x-" in i for i in ids))
        self.assertTrue(all(o.get("link_is_other_listing") for o in out))

    def test_unknown_state_goes_to_check_not_rejected(self):
        l = scout.normalize({"id": "fb-77", "source": "facebook", "category": "main", "model": "2021 Harley-Davidson Fat Boy 114",
                             "year": 2021, "price": 10900, "miles": 5000, "state": None, "verified": False,
                             "url": "https://www.facebook.com/marketplace/item/77/"}, FB)
        self.assertTrue(scout.eligibility(l, FB)[0], scout.eligibility(l, FB))
        self.assertIn("lokalizacja (stan)", scout.missing_info(l, FB)[1])

    def test_record_from_stdin(self):
        import json, os, subprocess, tempfile
        d = tempfile.mkdtemp()
        env = dict(os.environ, FBS_DATA_DIR=d)
        rid = json.loads(subprocess.run([sys.executable, str(HERE / "scout.py"), "begin"], env=env, capture_output=True,
                                        text=True, check=True).stdout)["run_id"]
        payload = {"q": "test", "results": 1, "credits": 2, "raw": [
            {"url": "https://www.facebook.com/marketplace/item/5/", "title": "2019 Harley-Davidson Fat Boy 114",
             "description": "2019 Harley-Davidson Fat Boy 114 - $10,500, Used, in Joliet, Illinois."}]}
        r = subprocess.run([sys.executable, str(HERE / "scout.py"), "record", rid, "-"], env=env, input=json.dumps(payload),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        run = json.loads((Path(d) / "runs" / f"{rid}.json").read_text())
        self.assertEqual(run["listings"][0]["id"], "fb-5")


class Run1115FixTests(unittest.TestCase):
    def test_neighbour_listing_price_not_taken(self):
        t = "2018 Harley Davidson Fat Boy 114 photo 3. 2017 Harley Sportster 883 - $5,700, Used, in Mandeville, Louisiana."
        self.assertEqual(scout.parse_snippet(t, "https://www.facebook.com/marketplace/item/1531297678396449/"), [])

    def test_repeated_title_still_parsed(self):
        t = "2019 Harley-Davidson Fat Boy 114 - 2019 Harley-Davidson Fat Boy 114 - $10,500, Used, in Joliet, Illinois."
        self.assertEqual(scout.parse_snippet(t, "https://www.facebook.com/marketplace/item/5/")[0]["price"], 10500)

    def test_known_mileage_inherited_and_rejected(self):
        base = {"id": "fb-1075545595270351", "source": "facebook", "category": "main", "model": "2020 Harley-Davidson Fat Boy",
                "year": 2020, "price": 10500, "city": "Nellysford", "state": "VA", "verified": False,
                "url": "https://www.facebook.com/marketplace/item/1075545595270351/"}
        st, _ = scout.merge(scout.empty_state(), {"date": "2026-11-12", "sources_checked": ["facebook"],
                                                  "listings": [dict(base, miles=26000)]}, FBV)
        st, d = scout.merge(st, {"date": "2026-11-15", "sources_checked": ["facebook"], "listings": [dict(base)]}, FBV)
        self.assertNotIn("fb-1075545595270351", [l["id"] for l in d["active"] + d["unverified_all"]])
        self.assertIn("przebieg", st["rejected"]["fb-1075545595270351"]["reason"])


if __name__ == "__main__":
    unittest.main()
