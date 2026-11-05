"""Parsowanie strony wyników Allegro (HTML z DOM załadowanej strony) do listy ofert.

UWAGA O WERYFIKACJI: środowisko, w którym powstał ten kod, nie miało dostępu do
allegro.pl (blokada sieci). Selektory NIE zostały sprawdzone na aktualnej stronie.
Dlatego parser opiera się na cechach semantycznych i stabilnych, a nie na
klasach CSS (które Allegro generuje i często zmienia):

1. Kontener oferty: element <article> zawierający link do /oferta/…-<ID>.
   Zapasowo: najwyższy przodek linku oferty, który zawiera kwotę i tylko jedno ID.
2. Tytuł: nagłówek h2/h3 w kontenerze, potem tekst linku, potem alt obrazka.
3. Cena: aria-label zawierające „cena”, a w drugiej kolejności tekst kontenera —
   każda kwota klasyfikowana po tekście bezpośrednio przed i po niej
   (rata / z dostawą / dostawa / cena referencyjna / cena).
4. Dane uzupełniające z JSON osadzonego w <script> (application/json, ld+json)
   — tylko dla ofert znalezionych w DOM (żeby nie dołączać ofert z rekomendacji).

Przed pierwszym użyciem uruchom `python -m allegro_ceny diagnozuj zapisana_strona.html`
na stronie zapisanej z przeglądarki i sprawdź, czy liczby się zgadzają.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Iterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .models import Oferta, WynikStrony
from .money import find_amounts, normalize_spaces, parse_amount
from .textnorm import clean_text, find_ean, fold
from .urls import BASE_URL, clean_offer_url, is_offer_href, is_tracking_link, offer_id_from_url

_STAN_RE = re.compile(
    r"\bstan\s*:?\s*(nowy|nowa|nowe|uzywany|uzywana|uzywane|uszkodzony|uszkodzona|uszkodzone|"
    r"powystawowy|powystawowa|po zwrocie|odnowiony|odnowiona|na czesci)\b"
)
_STAN_KANON = {
    "nowy": "nowy", "nowa": "nowy", "nowe": "nowy",
    "uzywany": "używany", "uzywana": "używany", "uzywane": "używany",
    "uszkodzony": "uszkodzony", "uszkodzona": "uszkodzony", "uszkodzone": "uszkodzony",
    "na czesci": "uszkodzony",
    "powystawowy": "powystawowy", "powystawowa": "powystawowy",
    "po zwrocie": "po zwrocie", "odnowiony": "odnowiony", "odnowiona": "odnowiony",
}


# ---------------------------------------------------------------- kontenery

def _offer_links(node: Tag) -> list[Tag]:
    return [a for a in node.find_all("a", href=True) if is_offer_href(a["href"])]


def _ids_in(node: Tag) -> set[str]:
    return {i for a in _offer_links(node) if (i := offer_id_from_url(urljoin(BASE_URL, a["href"])))}


def _containers(soup: BeautifulSoup) -> tuple[list[Tag], str | None]:
    articles = [a for a in soup.find_all("article") if _offer_links(a)]
    # przy zagnieżdżonych <article> bierzemy najbardziej wewnętrzne
    articles = [a for a in articles if not any(_offer_links(inner) for inner in a.find_all("article"))]
    if articles:
        return articles, "dom_article"

    containers: list[Tag] = []
    seen: set[int] = set()
    for link in _offer_links(soup):
        best = None
        for anc in link.parents:
            if not isinstance(anc, Tag) or anc.name in ("body", "html", "[document]"):
                break
            if len(_ids_in(anc)) > 1:
                break
            if find_amounts(anc.get_text(" ")):
                best = anc
        if best is not None and id(best) not in seen:
            seen.add(id(best))
            containers.append(best)
    return containers, ("dom_kotwica" if containers else None)


# ---------------------------------------------------------------- pola z DOM

def _title(container: Tag, link: Tag) -> str | None:
    for tag in ("h2", "h3", "h4"):
        h = container.find(tag)
        if h and clean_text(h.get_text(" ")):
            return clean_text(h.get_text(" "))
    text = max((clean_text(a.get_text(" ")) or "" for a in _offer_links(container)), key=len, default="")
    if text:
        return text
    img = container.find("img", alt=True)
    return clean_text(img["alt"]) if img else None


def _classify(before: str, after: str, own: str) -> tuple[str, bool]:
    """Rodzaj kwoty na podstawie tekstu tuż przed i tuż po niej.

    Zwraca (rodzaj, prefiks_od). Rodzaje: rata, z_dostawa, dostawa, referencyjna, cena.
    """
    # Etykieta PRZED kwotą liczy się tylko, gdy przylega do niej od lewej (dopasowanie do końca `b`),
    # etykieta PO kwocie — gdy przylega od prawej (dopasowanie od początku `a`). Tekst pomiędzy
    # dwiema kwotami może być opisem poprzedniej albo następnej, więc nie szukamy w nim „gdziekolwiek”.
    b = fold(before)[-45:]
    a = fold(after)[:30]
    od = bool(re.search(r"(?<![a-z])od\s*$", b))
    if (re.search(r"\d\s*x\s*$", b) or re.search(r"(?<![a-z])(rata|raty|rat)\s*:?\s*(od\s*)?$", b)
            or re.match(r"\s*(/\s*mies|mies|miesiecz|x\s|rat|w ratach|w \d+ rat)", a)):
        return "rata", od
    if re.match(r"\s*(z dostaw|z wysylk|z kosztem dostawy|lacznie z dostaw)", a) or re.search(
            r"(z dostawa|z dostawy|z wysylka|cena z dostaw|lacznie z dostaw[a-z]*)\s*:?\s*(od\s*)?$", b):
        return "z_dostawa", od
    if re.search(r"(najnizsza cena[a-z0-9 ]{0,20}|30 dni|przed obnizk[a-z]*|cena regularna|poprzednia cena|"
                 r"cena katalogowa|oszczedzasz|cena sprzed[a-z ]{0,15})\s*:?\s*$", b):
        return "referencyjna", od
    b_clean = b.replace("darmowa dostawa", " ").replace("darmowa wysylka", " ")
    if re.search(r"(dostaw|wysylk|przesylk)[a-z]*\s*(:|od)?\s*(od\s*)?$", b_clean[-25:]) or re.search(r"\+\s*$", b):
        return "dostawa", od
    if re.match(r"\s*\+", own):
        return "dostawa", od
    return "cena", od


def _prices(container: Tag, title: str | None, oferta: Oferta) -> None:
    # 1) aria-label z „cena”, bez rat i dostawy
    for el in container.find_all(attrs={"aria-label": True}):
        label = normalize_spaces(el["aria-label"])
        f = fold(label)
        if "cen" in f and not re.search(r"rat|mies|dostaw|najnizsz|30 dni", f):
            amounts = find_amounts(label)
            if amounts:
                oferta.cena = amounts[0][0]
                oferta.cena_rodzaj = "od" if re.search(r"(?<![a-z])od\s", f) else "pelna"
                break

    text = normalize_spaces(container.get_text(" "))
    if title and title in text:
        text = text.replace(title, " ", 1)
    amounts = find_amounts(text)
    found: dict[str, list[tuple[Decimal, bool]]] = {}
    for i, (value, start, end) in enumerate(amounts):
        prev_end = amounts[i - 1][2] if i else 0
        next_start = amounts[i + 1][1] if i + 1 < len(amounts) else len(text)
        kind, od = _classify(text[prev_end:start], text[end:next_start], text[max(0, start - 2):end])
        found.setdefault(kind, []).append((value, od))

    if oferta.cena is None and found.get("cena"):
        value, od = found["cena"][0]
        oferta.cena = value
        oferta.cena_rodzaj = "od" if od else "pelna"
        distinct = {v for v, _ in found["cena"]}
        if len(distinct) > 1:
            oferta.ostrzezenia_parsera.append(
                "wiele kandydatów ceny: " + ", ".join(f"{v:.2f}" for v in sorted(distinct)) + " — wybrano pierwszą"
            )
    if oferta.cena is not None:
        oferta.waluta = "PLN"
    elif found.get("rata"):
        oferta.ostrzezenia_parsera.append("znaleziono tylko ratę, brak pełnej ceny — cena = null")
    if oferta.cena_rodzaj == "od":
        oferta.uwagi.append("cena „od” — najniższa z wariantów, nie musi dotyczyć tego wariantu produktu")

    if found.get("z_dostawa"):
        oferta.cena_z_dostawa = found["z_dostawa"][0][0]
        oferta.cena_z_dostawa_zrodlo = "strona"
    if found.get("dostawa"):
        value, od = found["dostawa"][0]
        if od:
            oferta.koszt_dostawy_od = value
        else:
            oferta.koszt_dostawy = value

    _delivery_text(container, text, oferta)


def _delivery_text(container: Tag, text: str, oferta: Oferta) -> None:
    f = fold(text)
    if "smart" in f:
        oferta.smart = True
    # Oryginalne fragmenty tekstu o dostawie (z sąsiednią kwotą, jeśli etykieta stoi osobno).
    segs = [normalize_spaces(x) for x in container.stripped_strings]
    pieces: list[str] = []
    for i, seg in enumerate(segs):
        if not re.search(r"dostaw|wysylk|smart", fold(seg)):
            continue
        piece = seg
        if not find_amounts(seg):
            if re.match(r"\s*z\s", fold(seg)) and i > 0 and find_amounts(segs[i - 1]):
                piece = f"{segs[i - 1]} {seg}"
            elif i + 1 < len(segs) and find_amounts(segs[i + 1]) and re.search(r"(:|od)\s*$", fold(seg) + " "):
                piece = f"{seg} {segs[i + 1]}"
        pieces.append(piece)
    if pieces:
        oferta.dostawa_tekst = clean_text(" | ".join(dict.fromkeys(pieces)), 200)
    darmowa = re.search(r"darmowa (dostawa|wysylka)|dostawa (za darmo|gratis|0 zl)", f)
    warunkowa = re.search(r"smart|przy zakupie|od \d|powyzej|warunk", f)
    if darmowa and oferta.koszt_dostawy is None and oferta.koszt_dostawy_od is None:
        if warunkowa:
            oferta.uwagi.append("darmowa dostawa warunkowa (np. Smart/próg) — koszt dostawy nieustalony")
        else:
            oferta.koszt_dostawy = Decimal("0.00")
            oferta.uwagi.append("koszt dostawy 0 wg deklaracji „darmowa dostawa” na liście wyników")


def _from_container(container: Tag, strategy: str) -> Oferta | None:
    links = _offer_links(container)
    if not links:
        return None
    link = links[0]
    href = urljoin(BASE_URL, link["href"])
    oferta = Oferta(zrodlo_danych=strategy)
    oferta.offer_id = offer_id_from_url(href)
    oferta.id_pewne = oferta.offer_id is not None
    oferta.url = clean_offer_url(href)
    oferta.tytul = _title(container, link)
    _prices(container, oferta.tytul, oferta)

    if oferta.cena_z_dostawa is None and oferta.cena is not None and oferta.koszt_dostawy is not None:
        oferta.cena_z_dostawa = oferta.cena + oferta.koszt_dostawy
        oferta.cena_z_dostawa_zrodlo = "obliczona"

    folded = fold(container.get_text(" "))
    m = _STAN_RE.search(folded)
    if m:
        oferta.stan = _STAN_KANON[m.group(1)]
        oferta.stan_zrodlo = "parametr"

    seller = container.find("a", href=re.compile(r"/uzytkownik/"))
    if seller:
        oferta.sprzedawca = clean_text(seller.get_text(" "), 100)

    oferta.sponsorowana = bool(re.search(r"sponsorowan", folded) or any(is_tracking_link(urljoin(BASE_URL, a["href"])) for a in links))
    oferta.ean = find_ean(container.get_text(" "))
    return oferta


# ---------------------------------------------------------------- JSON osadzony

def _iter_json(soup: BeautifulSoup) -> Iterator[Any]:
    for script in soup.find_all("script"):
        stype = (script.get("type") or "").lower()
        if not (stype in ("application/json", "application/ld+json") or script.has_attr("data-serialize-box-id")):
            continue
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            yield json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue


def _walk(obj: Any, depth: int = 0) -> Iterator[dict]:
    if depth > 40:
        return
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, depth + 1)


def _dig(obj: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _text(v: Any) -> str | None:
    if isinstance(v, dict):
        v = v.get("text") or v.get("name") or v.get("label")
    return clean_text(v) if isinstance(v, str) else None


_JSON_PRICE_PATHS = (
    (("sellingMode", "price"), "pelna"),
    (("price", "mainPrice"), "pelna"),
    (("price", "normal"), "pelna"),
    (("price",), "pelna"),
    (("offers",), "pelna"),
)


def _json_price(d: dict) -> tuple[Decimal | None, str | None, str | None]:
    for path, kind in _JSON_PRICE_PATHS:
        node = _dig(d, *path)
        if node is None:
            continue
        if isinstance(node, dict):
            if "lowPrice" in node and "price" not in node:
                return parse_amount(node.get("lowPrice")), node.get("priceCurrency"), "od"
            amount = node.get("amount", node.get("price", node.get("value")))
            currency = node.get("currency") or node.get("priceCurrency")
        else:
            amount, currency = node, d.get("priceCurrency") or d.get("currency")
        value = parse_amount(amount)
        if value is not None:
            return value, currency if isinstance(currency, str) else None, kind
    return None, None, None


def _from_json(soup: BeautifulSoup) -> tuple[dict[str, Oferta], int]:
    found: dict[str, Oferta] = {}
    scripts = 0
    for blob in _iter_json(soup):
        scripts += 1
        for d in _walk(blob):
            url = d.get("url") if isinstance(d.get("url"), str) else None
            oid = offer_id_from_url(urljoin(BASE_URL, url)) if url else None
            if oid is None:
                continue
            title = _text(d.get("name")) or _text(d.get("title"))
            price, currency, kind = _json_price(d)
            if not title and price is None:
                continue
            o = found.setdefault(oid, Oferta(offer_id=oid, id_pewne=True, url=clean_offer_url(url),
                                             zrodlo_danych="json_osadzony"))
            o.tytul = o.tytul or title
            if o.cena is None and price is not None:
                o.cena, o.waluta, o.cena_rodzaj = price, (currency or "PLN").upper(), kind
            seller = _text(_dig(d, "seller", "login")) or _text(_dig(d, "seller", "name"))
            o.sprzedawca = o.sprzedawca or seller
            ean = d.get("ean") or d.get("gtin13") or d.get("gtin")
            if isinstance(ean, (str, int)) and find_ean(str(ean)):
                o.ean = str(ean)
            for flag in ("sponsored", "isSponsored"):
                if isinstance(d.get(flag), bool):
                    o.sponsorowana = d[flag]
    return found, scripts


# ---------------------------------------------------------------- API modułu

def parse_listing(html: str, *, strona: int | None = None) -> WynikStrony:
    soup = BeautifulSoup(html, "html.parser")
    containers, strategy = _containers(soup)
    oferty: list[Oferta] = []
    for pos, container in enumerate(containers, start=1):
        o = _from_container(container, strategy or "dom")
        if o is None:
            continue
        o.strona, o.pozycja = strona, pos
        oferty.append(o)

    json_offers, scripts = _from_json(soup)
    uzupelnione = 0
    if oferty:
        for o in oferty:
            j = json_offers.get(o.offer_id or "")
            if not j:
                continue
            uzupelnione += 1
            for attr in ("tytul", "sprzedawca", "ean"):
                if getattr(o, attr) is None and getattr(j, attr) is not None:
                    setattr(o, attr, getattr(j, attr))
            if o.cena is None and j.cena is not None:
                o.cena, o.waluta, o.cena_rodzaj = j.cena, j.waluta, j.cena_rodzaj
                o.ostrzezenia_parsera.append("cena z JSON osadzonego (brak w DOM)")
            elif o.cena is not None and j.cena is not None and o.cena != j.cena:
                o.ostrzezenia_parsera.append(f"rozbieżność ceny DOM {o.cena} vs JSON {j.cena}")
    elif json_offers:
        strategy = "json_osadzony"
        for pos, o in enumerate(json_offers.values(), start=1):
            o.strona, o.pozycja = strona, pos
            o.ostrzezenia_parsera.append("oferta tylko z JSON osadzonego — sprawdź, czy to wynik wyszukiwania, a nie rekomendacja")
            oferty.append(o)

    pola = ("offer_id", "tytul", "cena", "koszt_dostawy", "stan", "sprzedawca")
    braki = {p: sum(1 for o in oferty if getattr(o, p) is None) for p in pola}
    diag = {
        "strategia": strategy,
        "kontenery": len(containers),
        "linki_ofert_na_stronie": len(_ids_in(soup)),
        "skrypty_json": scripts,
        "oferty_w_json": len(json_offers),
        "uzupelnione_z_json": uzupelnione,
        "oferty": len(oferty),
        "braki_pol": braki,
        "elementy_article": len(soup.find_all("article")),
    }
    return WynikStrony(oferty=oferty, strategia=strategy, diagnostyka=diag)


def rel_next(html: str) -> str | None:
    """Link do następnej strony, jeśli strona go deklaruje (rel=next)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["a", "link"], rel=True):
        if "next" in [r.lower() for r in tag.get("rel", [])] and tag.get("href"):
            return urljoin(BASE_URL, tag["href"])
    return None
