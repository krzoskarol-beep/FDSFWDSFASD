"""Parser wyników wyszukiwania Ceneo (fallback).

Ceneo to porównywarka — „sprzedawca” to liczba sklepów z ofertą, a cena to cena minimalna.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .common import clean_text, dedupe, make_offer, offers_from_jsonld, text_containing

NAME = "ceneo"
HOME_URL = "https://www.ceneo.pl/"


def search_url(query: str) -> str:
    """Adres wyszukiwarki Ceneo dla zapytania."""
    return f"https://www.ceneo.pl/;szukaj-{quote_plus(query)}"


def parse(html: str) -> list[dict[str, Any]]:
    """Zwraca listę produktów z wyników Ceneo."""
    soup = BeautifulSoup(html, "html.parser")
    offers = []

    # Ceneo ma widok listy (cat-prod-row) i kafelków (cat-prod-box).
    for row in soup.select("div.cat-prod-row, div.cat-prod-box"):
        name_link = row.select_one(
            ".cat-prod-row__name a, .cat-prod-box__name a, a.go-to-product, a[href]"
        )
        title = row.get("data-productname") or (
            clean_text(name_link.get_text(" ")) if name_link else None
        )

        price_tag = row.select_one(".price")
        price = row.get("data-productminprice") or (
            price_tag.get_text("") if price_tag else None
        )

        if name_link and name_link.get("href"):
            link = urljoin(HOME_URL, name_link["href"])
        elif row.get("data-pid"):
            link = urljoin(HOME_URL, row["data-pid"])
        else:
            link = None

        score = row.select_one(".product-score")
        shops = row.select_one(".shop-numb")

        offers.append(
            make_offer(
                tytul=title,
                cena=price,
                dostawa=text_containing(row, ("dostaw",)),
                sprzedawca=f"Ceneo: {clean_text(shops.get_text(' '))}" if shops else "Ceneo",
                ocena=score.get_text(" ") if score else None,
                link=link,
                zrodlo=NAME,
            )
        )

    offers = dedupe(offers)
    return offers or dedupe(offers_from_jsonld(soup, NAME, HOME_URL))
