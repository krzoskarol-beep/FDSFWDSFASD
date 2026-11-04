"""Konfiguracja skrapera — wszystko da się nadpisać zmiennymi środowiskowymi."""

from __future__ import annotations

import os
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    """Czyta liczbę zmiennoprzecinkową ze zmiennej środowiskowej."""
    return float(os.getenv(name, default))


def _env_int(name: str, default: int) -> int:
    """Czyta liczbę całkowitą ze zmiennej środowiskowej."""
    return int(os.getenv(name, default))


def _env_bool(name: str, default: bool) -> bool:
    """Czyta flagę logiczną: 1/true/yes/tak oznaczają prawdę."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "tak", "on"}


# Katalogi na dane trwałe (cookies, ostatni skan) i logi.
# W Dockerze to są volume'y montowane pod /data i /logs.
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))

# Plik z cookies i „tożsamością” klienta (User-Agent, Accept-Language).
COOKIES_FILE = Path(os.getenv("COOKIES_FILE", str(DATA_DIR / "cookies.json")))
# Plik z wynikiem ostatniego skanu, czytany przez endpoint Flask.
LAST_SCAN_FILE = Path(os.getenv("LAST_SCAN_FILE", str(DATA_DIR / "last_scan.json")))

# Losowe opóźnienie przed każdym żądaniem (sekundy).
MIN_DELAY = _env_float("MIN_DELAY", 2.0)
MAX_DELAY = _env_float("MAX_DELAY", 8.0)

# Czekanie po 403/429 przed ponowieniem (sekundy) i limit ponowień.
BLOCK_WAIT_MIN = _env_float("BLOCK_WAIT_MIN", 30.0)
BLOCK_WAIT_MAX = _env_float("BLOCK_WAIT_MAX", 90.0)
MAX_RETRIES = _env_int("MAX_RETRIES", 3)

# Timeout pojedynczego żądania HTTP (sekundy).
REQUEST_TIMEOUT = _env_float("REQUEST_TIMEOUT", 20.0)

# Czy mieszać kolejność nagłówków przy każdym żądaniu.
SHUFFLE_HEADERS = _env_bool("SHUFFLE_HEADERS", True)

# Maksymalna liczba ofert zapisywana na jedno zapytanie i jedno źródło.
MAX_OFFERS_PER_QUERY = _env_int("MAX_OFFERS_PER_QUERY", 30)

# Zapytania domyślne, rozdzielone przecinkiem.
QUERIES = [
    q.strip()
    for q in os.getenv("QUERIES", "karta graficzna rtx 4070,słuchawki sony wh-1000xm5").split(",")
    if q.strip()
]

# Tryb pętli: co ile sekund powtarzać skan (z losowym rozrzutem ±10%).
SCAN_INTERVAL = _env_int("SCAN_INTERVAL", 3600)
