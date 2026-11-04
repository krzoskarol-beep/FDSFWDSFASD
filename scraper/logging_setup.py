"""Wspólna konfiguracja logowania: konsola + rotowany plik w katalogu logów."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(log_dir: Path, filename: str = "scraper.log", level: int = logging.INFO) -> None:
    """Ustawia logowanie na stdout oraz do pliku (max 5 MB x 5 plików)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)

    # Nie dublujemy handlerów przy wielokrotnym wywołaniu (np. w testach).
    if any(getattr(h, "_scraper_handler", False) for h in root.handlers):
        return

    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console._scraper_handler = True  # type: ignore[attr-defined]

    file_handler = RotatingFileHandler(
        log_dir / filename, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler._scraper_handler = True  # type: ignore[attr-defined]

    root.addHandler(console)
    root.addHandler(file_handler)
