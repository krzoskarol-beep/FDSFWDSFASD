"""Struktury danych: oferta, decyzja filtra, status przebiegu."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from .money import dec_str

TZ = ZoneInfo("Europe/Warsaw")

MARKA_NIEUSTALONA = "nieustalona"


def now_iso() -> str:
    """Czas ze strefą czasową, np. 2026-11-04T23:51:02+01:00."""
    return datetime.now(TZ).isoformat(timespec="seconds")


class Decyzja(str, Enum):
    PASUJE = "pasuje"
    ODRZUCONA = "odrzucona"
    DO_SPRAWDZENIA = "wymaga_sprawdzenia"


class StatusPrzebiegu(str, Enum):
    PELNY = "pelny"                      # pobrano wszystkie wyniki (lub potwierdzony brak wyników)
    OGRANICZONY = "ograniczony_limitem"  # zatrzymano na limicie stron/ofert z profilu
    NIEPELNY = "niepelny"                # blokada, błąd, nieznany układ strony, przerwanie
    W_TOKU = "w_toku"
    IMPORT = "import"                    # dane z plików: kompletność nieznana


# Przyczyny zakończenia pobierania -> status przebiegu
POWODY_ZAKONCZENIA: dict[str, tuple[StatusPrzebiegu, str]] = {
    "brak_wynikow": (StatusPrzebiegu.PELNY, "Allegro pokazało komunikat o braku wyników."),
    "koniec_wynikow": (StatusPrzebiegu.PELNY, "Kolejna strona nie zawierała ofert i miała komunikat o braku wyników."),
    "powtorzona_strona": (StatusPrzebiegu.PELNY, "Strona zwróciła te same oferty co poprzednia (zapętlenie) — prawdopodobnie koniec wyników."),
    "brak_nowych_ofert": (StatusPrzebiegu.PELNY, "Strona nie wniosła żadnych nowych ofert."),
    "limit_stron": (StatusPrzebiegu.OGRANICZONY, "Osiągnięto maksymalną liczbę stron z profilu."),
    "limit_ofert": (StatusPrzebiegu.OGRANICZONY, "Osiągnięto maksymalną liczbę ofert z profilu."),
    "blokada": (StatusPrzebiegu.NIEPELNY, "Allegro zablokowało dostęp (CAPTCHA / kontrola dostępu / kod HTTP). Pobieranie zatrzymano."),
    "blad_sieci": (StatusPrzebiegu.NIEPELNY, "Błąd sieci lub limit czasu po wyczerpaniu ponowień."),
    "blad_http": (StatusPrzebiegu.NIEPELNY, "Nieoczekiwany kod odpowiedzi HTTP."),
    "nieznany_uklad_strony": (StatusPrzebiegu.NIEPELNY, "Na stronie nie rozpoznano ofert ani komunikatu o braku wyników — możliwa zmiana układu strony. To NIE jest potwierdzony brak ofert."),
    "przerwane": (StatusPrzebiegu.NIEPELNY, "Przerwane przez użytkownika."),
    "blad_wewnetrzny": (StatusPrzebiegu.NIEPELNY, "Błąd programu w trakcie pobierania."),
    "import": (StatusPrzebiegu.IMPORT, "Dane z plików lokalnych — zakres i kompletność pobrania nieznane."),
}


@dataclass
class Oferta:
    """Jedna oferta z listingu. Brak danych = None (nigdy 0 ani wartość domyślna)."""

    offer_id: str | None = None
    id_pewne: bool = False            # False: ID wygenerowane (brak ID w linku)
    url: str | None = None            # bezpośredni, oczyszczony link
    tytul: str | None = None          # tekst sprzedawcy — dane niezaufane
    cena: Decimal | None = None       # pełna cena produktu (nie rata, nie cena z dostawą)
    waluta: str | None = None
    cena_rodzaj: str | None = None    # "pelna" | "od" (najniższa z wariantów — nieporównywalna 1:1)
    koszt_dostawy: Decimal | None = None       # tylko jeśli podany dokładnie
    koszt_dostawy_od: Decimal | None = None    # „dostawa od X zł” — dolna granica, nie koszt
    dostawa_tekst: str | None = None
    smart: bool | None = None         # widoczne oznaczenie Smart (nie oznacza darmowej dostawy dla każdego)
    cena_z_dostawa: Decimal | None = None
    cena_z_dostawa_zrodlo: str | None = None   # "strona" | "obliczona"
    stan: str | None = None           # nowy | używany | uszkodzony | inny tekst | None
    stan_zrodlo: str | None = None    # "parametr" | "tytuł"
    sprzedawca: str | None = None
    sponsorowana: bool | None = None  # True: wykryto oznaczenie; False: nie wykryto oznaczenia
    ean: str | None = None
    marka: str | None = None
    model: str | None = None
    strona: int | None = None
    pozycja: int | None = None
    pobrano: str | None = None        # ISO 8601 ze strefą; None przy imporcie bez czasu
    fraza: str | None = None
    profil: str | None = None
    zrodlo_danych: str | None = None  # dom | json_osadzony | json_ld | import_csv | import_json
    decyzja: Decyzja | None = None
    powod: str | None = None
    uwagi: list[str] = field(default_factory=list)
    ostrzezenia_parsera: list[str] = field(default_factory=list)
    wystapienia: int = 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key, value in d.items():
            if isinstance(value, Decimal):
                d[key] = dec_str(value)
            elif isinstance(value, Enum):
                d[key] = value.value
        return d


@dataclass
class WynikStrony:
    """Wynik parsowania jednej strony wyników."""

    oferty: list[Oferta]
    strategia: str | None
    diagnostyka: dict[str, Any] = field(default_factory=dict)
