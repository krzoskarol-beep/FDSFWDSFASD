"""Parser wyników wyszukiwania Morele.net (fallback). Sprzedawcą jest sam sklep."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .common import clean_text, dedupe, make_offer, offers_from_jsonld, text_containing

NAME = "morele"
HOME_URL = "https://www.morele.net/"


def search_url(query: str) -> str:
    """Adres wyszukiwarki Morele dla zapytania."""
    return f"https://www.morele.net/wyszukiwarka/?q={quote_plus(query)}"


def parse(html: str) -> list[dict[str, Any]]:
    """Zwraca listę produktów z wyników Morele."""
    soup = BeautifulSoup(html, "html.parser")
    offers = []

    for row in soup.select("div.cat-product"):
        name_link = row.select_one("a.productLink, .cat-product-name a, a[href]")
        title = row.get("data-product-name") or (
            clean_text(name_link.get_text(" ")) if name_link else None
        )

        price_tag = row.select_one(".price-new, .cat-product-price")
        price = row.get("data-product-price") or (price_tag.get_text(" ") if price_tag else None)

        # Ocena bywa w atrybucie data-rating albo w tekście elementu z „rating” w klasie.
        rating = None
        rating_tag = row.select_one("[data-rating]")
        if rating_tag:
            rating = rating_tag["data-rating"]
        else:
            rating_tag = row.select_one("[class*=rating]")
            if rating_tag:
                rating = rating_tag.get_text(" ")

        offers.append(
            make_offer(
                tytul=title,
                cena=price,
                dostawa=text_containing(row, ("dostaw", "wysyłka")),
                sprzedawca="morele.net",
                ocena=rating,
                link=urljoin(HOME_URL, name_link["href"]) if name_link and name_link.get("href") else None,
                zrodlo=NAME,
            )
        )

    offers = dedupe(offers)
    return offers or dedupe(offers_from_jsonld(soup, NAME, HOME_URL))
