"""Parser wyników wyszukiwania Allegro.

Allegro renderuje listing z danych JSON osadzonych w <script data-serialize-box-id>.
Najpierw szukamy ofert w tym JSON-ie, potem w HTML (<article>), na końcu w JSON-LD.
Struktura strony zmienia się często — parser jest celowo „tolerancyjny”.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from .common import (
    clean_text,
    dedupe,
    iter_script_json,
    make_offer,
    offers_from_jsonld,
    text_containing,
    walk_dicts,
)

NAME = "allegro"
HOME_URL = "https://allegro.pl/"

_RATING_RE = re.compile(r"(\d[.,]\d+)\s*(?:na|/)\s*5")


def search_url(query: str) -> str:
    """Adres listingu dla zapytania."""
    return f"https://allegro.pl/listing?string={quote_plus(query)}"


def _as_text(value: Any) -> str | None:
    """Pole bywa stringiem albo słownikiem {"text": ...}."""
    if isinstance(value, dict):
        return value.get("text") or value.get("label") or value.get("name")
    return value if isinstance(value, str) else None


def _dig(obj: Any, *path: str) -> Any:
    """Bezpieczne zejście po kluczach: _dig(d, "a", "b") == d["a"]["b"] albo None."""
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _price(price: Any) -> Any:
    """Cena z różnych wariantów struktury Allegro."""
    if not isinstance(price, dict):
        return price
    for path in (("mainPrice", "amount"), ("normal", "amount"), ("amount",), ("value",)):
        value = _dig(price, *path)
        if value is not None:
            return value
    return None


def _delivery(item: dict[str, Any]) -> str | None:
    """Opis dostawy: etykiety z bloku shipping + cena z dostawą, jeśli jest."""
    shipping = item.get("shipping")
    parts: list[str] = []
    if isinstance(shipping, dict):
        for d in walk_dicts(shipping):
            for key in ("text", "label"):
                value = d.get(key)
                if isinstance(value, str) and value.strip() and value not in parts:
                    parts.append(value.strip())
        with_delivery = _dig(shipping, "itemWithDelivery", "amount")
        if with_delivery:
            parts.append(f"z dostawą {with_delivery} zł")
    elif isinstance(shipping, str):
        parts.append(shipping)
    return ", ".join(parts[:3]) or None


def _seller(item: dict[str, Any]) -> str | None:
    seller = item.get("seller")
    if isinstance(seller, dict):
        return seller.get("login") or seller.get("title") or seller.get("name")
    return seller if isinstance(seller, str) else None


def _rating(item: dict[str, Any]) -> Any:
    for path in (
        ("productReview", "rating", "average"),
        ("productReview", "averageRating"),
        ("rating", "average"),
        ("rating",),
    ):
        value = _dig(item, *path)
        if isinstance(value, (int, float, str)):
            return value
    return None


def _from_embedded_json(soup: BeautifulSoup) -> list[dict[str, Any]]:
    offers = []
    for blob in iter_script_json(soup):
        for d in walk_dicts(blob):
            url = d.get("url")
            title = _as_text(d.get("name")) or _as_text(d.get("title"))
            if not (isinstance(url, str) and "/oferta/" in url and title and "price" in d):
                continue
            offers.append(
                make_offer(
                    tytul=title,
                    cena=_price(d.get("price")),
                    dostawa=_delivery(d),
                    sprzedawca=_seller(d),
                    ocena=_rating(d),
                    link=urljoin(HOME_URL, url),
                    zrodlo=NAME,
                )
            )
    return offers


def _from_html(soup: BeautifulSoup) -> list[dict[str, Any]]:
    offers = []
    for article in soup.find_all("article"):
        link_tag = article.find("a", href=re.compile(r"/oferta/"))
        if not link_tag:
            continue
        heading = article.find(["h2", "h3"])
        title = clean_text(heading.get_text(" ")) if heading else clean_text(link_tag.get_text(" "))

        price_tag = article.find(attrs={"aria-label": re.compile(r"^\s*cena", re.I)})
        price = price_tag["aria-label"] if price_tag else text_containing(article, ("zł",), 30)

        rating = None
        rating_tag = article.find(attrs={"aria-label": _RATING_RE})
        if rating_tag:
            rating = _RATING_RE.search(rating_tag["aria-label"]).group(1)

        seller = None
        seller_text = text_containing(article, ("od ",), 60)
        if seller_text and seller_text.lower().startswith("od "):
            seller = seller_text[3:]

        offers.append(
            make_offer(
                tytul=title,
                cena=price,
                dostawa=text_containing(article, ("dostaw", "smart")),
                sprzedawca=seller,
                ocena=rating,
                link=urljoin(HOME_URL, link_tag["href"]),
                zrodlo=NAME,
            )
        )
    return offers


def parse(html: str) -> list[dict[str, Any]]:
    """Zwraca listę ofert ze strony wyników Allegro."""
    soup = BeautifulSoup(html, "html.parser")
    for strategy in (_from_embedded_json, _from_html):
        offers = dedupe(strategy(soup))
        if offers:
            return offers
    return dedupe(offers_from_jsonld(soup, NAME, HOME_URL))
