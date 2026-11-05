from pathlib import Path

import pytest

from allegro_ceny.config import wczytaj_profil
from allegro_ceny.storage import Baza

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def profil():
    return wczytaj_profil(ROOT / "profile" / "stihl_ms391.toml")


@pytest.fixture
def baza(tmp_path):
    b = Baza(tmp_path / "test.sqlite")
    yield b
    b.close()


@pytest.fixture
def fixtures():
    return FIXTURES
