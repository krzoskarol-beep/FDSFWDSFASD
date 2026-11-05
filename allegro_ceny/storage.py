"""SQLite: przebiegi, oferty (jedna na ID) i obserwacje (historia ceny per przebieg).

- `oferty`      — jeden wiersz na ID oferty (deduplikacja po ID między przebiegami);
- `obserwacje`  — jeden wiersz na (przebieg, oferta): cena, dostawa, decyzja filtra…;
                  UNIQUE(przebieg_id, offer_id) usuwa duplikaty w obrębie przebiegu;
- `przebiegi`   — kryteria, status (pełny / ograniczony / niepełny), powód zakończenia.

Kwoty przechowujemy jako liczbę groszy (INTEGER). Brak danych = NULL.
W bazie nie ma cookies, tokenów ani danych logowania.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .models import POWODY_ZAKONCZENIA, Decyzja, Oferta, StatusPrzebiegu, now_iso
from .money import from_grosze, to_grosze

SCHEMAT = """
CREATE TABLE IF NOT EXISTS przebiegi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profil TEXT NOT NULL,
    fraza TEXT,
    url_zrodla TEXT,
    tryb TEXT NOT NULL,                -- pobieranie | import_html | import_csv | import_json
    rozpoczeto TEXT NOT NULL,
    zakonczono TEXT,
    status TEXT NOT NULL,
    powod_zakonczenia TEXT,
    szczegoly_zakonczenia TEXT,
    strony INTEGER NOT NULL DEFAULT 0,
    oferty_sparsowane INTEGER NOT NULL DEFAULT 0,
    dane_testowe INTEGER NOT NULL DEFAULT 0,
    kryteria_json TEXT,
    diagnostyka_json TEXT
);
CREATE TABLE IF NOT EXISTS oferty (
    offer_id TEXT PRIMARY KEY,
    id_pewne INTEGER NOT NULL,
    url TEXT,
    pierwszy_przebieg INTEGER REFERENCES przebiegi(id),
    ostatni_przebieg INTEGER REFERENCES przebiegi(id)
);
CREATE TABLE IF NOT EXISTS obserwacje (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    przebieg_id INTEGER NOT NULL REFERENCES przebiegi(id),
    offer_id TEXT NOT NULL REFERENCES oferty(offer_id),
    profil TEXT,
    fraza TEXT,
    pobrano TEXT,
    strona INTEGER,
    pozycja INTEGER,
    tytul TEXT,
    marka TEXT,
    model TEXT,
    ean TEXT,
    cena_gr INTEGER,
    waluta TEXT,
    cena_rodzaj TEXT,
    dostawa_gr INTEGER,
    dostawa_od_gr INTEGER,
    dostawa_tekst TEXT,
    smart INTEGER,
    z_dostawa_gr INTEGER,
    z_dostawa_zrodlo TEXT,
    stan TEXT,
    stan_zrodlo TEXT,
    sprzedawca TEXT,
    sponsorowana INTEGER,
    zrodlo_danych TEXT,
    decyzja TEXT,
    powod TEXT,
    uwagi_json TEXT,
    ostrzezenia_json TEXT,
    wystapienia INTEGER NOT NULL DEFAULT 1,
    UNIQUE (przebieg_id, offer_id)
);
CREATE INDEX IF NOT EXISTS idx_obs_offer ON obserwacje(offer_id);
CREATE INDEX IF NOT EXISTS idx_obs_profil ON obserwacje(profil);
"""


def _b(v: bool | None) -> int | None:
    return None if v is None else int(bool(v))


class Baza:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMAT)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Baza":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------ przebiegi

    def nowy_przebieg(self, *, profil: str, fraza: str | None, url: str | None, tryb: str,
                      kryteria: dict[str, Any], dane_testowe: bool = False) -> int:
        status = StatusPrzebiegu.IMPORT if tryb.startswith("import") else StatusPrzebiegu.W_TOKU
        cur = self.conn.execute(
            "INSERT INTO przebiegi(profil, fraza, url_zrodla, tryb, rozpoczeto, status, dane_testowe, kryteria_json)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (profil, fraza, url, tryb, now_iso(), status.value, int(dane_testowe),
             json.dumps(kryteria, ensure_ascii=False, default=str)),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def zakoncz_przebieg(self, przebieg_id: int, *, powod: str, szczegoly: str | None = None,
                         strony: int, oferty: int, diagnostyka: dict[str, Any] | None = None,
                         status: StatusPrzebiegu | None = None) -> StatusPrzebiegu:
        if status is None:
            status = POWODY_ZAKONCZENIA.get(powod, (StatusPrzebiegu.NIEPELNY, ""))[0]
        self.conn.execute(
            "UPDATE przebiegi SET zakonczono=?, status=?, powod_zakonczenia=?, szczegoly_zakonczenia=?,"
            " strony=?, oferty_sparsowane=?, diagnostyka_json=? WHERE id=?",
            (now_iso(), status.value, powod, szczegoly, strony, oferty,
             json.dumps(diagnostyka or {}, ensure_ascii=False, default=str), przebieg_id),
        )
        self.conn.commit()
        return status

    def przebieg(self, przebieg_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM przebiegi WHERE id=?", (przebieg_id,)).fetchone()
        return dict(row) if row else None

    def przebiegi(self, profil: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        q = "SELECT * FROM przebiegi" + (" WHERE profil=?" if profil else "") + " ORDER BY id DESC LIMIT ?"
        args: tuple = (profil, limit) if profil else (limit,)
        return [dict(r) for r in self.conn.execute(q, args)]

    def ostatni_przebieg(self, profil: str) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM przebiegi WHERE profil=? AND status != 'w_toku' ORDER BY id DESC LIMIT 1", (profil,)
        ).fetchone()
        return int(row["id"]) if row else None

    # ------------------------------------------------------------ oferty

    def zapisz_oferty(self, przebieg_id: int, oferty: Iterable[Oferta]) -> tuple[int, int]:
        """Zapisuje obserwacje. Zwraca (nowe_w_przebiegu, duplikaty_w_przebiegu)."""
        nowe = dup = 0
        with self.conn:
            for o in oferty:
                if not o.offer_id:
                    raise ValueError("Oferta bez offer_id — nadaj identyfikator zastępczy przed zapisem")
                self.conn.execute(
                    "INSERT INTO oferty(offer_id, id_pewne, url, pierwszy_przebieg, ostatni_przebieg)"
                    " VALUES (?,?,?,?,?) ON CONFLICT(offer_id) DO UPDATE SET"
                    " ostatni_przebieg=excluded.ostatni_przebieg, url=COALESCE(excluded.url, oferty.url)",
                    (o.offer_id, int(o.id_pewne), o.url, przebieg_id, przebieg_id),
                )
                exists = self.conn.execute(
                    "SELECT id FROM obserwacje WHERE przebieg_id=? AND offer_id=?", (przebieg_id, o.offer_id)
                ).fetchone()
                if exists:
                    dup += 1
                    self.conn.execute(
                        "UPDATE obserwacje SET wystapienia = wystapienia + 1,"
                        " sponsorowana = MAX(COALESCE(sponsorowana,0), ?) WHERE id=?",
                        (_b(o.sponsorowana) or 0, exists["id"]),
                    )
                    continue
                nowe += 1
                self.conn.execute(
                    "INSERT INTO obserwacje(przebieg_id, offer_id, profil, fraza, pobrano, strona, pozycja, tytul,"
                    " marka, model, ean, cena_gr, waluta, cena_rodzaj, dostawa_gr, dostawa_od_gr, dostawa_tekst,"
                    " smart, z_dostawa_gr, z_dostawa_zrodlo, stan, stan_zrodlo, sprzedawca, sponsorowana,"
                    " zrodlo_danych, decyzja, powod, uwagi_json, ostrzezenia_json)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (przebieg_id, o.offer_id, o.profil, o.fraza, o.pobrano, o.strona, o.pozycja, o.tytul,
                     o.marka, o.model, o.ean, to_grosze(o.cena), o.waluta, o.cena_rodzaj,
                     to_grosze(o.koszt_dostawy), to_grosze(o.koszt_dostawy_od), o.dostawa_tekst, _b(o.smart),
                     to_grosze(o.cena_z_dostawa), o.cena_z_dostawa_zrodlo, o.stan, o.stan_zrodlo, o.sprzedawca,
                     _b(o.sponsorowana), o.zrodlo_danych, o.decyzja.value if o.decyzja else None, o.powod,
                     json.dumps(o.uwagi, ensure_ascii=False), json.dumps(o.ostrzezenia_parsera, ensure_ascii=False)),
                )
        return nowe, dup

    @staticmethod
    def _row_to_oferta(r: sqlite3.Row) -> Oferta:
        def b(v: Any) -> bool | None:
            return None if v is None else bool(v)
        o = Oferta(
            offer_id=r["offer_id"], id_pewne=bool(r["id_pewne"]), url=r["url"], tytul=r["tytul"],
            cena=from_grosze(r["cena_gr"]), waluta=r["waluta"], cena_rodzaj=r["cena_rodzaj"],
            koszt_dostawy=from_grosze(r["dostawa_gr"]), koszt_dostawy_od=from_grosze(r["dostawa_od_gr"]),
            dostawa_tekst=r["dostawa_tekst"], smart=b(r["smart"]), cena_z_dostawa=from_grosze(r["z_dostawa_gr"]),
            cena_z_dostawa_zrodlo=r["z_dostawa_zrodlo"], stan=r["stan"], stan_zrodlo=r["stan_zrodlo"],
            sprzedawca=r["sprzedawca"], sponsorowana=b(r["sponsorowana"]), ean=r["ean"], marka=r["marka"],
            model=r["model"], strona=r["strona"], pozycja=r["pozycja"], pobrano=r["pobrano"], fraza=r["fraza"],
            profil=r["profil"], zrodlo_danych=r["zrodlo_danych"],
            decyzja=Decyzja(r["decyzja"]) if r["decyzja"] else None, powod=r["powod"],
            uwagi=json.loads(r["uwagi_json"] or "[]"), ostrzezenia_parsera=json.loads(r["ostrzezenia_json"] or "[]"),
            wystapienia=r["wystapienia"],
        )
        return o

    def oferty_przebiegu(self, przebieg_id: int) -> list[Oferta]:
        rows = self.conn.execute(
            "SELECT o.*, f.id_pewne, f.url FROM obserwacje o JOIN oferty f USING(offer_id)"
            " WHERE o.przebieg_id=? ORDER BY o.strona, o.pozycja, o.id",
            (przebieg_id,),
        )
        return [self._row_to_oferta(r) for r in rows]

    def historia(self, profil: str) -> dict[str, list[dict[str, Any]]]:
        """Historia ceny każdej oferty profilu: offer_id -> lista obserwacji w kolejności przebiegów."""
        rows = self.conn.execute(
            "SELECT o.offer_id, o.przebieg_id, o.pobrano, o.cena_gr, o.z_dostawa_gr, o.decyzja, o.tytul,"
            " f.url, p.rozpoczeto, p.status FROM obserwacje o JOIN oferty f USING(offer_id)"
            " JOIN przebiegi p ON p.id = o.przebieg_id WHERE o.profil=? ORDER BY o.offer_id, o.przebieg_id",
            (profil,),
        )
        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(r["offer_id"], []).append(dict(r))
        return out

    def liczba_obserwacji(self, offer_id: str) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM obserwacje WHERE offer_id=?", (offer_id,)).fetchone()[0])

    def liczba_ofert(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM oferty").fetchone()[0])
