"""Odróżnianie kompletnego produktu od części, dopasowanie modeli, marki, stany."""
from decimal import Decimal

import pytest

from allegro_ceny.filtering import model_regex, ocen_oferte
from allegro_ceny.models import MARKA_NIEUSTALONA, Decyzja, Oferta
from allegro_ceny.textnorm import fold


def ocen(profil, tytul, cena="2500", stan=None):
    o = Oferta(tytul=tytul, cena=Decimal(cena) if cena else None, id_pewne=True, offer_id="1", cena_rodzaj="pelna")
    o.stan = stan
    return ocen_oferte(o, profil)


@pytest.mark.parametrize("tekst", ["MS391", "MS 391", "ms-391", "Ms.391", "STIHL MS391,", "(MS 391)"])
def test_warianty_zapisu_modelu(tekst):
    assert model_regex("MS391").search(fold(tekst))


@pytest.mark.parametrize("tekst", ["MS39", "MS3910", "MS 3911", "MS 291", "MS 39 1", "AMS391"])
def test_podobne_numery_to_nie_ten_model(tekst):
    assert not model_regex("MS391").search(fold(tekst))


@pytest.mark.parametrize("tytul", [
    "Pilarka spalinowa STIHL MS 391 45 cm 3,3 KM",
    "Piła łańcuchowa STIHL MS391 nowa",
    "STIHL MS 391 piła spalinowa",
    "Pilarka STIHL MS391 do drewna",
])
def test_kompletny_produkt_pasuje(profil, tytul):
    assert ocen(profil, tytul).decyzja == Decyzja.PASUJE


@pytest.mark.parametrize("tytul, fragment", [
    ("Łańcuch Oregon do STIHL MS391 45cm 3/8 1,6", "część"),
    ("Prowadnica STIHL 45 cm MS 391", "część zamienna"),
    ("Gaźnik do STIHL MS391 MS311 MS362 zamiennik", "zamiennik"),
    ("Zębatka sprzęgła STIHL MS391", "część zamienna"),
    ("Filtr powietrza pasuje do STIHL MS 391", "część"),
    ("Pudełko karton STIHL MS391", "opakowanie"),
])
def test_czesci_i_opakowania_odrzucone(profil, tytul, fragment):
    o = ocen(profil, tytul, cena="1500")
    assert o.decyzja == Decyzja.ODRZUCONA
    assert fragment in o.powod


def test_wzmianka_o_czesci_w_kompletnym_produkcie_nie_odrzuca(profil):
    o = ocen(profil, "Pilarka STIHL MS391 + łańcuch gratis + olej")
    assert o.decyzja == Decyzja.PASUJE
    assert any("wyposażenie" in u for u in o.uwagi)


def test_piła_łańcuchowa_to_nie_łańcuch(profil):
    assert ocen(profil, "Piły łańcuchowej STIHL MS 391 sprzedam").decyzja == Decyzja.PASUJE


def test_inny_model_odrzucony(profil):
    o = ocen(profil, "Pilarka STIHL MS 362 C-M")
    assert o.decyzja == Decyzja.ODRZUCONA and "inny model: MS362" in o.powod
    assert o.model == "MS362"


def test_brak_modelu_do_sprawdzenia(profil):
    o = ocen(profil, "Pilarka spalinowa STIHL 3,3 KM mocna")
    assert o.decyzja == Decyzja.DO_SPRAWDZENIA
    assert "brak pewności co do modelu" in o.powod


def test_sufiks_wariantu_do_sprawdzenia(profil):
    o = ocen(profil, "Pilarka STIHL MS391C")
    assert o.decyzja == Decyzja.DO_SPRAWDZENIA and "wariant" in o.powod


def test_kilka_modeli_bez_slowa_czesci_do_sprawdzenia(profil):
    o = ocen(profil, "Pilarka STIHL MS391 MS362 komplet")
    assert o.decyzja == Decyzja.DO_SPRAWDZENIA


def test_uszkodzony_odrzucony_gdy_profil_nie_akceptuje(profil):
    o = ocen(profil, "Pilarka STIHL MS391 uszkodzona na części", cena="900")
    assert o.decyzja == Decyzja.ODRZUCONA and "uszkodzony" in o.powod
    assert o.stan == "uszkodzony"
    assert not any("wyposażenie" in u for u in o.uwagi)


def test_uszkodzony_akceptowany_gdy_w_profilu(profil):
    profil.stany = ["nowy", "używany", "uszkodzony"]
    assert ocen(profil, "Pilarka STIHL MS391 nie odpala", cena="900").decyzja == Decyzja.PASUJE


def test_bez_uszkodzen_to_nie_uszkodzony(profil):
    o = ocen(profil, "Pilarka STIHL MS 391 używana, bez uszkodzeń")
    assert o.decyzja == Decyzja.PASUJE and o.stan == "używany"


def test_stan_z_parametru_vs_profil(profil):
    profil.stany = ["nowy"]
    o = ocen(profil, "Pilarka STIHL MS391", stan="używany")
    assert o.decyzja == Decyzja.ODRZUCONA and "używany" in o.powod


def test_marka_nieustalona_nie_no_name(profil):
    o = ocen(profil, "Pilarka MS391 spalinowa")
    assert o.marka == MARKA_NIEUSTALONA
    assert o.decyzja == Decyzja.DO_SPRAWDZENIA and "marka nieustalona" in o.powod


def test_inna_marka(profil):
    o = ocen(profil, "Pilarka Husqvarna 455 Rancher")
    assert o.decyzja == Decyzja.ODRZUCONA and "inna marka: Husqvarna" in o.powod


def test_niekompletny_do_sprawdzenia(profil):
    o = ocen(profil, "Pilarka STIHL MS391 bez prowadnicy i łańcucha")
    assert o.decyzja == Decyzja.DO_SPRAWDZENIA and "niekompletny" in o.powod


def test_brak_ceny_i_cena_od(profil):
    assert ocen(profil, "Pilarka STIHL MS391", cena=None).decyzja == Decyzja.DO_SPRAWDZENIA
    o = Oferta(tytul="Pilarka STIHL MS391", cena=Decimal("2500"), cena_rodzaj="od", offer_id="1", id_pewne=True)
    assert ocen_oferte(o, profil).decyzja == Decyzja.DO_SPRAWDZENIA


def test_zakres_cen(profil):
    assert ocen(profil, "Pilarka STIHL MS391", cena="300").decyzja == Decyzja.ODRZUCONA
    assert ocen(profil, "Pilarka STIHL MS391", cena="9000").decyzja == Decyzja.ODRZUCONA


def test_slowa_wykluczone(profil):
    assert ocen(profil, "Wynajem pilarka STIHL MS391 na dobę").decyzja == Decyzja.ODRZUCONA


def test_klon_typu_stihl(profil):
    o = ocen(profil, "Pilarka spalinowa typu MS 391 5,2 KM", cena="900")
    assert o.decyzja == Decyzja.ODRZUCONA
