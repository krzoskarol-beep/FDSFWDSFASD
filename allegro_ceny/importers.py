"""Import lokalnych plików: HTML zapisany z przeglądarki, CSV i JSON.

Ograniczenia trybu importu:
- nie wiadomo, czy plik zawiera wszystkie strony wyników — kompletność „nieznana”;
- czas pobrania jest znany tylko, jeśli plik go zawiera (inaczej null);
- HTML zapisany jako „tylko HTML” może nie zawierać ofert doładowanych skryptami —
  zapisuj stronę jako „Strona internetowa, kompletna” po przewinięciu do końca;
- dane z CSV/JSON są tak dobre, jak ich źródło — nie są weryfikowane z Allegro.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from .models import Oferta
from .money import parse_amount
from .parse import parse_listing
from .textnorm import clean_text, find_ean, fold
from .urls import clean_offer_url, offer_id_from_url

_ALIASY = {
    "offer_id": ("offer_id", "id", "id_oferty", "offerid"),
    "url": ("url", "link", "adres"),
    "tytul": ("tytul", "tytuł", "title", "nazwa", "name"),
    "cena": ("cena", "price", "cena_pln"),
    "waluta": ("waluta", "currency"),
    "koszt_dostawy": ("koszt_dostawy", "dostawa", "dostawa_koszt", "delivery", "delivery_cost", "shipping"),
    "cena_z_dostawa": ("cena_z_dostawa", "cena_z_dostawą", "total", "price_with_delivery"),
    "stan": ("stan", "condition"),
    "sprzedawca": ("sprzedawca", "seller"),
    "sponsorowana": ("sponsorowana", "sponsored"),
    "ean": ("ean", "gtin"),
    "pobrano": ("pobrano", "fetched_at", "data"),
    "fraza": ("fraza", "query"),
}

_STANY = {"nowy": "nowy", "nowe": "nowy", "new": "nowy", "uzywany": "używany", "uzywane": "używany",
          "used": "używany", "uszkodzony": "uszkodzony", "uszkodzone": "uszkodzony", "damaged": "uszkodzony"}


def _pole(row: dict[str, Any], klucz: str) -> Any:
    lower = {fold(str(k)).replace(" ", "_"): v for k, v in row.items()}
    for alias in _ALIASY[klucz]:
        v = lower.get(fold(alias).replace(" ", "_"))
        if v not in (None, ""):
            return v
    return None


def _bool(v: Any) -> bool | None:
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    f = fold(str(v))
    if f in ("1", "tak", "true", "yes"):
        return True
    if f in ("0", "nie", "false", "no"):
        return False
    return None


def oferta_z_wiersza(row: dict[str, Any], zrodlo: str) -> Oferta:
    if isinstance(row.get("tekst_sprzedawcy"), dict):  # format eksportu AI
        row = {**row, **row["tekst_sprzedawcy"]}
    url = _pole(row, "url")
    o = Oferta(zrodlo_danych=zrodlo)
    o.url = clean_offer_url(str(url)) if url else None
    oid = _pole(row, "offer_id")
    o.offer_id = str(oid).strip() if oid not in (None, "") else offer_id_from_url(str(url) if url else None)
    o.id_pewne = bool(o.offer_id) and not str(o.offer_id).startswith("x-")
    o.tytul = clean_text(_pole(row, "tytul"))
    o.cena = parse_amount(_pole(row, "cena"))
    o.waluta = (clean_text(_pole(row, "waluta")) or ("PLN" if o.cena is not None else None))
    o.cena_rodzaj = "pelna" if o.cena is not None else None
    o.koszt_dostawy = parse_amount(_pole(row, "koszt_dostawy"))
    o.cena_z_dostawa = parse_amount(_pole(row, "cena_z_dostawa"))
    if o.cena_z_dostawa is not None:
        o.cena_z_dostawa_zrodlo = "plik"
    elif o.cena is not None and o.koszt_dostawy is not None:
        o.cena_z_dostawa, o.cena_z_dostawa_zrodlo = o.cena + o.koszt_dostawy, "obliczona"
    stan = _pole(row, "stan")
    if stan:
        o.stan = _STANY.get(fold(str(stan)), clean_text(stan))
        o.stan_zrodlo = "plik"
    o.sprzedawca = clean_text(_pole(row, "sprzedawca"), 100)
    o.sponsorowana = _bool(_pole(row, "sponsorowana"))
    ean = _pole(row, "ean")
    o.ean = find_ean(str(ean)) if ean else None
    o.pobrano = clean_text(_pole(row, "pobrano"))
    o.fraza = clean_text(_pole(row, "fraza"))
    return o


def wczytaj_csv(path: Path) -> list[Oferta]:
    raw = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(raw[:4096], delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    return [oferta_z_wiersza(row, "import_csv") for row in csv.DictReader(io.StringIO(raw), dialect=dialect)]


def wczytaj_json(path: Path) -> list[Oferta]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        rows: list[Any] = []
        for key in ("oferty", "oferty_pasujace", "oferty_do_sprawdzenia", "offers"):
            if isinstance(data.get(key), list):
                rows.extend(data[key])
        data = rows
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: oczekiwano listy ofert albo obiektu z kluczem 'oferty'")
    return [oferta_z_wiersza(r, "import_json") for r in data if isinstance(r, dict)]


def wczytaj_plik(path: Path, strona: int | None = None) -> tuple[list[Oferta], dict[str, Any], str | None]:
    """Zwraca (oferty, diagnostyka, html lub None)."""
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm"):
        html = path.read_text(encoding="utf-8", errors="replace")
        wynik = parse_listing(html, strona=strona)
        return wynik.oferty, dict(wynik.diagnostyka), html
    if suffix == ".csv":
        return wczytaj_csv(path), {"format": "csv"}, None
    if suffix == ".json":
        return wczytaj_json(path), {"format": "json"}, None
    raise ValueError(f"Nieobsługiwany format pliku: {path.name} (obsługiwane: .html, .htm, .csv, .json)")
