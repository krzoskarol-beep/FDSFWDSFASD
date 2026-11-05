"""Przebieg: pobieranie / import -> parsowanie -> filtrowanie -> zapis.

Zebrane dane są zapisywane po każdej stronie, więc blokada lub przerwanie
w połowie nie kasuje tego, co już pobrano — przebieg zostaje oznaczony jako niepełny.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .blocking import OcenaStrony, ocen_strone
from .config import Profil
from .filtering import ocen_oferte
from .importers import wczytaj_plik
from .models import POWODY_ZAKONCZENIA, Oferta, StatusPrzebiegu, now_iso
from .parse import parse_listing
from .storage import Baza
from .urls import page_number, safe_url_for_log, search_url, with_page

log = logging.getLogger(__name__)


def nadaj_id_zastepcze(o: Oferta) -> None:
    """Gdy link nie zawiera ID: stabilny identyfikator z linku albo tytułu+ceny (oznaczony jako niepewny)."""
    if o.offer_id:
        return
    klucz = o.url or f"{o.tytul}|{o.cena}|{o.sprzedawca}"
    o.offer_id = "x-" + hashlib.sha1(klucz.encode("utf-8")).hexdigest()[:16]
    o.id_pewne = False


@dataclass
class Paginacja:
    """Decyzja o kontynuacji po każdej stronie. Czysta logika — testowalna bez przeglądarki."""

    max_stron: int
    max_ofert: int
    widziane: set[str] = field(default_factory=set)
    poprzednie: frozenset[str] | None = None
    przyjete: int = 0

    def ocen(self, nr: int, ids: list[str], ocena: OcenaStrony, *, blad: str | None, status: int | None,
             url_koncowy: str | None) -> tuple[str | None, list[str]]:
        """Zwraca (powód_zatrzymania | None, ID ofert z tej strony do przyjęcia)."""
        if blad:
            return "blad_sieci", []
        if ocena.zablokowana:
            return "blokada", []
        if ocena.przejsciowy_blad or (status is not None and status >= 400):
            return "blad_http", []
        if not ids:
            if ocena.brak_wynikow:
                return ("brak_wynikow" if nr == 1 else "koniec_wynikow"), []
            return "nieznany_uklad_strony", []
        zestaw = frozenset(ids)
        if self.poprzednie is not None and zestaw == self.poprzednie:
            return "powtorzona_strona", []
        if nr > 1 and url_koncowy and page_number(url_koncowy) != nr:
            return "powtorzona_strona", []
        nowe = [i for i in dict.fromkeys(ids) if i not in self.widziane]
        if not nowe:
            return "brak_nowych_ofert", []
        self.poprzednie = zestaw
        miejsce = self.max_ofert - self.przyjete
        przyjmij = nowe[:miejsce]
        self.widziane.update(przyjmij)
        self.przyjete += len(przyjmij)
        if self.przyjete >= self.max_ofert:
            return "limit_ofert", przyjmij
        if nr >= self.max_stron:
            return "limit_stron", przyjmij
        return None, przyjmij


def _przygotuj(oferty: list[Oferta], profil: Profil, pobrano: str | None) -> list[Oferta]:
    for o in oferty:
        nadaj_id_zastepcze(o)
        o.pobrano = o.pobrano or pobrano
        o.fraza = o.fraza or profil.fraza
        o.profil = profil.nazwa
        ocen_oferte(o, profil)
    return oferty


def adres_startowy(profil: Profil) -> str:
    if profil.url:
        return profil.url
    if profil.fraza:
        return search_url(profil.fraza)
    raise ValueError("Profil musi mieć frazę albo adres wyników (url)")


def pobierz(profil: Profil, baza: Baza, *, katalog: Path, headless: bool = False, zapisz_html: bool = False,
            dane_testowe: bool = False, przegladarka: Callable[..., Any] | None = None,
            sleep: Callable[[float], None] = time.sleep, info: Callable[[str], None] = print) -> dict[str, Any]:
    """Pobiera wyniki wg profilu. Zwraca podsumowanie przebiegu."""
    if przegladarka is None:
        from .fetch import PrzegladarkaAllegro as przegladarka  # import leniwy: testy bez Playwright

    start = adres_startowy(profil)
    host = (urlsplit(start).hostname or "").removeprefix("www.") or None
    przebieg_id = baza.nowy_przebieg(profil=profil.nazwa, fraza=profil.fraza, url=safe_url_for_log(start),
                                     tryb="pobieranie", kryteria=profil.kryteria(), dane_testowe=dane_testowe)
    diag_dir = katalog / "diagnostyka" / f"przebieg_{przebieg_id}"
    strony_dir = katalog / "strony" / f"przebieg_{przebieg_id}"
    pag = Paginacja(profil.max_stron, profil.max_ofert)
    diagnostyka: dict[str, Any] = {"strony": []}
    powod, szczegoly, strony, zapisane = None, None, 0, 0
    status: StatusPrzebiegu | None = None

    def finalizuj() -> StatusPrzebiegu:
        nonlocal powod, szczegoly, status
        if status is None:
            if powod is None:
                powod = "blad_wewnetrzny"
                szczegoly = szczegoly or "pobieranie zakończone bez ustalenia przyczyny"
            status = baza.zakoncz_przebieg(przebieg_id, powod=powod, szczegoly=szczegoly, strony=strony,
                                           oferty=zapisane, diagnostyka=diagnostyka)
        return status

    try:
        with przegladarka(headless=headless, limit_czasu_s=profil.limit_czasu_s, ponowienia=profil.ponowienia) as br:
            for nr in range(1, profil.max_stron + 1):
                url = with_page(start, nr)
                info(f"[strona {nr}] {safe_url_for_log(url)}")
                wynik = br.pobierz(url)
                strony += 1
                parsed = parse_listing(wynik.html, strona=nr) if wynik.html else None
                oferty = parsed.oferty if parsed else []
                for o in oferty:
                    nadaj_id_zastepcze(o)
                ocena = ocen_strone(wynik.html, wynik.status, wynik.url_koncowy, len(oferty), oczekiwany_host=host)
                stop, przyjmij = pag.ocen(nr, [o.offer_id for o in oferty], ocena, blad=wynik.blad,
                                          status=wynik.status, url_koncowy=wynik.url_koncowy)

                wpis = {
                    "nr": nr, "url": safe_url_for_log(url), "status_http": wynik.status,
                    "url_koncowy": safe_url_for_log(wynik.url_koncowy) if wynik.url_koncowy else None,
                    "tytul_strony": (wynik.tytul_strony or "")[:120], "proby": wynik.proby, "blad": wynik.blad,
                    "markery": ocena.markery, "baner_zgody": ocena.baner_zgody,
                    "parser": parsed.diagnostyka if parsed else None, "przyjete_oferty": len(przyjmij),
                }
                if stop in ("blokada", "nieznany_uklad_strony", "blad_http") and br.page is not None:
                    shot = br.zrzut_ekranu(diag_dir / f"strona_{nr}.png")
                    wpis["zrzut_ekranu"] = str(shot) if shot else None
                if zapisz_html and wynik.html:
                    strony_dir.mkdir(parents=True, exist_ok=True)
                    (strony_dir / f"strona_{nr}.html").write_text(wynik.html, encoding="utf-8")
                diagnostyka["strony"].append(wpis)

                if przyjmij:
                    # duplikat tej samej oferty na stronie (np. sponsorowana + zwykła) zwiększa licznik wystąpień
                    akceptowane = set(przyjmij)
                    do_zapisu = [o for o in oferty if o.offer_id in akceptowane]
                    _przygotuj(do_zapisu, profil, now_iso())
                    baza.zapisz_oferty(przebieg_id, do_zapisu)
                    zapisane += len(przyjmij)
                info(f"           ofert na stronie: {len(oferty)}, przyjętych nowych: {len(przyjmij)}"
                     + (f", ZATRZYMANIE: {stop}" if stop else ""))
                if stop:
                    powod = stop
                    szczegoly = ocena.powod or wynik.blad
                    break
                sleep(profil.odstep_s)
            finalizuj()  # zapis statusu jeszcze przed zamknięciem przeglądarki
    except KeyboardInterrupt:
        powod, szczegoly = "przerwane", "Ctrl+C"
    except Exception as e:  # zapisujemy powód, dane już zapisane zostają
        log.exception("Błąd w trakcie pobierania")
        powod, szczegoly = "blad_wewnetrzny", f"{type(e).__name__}: {str(e)[:300]}"
    finally:
        finalizuj()
    return {"przebieg_id": przebieg_id, "status": status.value, "powod": powod,
            "opis": POWODY_ZAKONCZENIA.get(powod, (None, ""))[1], "szczegoly": szczegoly,
            "strony": strony, "oferty": zapisane}


def importuj(profil: Profil, baza: Baza, pliki: list[Path], *, dane_testowe: bool = False,
             info: Callable[[str], None] = print) -> dict[str, Any]:
    rodzaje = sorted({ {"htm": "html"}.get(s, s) for s in (p.suffix.lower().lstrip(".") for p in pliki)})
    przebieg_id = baza.nowy_przebieg(profil=profil.nazwa, fraza=profil.fraza, url=None,
                                     tryb="import_" + "+".join(rodzaje), kryteria=profil.kryteria(),
                                     dane_testowe=dane_testowe)
    diagnostyka: dict[str, Any] = {"pliki": []}
    lacznie, blokady = 0, []
    for nr, plik in enumerate(pliki, start=1):
        oferty, diag, html = wczytaj_plik(plik, strona=nr)
        if html is not None:
            ocena = ocen_strone(html, None, None, len(oferty), oczekiwany_host=None)
            diag["markery"] = ocena.markery
            if ocena.zablokowana:
                blokady.append(plik.name)
        _przygotuj(oferty, profil, None)
        nowe, dup = baza.zapisz_oferty(przebieg_id, oferty)
        lacznie += nowe
        diag.update({"plik": plik.name, "oferty": len(oferty), "nowe": nowe, "duplikaty": dup})
        diagnostyka["pliki"].append(diag)
        info(f"[import] {plik.name}: ofert {len(oferty)}, nowych w przebiegu {nowe}, duplikatów {dup}")
    if blokady:
        powod, status = "blokada", StatusPrzebiegu.NIEPELNY
        szczegoly = "Zapisane strony zawierają blokadę/CAPTCHA: " + ", ".join(blokady)
    else:
        powod, status = "import", StatusPrzebiegu.IMPORT
        szczegoly = "Import z plików — zakres i kompletność pobrania nieznane."
    baza.zakoncz_przebieg(przebieg_id, powod=powod, szczegoly=szczegoly, strony=len(pliki), oferty=lacznie,
                          diagnostyka=diagnostyka, status=status)
    return {"przebieg_id": przebieg_id, "status": status.value, "powod": powod, "szczegoly": szczegoly,
            "strony": len(pliki), "oferty": lacznie}
