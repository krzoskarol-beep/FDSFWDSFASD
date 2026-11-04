"""Klient HTTP oparty na requests.Session.

Co robi:
- losuje User-Agent z puli 10 i przypina go do zapisanych cookies (spójna „tożsamość”),
- buduje nagłówki pasujące do rodziny przeglądarki i opcjonalnie miesza ich kolejność,
- czeka losowo MIN_DELAY–MAX_DELAY sekund przed każdym żądaniem,
- zapisuje i wczytuje cookies z pliku JSON, żeby kolejne uruchomienia nie startowały od zera,
- przy 403/429 (lub stronie z captchą DataDome) czeka 30–90 s i ponawia maks. 3 razy,
  a potem rzuca BlockedError — wyżej decydujemy o przełączeniu na fallback.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests
from requests.structures import CaseInsensitiveDict

log = logging.getLogger(__name__)

# Pula 10 User-Agentów popularnych przeglądarek desktopowych.
# Wersje warto odświeżać co kilka miesięcy — stary UA sam w sobie jest sygnałem bota.
USER_AGENTS: list[str] = [
    # Chrome / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    # Chrome / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    # Chrome / Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    # Edge / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
    # Opera / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 OPR/130.0.0.0",
    # Firefox / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
    # Firefox / Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
    # Firefox / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:145.0) Gecko/20100101 Firefox/145.0",
    # Safari / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15",
]

# Warianty Accept-Language typowe dla polskiego użytkownika.
ACCEPT_LANGUAGES: list[str] = [
    "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "pl,en-US;q=0.7,en;q=0.3",
    "pl-PL,pl;q=0.9,en;q=0.8",
]

# requests potrafi rozpakować brotli tylko z zainstalowanym pakietem brotli.
# Deklarujemy „br” tylko wtedy, gdy faktycznie umiemy go zdekodować.
try:
    import brotli  # noqa: F401

    ACCEPT_ENCODING = "gzip, deflate, br"
except ImportError:  # pragma: no cover - zależy od środowiska
    ACCEPT_ENCODING = "gzip, deflate"

# Kody, po których czekamy dłużej i ponawiamy.
RETRYABLE_STATUSES = {403, 429}

# Znaczniki strony z wyzwaniem DataDome (czasem przychodzi z kodem 200).
DATADOME_CHALLENGE_MARKERS = ("geo.captcha-delivery.com", "ct.captcha-delivery.com")


class BlockedError(RuntimeError):
    """Serwis odpowiada 403/429 (lub captchą) mimo wszystkich ponowień."""

    def __init__(self, url: str, status: int | None):
        self.url = url
        self.status = status
        super().__init__(f"Zablokowano dostęp do {url} (status {status}) po wyczerpaniu ponowień")


def _browser_family(ua: str) -> str:
    """Zwraca rodzinę przeglądarki na podstawie User-Agenta."""
    if "Firefox/" in ua:
        return "firefox"
    if "Chrome/" in ua:
        return "chromium"  # Chrome, Edge i Opera są na silniku Chromium
    return "safari"


def _platform(ua: str) -> str:
    """Platforma w formacie nagłówka Sec-CH-UA-Platform."""
    if "Windows" in ua:
        return '"Windows"'
    if "Macintosh" in ua:
        return '"macOS"'
    return '"Linux"'


def _sec_ch_ua(ua: str) -> str:
    """Buduje nagłówek Sec-CH-UA, który wysyłają tylko przeglądarki Chromium."""
    chrome = re.search(r"Chrome/(\d+)", ua)
    major = chrome.group(1) if chrome else "146"
    brands = [f'"Chromium";v="{major}"', '"Not)A;Brand";v="24"']
    if "Edg/" in ua:
        brands.append(f'"Microsoft Edge";v="{major}"')
    elif "OPR/" in ua:
        opr = re.search(r"OPR/(\d+)", ua)
        brands.append(f'"Opera";v="{opr.group(1) if opr else major}"')
    else:
        brands.append(f'"Google Chrome";v="{major}"')
    return ", ".join(brands)


class PersistentSession:
    """Sesja HTTP z trwałymi cookies, losowymi opóźnieniami i ponawianiem po blokadzie."""

    def __init__(
        self,
        cookies_file: Path,
        min_delay: float = 2.0,
        max_delay: float = 8.0,
        block_wait: tuple[float, float] = (30.0, 90.0),
        max_retries: int = 3,
        timeout: float = 20.0,
        shuffle_headers: bool = True,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.cookies_file = Path(cookies_file)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.block_wait = block_wait
        self.max_retries = max_retries
        self.timeout = timeout
        self.shuffle_headers = shuffle_headers
        self._sleep = sleep  # wstrzykiwane, żeby testy nie czekały naprawdę

        self.session = requests.Session()
        # Czyścimy domyślne nagłówki requests (python-requests/x.y itd.),
        # żeby to wyłącznie nasz słownik decydował o treści i kolejności.
        self.session.headers = CaseInsensitiveDict()

        self.identity: dict[str, str] = {}
        self._load_state()

    # ------------------------------------------------------------------ #
    # Tożsamość i cookies
    # ------------------------------------------------------------------ #
    def _new_identity(self) -> dict[str, str]:
        """Losuje nową tożsamość: User-Agent z puli + Accept-Language."""
        return {
            "user_agent": random.choice(USER_AGENTS),
            "accept_language": random.choice(ACCEPT_LANGUAGES),
        }

    @property
    def user_agent(self) -> str:
        return self.identity["user_agent"]

    def _load_state(self) -> None:
        """Wczytuje cookies i tożsamość z pliku; brak pliku = świeży start."""
        if not self.cookies_file.exists():
            self.identity = self._new_identity()
            log.info("Brak pliku cookies — nowa tożsamość: %s", self.user_agent)
            return

        try:
            state = json.loads(self.cookies_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("Nie da się odczytać %s (%s) — startuję od zera", self.cookies_file, exc)
            self.identity = self._new_identity()
            return

        identity = state.get("identity") or {}
        # UA spoza aktualnej puli (np. po aktualizacji listy) wymieniamy na nowy.
        if identity.get("user_agent") not in USER_AGENTS:
            identity = self._new_identity()
        identity.setdefault("accept_language", random.choice(ACCEPT_LANGUAGES))
        self.identity = identity

        now = time.time()
        loaded = 0
        for c in state.get("cookies", []):
            expires = c.get("expires")
            if expires is not None and expires < now:
                continue  # pomijamy wygasłe cookies
            self.session.cookies.set(
                c["name"],
                c["value"],
                domain=c.get("domain", ""),
                path=c.get("path", "/"),
                expires=expires,
                secure=c.get("secure", False),
                rest={"HttpOnly": None} if c.get("httponly") else {},
            )
            loaded += 1
        log.info("Wczytano %d cookies z %s (UA: %s)", loaded, self.cookies_file, self.user_agent)

    def save_state(self) -> None:
        """Zapisuje cookies i tożsamość do pliku JSON (atomowo, przez plik tymczasowy)."""
        cookies = [
            {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires,
                "secure": bool(c.secure),
                "httponly": c.has_nonstandard_attr("HttpOnly"),
            }
            for c in self.session.cookies
        ]
        state = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "identity": self.identity,
            "cookies": cookies,
        }
        self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.cookies_file.parent, prefix=".cookies-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(state, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.cookies_file)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def reset(self) -> None:
        """Kasuje cookies i losuje nową tożsamość (np. gdy stare cookie jest „spalone”)."""
        self.session.cookies.clear()
        self.identity = self._new_identity()
        self.save_state()
        log.info("Zresetowano cookies, nowa tożsamość: %s", self.user_agent)

    def has_cookies_for(self, host: str) -> bool:
        """Czy mamy jakiekolwiek cookies dla danej domeny (np. allegro.pl)."""
        base = host.removeprefix("www.")
        return any(c.domain.lstrip(".").endswith(base) for c in self.session.cookies)

    # ------------------------------------------------------------------ #
    # Nagłówki i opóźnienia
    # ------------------------------------------------------------------ #
    def build_headers(self, url: str, referer: str | None = None) -> dict[str, str]:
        """Buduje nagłówki zgodne z rodziną przeglądarki z bieżącego User-Agenta."""
        ua = self.user_agent
        family = _browser_family(ua)

        if referer is None:
            fetch_site = "none"  # wejście „z paska adresu”
        elif urlparse(referer).netloc == urlparse(url).netloc:
            fetch_site = "same-origin"
        else:
            fetch_site = "cross-site"

        headers: dict[str, str] = {
            "User-Agent": ua,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": self.identity["accept_language"],
            "Accept-Encoding": ACCEPT_ENCODING,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": fetch_site,
            "Sec-Fetch-User": "?1",
        }
        if referer:
            headers["Referer"] = referer
        # Client Hints wysyłają tylko przeglądarki Chromium — Firefox i Safari nie.
        if family == "chromium":
            headers["Sec-CH-UA"] = _sec_ch_ua(ua)
            headers["Sec-CH-UA-Mobile"] = "?0"
            headers["Sec-CH-UA-Platform"] = _platform(ua)

        if self.shuffle_headers:
            items = list(headers.items())
            random.shuffle(items)
            headers = dict(items)
        return headers

    def _random_delay(self) -> None:
        """Losowa pauza przed żądaniem, żeby ruch nie miał stałego rytmu."""
        delay = random.uniform(self.min_delay, self.max_delay)
        log.debug("Pauza %.1f s", delay)
        self._sleep(delay)

    @staticmethod
    def _is_challenge_page(resp: requests.Response) -> bool:
        """Rozpoznaje stronę z captchą DataDome, nawet gdy przyszła z kodem 200."""
        if resp.status_code in RETRYABLE_STATUSES:
            return True
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype:
            return False
        # Strona wyzwania jest mała; pełny listing ma setki kB.
        body = resp.text[:20000] if len(resp.content) < 60000 else ""
        return any(marker in body for marker in DATADOME_CHALLENGE_MARKERS)

    # ------------------------------------------------------------------ #
    # Żądania
    # ------------------------------------------------------------------ #
    def get(self, url: str, referer: str | None = None) -> requests.Response:
        """GET z losowym opóźnieniem i ponawianiem po 403/429 (maks. max_retries razy)."""
        attempts = self.max_retries + 1  # pierwsza próba + ponowienia
        last_status: int | None = None

        for attempt in range(1, attempts + 1):
            self._random_delay()
            headers = self.build_headers(url, referer)
            try:
                resp = self.session.get(url, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                log.warning("Błąd sieci (%s) przy %s, próba %d/%d", exc, url, attempt, attempts)
                if attempt == attempts:
                    raise
                continue

            # Cookies zapisujemy po każdej odpowiedzi — także po 403,
            # bo DataDome ustawia/odświeża swoje cookie również wtedy.
            self.save_state()
            last_status = resp.status_code

            if not self._is_challenge_page(resp):
                resp.raise_for_status()
                log.info("OK %s %s", resp.status_code, url)
                return resp

            if attempt == attempts:
                break

            wait = random.uniform(*self.block_wait)
            log.warning(
                "Blokada (status %s, DataDome: %s) przy %s — czekam %.0f s, ponowienie %d/%d",
                resp.status_code,
                "tak" if "x-datadome" in {k.lower() for k in resp.headers} else "nie wiadomo",
                url,
                wait,
                attempt,
                self.max_retries,
            )
            self._sleep(wait)

        raise BlockedError(url, last_status)

    def warm_up(self, home_url: str) -> None:
        """Jeśli nie mamy cookies dla domeny, najpierw odwiedzamy stronę główną."""
        host = urlparse(home_url).netloc
        if self.has_cookies_for(host):
            return
        log.info("Brak cookies dla %s — wchodzę najpierw na stronę główną", host)
        self.get(home_url)
