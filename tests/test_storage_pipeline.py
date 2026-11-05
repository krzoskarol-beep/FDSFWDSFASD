"""Deduplikacja, historia cen, rozpoznawanie niepełnego przebiegu (bez przeglądarki)."""
from decimal import Decimal
from pathlib import Path

import pytest

from allegro_ceny.analysis import zmiany_cen
from allegro_ceny.blocking import OcenaStrony
from allegro_ceny.fetch import WynikPobrania
from allegro_ceny.models import Decyzja, Oferta
from allegro_ceny.pipeline import Paginacja, importuj, pobierz
from allegro_ceny.urls import page_number


# ---------------------------------------------------------------- baza

def _oferta(oid, cena, tytul="Pilarka STIHL MS391"):
    return Oferta(offer_id=oid, id_pewne=True, url=f"https://allegro.pl/oferta/x-{oid}", tytul=tytul,
                  cena=Decimal(cena), waluta="PLN", decyzja=Decyzja.PASUJE, profil="p")


def test_deduplikacja_w_przebiegu(baza):
    pid = baza.nowy_przebieg(profil="p", fraza="f", url=None, tryb="pobieranie", kryteria={})
    nowe, dup = baza.zapisz_oferty(pid, [_oferta("99000000001", "100"), _oferta("99000000001", "100"),
                                         _oferta("99000000002", "200")])
    assert (nowe, dup) == (2, 1)
    oferty = baza.oferty_przebiegu(pid)
    assert len(oferty) == 2
    assert {o.offer_id: o.wystapienia for o in oferty}["99000000001"] == 2


def test_historia_zamiast_duplikatow(baza):
    p1 = baza.nowy_przebieg(profil="p", fraza="f", url=None, tryb="pobieranie", kryteria={})
    baza.zapisz_oferty(p1, [_oferta("99000000001", "2500.00"), _oferta("99000000002", "2000")])
    p2 = baza.nowy_przebieg(profil="p", fraza="f", url=None, tryb="pobieranie", kryteria={})
    baza.zapisz_oferty(p2, [_oferta("99000000001", "2399.99"), _oferta("99000000003", "2100")])
    assert baza.liczba_ofert() == 3                     # jedna pozycja na ID
    assert baza.liczba_obserwacji("99000000001") == 2   # dwie obserwacje w historii
    zm = zmiany_cen(baza.historia("p"))
    assert len(zm) == 1
    z = zm[0]
    assert (z["offer_id"], z["cena_poprzednia"], z["cena_biezaca"], z["roznica"]) == (
        "99000000001", "2500.00", "2399.99", "-100.01")


def test_null_zostaje_null(baza):
    pid = baza.nowy_przebieg(profil="p", fraza="f", url=None, tryb="pobieranie", kryteria={})
    o = Oferta(offer_id="99000000009", id_pewne=True, tytul="x", cena=None, koszt_dostawy=None, sponsorowana=None)
    baza.zapisz_oferty(pid, [o])
    back = baza.oferty_przebiegu(pid)[0]
    assert back.cena is None and back.koszt_dostawy is None and back.sponsorowana is None and back.smart is None


def test_kwoty_bez_utraty_precyzji(baza):
    pid = baza.nowy_przebieg(profil="p", fraza="f", url=None, tryb="pobieranie", kryteria={})
    o = _oferta("99000000010", "1299.99")
    o.koszt_dostawy = Decimal("0.01")
    baza.zapisz_oferty(pid, [o])
    back = baza.oferty_przebiegu(pid)[0]
    assert back.cena == Decimal("1299.99") and back.koszt_dostawy == Decimal("0.01")


# ---------------------------------------------------------------- paginacja / kompletność

OK = OcenaStrony()


def test_paginacja_limit_stron():
    p = Paginacja(max_stron=2, max_ofert=100)
    assert p.ocen(1, ["a", "b"], OK, blad=None, status=200, url_koncowy="https://allegro.pl/listing?p=1") == (None, ["a", "b"])
    assert p.ocen(2, ["c"], OK, blad=None, status=200, url_koncowy="https://allegro.pl/listing?p=2") == ("limit_stron", ["c"])


def test_paginacja_limit_ofert_tnie_strone():
    p = Paginacja(max_stron=5, max_ofert=3)
    assert p.ocen(1, ["a", "b"], OK, blad=None, status=200, url_koncowy=None)[0] is None
    assert p.ocen(2, ["c", "d", "e"], OK, blad=None, status=200, url_koncowy=None) == ("limit_ofert", ["c"])


def test_zapetlenie_ta_sama_strona():
    p = Paginacja(max_stron=5, max_ofert=100)
    p.ocen(1, ["a", "b"], OK, blad=None, status=200, url_koncowy=None)
    assert p.ocen(2, ["a", "b"], OK, blad=None, status=200, url_koncowy=None)[0] == "powtorzona_strona"


def test_zapetlenie_przekierowanie_na_inny_numer_strony():
    p = Paginacja(max_stron=5, max_ofert=100)
    p.ocen(1, ["a"], OK, blad=None, status=200, url_koncowy=None)
    p.ocen(2, ["b"], OK, blad=None, status=200, url_koncowy="https://allegro.pl/listing?p=2")
    assert p.ocen(3, ["c"], OK, blad=None, status=200, url_koncowy="https://allegro.pl/listing?p=2")[0] == "powtorzona_strona"


def test_blokada_to_nie_brak_ofert():
    p = Paginacja(max_stron=5, max_ofert=100)
    assert p.ocen(1, [], OcenaStrony(zablokowana=True), blad=None, status=403, url_koncowy=None)[0] == "blokada"


def test_pusta_strona_bez_komunikatu_to_nieznany_uklad():
    p = Paginacja(max_stron=5, max_ofert=100)
    assert p.ocen(1, [], OK, blad=None, status=200, url_koncowy=None)[0] == "nieznany_uklad_strony"
    assert p.ocen(1, [], OcenaStrony(brak_wynikow=True), blad=None, status=200, url_koncowy=None)[0] == "brak_wynikow"


# ---------------------------------------------------------------- pobieranie z atrapą przeglądarki

class AtrapaPrzegladarki:
    """Zastępuje Playwright: zwraca zadane strony. Zapisuje kolejność żądań."""

    def __init__(self, strony, **_):
        self.strony = strony
        self.page = None
        self.zadania = []

    def __call__(self, **_):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def pobierz(self, url):
        self.zadania.append(url)
        nr = page_number(url)
        akcja = self.strony.get(nr)
        if isinstance(akcja, BaseException):
            raise akcja
        if akcja is None:
            return WynikPobrania(url=url, blad="net::ERR_TIMED_OUT", proby=3)
        status, html = akcja
        return WynikPobrania(url=url, url_koncowy=url, status=status, html=html, tytul_strony="t", proby=1)

    def zrzut_ekranu(self, sciezka):
        return None


def _uruchom(profil, baza, tmp_path, strony):
    profil.odstep_s = 0
    profil.max_stron = 5
    atrapa = AtrapaPrzegladarki(strony)
    wynik = pobierz(profil, baza, katalog=tmp_path, przegladarka=atrapa, sleep=lambda s: None, info=lambda m: None)
    return wynik, atrapa


def test_blokada_w_trakcie_zachowuje_zebrane_dane(profil, baza, tmp_path, fixtures):
    s1 = (fixtures / "strona_1.html").read_text()
    cap = (fixtures / "captcha.html").read_text()
    wynik, atrapa = _uruchom(profil, baza, tmp_path, {1: (200, s1), 2: (403, cap)})
    assert wynik["status"] == "niepelny" and wynik["powod"] == "blokada"
    assert len(atrapa.zadania) == 2                  # po blokadzie nie ma kolejnych żądań
    assert wynik["oferty"] == 11                     # dane ze strony 1 zostały zapisane
    przebieg = baza.przebieg(wynik["przebieg_id"])
    assert przebieg["status"] == "niepelny" and "captcha" in przebieg["szczegoly_zakonczenia"]
    assert len(baza.oferty_przebiegu(wynik["przebieg_id"])) == 11


def test_pelny_przebieg_z_paginacja_i_zapetleniem(profil, baza, tmp_path, fixtures):
    s1 = (fixtures / "strona_1.html").read_text()
    s2 = (fixtures / "strona_2.html").read_text()
    wynik, atrapa = _uruchom(profil, baza, tmp_path, {1: (200, s1), 2: (200, s2), 3: (200, s2)})
    assert wynik["powod"] == "powtorzona_strona" and wynik["status"] == "pelny"
    oferty = baza.oferty_przebiegu(wynik["przebieg_id"])
    ids = [o.offer_id for o in oferty]
    assert len(ids) == len(set(ids)) == 14           # 11 + 3 nowe (99000000003 powtórzona -> pominięta)
    dec = {o.offer_id: o.decyzja for o in oferty}
    assert dec["99000000001"] == Decyzja.PASUJE
    assert dec["99000000004"] == Decyzja.ODRZUCONA  # łańcuch
    assert dec["99000000022"] == Decyzja.ODRZUCONA  # gaźnik
    assert all(o.pobrano and o.pobrano[-6] in "+-" for o in oferty)  # czas ze strefą
    sponsor = {o.offer_id: o for o in oferty}["99000000002"]
    assert sponsor.wystapienia == 2 and sponsor.sponsorowana is True


def test_blad_sieci_po_ponowieniach(profil, baza, tmp_path, fixtures):
    s1 = (fixtures / "strona_1.html").read_text()
    wynik, _ = _uruchom(profil, baza, tmp_path, {1: (200, s1)})  # strona 2 -> timeout
    assert wynik["status"] == "niepelny" and wynik["powod"] == "blad_sieci" and wynik["oferty"] == 11


def test_nieznany_uklad_na_pierwszej_stronie(profil, baza, tmp_path, fixtures):
    wynik, _ = _uruchom(profil, baza, tmp_path, {1: (200, (fixtures / "nieznany_uklad.html").read_text())})
    assert wynik["status"] == "niepelny" and wynik["powod"] == "nieznany_uklad_strony"
    assert "NIE jest potwierdzony brak ofert" in wynik["opis"]


def test_potwierdzony_brak_wynikow(profil, baza, tmp_path, fixtures):
    wynik, _ = _uruchom(profil, baza, tmp_path, {1: (200, (fixtures / "brak_wynikow.html").read_text())})
    assert wynik["status"] == "pelny" and wynik["powod"] == "brak_wynikow" and wynik["oferty"] == 0


def test_przerwanie_ctrl_c(profil, baza, tmp_path, fixtures):
    s1 = (fixtures / "strona_1.html").read_text()
    wynik, _ = _uruchom(profil, baza, tmp_path, {1: (200, s1), 2: KeyboardInterrupt()})
    assert wynik["status"] == "niepelny" and wynik["powod"] == "przerwane" and wynik["oferty"] == 11


def test_blad_programu_oznacza_niepelny(profil, baza, tmp_path, fixtures):
    s1 = (fixtures / "strona_1.html").read_text()
    wynik, _ = _uruchom(profil, baza, tmp_path, {1: (200, s1), 2: RuntimeError("awaria")})
    assert wynik["status"] == "niepelny" and wynik["powod"] == "blad_wewnetrzny"
    assert "RuntimeError" in wynik["szczegoly"]


# ---------------------------------------------------------------- import

def test_import_html_csv(profil, baza, fixtures):
    wynik = importuj(profil, baza, [fixtures / "strona_1.html", fixtures / "import_przyklad.csv"],
                     dane_testowe=True, info=lambda m: None)
    assert wynik["status"] == "import"
    oferty = {o.offer_id: o for o in baza.oferty_przebiegu(wynik["przebieg_id"])}
    csv1 = oferty["99000000051"]
    assert csv1.cena == Decimal("2450.00") and csv1.koszt_dostawy == Decimal("15.00")
    assert csv1.cena_z_dostawa == Decimal("2465.00") and csv1.stan == "używany"
    assert csv1.pobrano is None                       # czas nieznany -> null
    assert oferty["99000000052"].decyzja == Decyzja.ODRZUCONA   # osłona = część
    zastepcze = [o for o in oferty.values() if not o.id_pewne]
    assert len(zastepcze) == 1 and zastepcze[0].offer_id.startswith("x-")
    assert baza.przebieg(wynik["przebieg_id"])["dane_testowe"] == 1


def test_import_strony_z_blokada_oznacza_niepelny(profil, baza, fixtures):
    wynik = importuj(profil, baza, [fixtures / "captcha.html"], info=lambda m: None)
    assert wynik["status"] == "niepelny" and wynik["powod"] == "blokada"


def test_import_nieobslugiwany_format(profil, baza, tmp_path):
    f = tmp_path / "x.xlsx"
    f.write_text("x")
    with pytest.raises(ValueError):
        importuj(profil, baza, [f], info=lambda m: None)


def test_status_zapisany_przed_zamknieciem_przegladarki(profil, baza, tmp_path, fixtures):
    """Regresja: zamykanie przeglądarki potrafiło się zawiesić — status musi być w bazie wcześniej."""
    s1 = (fixtures / "strona_1.html").read_text()
    stan_przy_zamykaniu = {}

    class Atrapa(AtrapaPrzegladarki):
        def __exit__(self, *a):
            pid = baza.przebiegi(limit=1)[0]["id"]
            stan_przy_zamykaniu["status"] = baza.przebieg(pid)["status"]

    profil.odstep_s, profil.max_stron = 0, 1
    pobierz(profil, baza, katalog=tmp_path, przegladarka=Atrapa({1: (200, s1)}), sleep=lambda s: None,
            info=lambda m: None)
    assert stan_przy_zamykaniu["status"] == "ograniczony_limitem"
