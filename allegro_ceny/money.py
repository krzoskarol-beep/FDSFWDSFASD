"""Kwoty pieniężne: parsowanie polskich formatów cen i arytmetyka na Decimal.

Zasady:
- nigdy float — wszystko przez Decimal, w bazie jako liczba groszy (int);
- brak danych to None, nigdy 0;
- raty, ceny „z dostawą” i ceny referencyjne rozróżnia moduł parse.py,
  tutaj tylko zamieniamy tekst na kwotę.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

GROSZ = Decimal("0.01")

# Separatory tysięcy spotykane na polskich stronach: spacja, twarda spacja,
# wąska twarda spacja, kropka.
_THOUSANDS = "[    .]"

# Kwota z walutą: „1 299,99 zł”, „1.299,99 zł”, „1299 zł”, „2 499,00 PLN”.
# Część całkowita: albo grupy tysięcy, albo ciąg cyfr. Grosze po przecinku
# (albo po kropce, jeśli nie ma grup tysięcy z kropką).
_AMOUNT_WITH_CURRENCY = re.compile(
    r"(?<![\d,.])"
    r"(?P<int>\d{1,3}(?:" + _THOUSANDS + r"\d{3})+|\d+)"
    r"(?:\s?[,.]\s?(?P<frac>\d{1,2}))?"
    r"\s*(?P<cur>zł|zl|pln)(?![a-ząćęłńóśźż])",
    re.IGNORECASE,
)

# Kwota bez waluty (np. wartość aria-label albo komórka CSV „1299,99”).
_BARE_AMOUNT = re.compile(
    r"^\s*(?P<int>\d{1,3}(?:" + _THOUSANDS + r"\d{3})+|\d+)(?:[,.](?P<frac>\d{1,2}))?\s*$"
)


def _build(int_part: str, frac: str | None) -> Decimal | None:
    digits = re.sub(r"\D", "", int_part)
    if not digits:
        return None
    frac = (frac or "0").ljust(2, "0")
    try:
        return Decimal(f"{digits}.{frac}").quantize(GROSZ)
    except InvalidOperation:
        return None


def find_amounts(text: str) -> list[tuple[Decimal, int, int]]:
    """Wszystkie kwoty z walutą w tekście: (kwota, początek, koniec)."""
    if not text:
        return []
    found = []
    for m in _AMOUNT_WITH_CURRENCY.finditer(normalize_spaces(text)):
        value = _build(m.group("int"), m.group("frac"))
        if value is not None:
            found.append((value, m.start(), m.end()))
    return found


def parse_price_text(text: Any) -> Decimal | None:
    """Pierwsza kwota z walutą w tekście, np. „1 299,99 zł” -> Decimal('1299.99')."""
    if text is None:
        return None
    amounts = find_amounts(str(text))
    return amounts[0][0] if amounts else None


def parse_amount(value: Any) -> Decimal | None:
    """Kwota z wartości JSON/CSV: liczba, „1299.99”, „1 299,99”, „1299,99 zł”.

    Zwraca None dla pustych i nieczytelnych wartości (nigdy 0 „na wszelki wypadek”).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value.quantize(GROSZ, rounding=ROUND_HALF_UP)
    if isinstance(value, int):
        return Decimal(value).quantize(GROSZ)
    if isinstance(value, float):
        # repr floata -> str -> Decimal, żeby nie wnosić błędu binarnego
        return Decimal(str(value)).quantize(GROSZ, rounding=ROUND_HALF_UP)
    text = normalize_spaces(str(value)).strip()
    if not text:
        return None
    with_currency = parse_price_text(text)
    if with_currency is not None:
        return with_currency
    m = _BARE_AMOUNT.match(text)
    if m:
        return _build(m.group("int"), m.group("frac"))
    # Format „1299.99” z kropką dziesiętną i bez separatorów tysięcy
    if re.fullmatch(r"\d+\.\d{1,2}", text):
        return Decimal(text).quantize(GROSZ)
    return None


def normalize_spaces(text: str) -> str:
    return text.replace(" ", " ").replace(" ", " ").replace(" ", " ")


def to_grosze(value: Decimal | None) -> int | None:
    if value is None:
        return None
    return int((value.quantize(GROSZ, rounding=ROUND_HALF_UP) * 100).to_integral_value())


def from_grosze(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return (Decimal(int(value)) / 100).quantize(GROSZ)


def fmt_pl(value: Decimal | None, currency: str | None = "zł") -> str:
    """Do wyświetlania w terminalu: 1 299,99 zł. None -> „brak danych”."""
    if value is None:
        return "brak danych"
    q = value.quantize(GROSZ)
    int_part, frac = f"{q:.2f}".split(".")
    sign = "-" if int_part.startswith("-") else ""
    int_part = int_part.lstrip("-")
    groups = []
    while int_part:
        groups.insert(0, int_part[-3:])
        int_part = int_part[:-3]
    out = f"{sign}{' '.join(groups)},{frac}"
    return f"{out} {currency}" if currency else out


def dec_str(value: Decimal | None) -> str | None:
    """Do JSON: kwota jako tekst „1299.99” (bez utraty precyzji), None zostaje None."""
    return None if value is None else f"{value.quantize(GROSZ):.2f}"
