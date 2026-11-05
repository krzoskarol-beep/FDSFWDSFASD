"""Analiza cen ofertowych.

To są ceny OFERTOWE (wystawione), nie potwierdzone ceny sprzedaży.
Zniknięcie oferty między przebiegami nie oznacza sprzedaży.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from .config import Profil
from .models import Decyzja, Oferta
from .money import GROSZ, dec_str, from_grosze

MALA_PROBA = 5          # poniżej: tylko orientacyjne wartości, bez kwartyli
MIN_DO_KWARTYLI = 4


def kwantyl(posortowane: list[Decimal], q: Decimal) -> Decimal:
    """Interpolacja liniowa (jak numpy 'linear' / Excel KWARTYL.PRZEDZ.ZAMK)."""
    n = len(posortowane)
    if n == 1:
        return posortowane[0]
    pos = (Decimal(n) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return (posortowane[lo] + (posortowane[hi] - posortowane[lo]) * frac).quantize(GROSZ)


def statystyki(ceny: list[Decimal]) -> dict[str, Any]:
    ceny = sorted(c for c in ceny if c is not None)
    n = len(ceny)
    out: dict[str, Any] = {"n": n}
    if n == 0:
        out["uwaga"] = "brak danych"
        return out
    out["min"] = dec_str(ceny[0])
    out["mediana"] = dec_str(kwantyl(ceny, Decimal("0.5")))
    out["max"] = dec_str(ceny[-1])
    if n >= MIN_DO_KWARTYLI:
        out["q1"] = dec_str(kwantyl(ceny, Decimal("0.25")))
        out["q3"] = dec_str(kwantyl(ceny, Decimal("0.75")))
    else:
        out["q1"] = out["q3"] = None
    if n < MALA_PROBA:
        out["uwaga"] = f"mała próba (n={n}) — wartości orientacyjne, bez mocnych wniosków"
    return out


def _grupa_stanu(stan: str | None) -> str:
    if stan in ("nowy", "używany", "uszkodzony"):
        return stan
    return "nieznany" if stan is None else "inny"


def podejrzanie_niskie(oferty: list[Oferta], profil: Profil | None = None) -> list[dict[str, Any]]:
    """Oferty o cenie odstającej w dół (do kontroli: część, błąd, oszustwo, cena „od”)."""
    ceny = sorted(o.cena for o in oferty if o.cena is not None)
    flagi = []
    prog_iqr = prog_med = None
    if len(ceny) >= MALA_PROBA:
        q1, q3 = kwantyl(ceny, Decimal("0.25")), kwantyl(ceny, Decimal("0.75"))
        prog_iqr = q1 - (q3 - q1) * Decimal("1.5")
    if len(ceny) >= 3:
        prog_med = kwantyl(ceny, Decimal("0.5")) * Decimal("0.6")
    for o in oferty:
        if o.cena is None:
            continue
        powody = []
        if profil and profil.cena_podejrzana_ponizej is not None and o.cena < profil.cena_podejrzana_ponizej:
            powody.append(f"poniżej progu z profilu ({dec_str(profil.cena_podejrzana_ponizej)})")
        if prog_iqr is not None and o.cena < prog_iqr:
            powody.append(f"poniżej Q1 − 1,5·IQR ({dec_str(prog_iqr)})")
        if prog_med is not None and o.cena < prog_med:
            powody.append(f"poniżej 60% mediany ({dec_str(prog_med)})")
        if powody:
            flagi.append({"offer_id": o.offer_id, "cena": dec_str(o.cena), "url": o.url, "powody": powody})
    return flagi


def analizuj(oferty: list[Oferta], profil: Profil | None = None, top: int = 10) -> dict[str, Any]:
    licznik = Counter(o.decyzja.value if o.decyzja else "brak_decyzji" for o in oferty)
    pasujace = [o for o in oferty if o.decyzja == Decyzja.PASUJE]
    porownywalne = [o for o in pasujace if o.cena is not None and o.cena_rodzaj != "od"]

    wg_stanu: dict[str, Any] = {}
    for grupa in ("nowy", "używany", "uszkodzony", "inny", "nieznany"):
        ceny = [o.cena for o in porownywalne if _grupa_stanu(o.stan) == grupa]
        if ceny:
            wg_stanu[grupa] = statystyki(ceny)

    z_dostawa = [o for o in porownywalne if o.cena_z_dostawa is not None]
    flagi = podejrzanie_niskie(porownywalne, profil)
    podejrzane_ids = {f["offer_id"] for f in flagi}

    najtansze = sorted(porownywalne, key=lambda o: o.cena)[:top]
    powody_odrzucen = Counter(
        (o.powod or "").split(";")[0].strip() for o in oferty if o.decyzja == Decyzja.ODRZUCONA
    )

    wynik = {
        "liczby": {
            "wszystkie": len(oferty),
            "pasuje": licznik.get(Decyzja.PASUJE.value, 0),
            "odrzucona": licznik.get(Decyzja.ODRZUCONA.value, 0),
            "wymaga_sprawdzenia": licznik.get(Decyzja.DO_SPRAWDZENIA.value, 0),
            "porownywalne_pasujace": len(porownywalne),
            "pasujace_wykluczone_ze_statystyk": len(pasujace) - len(porownywalne),
        },
        "ceny_pasujacych": statystyki([o.cena for o in porownywalne]),
        "ceny_pasujacych_bez_podejrzanych": (
            statystyki([o.cena for o in porownywalne if o.offer_id not in podejrzane_ids]) if podejrzane_ids else None
        ),
        "wg_stanu": wg_stanu,
        "z_dostawa": {
            "opis": "tylko oferty, dla których cena z dostawą jest znana (ze strony lub cena + dokładny koszt dostawy)",
            "pokrycie": f"{len(z_dostawa)}/{len(porownywalne)}",
            "statystyki": statystyki([o.cena_z_dostawa for o in z_dostawa]),
        },
        "najtansze": [
            {"offer_id": o.offer_id, "cena": dec_str(o.cena), "cena_z_dostawa": dec_str(o.cena_z_dostawa),
             "stan": o.stan, "url": o.url, "tytul": o.tytul, "podejrzanie_niska": o.offer_id in podejrzane_ids}
            for o in najtansze
        ],
        "podejrzanie_niskie": flagi,
        "glowne_powody_odrzucen": dict(powody_odrzucen.most_common(10)),
        "zastrzezenia": [
            "Ceny ofertowe, nie potwierdzone ceny sprzedaży.",
            "Statystyki tylko dla ofert 'pasuje' z pełną ceną (bez cen „od”).",
            "Oferty 'wymaga_sprawdzenia' nie są wliczone w statystyki.",
        ],
    }
    if len(porownywalne) < MALA_PROBA:
        wynik["zastrzezenia"].append(f"Mała próba (n={len(porownywalne)}): nie wyciągaj mocnych wniosków.")
    return wynik


def zmiany_cen(historia: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Zmiany ceny tej samej oferty między kolejnymi obserwacjami."""
    zmiany = []
    for offer_id, obs in historia.items():
        for prev, cur in zip(obs, obs[1:]):
            if prev["cena_gr"] is None or cur["cena_gr"] is None or prev["cena_gr"] == cur["cena_gr"]:
                continue
            p, c = from_grosze(prev["cena_gr"]), from_grosze(cur["cena_gr"])
            zmiany.append({
                "offer_id": offer_id, "url": cur["url"], "tytul": cur["tytul"],
                "przebieg_poprzedni": prev["przebieg_id"], "przebieg_biezacy": cur["przebieg_id"],
                "cena_poprzednia": dec_str(p), "cena_biezaca": dec_str(c), "roznica": dec_str(c - p),
                "zmiana_proc": f"{((c - p) / p * 100).quantize(Decimal('0.1'))}" if p else None,
            })
    return zmiany


def niewidziane(historia: dict[str, list[dict[str, Any]]], ostatni_przebieg: int,
                status_ostatniego: str) -> dict[str, Any]:
    """Oferty widziane wcześniej, a nieobecne w ostatnim przebiegu. NIE oznacza sprzedaży."""
    ids = [oid for oid, obs in historia.items() if obs and obs[-1]["przebieg_id"] < ostatni_przebieg]
    return {
        "liczba": len(ids),
        "offer_ids": ids[:50],
        "uwaga": (
            "Brak oferty w ostatnim przebiegu może oznaczać zakończenie, zmianę pozycji w wynikach, "
            "limit stron lub zmianę tytułu — nie jest dowodem sprzedaży."
            + ("" if status_ostatniego == "pelny" else " Ostatni przebieg nie był pełny, więc lista jest szczególnie niepewna.")
        ),
    }
