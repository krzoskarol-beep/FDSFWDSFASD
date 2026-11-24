#!/usr/bin/env python3
"""Niezależne przeliczenie wypłaty z pliku CSV aplikacji „Godziny Pracy”.

Nie używa kodu aplikacji. Liczy od surowych znaczników czasu (start_ms, end_ms),
przerwy i stawki każdego wpisu, arytmetyką dziesiętną (Decimal):
  * tydzień roboczy: stałe 7 dni od wybranego dnia, 00:00 (29 CFR 778.105),
  * minuty wpisu = pełne minuty od początku do końca − bezpłatna przerwa (29 CFR 785.19),
  * wypłata tygodnia = Σ minuty × stawka wpisu / 60, bez nadgodzin.

Użycie:
  python3 sprawdz_csv.py godziny.csv [--tydzien-od pn|wt|sr|cz|pt|sb|nd]
  python3 sprawdz_csv.py godziny.csv --porownaj oczekiwane.txt   # kod wyjścia 1 przy różnicy
"""
import argparse
import csv
import datetime as dt
import sys
from decimal import Decimal, ROUND_HALF_UP

DNI = {"pn": 0, "wt": 1, "sr": 2, "cz": 3, "pt": 4, "sb": 5, "nd": 6}
CENT = Decimal("0.01")


def tydzien(data: dt.date, od: int) -> dt.date:
    return data - dt.timedelta(days=(data.weekday() - od) % 7)


def przelicz(sciezka, od):
    tygodnie = {}
    with open(sciezka, encoding="utf-8-sig", newline="") as f:
        for w in csv.DictReader(f):
            start, koniec = int(w["start_ms"]), int(w["end_ms"])
            if koniec == 0:                      # trwająca zmiana: pomijamy (nie jest zamknięta)
                continue
            minuty = (koniec - start) // 60000 - int(w["przerwa_min"])
            stawka = Decimal(w["stawka_usd"])
            t = tydzien(dt.date.fromisoformat(w["data"]), od)
            m, kwota = tygodnie.get(t, (0, Decimal(0)))
            tygodnie[t] = (m + minuty, kwota + Decimal(minuty) * stawka / 60)
    wynik = {}
    for t, (m, kwota) in sorted(tygodnie.items()):
        srednia = kwota * 60 / m if m else Decimal(0)
        wynik[t] = dict(minuty=m, stawka=srednia.quantize(CENT, ROUND_HALF_UP),
                        razem=kwota.quantize(CENT, ROUND_HALF_UP))
    return wynik


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    p.add_argument("--tydzien-od", default="pn", choices=DNI)
    p.add_argument("--porownaj", help="plik z liniami: YYYY-MM-DD minuty centy_razem")
    a = p.parse_args()
    wynik = przelicz(a.csv, DNI[a.tydzien_od])

    for t, w in wynik.items():
        print(f"{t}  {w['minuty'] // 60}:{w['minuty'] % 60:02d} h  śr. stawka ${w['stawka']}  "
              f"RAZEM ${w['razem']}")

    if a.porownaj:
        bledy = 0
        with open(a.porownaj, encoding="utf-8") as f:
            for linia in f:
                if not linia.strip():
                    continue
                data, minuty, centy = linia.split()
                w = wynik.get(dt.date.fromisoformat(data))
                moje = (w["minuty"], int(w["razem"] * 100)) if w else None
                if moje != (int(minuty), int(centy)):
                    bledy += 1
                    print(f"RÓŻNICA {data}: aplikacja {minuty} min / {centy} c, skrypt {moje}")
        print("ZGODNE co do minuty i centa." if bledy == 0 else f"{bledy} różnic.")
        sys.exit(1 if bledy else 0)


if __name__ == "__main__":
    main()
