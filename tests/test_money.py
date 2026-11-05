"""Polskie formaty cen i arytmetyka na Decimal."""
from decimal import Decimal

import pytest

from allegro_ceny.money import find_amounts, fmt_pl, from_grosze, parse_amount, parse_price_text, to_grosze


@pytest.mark.parametrize("text, expected", [
    ("1 299,99 zł", "1299.99"),
    ("1 299,99 zł", "1299.99"),          # twarda spacja
    ("1 299,99 zł", "1299.99"),               # wąska twarda spacja
    ("1.299,99 zł", "1299.99"),                    # kropka jako separator tysięcy
    ("1299 zł", "1299.00"),
    ("12 345 zł", "12345.00"),
    ("2 499,00 PLN", "2499.00"),
    ("89,9 zł", "89.90"),
    ("cena: 3 150 ,00 zł", "3150.00"),             # cena złożona z kilku elementów DOM
    ("0,99 zł", "0.99"),
])
def test_polskie_formaty(text, expected):
    assert parse_price_text(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["", "brak ceny", "zł", "Zapytaj o cenę", None])
def test_brak_ceny_to_none_nie_zero(text):
    assert parse_price_text(text) is None


def test_kilka_kwot_w_tekscie():
    amounts = [a for a, _, _ in find_amounts("2 899,00 zł 10 x 289,90 zł 2 914,99 zł z dostawą")]
    assert amounts == [Decimal("2899.00"), Decimal("289.90"), Decimal("2914.99")]


def test_nie_lapie_slow_zaczynajacych_sie_od_zl():
    assert parse_price_text("100 złotych") is None
    assert parse_price_text("model 391 złoty kolor") is None


@pytest.mark.parametrize("value, expected", [
    (1299.99, "1299.99"), (1299, "1299.00"), ("1299.99", "1299.99"), ("1 299,99", "1299.99"),
    ("2450,00", "2450.00"), (Decimal("10.005"), "10.01"), ("15,00 zł", "15.00"),
])
def test_parse_amount(value, expected):
    assert parse_amount(value) == Decimal(expected)


@pytest.mark.parametrize("value", [None, "", "  ", "abc", True, "n/d"])
def test_parse_amount_brak(value):
    assert parse_amount(value) is None


def test_float_nie_wprowadza_bledu():
    assert parse_amount(0.1) + parse_amount(0.2) == Decimal("0.30")


def test_grosze_w_obie_strony():
    assert to_grosze(Decimal("1299.99")) == 129999
    assert from_grosze(129999) == Decimal("1299.99")
    assert to_grosze(None) is None and from_grosze(None) is None


def test_format_wyswietlania():
    assert fmt_pl(Decimal("12345.5")) == "12 345,50 zł"
    assert fmt_pl(None) == "brak danych"
