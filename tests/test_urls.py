from allegro_ceny.urls import clean_offer_url, offer_id_from_url, page_number, search_url, with_page


def test_id_i_czysty_link():
    u = "https://allegro.pl/oferta/pilarka-stihl-ms-391-99000000001?bi_s=ads&utm=x#opis"
    assert offer_id_from_url(u) == "99000000001"
    assert clean_offer_url(u) == "https://allegro.pl/oferta/pilarka-stihl-ms-391-99000000001"


def test_link_wzgledny():
    assert clean_offer_url("/oferta/abc-99000000005") == "https://allegro.pl/oferta/abc-99000000005"


def test_link_sledzacy_sponsorowanej():
    u = ("https://allegro.pl/events/clicks?emission_unit_id=1&redirect="
         "https%3A%2F%2Fallegro.pl%2Foferta%2Fpila-99000000002%3Fbi_s%3Dads")
    assert offer_id_from_url(u) == "99000000002"
    assert clean_offer_url(u) == "https://allegro.pl/oferta/pila-99000000002"


def test_produkt_z_offer_id():
    u = "https://allegro.pl/produkt/pilarka-stihl-ms-391-abcd?offerId=99000000077&x=1"
    assert offer_id_from_url(u) == "99000000077"
    assert clean_offer_url(u) == "https://allegro.pl/produkt/pilarka-stihl-ms-391-abcd?offerId=99000000077"


def test_brak_id():
    assert offer_id_from_url("https://allegro.pl/listing?string=stihl") is None
    assert offer_id_from_url("/oferta/model-391") is None  # za krótka liczba to nie ID


def test_paginacja_url():
    base = search_url("pilarka stihl ms391")
    assert base == "https://allegro.pl/listing?string=pilarka%20stihl%20ms391"
    p3 = with_page(base, 3)
    assert page_number(p3) == 3
    assert "string=pilarka+stihl+ms391" in p3 or "string=pilarka%20stihl%20ms391" in p3
    assert page_number(with_page(p3, 1)) == 1
    # zachowanie filtrów z adresu użytkownika
    assert "stan=nowe" in with_page("https://allegro.pl/listing?string=x&stan=nowe", 2)
