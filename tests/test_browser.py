"""Prawdziwy Chromium (Playwright) na LOKALNYM serwerze z syntetycznymi stronami.

Sprawdza mechanikę pobierania: paginację, wykrycie zapętlenia, blokadę (403 + CAPTCHA),
ponowienie po błędzie przejściowym (503), brak zapisu cookies, brak ukrywania automatyzacji.
Nie łączy się z Allegro.
"""
import functools
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

pytestmark = pytest.mark.browser

FIX = Path(__file__).resolve().parent / "fixtures"


def _chromium_dostepny():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
        return True
    except Exception:
        return False


if not _chromium_dostepny():
    pytest.skip("Chromium/Playwright niedostępny", allow_module_level=True)


class Handler(BaseHTTPRequestHandler):
    licznik_niestabilny = 0

    def log_message(self, *a):
        pass

    def _send(self, code, name):
        body = (FIX / name).read_bytes()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Set-Cookie", "sesja=SEKRET_TESTOWY_123; Path=/")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlsplit(self.path)
        p = int(parse_qs(u.query).get("p", ["1"])[0])
        if u.path == "/zwykly/listing":
            self._send(200, {1: "strona_1.html", 2: "strona_2.html"}.get(p, "strona_2.html"))  # p>=3 -> pętla
        elif u.path == "/blok/listing":
            self._send(200, "strona_1.html") if p == 1 else self._send(403, "captcha.html")
        elif u.path == "/niestabilny/listing":
            if p == 1:
                Handler.licznik_niestabilny += 1
                if Handler.licznik_niestabilny == 1:
                    return self._send(503, "nieznany_uklad.html")
                return self._send(200, "strona_1.html")
            self._send(200, "brak_wynikow.html")
        else:
            self._send(404, "nieznany_uklad.html")


@pytest.fixture(scope="module")
def serwer():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _przegladarka():
    from allegro_ceny.fetch import PrzegladarkaAllegro
    return functools.partial(PrzegladarkaAllegro, przewijanie=False, czekaj_na_oferty_s=2, przerwa_ponowienia_s=0.1)


def _run(profil, baza, tmp_path, url):
    from allegro_ceny.pipeline import pobierz
    profil.url, profil.odstep_s, profil.max_stron = url, 0, 5
    return pobierz(profil, baza, katalog=tmp_path, headless=True, zapisz_html=True,
                   przegladarka=_przegladarka(), sleep=lambda s: None, info=lambda m: None)


def test_paginacja_i_zapetlenie(serwer, profil, baza, tmp_path):
    w = _run(profil, baza, tmp_path, f"{serwer}/zwykly/listing?string=pilarka+stihl+ms391")
    assert w["powod"] == "powtorzona_strona" and w["status"] == "pelny"
    assert w["strony"] == 3 and w["oferty"] == 14
    # brak zapisanych cookies (zapisany HTML stron jest, cookies — nie)
    for f in tmp_path.rglob("*"):
        if f.is_file() and f.suffix != ".sqlite":
            assert "SEKRET_TESTOWY_123" not in f.read_text(errors="ignore")
    assert not any("cookie" in f.name.lower() or "storage_state" in f.name for f in tmp_path.rglob("*"))
    assert b"SEKRET_TESTOWY_123" not in (tmp_path / "test.sqlite").read_bytes() if (tmp_path / "test.sqlite").exists() else True


def test_blokada_zatrzymuje_i_zachowuje_dane(serwer, profil, baza, tmp_path):
    w = _run(profil, baza, tmp_path, f"{serwer}/blok/listing?string=x")
    assert w["status"] == "niepelny" and w["powod"] == "blokada"
    assert w["strony"] == 2 and w["oferty"] == 11
    assert (tmp_path / "diagnostyka" / f"przebieg_{w['przebieg_id']}" / "strona_2.png").exists()


def test_ponowienie_po_503_i_koniec_wynikow(serwer, profil, baza, tmp_path):
    import json
    w = _run(profil, baza, tmp_path, f"{serwer}/niestabilny/listing?string=x")
    assert w["oferty"] == 11
    assert w["powod"] == "koniec_wynikow" and w["status"] == "pelny"
    diag = json.loads(baza.przebieg(w["przebieg_id"])["diagnostyka_json"])
    assert diag["strony"][0]["proby"] == 2


def test_brak_ukrywania_automatyzacji(serwer):
    from allegro_ceny.fetch import PrzegladarkaAllegro
    with PrzegladarkaAllegro(headless=True, przewijanie=False, czekaj_na_oferty_s=1) as b:
        b.pobierz(f"{serwer}/zwykly/listing")
        assert b.page.evaluate("navigator.webdriver") is True
    assert b.page is None and b._browser is None  # przeglądarka zamknięta
