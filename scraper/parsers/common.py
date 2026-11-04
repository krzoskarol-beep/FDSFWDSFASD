"""Wspólne narzędzia parserów: ceny, oceny, JSON osadzony w HTML, format oferty."""

from __future__ import annotations

import json
import re
from typing import Any, Iterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

# Liczba z separatorami tysięcy (spacja, twarda spacja, kropka) i groszami po przecinku/kropce.
_PRICE_RE = re.compile(r"\d[\d   .]*(?:[.,]\d{1,2})?")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def clean_text(value: Any) -> str | None:
    """Zwija białe znaki; pusty tekst zamienia na None."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def parse_price(value: Any) -> float | None:
    """Zamienia „1 299,99 zł” / „1299.99” / 1299.99 na float."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    text = str(value).replace(" ", " ").replace(" ", " ")
    match = _PRICE_RE.search(text)
    if not match:
        return None
    num = match.group(0).strip().replace(" ", "")
    if "," in num:
        # Format polski: kropka/spacja = tysiące, przecinek = grosze.
        num = num.replace(".", "").replace(",", ".")
    elif num.count(".") > 1:
        num = num.replace(".", "")
    try:
        return round(float(num), 2)
    except ValueError:
        return None


def parse_rating(value: Any, scale: float = 5.0) -> float | None:
    """Wyciąga ocenę, np. „4,8 / 5” -> 4.8. Odrzuca wartości spoza skali."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        rating = float(value)
    else:
        match = _NUMBER_RE.search(str(value))
        if not match:
            return None
        rating = float(match.group(0).replace(",", "."))
    return round(rating, 2) if 0 <= rating <= scale else None


def make_offer(
    *,
    tytul: Any,
    cena: Any,
    dostawa: Any,
    sprzedawca: Any,
    ocena: Any,
    link: Any,
    zrodlo: str,
) -> dict[str, Any]:
    """Jednolity format oferty — te same pola niezależnie od źródła."""
    return {
        "tytul": clean_text(tytul),
        "cena": parse_price(cena),
        "dostawa": clean_text(dostawa),
        "sprzedawca": clean_text(sprzedawca),
        "ocena": parse_rating(ocena),
        "link": clean_text(link),
        "zrodlo": zrodlo,
    }


def dedupe(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Usuwa duplikaty (po linku) i oferty bez tytułu lub linku."""
    seen: set[str] = set()
    result = []
    for offer in offers:
        link = offer.get("link")
        if not link or not offer.get("tytul") or link in seen:
            continue
        seen.add(link)
        result.append(offer)
    return result


def iter_script_json(soup: BeautifulSoup, ld_only: bool = False) -> Iterator[Any]:
    """Zwraca sparsowane bloki JSON osadzone w <script> (application/json, ld+json)."""
    for script in soup.find_all("script"):
        stype = (script.get("type") or "").lower()
        is_ld = stype == "application/ld+json"
        is_json = stype == "application/json" or script.has_attr("data-serialize-box-id")
        if not (is_ld or (is_json and not ld_only)):
            continue
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            yield json.loads(raw)
        except ValueError:
            continue


def walk_dicts(obj: Any) -> Iterator[dict[str, Any]]:
    """Iteracyjnie (bez rekurencji) przechodzi po wszystkich słownikach w strukturze JSON."""
    stack = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def text_containing(tag: Tag, keywords: tuple[str, ...], max_len: int = 80) -> str | None:
    """Pierwszy krótki fragment tekstu w elemencie zawierający któreś ze słów kluczowych."""
    for string in tag.find_all(string=True):
        text = clean_text(string)
        if text and len(text) <= max_len and any(k in text.lower() for k in keywords):
            return text
    return None


def offers_from_jsonld(soup: BeautifulSoup, zrodlo: str, base_url: str) -> list[dict[str, Any]]:
    """Fallback: oferty z danych strukturalnych schema.org (Product / Offer)."""
    offers = []
    for blob in iter_script_json(soup, ld_only=True):
        for d in walk_dicts(blob):
            dtype = d.get("@type")
            types = dtype if isinstance(dtype, list) else [dtype]
            if "Product" not in types:
                continue
            offer_data = d.get("offers") or {}
            if isinstance(offer_data, list):
                offer_data = offer_data[0] if offer_data else {}
            seller = offer_data.get("seller") or {}
            rating = d.get("aggregateRating") or {}
            url = d.get("url") or offer_data.get("url")
            offers.append(
                make_offer(
                    tytul=d.get("name"),
                    cena=offer_data.get("price") or offer_data.get("lowPrice"),
                    dostawa=None,
                    sprzedawca=seller.get("name") if isinstance(seller, dict) else seller,
                    ocena=rating.get("ratingValue") if isinstance(rating, dict) else None,
                    link=urljoin(base_url, url) if url else None,
                    zrodlo=zrodlo,
                )
            )
    return offers
