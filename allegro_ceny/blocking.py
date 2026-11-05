"""Rozpoznawanie blokady, CAPTCHA i komunikatu o braku wyników.

Program NIE próbuje obchodzić blokad. Wykrycie blokady kończy pobieranie,
a przebieg jest oznaczany jako niepełny (nigdy jako „brak ofert”).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .textnorm import fold

KODY_BLOKADY = {401, 403, 407, 429}
KODY_PRZEJSCIOWE = {500, 502, 503, 504}

# Domeny wyzwań antybotowych (iframe/skrypt wyzwania, nie zwykły tag pomiarowy).
_CAPTCHA_HOSTS = ("captcha-delivery.com", "hcaptcha.com", "recaptcha", "challenges.cloudflare.com")

_FRAZY_BLOKADY = (
    "potwierdz, ze jestes czlowiekiem", "potwierdz ze jestes czlowiekiem", "nie jestes robotem",
    "jestes robotem", "wykrylismy nietypowy ruch", "nietypowa aktywnosc", "dostep zablokowany",
    "access denied", "verify you are human", "are you a robot", "zostales zablokowany",
)

_FRAZY_BRAK_WYNIKOW = (
    "nie znalezlismy", "brak wynikow", "brak ofert", "nie ma ofert", "0 ofert",
    "sprobuj zmienic", "nie znaleziono",
)

_FRAZY_ZGODY = ("zgadzam sie", "akceptuje", "pliki cookie", "ustawienia prywatnosci")


@dataclass
class OcenaStrony:
    zablokowana: bool = False
    przejsciowy_blad: bool = False
    powod: str | None = None
    brak_wynikow: bool = False
    baner_zgody: bool = False
    markery: list[str] = field(default_factory=list)


def ocen_strone(html: str, status: int | None, final_url: str | None, liczba_ofert: int,
                oczekiwany_host: str | None = "allegro.pl") -> OcenaStrony:
    ocena = OcenaStrony()
    soup = BeautifulSoup(html or "", "html.parser")
    text = fold(soup.get_text(" "))[:200_000]

    if status in KODY_BLOKADY:
        ocena.zablokowana = True
        ocena.markery.append(f"http_{status}")
    elif status in KODY_PRZEJSCIOWE:
        ocena.przejsciowy_blad = True
        ocena.markery.append(f"http_{status}")

    for tag in soup.find_all(["iframe", "script"], src=True):
        src = tag["src"].lower()
        if any(h in src for h in _CAPTCHA_HOSTS) and (tag.name == "iframe" or "captcha" in src):
            ocena.zablokowana = True
            ocena.markery.append("captcha:" + urlsplit(src).netloc)

    for fraza in _FRAZY_BLOKADY:
        if fraza in text:
            ocena.markery.append("tekst:" + fraza)
            # fraza bez ofert = blokada; fraza obok ofert odnotowujemy jako podejrzaną
            if liczba_ofert == 0:
                ocena.zablokowana = True

    if final_url and oczekiwany_host:
        host = urlsplit(final_url).hostname or ""
        if host and not (host == oczekiwany_host or host.endswith("." + oczekiwany_host)):
            ocena.markery.append("przekierowanie:" + host)
            if liczba_ofert == 0:
                ocena.zablokowana = True

    if liczba_ofert == 0 and not ocena.zablokowana:
        for fraza in _FRAZY_BRAK_WYNIKOW:
            if re.search(r"(?<![a-z0-9])" + re.escape(fraza), text):
                ocena.brak_wynikow = True
                ocena.markery.append("brak_wynikow:" + fraza)
                break

    ocena.baner_zgody = any(f in text for f in _FRAZY_ZGODY)

    if ocena.zablokowana:
        ocena.powod = "Wykryto blokadę lub wyzwanie antybotowe: " + ", ".join(ocena.markery)
    elif ocena.przejsciowy_blad:
        ocena.powod = f"Błąd serwera HTTP {status}"
    return ocena
