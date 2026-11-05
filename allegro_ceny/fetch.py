"""Pobieranie stron wyników przez Playwright (Chromium).

Świadome ograniczenia (zgodnie z założeniami projektu):
- brak ukrywania automatyzacji: domyślny User-Agent Playwright/Chromium, brak
  wtyczek „stealth”, brak rotacji proxy, brak podmiany odcisku przeglądarki;
- brak obchodzenia CAPTCHA i kontroli dostępu — wykrycie blokady kończy pobieranie;
- nowy, pusty kontekst przeglądarki przy każdym uruchomieniu; cookies nie są
  zapisywane na dysk (znikają po zamknięciu przeglądarki);
- ponowienia tylko dla błędów przejściowych (timeout, błąd sieci, HTTP 5xx),
  nigdy po blokadzie (403/429/CAPTCHA).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .urls import safe_url_for_log

log = logging.getLogger(__name__)

OFFER_LINK_SELECTOR = 'a[href*="/oferta/"]'


@dataclass
class WynikPobrania:
    url: str
    url_koncowy: str | None = None
    status: int | None = None
    tytul_strony: str | None = None
    html: str = ""
    blad: str | None = None
    proby: int = 0


class PrzegladarkaAllegro:
    """Kontekstowy menedżer przeglądarki: `with PrzegladarkaAllegro() as b: b.pobierz(url)`."""

    def __init__(self, *, headless: bool = False, limit_czasu_s: float = 45.0, ponowienia: int = 2,
                 przerwa_ponowienia_s: float = 5.0, przewijanie: bool = True,
                 czekaj_na_oferty_s: float = 12.0, sleep: Callable[[float], None] = time.sleep):
        self.headless = headless
        self.limit_ms = int(limit_czasu_s * 1000)
        self.ponowienia = ponowienia
        self.przerwa_ponowienia_s = przerwa_ponowienia_s
        self.przewijanie = przewijanie
        self.czekaj_na_oferty_ms = int(czekaj_na_oferty_s * 1000)
        self.sleep = sleep
        self._pw = self._browser = self._context = self.page = None

    def __enter__(self) -> "PrzegladarkaAllegro":
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        try:
            launch_kwargs = {"headless": self.headless}
            exe = os.environ.get("ALLEGRO_CENY_CHROMIUM")
            if exe:
                launch_kwargs["executable_path"] = exe
            self._browser = self._pw.chromium.launch(**launch_kwargs)
            self._context = self._browser.new_context(
                locale="pl-PL", timezone_id="Europe/Warsaw", viewport={"width": 1366, "height": 900}
            )
            self._context.set_default_timeout(self.limit_ms)
            self.page = self._context.new_page()
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *exc: object) -> None:
        # Zamykamy całą przeglądarkę naraz (zamyka też kontekst i strony). Osobne page.close()
        # potrafi się zawiesić na stronie błędu Chromium (chrome-error://) po nieudanej nawigacji.
        self.page = self._context = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception as e:
                log.debug("zamykanie przeglądarki: %s", e)
            self._browser = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception as e:
                log.debug("zatrzymywanie playwright: %s", e)
            self._pw = None

    # ---------------------------------------------------------------------

    def _jedna_proba(self, url: str) -> WynikPobrania:
        from playwright.sync_api import TimeoutError as PwTimeout

        page = self.page
        resp = page.goto(url, wait_until="domcontentloaded", timeout=self.limit_ms)
        wynik = WynikPobrania(url=url, status=resp.status if resp else None)
        try:
            page.wait_for_selector(OFFER_LINK_SELECTOR, timeout=self.czekaj_na_oferty_ms)
        except PwTimeout:
            pass  # brak ofert w czasie — ocenimy stronę po treści (blokada / brak wyników / nieznany układ)
        if self.przewijanie:
            # zwykłe przewijanie, żeby doładowały się leniwie wczytywane oferty
            for _ in range(6):
                page.mouse.wheel(0, 1400)
                page.wait_for_timeout(350)
            page.wait_for_timeout(500)
        wynik.url_koncowy = page.url
        wynik.tytul_strony = page.title()
        wynik.html = page.content()
        return wynik

    def pobierz(self, url: str) -> WynikPobrania:
        from playwright.sync_api import Error as PwError

        ostatni_blad = None
        for proba in range(1, self.ponowienia + 2):
            try:
                wynik = self._jedna_proba(url)
                wynik.proby = proba
                if wynik.status in (500, 502, 503, 504) and proba <= self.ponowienia:
                    ostatni_blad = f"HTTP {wynik.status}"
                    log.warning("HTTP %s dla %s — ponowienie %d/%d", wynik.status, safe_url_for_log(url),
                                proba, self.ponowienia)
                    self.sleep(self.przerwa_ponowienia_s * proba)
                    continue
                return wynik
            except PwError as e:  # TimeoutError dziedziczy po Error
                ostatni_blad = str(e).splitlines()[0][:300]
                log.warning("Błąd przejściowy (%s) dla %s — próba %d/%d", ostatni_blad, safe_url_for_log(url),
                            proba, self.ponowienia + 1)
                if proba <= self.ponowienia:
                    self.sleep(self.przerwa_ponowienia_s * proba)
        return WynikPobrania(url=url, blad=ostatni_blad, proby=self.ponowienia + 1)

    def zrzut_ekranu(self, sciezka: Path) -> Path | None:
        try:
            sciezka.parent.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(sciezka), full_page=False)
            return sciezka
        except Exception as e:
            log.warning("Nie udało się zapisać zrzutu ekranu: %s", e)
            return None
