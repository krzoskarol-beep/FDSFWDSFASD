"""Profile wyszukiwania (pliki TOML w katalogu profile/)."""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from .money import parse_amount
from .textnorm import phrase_pattern

STANY = {"nowy", "używany", "uszkodzony"}
_STAN_ALIASY = {
    "nowe": "nowy", "nowy": "nowy", "nowa": "nowy",
    "używane": "używany", "używany": "używany", "uzywane": "używany", "uzywany": "używany",
    "uszkodzone": "uszkodzony", "uszkodzony": "uszkodzony", "na części": "uszkodzony",
}


class BladProfilu(ValueError):
    pass


@dataclass
class Profil:
    nazwa: str
    fraza: str | None = None
    url: str | None = None

    marka: str | None = None
    model: str | None = None
    aliasy_modelu: list[str] = field(default_factory=list)
    akceptowane_marki: list[str] = field(default_factory=list)

    slowa_produktu: list[str] = field(default_factory=list)
    frazy_neutralne: list[str] = field(default_factory=list)
    slowa_czesci: list[str] = field(default_factory=list)
    slowa_opakowania: list[str] = field(default_factory=list)
    marki_czesci: list[str] = field(default_factory=list)
    slowa_niekompletny: list[str] = field(default_factory=list)
    wykluczone_slowa: list[str] = field(default_factory=list)

    stany: list[str] = field(default_factory=lambda: ["nowy", "używany"])
    cena_min: Decimal | None = None
    cena_max: Decimal | None = None
    cena_podejrzana_ponizej: Decimal | None = None

    max_stron: int = 3
    max_ofert: int = 150
    odstep_s: float = 6.0
    limit_czasu_s: float = 45.0
    ponowienia: int = 2

    def kryteria(self) -> dict[str, Any]:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, Decimal):
                d[k] = f"{v:.2f}"
        return d


def _str_list(raw: Any, key: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(x, str) and x.strip() for x in raw):
        raise BladProfilu(f"'{key}' musi być listą niepustych tekstów")
    return [x.strip() for x in raw]


def _norm_stany(raw: list[str]) -> list[str]:
    out = []
    for s in raw:
        norm = _STAN_ALIASY.get(s.strip().lower())
        if norm is None:
            raise BladProfilu(f"Nieznany stan '{s}'. Dozwolone: nowe, używane, uszkodzone")
        if norm not in out:
            out.append(norm)
    return out


def _amount(raw: Any, key: str) -> Decimal | None:
    if raw is None:
        return None
    value = parse_amount(raw)
    if value is None:
        raise BladProfilu(f"'{key}' nie jest poprawną kwotą: {raw!r}")
    return value


def profil_z_dict(data: dict[str, Any], nazwa_domyslna: str = "adhoc") -> Profil:
    wyszukiwanie = data.get("wyszukiwanie", {})
    produkt = data.get("produkt", {})
    filtry = data.get("filtry", {})
    pobieranie = data.get("pobieranie", {})

    p = Profil(
        nazwa=str(data.get("nazwa") or nazwa_domyslna),
        fraza=wyszukiwanie.get("fraza"),
        url=wyszukiwanie.get("url"),
        marka=produkt.get("marka"),
        model=produkt.get("model"),
        aliasy_modelu=_str_list(produkt.get("aliasy_modelu"), "produkt.aliasy_modelu"),
        akceptowane_marki=_str_list(produkt.get("akceptowane_marki"), "produkt.akceptowane_marki"),
        slowa_produktu=_str_list(produkt.get("slowa_produktu"), "produkt.slowa_produktu"),
        frazy_neutralne=_str_list(produkt.get("frazy_neutralne"), "produkt.frazy_neutralne"),
        slowa_czesci=_str_list(filtry.get("slowa_czesci"), "filtry.slowa_czesci"),
        slowa_opakowania=_str_list(filtry.get("slowa_opakowania"), "filtry.slowa_opakowania"),
        marki_czesci=_str_list(filtry.get("marki_czesci"), "filtry.marki_czesci"),
        slowa_niekompletny=_str_list(filtry.get("slowa_niekompletny"), "filtry.slowa_niekompletny"),
        wykluczone_slowa=_str_list(filtry.get("wykluczone_slowa"), "filtry.wykluczone_slowa"),
        stany=_norm_stany(_str_list(filtry.get("stany"), "filtry.stany") or ["nowe", "używane"]),
        cena_min=_amount(filtry.get("cena_min"), "filtry.cena_min"),
        cena_max=_amount(filtry.get("cena_max"), "filtry.cena_max"),
        cena_podejrzana_ponizej=_amount(filtry.get("cena_podejrzana_ponizej"), "filtry.cena_podejrzana_ponizej"),
        max_stron=int(pobieranie.get("max_stron", 3)),
        max_ofert=int(pobieranie.get("max_ofert", 150)),
        odstep_s=float(pobieranie.get("odstep_s", 6.0)),
        limit_czasu_s=float(pobieranie.get("limit_czasu_s", 45.0)),
        ponowienia=int(pobieranie.get("ponowienia", 2)),
    )
    if p.marka and not p.akceptowane_marki:
        p.akceptowane_marki = [p.marka]
    waliduj(p)
    return p


def waliduj(p: Profil) -> None:
    if p.max_stron < 1 or p.max_stron > 50:
        raise BladProfilu("max_stron musi być w zakresie 1–50")
    if p.max_ofert < 1:
        raise BladProfilu("max_ofert musi być dodatnie")
    if p.odstep_s < 2 and p.odstep_s != 0:
        # 0 dopuszczamy wyłącznie dla testów na lokalnym serwerze
        raise BladProfilu("odstep_s: minimum 2 sekundy między stronami (nie obciążaj serwisu)")
    if p.ponowienia < 0 or p.ponowienia > 5:
        raise BladProfilu("ponowienia: zakres 0–5")
    if p.cena_min is not None and p.cena_max is not None and p.cena_min > p.cena_max:
        raise BladProfilu("cena_min jest większa niż cena_max")
    for lista in (p.aliasy_modelu, p.slowa_produktu, p.frazy_neutralne, p.slowa_czesci, p.slowa_opakowania,
                  p.slowa_niekompletny, p.wykluczone_slowa, p.akceptowane_marki, p.marki_czesci):
        for fraza in lista:
            phrase_pattern(fraza)  # zgłosi błąd dla pustych fraz


def wczytaj_profil(path: str | Path) -> Profil:
    path = Path(path)
    if not path.exists():
        raise BladProfilu(f"Nie znaleziono profilu: {path}")
    with path.open("rb") as fh:
        try:
            data = tomllib.load(fh)
        except tomllib.TOMLDecodeError as exc:
            raise BladProfilu(f"Błąd składni TOML w {path}: {exc}") from exc
    return profil_z_dict(data, nazwa_domyslna=path.stem)
