"""Filtr ofert: każda oferta dostaje decyzję i uzasadnienie.

Decyzje:
- pasuje             — zgodny model, akceptowana marka, akceptowany stan, znana pełna cena;
- odrzucona          — pewny powód (inny model, część, inna marka, stan, cena poza zakresem…);
- wymaga_sprawdzenia — brak pewności (brak modelu w tytule, marka nieustalona, kilka modeli,
                       cena „od”, możliwy brak elementów…).

Zasada ostrożności: przy wątpliwości wybieramy „wymaga_sprawdzenia”, a nie odrzucenie.
Wzmianka o części w tytule kompletnego produktu (np. „Pilarka … + łańcuch”) nie odrzuca oferty.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Profil
from .models import MARKA_NIEUSTALONA, Decyzja, Oferta
from .textnorm import find_phrases, fold, remove_phrases

# Marki narzędzi i sprzętu, które rozpoznajemy w tytułach (oprócz marek z profilu).
ZNANE_MARKI = [
    "STIHL", "Husqvarna", "Makita", "Dolmar", "Echo", "Oleo-Mac", "Oleo Mac", "Solo", "McCulloch",
    "Jonsered", "Einhell", "Ryobi", "Bosch", "DeWalt", "Milwaukee", "Parkside", "Hecht", "Dedra",
    "NAC", "Kraft&Dele", "Greenworks", "EGO", "HiKOKI", "Hitachi", "Black+Decker", "Worx", "AL-KO",
    "Sthor", "Yato", "Vorel", "Stiga", "Cedrus", "Kawasaki", "Shindaiwa", "Tanaka", "Efco", "Zipper",
    "Scheppach", "Nac", "Mar-Pol", "Graphite", "Verto", "Neo Tools", "Riwall", "Fieldmann", "Daewoo",
]

_ZAPRZECZENIA_USZKODZEN = (
    r"bez uszkodz[a-z]*", r"nieuszkodz[a-z]*", r"nie uszkodz[a-z]*", r"bez wad", r"nie jest uszkodz[a-z]*",
)
_USZKODZENIA = [
    "uszkodz", "na czesci", "na części", "nie odpala", "nie dziala", "nie działa", "do naprawy",
    "zatart", "brak kompresji", "spalon", "niesprawn", "do remontu", "kompletna na czesci",
]
_ZNACZNIKI_ZGODNOSCI = r"(pasuj[a-z]*|zamiennik[a-z]*|zamienn[a-z]*|kompatybiln[a-z]*|fits|for|odpowiednik[a-z]*|typu)"


@dataclass
class _Ocena:
    odrzuc: list[str]
    sprawdz: list[str]
    uwagi: list[str]


def _brand_regex(brand: str) -> re.Pattern[str]:
    words = [re.escape(w) for w in fold(brand).replace("&", " ").replace("+", " ").split()]
    body = r"[\s\-/&+]*".join(words)
    return re.compile(r"(?<![a-z0-9])" + body + r"(?:a|u|em|y|ie)?(?![a-z0-9])")


def _model_parts(model: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+", fold(model))


def model_regex(model: str) -> re.Pattern[str]:
    """MS391 / „MS 391” / „ms-391” — ale nie MS3910, MS39, MS 391 1… Sufiks literowy w grupie `suf`."""
    parts = _model_parts(model)
    if not parts:
        raise ValueError(f"Pusty model: {model!r}")
    body = r"[\s\-_./]?".join(re.escape(p) for p in parts)
    tail = r"(?!\d)" if parts[-1].isdigit() else r"(?![a-z])"
    return re.compile(r"(?<![a-z0-9])" + body + tail + r"(?P<suf>[a-z]{1,3}(?![a-z0-9]))?")


def family_regex(model: str) -> re.Pattern[str] | None:
    """Wzorzec innych modeli tej samej serii: dla MS391 -> „ms <liczba>”."""
    parts = _model_parts(model)
    if len(parts) >= 2 and parts[0].isalpha() and parts[1].isdigit():
        return re.compile(r"(?<![a-z0-9])" + re.escape(parts[0]) + r"[\s\-_./]?(\d{2,4})(?!\d)")
    return None


def _wykryj_marke(t: str, p: Profil) -> str:
    akceptowane = [(b, m.start()) for b in p.akceptowane_marki if (m := _brand_regex(b).search(t))]
    if akceptowane:
        return min(akceptowane, key=lambda x: x[1])[0]
    inne = [(b, m.start()) for b in ZNANE_MARKI + p.marki_czesci if (m := _brand_regex(b).search(t))]
    if inne:
        return min(inne, key=lambda x: x[1])[0]
    return MARKA_NIEUSTALONA


def _stan_z_tytulu(t: str) -> str | None:
    if re.search(r"(?<![a-z])(fabrycznie now|nowa|nowy|nowe)(?![a-z])", t):
        return "nowy"
    if re.search(r"(?<![a-z])uzywan[a-z]*", t):
        return "używany"
    return None


def ocen_oferte(o: Oferta, p: Profil) -> Oferta:
    oc = _Ocena([], [], [])
    t = fold(o.tytul)
    if not t:
        o.decyzja, o.powod = Decyzja.DO_SPRAWDZENIA, "brak tytułu oferty"
        o.marka = MARKA_NIEUSTALONA
        return o

    # 1. słowa wykluczone z profilu
    for fraza, _ in find_phrases(t, p.wykluczone_slowa):
        oc.odrzuc.append(f"słowo wykluczone: „{fraza}”")

    # 2. marka
    o.marka = _wykryj_marke(t, p)

    # 3. model
    model_ok = False
    inne_modele: list[str] = []
    if p.model:
        wzorce = [model_regex(p.model)] + [model_regex(a) for a in p.aliasy_modelu]
        for w in wzorce:
            m = w.search(t)
            if m:
                model_ok = True
                if m.group("suf"):
                    oc.sprawdz.append(f"możliwy inny wariant modelu: „{m.group(0).strip()}”")
                break
        fam = family_regex(p.model)
        docelowy = _model_parts(p.model)[1] if fam else None
        if fam:
            inne_modele = sorted({n for n in fam.findall(t) if n != docelowy})
        prefiks = _model_parts(p.model)[0].upper() if fam else ""
        if model_ok:
            o.model = p.model
        elif inne_modele:
            o.model = prefiks + inne_modele[0]

    # 4. części, akcesoria, zgodność („do …”, „pasuje do …”, „zamiennik”)
    # „na części” to stan (uszkodzenie), nie część — usuwamy przed szukaniem części
    t_czesci = remove_phrases(t, p.frazy_neutralne + ["na czesci=", "na czesciach="])
    czesci = find_phrases(t_czesci, p.slowa_czesci + p.slowa_opakowania)
    opakowania = set(p.slowa_opakowania)

    def etykieta(fraza: str) -> str:
        return "opakowanie / dokumenty, nie produkt" if fraza in opakowania else "część zamienna"

    marki_czesci = [(b, m.start()) for b in p.marki_czesci if (m := _brand_regex(b).search(t_czesci))]
    produkt = find_phrases(t, p.slowa_produktu)
    poz_produktu = produkt[0][1] if produkt else None

    cele = [re.escape(fold(b)) for b in p.akceptowane_marki]
    if p.model:
        cele.append(model_regex(p.model).pattern.replace("(?P<suf>", "(?:"))
    cele_re = "(?:" + "|".join(cele) + ")" if cele else None
    zgodnosc = None
    m = re.search(r"(?<![a-z])" + _ZNACZNIKI_ZGODNOSCI + r"(?![a-z])", t)
    if m:
        zgodnosc = m
    elif cele_re:
        zgodnosc = re.search(r"(?<![a-z])do\s+(?:[a-z0-9\-./]+\s+){0,2}?" + cele_re, t)

    if cele_re:
        klon = re.search(r"(?<![a-z])(typu|zamiennik[a-z]*|odpowiednik[a-z]*|replik[a-z]*|klon[a-z]*|wzorowan[a-z]* na)"
                         r"\s+(?:[a-z0-9\-./]+\s+)?" + cele_re, t)
        if klon:
            oc.odrzuc.append(f"zamiennik / nie oryginał (fraza „{klon.group(0).strip()}”)")

    czesc_pierwsza = czesci[0] if czesci else None
    produkt_przed_czescia = poz_produktu is not None and (czesc_pierwsza is None or poz_produktu < czesc_pierwsza[1])
    if zgodnosc and not (produkt_przed_czescia and poz_produktu < zgodnosc.start()):
        oc.odrzuc.append(f"część zamienna / akcesorium / zamiennik (fraza „{zgodnosc.group(0).strip()}”)")
    elif zgodnosc:
        oc.sprawdz.append(f"kompletny produkt ze wzmianką „{zgodnosc.group(0).strip()}” — sprawdź, czego dotyczy")

    if czesci:
        nazwa_czesci = czesci[0][0]
        if produkt_przed_czescia:
            oc.uwagi.append(f"wspomniano „{nazwa_czesci}” po nazwie produktu — potraktowano jako wyposażenie/opis")
        elif czesci[0][1] == 0 or (poz_produktu is None and czesci[0][1] <= len(t) // 3):
            oc.odrzuc.append(f"{etykieta(nazwa_czesci)}: „{nazwa_czesci}”")
        else:
            oc.sprawdz.append(f"możliwa {etykieta(nazwa_czesci)}: „{nazwa_czesci}”")
    if marki_czesci and not produkt_przed_czescia:
        oc.odrzuc.append(f"marka części/osprzętu: {marki_czesci[0][0]}")

    # 5. model: inny / kilka / brak
    if p.model:
        if not model_ok and inne_modele:
            oc.odrzuc.append("inny model: " + ", ".join(f"{_model_parts(p.model)[0].upper()}{n}" for n in inne_modele))
        elif model_ok and inne_modele:
            oc.sprawdz.append("w tytule kilka modeli (" + ", ".join(inne_modele) + ") — możliwa część lub lista zgodności")
        elif not model_ok:
            oc.sprawdz.append("brak pewności co do modelu (model nie występuje w tytule)")

    # 6. uszkodzenia
    t_usz = t
    for z in _ZAPRZECZENIA_USZKODZEN:
        t_usz = re.sub(z, " ", t_usz)
    usz = find_phrases(t_usz, _USZKODZENIA)
    if usz:
        if o.stan is None or o.stan != "uszkodzony":
            if o.stan not in (None, "uszkodzony"):
                oc.uwagi.append(f"parametr stanu „{o.stan}”, ale tytuł wskazuje uszkodzenie („{usz[0][0]}”)")
            o.stan, o.stan_zrodlo = "uszkodzony", "tytuł"
    if o.stan is None:
        stan = _stan_z_tytulu(t)
        if stan:
            o.stan, o.stan_zrodlo = stan, "tytuł"

    # 7. stan vs profil
    if o.stan in ("nowy", "używany", "uszkodzony"):
        if o.stan not in p.stany:
            powod = "produkt uszkodzony / na części" if o.stan == "uszkodzony" else f"stan „{o.stan}” nieakceptowany w profilu"
            oc.odrzuc.append(powod)
    elif o.stan is not None:
        oc.sprawdz.append(f"stan „{o.stan}” — oceń ręcznie")
    else:
        oc.uwagi.append("stan nieznany")

    # 8. niekompletność
    for fraza, _ in find_phrases(t, p.slowa_niekompletny):
        oc.sprawdz.append(f"możliwie niekompletny: „{fraza}”")

    # 9. marka
    if p.akceptowane_marki:
        akcept = {fold(b) for b in p.akceptowane_marki}
        if o.marka == MARKA_NIEUSTALONA:
            oc.sprawdz.append("marka nieustalona")
        elif fold(o.marka) not in akcept:
            oc.odrzuc.append(f"inna marka: {o.marka}")

    # 10. cena
    if o.cena is None:
        oc.sprawdz.append("brak ceny")
    else:
        if o.cena_rodzaj == "od":
            oc.sprawdz.append("cena „od” (wariantowa) — nieporównywalna z ceną pełną")
        if o.waluta and o.waluta != "PLN":
            oc.sprawdz.append(f"waluta {o.waluta}")
        if p.cena_min is not None and o.cena < p.cena_min:
            oc.odrzuc.append(f"cena {o.cena} poniżej minimum profilu {p.cena_min} (często część lub błąd)")
        if p.cena_max is not None and o.cena > p.cena_max:
            oc.odrzuc.append(f"cena {o.cena} powyżej maksimum profilu {p.cena_max}")

    if not o.id_pewne:
        oc.uwagi.append("brak ID oferty w linku — deduplikacja po identyfikatorze zastępczym")

    o.uwagi = list(dict.fromkeys(o.uwagi + oc.uwagi))
    if oc.odrzuc:
        o.decyzja = Decyzja.ODRZUCONA
        o.powod = "; ".join(dict.fromkeys(oc.odrzuc + oc.sprawdz))
    elif oc.sprawdz:
        o.decyzja = Decyzja.DO_SPRAWDZENIA
        o.powod = "; ".join(dict.fromkeys(oc.sprawdz))
    else:
        o.decyzja = Decyzja.PASUJE
        o.powod = "zgodny model, marka i stan"
    return o
