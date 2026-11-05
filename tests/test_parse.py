"""Parser na SYNTETYCZNYCH stronach testowych (tests/fixtures). Nie są to kopie Allegro."""
from decimal import Decimal

from allegro_ceny.blocking import ocen_strone
from allegro_ceny.parse import parse_listing, rel_next


def _by_id(fixtures, name):
    wynik = parse_listing((fixtures / name).read_text(encoding="utf-8"), strona=1)
    out = {}
    for o in wynik.oferty:
        out.setdefault(o.offer_id, o)
    return wynik, out


def test_strona_1_liczba_i_duplikat(fixtures):
    wynik, oferty = _by_id(fixtures, "strona_1.html")
    assert wynik.strategia == "dom_article"
    assert len(wynik.oferty) == 12          # z duplikatem
    assert len(oferty) == 11                # unikalne ID


def test_cena_rozbita_rata_i_cena_z_dostawa(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    a = o["99000000001"]
    assert a.cena == Decimal("2899.00")           # nie rata 289,90
    assert a.cena_z_dostawa == Decimal("2914.99")
    assert a.cena_z_dostawa_zrodlo == "strona"
    assert a.koszt_dostawy is None                # nie wymyślamy kosztu dostawy
    assert a.stan == "nowy"
    assert a.sprzedawca == "sprzedawca_testowy_1"
    assert a.url == "https://allegro.pl/oferta/pilarka-spalinowa-stihl-ms-391-45-cm-99000000001"


def test_sponsorowana_smart_bez_zalozenia_darmowej_dostawy(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    s = o["99000000002"]
    assert s.sponsorowana is True
    assert s.smart is True
    assert s.koszt_dostawy is None and s.cena_z_dostawa is None
    assert s.url == "https://allegro.pl/oferta/pila-lancuchowa-stihl-ms391-nowa-99000000002"
    assert s.cena == Decimal("3150.00")


def test_dokladny_koszt_dostawy_i_obliczona_cena_laczna(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    u = o["99000000003"]
    assert (u.cena, u.koszt_dostawy, u.cena_z_dostawa) == (Decimal("1750.00"), Decimal("19.99"), Decimal("1769.99"))
    assert u.cena_z_dostawa_zrodlo == "obliczona"
    assert u.stan == "używany"


def test_dostawa_od_to_nie_koszt(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    c = o["99000000004"]
    assert c.cena == Decimal("89.99")
    assert c.koszt_dostawy is None
    assert c.koszt_dostawy_od == Decimal("9.99")
    assert c.cena_z_dostawa is None


def test_darmowa_dostawa_bez_warunkow(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    m = o["99000000006"]
    assert m.koszt_dostawy == Decimal("0.00")
    assert any("darmowa dostawa" in u for u in m.uwagi)


def test_cena_od_wariantowa(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    w = o["99000000008"]
    assert w.cena == Decimal("2999.00") and w.cena_rodzaj == "od"
    assert w.stan is None


def test_tylko_rata_daje_null(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    r = o["99000000011"]
    assert r.cena is None
    assert any("rat" in w for w in r.ostrzezenia_parsera)


def test_cena_referencyjna_30_dni_ignorowana(fixtures):
    _, o = _by_id(fixtures, "strona_1.html")
    p = o["99000000012"]
    assert p.cena == Decimal("2799.00")
    assert p.koszt_dostawy is None  # „Dostawa: brak informacji” -> null


def test_rel_next(fixtures):
    assert rel_next((fixtures / "strona_1.html").read_text()).endswith("p=2")


def test_strategia_zapasowa_bez_article(fixtures):
    wynik, o = _by_id(fixtures, "kotwica_bez_article.html")
    assert wynik.strategia == "dom_kotwica"
    assert set(o) == {"99000000031", "99000000032"}
    assert o["99000000031"].cena == Decimal("2600.00")
    assert o["99000000031"].tytul == "Pilarka STIHL MS391 kompletna"


def test_json_osadzony_jako_ostatnia_deska(fixtures):
    wynik, o = _by_id(fixtures, "json_osadzony.html")
    assert wynik.strategia == "json_osadzony"
    assert o["99000000041"].cena == Decimal("2699.00")
    assert o["99000000041"].sprzedawca == "sprzedawca_testowy_41"
    assert all(x.ostrzezenia_parsera for x in o.values())


def test_blokada_captcha(fixtures):
    html = (fixtures / "captcha.html").read_text()
    wynik = parse_listing(html)
    ocena = ocen_strone(html, 403, "https://allegro.pl/listing?string=x", len(wynik.oferty))
    assert ocena.zablokowana and not ocena.brak_wynikow
    assert "http_403" in ocena.markery
    # nawet z kodem 200 iframe wyzwania = blokada
    assert ocen_strone(html, 200, None, 0).zablokowana


def test_brak_wynikow_rozpoznany(fixtures):
    ocena = ocen_strone((fixtures / "brak_wynikow.html").read_text(), 200, None, 0)
    assert ocena.brak_wynikow and not ocena.zablokowana


def test_nieznany_uklad_to_nie_brak_wynikow(fixtures):
    html = (fixtures / "nieznany_uklad.html").read_text()
    assert parse_listing(html).oferty == []
    ocena = ocen_strone(html, 200, None, 0)
    assert not ocena.brak_wynikow and not ocena.zablokowana


def test_skrypt_pomiarowy_antybota_to_jeszcze_nie_blokada(fixtures):
    html = (fixtures / "strona_1.html").read_text().replace(
        "</head>", '<script src="https://js.datadome.co/tags.js"></script></head>')
    wynik = parse_listing(html)
    assert not ocen_strone(html, 200, "https://allegro.pl/listing", len(wynik.oferty)).zablokowana
