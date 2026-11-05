"""Interfejs terminalowy.

    python -m allegro_ceny pobierz   --profil profile/stihl_ms391.toml
    python -m allegro_ceny importuj  --profil profile/stihl_ms391.toml strona1.html oferty.csv
    python -m allegro_ceny analiza   --profil profile/stihl_ms391.toml
    python -m allegro_ceny eksport   --profil profile/stihl_ms391.toml --katalog eksport/
    python -m allegro_ceny historia  --profil profile/stihl_ms391.toml
    python -m allegro_ceny przebiegi
    python -m allegro_ceny diagnozuj zapisana_strona.html
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .analysis import analizuj, zmiany_cen
from .config import BladProfilu, Profil, profil_z_dict, waliduj, wczytaj_profil
from .export import eksport_ai, eksport_csv, eksport_json
from .models import Decyzja
from .money import fmt_pl, parse_amount
from .storage import Baza

DOMYSLNY_KATALOG = Path("dane")


def _profil(args: argparse.Namespace) -> Profil:
    if args.profil:
        p = wczytaj_profil(args.profil)
    else:
        if not (getattr(args, "fraza", None) or getattr(args, "url", None)):
            raise BladProfilu("Podaj --profil albo --fraza / --url")
        p = profil_z_dict({"nazwa": args.nazwa or "adhoc"})
    for attr in ("fraza", "url", "marka", "model"):
        v = getattr(args, attr, None)
        if v:
            setattr(p, attr, v)
    if getattr(args, "marka", None):
        p.akceptowane_marki = [args.marka]
    if getattr(args, "max_stron", None):
        p.max_stron = args.max_stron
    if getattr(args, "max_ofert", None):
        p.max_ofert = args.max_ofert
    if getattr(args, "odstep", None) is not None:
        p.odstep_s = args.odstep
    for attr in ("cena_min", "cena_max"):
        v = getattr(args, attr, None)
        if v:
            setattr(p, attr, parse_amount(v))
    waliduj(p)
    return p


def _baza(args: argparse.Namespace) -> Baza:
    return Baza(args.baza or (Path(args.katalog_danych) / "allegro_ceny.sqlite"))


def _przebieg_id(args: argparse.Namespace, baza: Baza, profil: Profil) -> int:
    pid = getattr(args, "przebieg", None) or baza.ostatni_przebieg(profil.nazwa)
    if pid is None:
        raise BladProfilu(f"Brak przebiegów dla profilu '{profil.nazwa}'. Uruchom najpierw 'pobierz' lub 'importuj'.")
    return pid


def _wypisz_przebieg(wynik: dict) -> None:
    print("\n=== Podsumowanie przebiegu", wynik["przebieg_id"], "===")
    print(f"Status: {wynik['status']}  |  powód zakończenia: {wynik['powod']}")
    if wynik.get("opis"):
        print("  ", wynik["opis"])
    if wynik.get("szczegoly"):
        print("   szczegóły:", wynik["szczegoly"])
    print(f"Stron: {wynik['strony']}  |  zapisanych ofert: {wynik['oferty']}")
    if wynik["status"] == "niepelny":
        print("UWAGA: przebieg NIEPEŁNY — wyniki nie obejmują wszystkich ofert. Brak ofert ≠ brak na Allegro.")


def cmd_pobierz(args: argparse.Namespace) -> int:
    from .pipeline import pobierz

    profil = _profil(args)
    katalog = Path(args.katalog_danych)
    with _baza(args) as baza:
        wynik = pobierz(profil, baza, katalog=katalog, headless=args.headless, zapisz_html=args.zapisz_html,
                        dane_testowe=args.testowe)
        _wypisz_przebieg(wynik)
        if wynik["oferty"]:
            _wypisz_analize(baza, profil, wynik["przebieg_id"], args.top)
    return 0 if wynik["status"] != "niepelny" else 3


def cmd_importuj(args: argparse.Namespace) -> int:
    from .pipeline import importuj

    profil = _profil(args)
    pliki = [Path(p) for p in args.pliki]
    for p in pliki:
        if not p.exists():
            raise BladProfilu(f"Nie znaleziono pliku: {p}")
    with _baza(args) as baza:
        wynik = importuj(profil, baza, pliki, dane_testowe=args.testowe)
        wynik["opis"] = None
        _wypisz_przebieg(wynik)
        _wypisz_analize(baza, profil, wynik["przebieg_id"], args.top)
    return 0


def _wypisz_staty(nazwa: str, s: dict) -> None:
    if not s or s.get("n", 0) == 0:
        print(f"  {nazwa}: brak danych")
        return
    q = lambda k: fmt_pl(parse_amount(s[k])) if s.get(k) else "—"  # noqa: E731
    print(f"  {nazwa} (n={s['n']}): min {q('min')} | Q1 {q('q1')} | mediana {q('mediana')} | "
          f"Q3 {q('q3')} | max {q('max')}")
    if s.get("uwaga"):
        print(f"      ! {s['uwaga']}")


def _wypisz_analize(baza: Baza, profil: Profil, przebieg_id: int, top: int = 10) -> None:
    oferty = baza.oferty_przebiegu(przebieg_id)
    a = analizuj(oferty, profil, top=top)
    przebieg = baza.przebieg(przebieg_id)
    if przebieg and przebieg["dane_testowe"]:
        print("\n*** DANE TESTOWE / SYNTETYCZNE — nie są aktualnymi ofertami ***")
    l = a["liczby"]
    print(f"\n=== Analiza: profil '{profil.nazwa}', przebieg {przebieg_id} ({przebieg['status'] if przebieg else '?'}) ===")
    print(f"Oferty: {l['wszystkie']} | pasuje: {l['pasuje']} | odrzucone: {l['odrzucona']} | "
          f"do sprawdzenia: {l['wymaga_sprawdzenia']}")
    if l["pasujace_wykluczone_ze_statystyk"]:
        print(f"  ({l['pasujace_wykluczone_ze_statystyk']} pasujących bez pełnej ceny pominięto w statystykach)")
    print("Ceny (oferty pasujące):")
    _wypisz_staty("wszystkie", a["ceny_pasujacych"])
    if a["ceny_pasujacych_bez_podejrzanych"]:
        _wypisz_staty("bez podejrzanie niskich", a["ceny_pasujacych_bez_podejrzanych"])
    for stan, s in a["wg_stanu"].items():
        _wypisz_staty(f"stan: {stan}", s)
    print(f"Z dostawą (pokrycie {a['z_dostawa']['pokrycie']}):")
    _wypisz_staty("cena z dostawą", a["z_dostawa"]["statystyki"])
    if a["najtansze"]:
        print(f"\nNajtańsze pasujące (do {top}):")
        for o in a["najtansze"]:
            flag = "  [PODEJRZANIE NISKA — sprawdź]" if o["podejrzanie_niska"] else ""
            dost = f", z dostawą {fmt_pl(parse_amount(o['cena_z_dostawa']))}" if o["cena_z_dostawa"] else ""
            print(f"  {fmt_pl(parse_amount(o['cena']))}{dost} | {o['stan'] or 'stan ?'} | {o['tytul'][:70] if o['tytul'] else ''}{flag}")
            print(f"      {o['url']}")
    if a["podejrzanie_niskie"]:
        print(f"\nPodejrzanie niskie ceny ({len(a['podejrzanie_niskie'])}): sprawdź ręcznie — możliwa część, błąd lub oszustwo.")
    dosp = [o for o in oferty if o.decyzja == Decyzja.DO_SPRAWDZENIA]
    if dosp:
        print(f"\nWymagają sprawdzenia ({len(dosp)}):")
        for o in dosp[:top]:
            print(f"  {fmt_pl(o.cena)} | {(o.tytul or '')[:60]} -> {o.powod}")
    if a["glowne_powody_odrzucen"]:
        print("\nGłówne powody odrzuceń:")
        for powod, n in a["glowne_powody_odrzucen"].items():
            print(f"  {n:>3} × {powod}")
    for z in a["zastrzezenia"]:
        print("  *", z)


def cmd_analiza(args: argparse.Namespace) -> int:
    profil = _profil(args)
    with _baza(args) as baza:
        _wypisz_analize(baza, profil, _przebieg_id(args, baza, profil), args.top)
    return 0


def cmd_eksport(args: argparse.Namespace) -> int:
    profil = _profil(args)
    katalog = Path(args.katalog)
    with _baza(args) as baza:
        pid = _przebieg_id(args, baza, profil)
        oferty = baza.oferty_przebiegu(pid)
        przebieg = baza.przebieg(pid)
        historia = baza.historia(profil.nazwa)
        prefix = f"{profil.nazwa}_przebieg{pid}"
        pliki = []
        if "csv" in args.formaty:
            pliki.append(eksport_csv(oferty, katalog / f"{prefix}.csv"))
        if "json" in args.formaty:
            pliki.append(eksport_json(oferty, przebieg, katalog / f"{prefix}.json"))
        if "ai" in args.formaty:
            pliki.append(eksport_ai(oferty, przebieg, profil, historia, katalog / f"{prefix}_ai.json"))
    for p in pliki:
        print("Zapisano:", p)
    return 0


def cmd_historia(args: argparse.Namespace) -> int:
    profil = _profil(args)
    with _baza(args) as baza:
        hist = baza.historia(profil.nazwa)
    zmiany = zmiany_cen(hist)
    wielokrotne = sum(1 for obs in hist.values() if len(obs) > 1)
    print(f"Ofert w historii profilu '{profil.nazwa}': {len(hist)} (widzianych w >1 przebiegu: {wielokrotne})")
    if not zmiany:
        print("Brak zmian cen między przebiegami.")
    for z in zmiany:
        print(f"  {z['offer_id']}: {fmt_pl(parse_amount(z['cena_poprzednia']))} -> {fmt_pl(parse_amount(z['cena_biezaca']))}"
              f" ({z['zmiana_proc']}%), przebiegi {z['przebieg_poprzedni']}→{z['przebieg_biezacy']}")
        print(f"      {z['url']}")
    print("Uwaga: ceny ofertowe; zniknięcie oferty nie oznacza sprzedaży.")
    return 0


def cmd_przebiegi(args: argparse.Namespace) -> int:
    with _baza(args) as baza:
        rows = baza.przebiegi(args.nazwa_profilu, limit=args.limit)
    if not rows:
        print("Brak przebiegów.")
    for r in rows:
        test = " [TESTOWE]" if r["dane_testowe"] else ""
        print(f"#{r['id']:<4} {r['rozpoczeto']}  {r['profil']:<20} {r['tryb']:<14} {r['status']:<20} "
              f"{r['powod_zakonczenia'] or '':<22} stron {r['strony']}, ofert {r['oferty_sparsowane']}{test}")
    return 0


def cmd_diagnozuj(args: argparse.Namespace) -> int:
    from .blocking import ocen_strone
    from .parse import parse_listing

    html = Path(args.plik).read_text(encoding="utf-8", errors="replace")
    wynik = parse_listing(html, strona=1)
    ocena = ocen_strone(html, None, None, len(wynik.oferty), oczekiwany_host=None)
    print(json.dumps({"parser": wynik.diagnostyka, "blokada": ocena.zablokowana, "brak_wynikow": ocena.brak_wynikow,
                      "markery": ocena.markery}, ensure_ascii=False, indent=2))
    print(f"\nPierwsze {min(args.ile, len(wynik.oferty))} ofert (sprawdź z tym, co widać w przeglądarce):")
    for o in wynik.oferty[: args.ile]:
        print(f"- [{o.offer_id}] {(o.tytul or '∅')[:80]}")
        print(f"    cena={o.cena} ({o.cena_rodzaj}) dostawa={o.koszt_dostawy} dostawa_od={o.koszt_dostawy_od} "
              f"z_dostawą={o.cena_z_dostawa} stan={o.stan} sprzedawca={o.sprzedawca} sponsor={o.sponsorowana} "
              f"smart={o.smart}")
        if o.ostrzezenia_parsera:
            print("    ostrzeżenia:", "; ".join(o.ostrzezenia_parsera))
    if not wynik.oferty:
        print("Nie rozpoznano ofert. Jeśli strona w przeglądarce pokazuje oferty, układ strony się zmienił —"
              " parser wymaga aktualizacji (patrz README, sekcja 'Gdy parser nie widzi ofert').")
        return 4
    return 0


def _wspolne(sp: argparse.ArgumentParser, profil_wymagany: bool = False) -> None:
    sp.add_argument("--profil", required=profil_wymagany, help="plik profilu TOML (np. profile/stihl_ms391.toml)")
    sp.add_argument("--fraza", help="fraza wyszukiwania (nadpisuje profil)")
    sp.add_argument("--url", help="adres wyników Allegro (nadpisuje frazę)")
    sp.add_argument("--marka", help="oczekiwana marka (nadpisuje profil)")
    sp.add_argument("--model", help="oczekiwany model (nadpisuje profil)")
    sp.add_argument("--nazwa", help="nazwa profilu ad-hoc (gdy brak --profil)")
    sp.add_argument("--cena-min", dest="cena_min")
    sp.add_argument("--cena-max", dest="cena_max")
    sp.add_argument("--top", type=int, default=10, help="ile najtańszych ofert pokazać")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m allegro_ceny", description="Ceny ofert Allegro: pobieranie, filtr, analiza, eksport.")
    ap.add_argument("--katalog-danych", default=str(DOMYSLNY_KATALOG), help="katalog na bazę, logi, diagnostykę (domyślnie dane/)")
    ap.add_argument("--baza", help="ścieżka bazy SQLite (domyślnie <katalog-danych>/allegro_ceny.sqlite)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("pobierz", help="pobierz wyniki z Allegro przeglądarką (domyślnie widoczne okno)")
    _wspolne(sp)
    sp.add_argument("--headless", action="store_true", help="bez widocznego okna przeglądarki")
    sp.add_argument("--max-stron", type=int, dest="max_stron")
    sp.add_argument("--max-ofert", type=int, dest="max_ofert")
    sp.add_argument("--odstep", type=float, help="sekundy między stronami (min. 2)")
    sp.add_argument("--zapisz-html", action="store_true", help="zapisz HTML stron do dane/strony/ (do diagnostyki)")
    sp.add_argument("--testowe", action="store_true", help="oznacz przebieg jako testowy")
    sp.set_defaults(func=cmd_pobierz)

    sp = sub.add_parser("importuj", help="importuj zapisane strony HTML oraz pliki CSV/JSON")
    _wspolne(sp)
    sp.add_argument("pliki", nargs="+")
    sp.add_argument("--testowe", action="store_true", help="oznacz dane jako testowe/syntetyczne")
    sp.set_defaults(func=cmd_importuj)

    for name, func, hlp in (("analiza", cmd_analiza, "statystyki ostatniego (lub wskazanego) przebiegu"),
                            ("historia", cmd_historia, "zmiany cen tych samych ofert między przebiegami")):
        sp = sub.add_parser(name, help=hlp)
        _wspolne(sp)
        sp.add_argument("--przebieg", type=int)
        sp.set_defaults(func=func)

    sp = sub.add_parser("eksport", help="eksport CSV / JSON / JSON dla AI")
    _wspolne(sp)
    sp.add_argument("--przebieg", type=int)
    sp.add_argument("--katalog", default="eksport", help="katalog wyjściowy")
    sp.add_argument("--formaty", nargs="+", default=["csv", "json", "ai"], choices=["csv", "json", "ai"])
    sp.set_defaults(func=cmd_eksport)

    sp = sub.add_parser("przebiegi", help="lista przebiegów")
    sp.add_argument("--profil", dest="nazwa_profilu", help="nazwa profilu")
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_przebiegi)

    sp = sub.add_parser("diagnozuj", help="sprawdź parser na zapisanej stronie HTML")
    sp.add_argument("plik")
    sp.add_argument("--ile", type=int, default=10)
    sp.set_defaults(func=cmd_diagnozuj)
    return ap


def _logi(katalog: Path, verbose: bool) -> None:
    katalog.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [logging.FileHandler(katalog / "allegro_ceny.log", encoding="utf-8")]
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.DEBUG if verbose else logging.WARNING)
    handlers.append(stderr)
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)
    # biblioteki sieciowe mogą logować nagłówki — wyciszamy je
    for noisy in ("asyncio", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _logi(Path(args.katalog_danych), args.verbose)
    try:
        return args.func(args)
    except BladProfilu as e:
        print("Błąd:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
