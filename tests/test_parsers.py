"""Testy parserów na syntetycznym HTML (bez sieci)."""

import json

from scraper.parsers import allegro, ceneo, morele
from scraper.parsers.common import parse_price, parse_rating

FIELDS = {"tytul", "cena", "dostawa", "sprzedawca", "ocena", "link", "zrodlo"}


def test_parse_price_formats():
    assert parse_price("1 299,99 zł") == 1299.99
    assert parse_price("1 299,00 zł") == 1299.0
    assert parse_price("2499.50") == 2499.5
    assert parse_price(15) == 15.0
    assert parse_price("brak") is None


def test_parse_rating():
    assert parse_rating("4,8 / 5") == 4.8
    assert parse_rating("4.75") == 4.75
    assert parse_rating("98") is None  # spoza skali 0-5


def test_allegro_embedded_json():
    data = {
        "__listing_StoreState": {
            "items": {
                "elements": [
                    {
                        "name": "Karta RTX 4070 12GB",
                        "url": "https://allegro.pl/oferta/karta-rtx-4070-123",
                        "price": {"mainPrice": {"amount": "2599.00", "currency": "PLN"}},
                        "shipping": {"summary": {"label": "darmowa dostawa"},
                                     "itemWithDelivery": {"amount": "2599.00"}},
                        "seller": {"login": "SklepGPU"},
                        "productReview": {"rating": {"average": "4.9"}},
                    }
                ]
            }
        }
    }
    html = f'<html><script type="application/json" data-serialize-box-id="x">{json.dumps(data)}</script></html>'
    offers = allegro.parse(html)
    assert len(offers) == 1
    o = offers[0]
    assert set(o) == FIELDS
    assert o["tytul"] == "Karta RTX 4070 12GB"
    assert o["cena"] == 2599.0
    assert "darmowa dostawa" in o["dostawa"]
    assert o["sprzedawca"] == "SklepGPU"
    assert o["ocena"] == 4.9


def test_allegro_html_fallback():
    html = """
    <article>
      <h2><a href="/oferta/sluchawki-sony-999">Słuchawki Sony WH-1000XM5</a></h2>
      <span aria-label="cena 1 199,00 zł">1 199,00 zł</span>
      <span>dostawa od 9,99 zł</span>
      <span aria-label="4,85 na 5 gwiazdek"></span>
    </article>"""
    o = allegro.parse(html)[0]
    assert o["link"] == "https://allegro.pl/oferta/sluchawki-sony-999"
    assert o["cena"] == 1199.0
    assert o["ocena"] == 4.85
    assert o["dostawa"].startswith("dostawa")


def test_ceneo():
    html = """
    <div class="cat-prod-row" data-pid="123" data-productname="Sony WH-1000XM5" data-productminprice="1099.00">
      <strong class="cat-prod-row__name"><a href="/123"><span>Sony WH-1000XM5</span></a></strong>
      <span class="price"><span class="value">1 099</span><span class="penny">,00</span></span>
      <span class="product-score">4,9 / 5</span>
      <span class="shop-numb">w 25 sklepach</span>
      <span>Darmowa dostawa</span>
    </div>"""
    o = ceneo.parse(html)[0]
    assert o == {
        "tytul": "Sony WH-1000XM5", "cena": 1099.0, "dostawa": "Darmowa dostawa",
        "sprzedawca": "Ceneo: w 25 sklepach", "ocena": 4.9,
        "link": "https://www.ceneo.pl/123", "zrodlo": "ceneo",
    }


def test_morele():
    html = """
    <div class="cat-product" data-product-name="Karta MSI RTX 4070" data-product-price="2649.00">
      <a class="productLink" href="/karta-msi-rtx-4070-111/">Karta MSI RTX 4070</a>
      <div class="cat-product-rating" data-rating="4.7"></div>
      <span>Darmowa dostawa</span>
    </div>"""
    o = morele.parse(html)[0]
    assert o["tytul"] == "Karta MSI RTX 4070"
    assert o["cena"] == 2649.0
    assert o["ocena"] == 4.7
    assert o["sprzedawca"] == "morele.net"
    assert o["link"] == "https://www.morele.net/karta-msi-rtx-4070-111/"


def test_jsonld_fallback():
    ld = {"@type": "Product", "name": "Produkt X", "url": "/x",
          "offers": {"price": "10.50"}, "aggregateRating": {"ratingValue": 4.2}}
    html = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    o = morele.parse(html)[0]
    assert (o["tytul"], o["cena"], o["ocena"], o["link"]) == (
        "Produkt X", 10.5, 4.2, "https://www.morele.net/x")
