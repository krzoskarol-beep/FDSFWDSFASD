"""Adresy Allegro: budowa adresu wyników, numer strony, czyszczenie linków ofert, ID oferty."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit, urlunsplit

BASE_URL = "https://allegro.pl/"

# Identyfikator oferty jest liczbą na końcu ścieżki /oferta/<slug>-<id>
# (albo /oferta/<id>). Wymagamy co najmniej 6 cyfr, żeby nie łapać fragmentów slugów.
_OFFER_PATH_ID = re.compile(r"/oferta/(?:[^/?#]*?-)?(?P<id>\d{6,})(?:[/?#]|$)")

# Parametry, które w adresie wyników mogą zawierać docelowy link oferty
# (np. linki śledzące ofert sponsorowanych).
_REDIRECT_KEYS = ("redirect", "url", "u", "target", "destination")


def search_url(phrase: str, base: str = BASE_URL) -> str:
    """Adres wyników dla frazy. Celowo tylko parametr `string` — pozostałe filtry
    Allegro najlepiej ustawić w przeglądarce i podać gotowy adres (--url)."""
    return urljoin(base, "listing") + "?string=" + quote(phrase.strip(), safe="")


def with_page(url: str, page: int) -> str:
    """Ustawia numer strony (parametr `p`), zachowując pozostałe parametry."""
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    if page <= 1:
        query.pop("p", None)
    else:
        query["p"] = [str(page)]
    return urlunsplit(parts._replace(query=urlencode(query, doseq=True)))


def page_number(url: str) -> int:
    try:
        return int(parse_qs(urlsplit(url).query).get("p", ["1"])[0])
    except (ValueError, IndexError):
        return 1


def _unwrap_redirect(url: str, depth: int = 0) -> str:
    """Jeśli link jest przekierowaniem (np. link śledzący), zwraca adres docelowy oferty."""
    if depth > 3:
        return url
    parts = urlsplit(url)
    if "/oferta/" in parts.path or "/produkt/" in parts.path:
        return url
    query = parse_qs(parts.query)
    for key in _REDIRECT_KEYS:
        for candidate in query.get(key, []):
            if "/oferta/" in candidate or "/produkt/" in candidate:
                return _unwrap_redirect(candidate, depth + 1)
    return url


def is_tracking_link(url: str) -> bool:
    return _unwrap_redirect(url) != url


def offer_id_from_url(url: str | None) -> str | None:
    if not url:
        return None
    target = _unwrap_redirect(url)
    m = _OFFER_PATH_ID.search(urlsplit(target).path + "/")
    if m:
        return m.group("id")
    offer_param = parse_qs(urlsplit(target).query).get("offerId")
    if offer_param and offer_param[0].isdigit():
        return offer_param[0]
    return None


def clean_offer_url(url: str | None, base: str = BASE_URL) -> str | None:
    """Bezpośredni, oczyszczony link: bez parametrów śledzących i fragmentu.

    /oferta/...-123   -> https://allegro.pl/oferta/...-123
    /produkt/...?offerId=123&x=y -> https://allegro.pl/produkt/...?offerId=123
    """
    if not url:
        return None
    absolute = urljoin(base, url.strip())
    target = _unwrap_redirect(absolute)
    parts = urlsplit(urljoin(base, target))
    if "/oferta/" in parts.path:
        return urlunsplit((parts.scheme or "https", parts.netloc, parts.path, "", ""))
    if "/produkt/" in parts.path:
        offer = parse_qs(parts.query).get("offerId")
        query = urlencode({"offerId": offer[0]}) if offer else ""
        return urlunsplit((parts.scheme or "https", parts.netloc, parts.path, query, ""))
    return None


def is_offer_href(href: str | None) -> bool:
    if not href:
        return False
    return offer_id_from_url(urljoin(BASE_URL, href)) is not None


def safe_url_for_log(url: str) -> str:
    """Adres do logów/diagnostyki: tylko host, ścieżka i parametry wyszukiwania."""
    parts = urlsplit(url)
    allowed = {k: v for k, v in parse_qs(parts.query).items() if k in {"string", "p", "order", "stan"}}
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(allowed, doseq=True), ""))
