"""Testy klienta HTTP i logiki fallbacku — bez sieci i bez prawdziwego czekania."""

import json
from unittest import mock

import pytest
import requests

from scraper import runner
from scraper.api import create_app
from scraper.http_client import USER_AGENTS, BlockedError, PersistentSession


def make_resp(status, body="<html></html>", ctype="text/html"):
    resp = requests.Response()
    resp.status_code = status
    resp._content = body.encode()
    resp.headers["Content-Type"] = ctype
    resp.url = "https://example.test/"
    return resp


@pytest.fixture
def client(tmp_path):
    sleeps = []
    c = PersistentSession(tmp_path / "cookies.json", sleep=sleeps.append)
    c.sleeps = sleeps
    return c


def test_ten_user_agents():
    assert len(USER_AGENTS) == 10 and len(set(USER_AGENTS)) == 10


def test_cookies_and_identity_persist(tmp_path):
    path = tmp_path / "cookies.json"
    c1 = PersistentSession(path, sleep=lambda s: None)
    c1.session.cookies.set("datadome", "abc", domain=".allegro.pl", path="/")
    c1.save_state()

    c2 = PersistentSession(path, sleep=lambda s: None)
    assert c2.session.cookies.get("datadome", domain=".allegro.pl") == "abc"
    assert c2.user_agent == c1.user_agent  # UA przypięty do cookies
    assert c2.has_cookies_for("allegro.pl")
    assert json.loads(path.read_text())["cookies"][0]["name"] == "datadome"


def test_headers_consistent_with_browser(client):
    client.identity["user_agent"] = USER_AGENTS[6]  # Firefox
    assert "Sec-CH-UA" not in client.build_headers("https://allegro.pl/")
    client.identity["user_agent"] = USER_AGENTS[0]  # Chrome
    h = client.build_headers("https://allegro.pl/listing", referer="https://allegro.pl/")
    assert h["Sec-Fetch-Site"] == "same-origin"
    assert "Google Chrome" in h["Sec-CH-UA"]


def test_header_order_is_shuffled(client):
    orders = {tuple(client.build_headers("https://allegro.pl/")) for _ in range(30)}
    assert len(orders) > 1


def test_delay_range(client):
    with mock.patch.object(client.session, "get", return_value=make_resp(200)):
        client.get("https://allegro.pl/")
    assert 2 <= client.sleeps[0] <= 8


def test_403_retries_three_times_then_blocked(client):
    with mock.patch.object(client.session, "get", return_value=make_resp(403)) as get:
        with pytest.raises(BlockedError):
            client.get("https://allegro.pl/listing?string=x")
    assert get.call_count == 4  # 1 próba + 3 ponowienia
    block_waits = [s for s in client.sleeps if s >= 30]
    assert len(block_waits) == 3 and all(30 <= s <= 90 for s in block_waits)


def test_403_then_success(client):
    responses = [make_resp(403), make_resp(200, "ok")]
    with mock.patch.object(client.session, "get", side_effect=responses):
        assert client.get("https://allegro.pl/").text == "ok"


def test_datadome_challenge_with_200_is_blocked(client):
    body = '<html><script src="https://ct.captcha-delivery.com/c.js"></script></html>'
    with mock.patch.object(client.session, "get", return_value=make_resp(200, body)):
        with pytest.raises(BlockedError):
            client.get("https://allegro.pl/")


def test_fallback_when_allegro_blocked(client, tmp_path):
    ceneo_html = ('<div class="cat-prod-row" data-productname="P" data-productminprice="5">'
                  '<a href="/1">P</a></div>')
    morele_html = ('<div class="cat-product" data-product-name="M" data-product-price="7">'
                   '<a class="productLink" href="/m/">M</a></div>')

    def fake_get(url, **kwargs):
        if "allegro" in url:
            return make_resp(403)
        if "ceneo" in url:
            return make_resp(200, ceneo_html)
        return make_resp(200, morele_html)

    out = tmp_path / "last_scan.json"
    with mock.patch.object(client.session, "get", side_effect=fake_get) as get:
        result = runner.run_scan(["a", "b"], client=client, output=out)

    allegro_calls = [c for c in get.call_args_list if "allegro" in c.args[0]]
    assert len(allegro_calls) == 4  # tylko pierwsze zapytanie, potem Allegro pomijane
    assert result["meta"]["allegro_zablokowane"] is True
    assert result["meta"]["zrodla"] == ["ceneo", "morele"]
    assert {o["zapytanie"] for o in result["oferty"]} == {"a", "b"}
    assert json.loads(out.read_text(encoding="utf-8")) == result


def test_api_latest_scan(tmp_path):
    scan_file = tmp_path / "last_scan.json"
    app = create_app(scan_file).test_client()
    assert app.get("/scan/latest").status_code == 404
    runner.save_json({"meta": {}, "oferty": [{"tytul": "Łódka"}]}, scan_file)
    resp = app.get("/scan/latest")
    assert resp.status_code == 200
    assert resp.get_json()["oferty"][0]["tytul"] == "Łódka"
    assert app.get("/health").get_json() == {"status": "ok"}
