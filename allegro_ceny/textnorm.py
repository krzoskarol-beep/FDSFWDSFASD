"""Normalizacja tekstu do dopasowań: małe litery, bez polskich znaków, bez interpunkcji.

Dopasowania słów działają „od początku słowa” (rdzenie): „łańcuch” trafia w
„łańcucha”, „łańcuchem”. Wielowyrazowe frazy dopasowujemy słowo po słowie,
każde jako rdzeń: „piła łańcuchowa” trafia w „piły łańcuchowej” tylko wtedy,
gdy rdzenie podano jako „pił łańcuchow”.
"""

from __future__ import annotations

import re
import unicodedata

_PL_MAP = str.maketrans({"ł": "l", "Ł": "l"})


def fold(text: str | None) -> str:
    """„Piła ŁAŃCUCHOWA, MS-391!” -> „pila lancuchowa ms-391”."""
    if not text:
        return ""
    text = text.translate(_PL_MAP).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # zostawiamy litery, cyfry, myślnik, kropkę, ukośnik, plus i spacje
    text = re.sub(r"[^a-z0-9\-./+ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Wzorzec dla frazy z profilu. Każde słowo to rdzeń (prefiks).

    Słowo zakończone „=” musi wystąpić dokładnie, np. „do=” nie trafi w „dom”.
    """
    parts: list[str] = []
    for raw in phrase.split():
        exact = raw.endswith("=")
        for word in fold(raw.rstrip("=")).split():
            parts.append(re.escape(word) + (r"(?![a-z0-9])" if exact else r"[a-z0-9]*"))
    if not parts:
        raise ValueError(f"Pusta fraza w profilu: {phrase!r}")
    body = r"[\s\-/]+".join(parts)
    return re.compile(r"(?<![a-z0-9])" + body)


def find_phrases(text_folded: str, phrases: list[str]) -> list[tuple[str, int]]:
    """Lista (fraza, pozycja) dopasowań w tekście już znormalizowanym przez fold()."""
    hits = []
    for phrase in phrases:
        m = phrase_pattern(phrase).search(text_folded)
        if m:
            hits.append((phrase, m.start()))
    return sorted(hits, key=lambda x: x[1])


def remove_phrases(text_folded: str, phrases: list[str]) -> str:
    for phrase in phrases:
        text_folded = phrase_pattern(phrase).sub(" ", text_folded)
    return re.sub(r"\s+", " ", text_folded).strip()


def clean_text(value: object, limit: int = 500) -> str | None:
    """Zwija białe znaki, usuwa znaki sterujące, przycina. Pusty -> None."""
    if value is None:
        return None
    text = "".join(ch for ch in str(value) if ch == " " or unicodedata.category(ch)[0] != "C")
    text = " ".join(text.split())
    if not text:
        return None
    return text[:limit]


def valid_ean13(code: str) -> bool:
    if not re.fullmatch(r"\d{13}", code):
        return False
    digits = [int(c) for c in code]
    check = (10 - sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits[:12])) % 10) % 10
    return check == digits[12]


def find_ean(text: str | None) -> str | None:
    if not text:
        return None
    for m in re.finditer(r"(?<!\d)(\d{13})(?!\d)", text):
        if valid_ean13(m.group(1)):
            return m.group(1)
    return None
