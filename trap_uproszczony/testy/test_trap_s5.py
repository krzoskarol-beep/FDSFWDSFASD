# -*- coding: utf-8 -*-
"""
Testy weryfikujące obliczenia trapu S5 – niezależnie od tego, kto (lub co) je napisał.
  cd trap_uproszczony && python3 -m pytest testy -q

1–3: model rusztu (sily.py) porównany z rozwiązaniami z podręcznika i z równowagą sił.
4–5: obliczenia ręczne (stal.py) przeliczone od zera inną drogą.
6:   model 3D: każda śruba przechodzi przez otwory, nic nie koliduje po złożeniu.
7–9: regresja wniosków projektowych (żeby zmiana w kodzie nie cofnęła poprawek).
"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import generuj as g
import sily
import stal
import stal_s5 as s5

E = 210000.0
LANE = sily.rhs_IJ(40, 100, 2)


def _beam(L=1250.0):
    """jedna linia rur: A + B połączone zawiasem, podparta sworzniem (A, s=0) i ziemią (B, s=L) – belka swobodna 2L"""
    return sily.Ruszt([0.0], -20.0, 20.0, L, LANE, LANE, sily.rhs_IJ(60, 40, 3), [], [], hinges=(0.0,), pins=(0.0,))


def test_1_belka_swobodna_ugiecie_jak_w_podreczniku():
    L, P = 1250.0, 1000.0
    res = _beam(L).solve([(("A", "t", 0.0, L), P)])
    w = -res["W"][("A", "t", 0.0, L)]
    wz = P * (2 * L) ** 3 / (48 * E * LANE[0])          # P·l³ / 48EI
    assert w == pytest.approx(wz, rel=0.01)


def test_2_belka_swobodna_reakcje():
    L, P = 1250.0, 1000.0
    res = _beam(L).solve([(("A", "t", 0.0, 600.0), P)])   # siła 600 mm od sworznia, rozpiętość 2500
    R = res["R"]
    assert R[("sworzeń przy przyczepie", 0.0)] == pytest.approx(P * 1900 / 2500, rel=0.01)
    assert R[("ziemia", 0.0)] == pytest.approx(P * 600 / 2500, rel=0.01)


def test_3_ruszt_s5_rownowaga_sil():
    r = s5.ruszt(True)
    for key, P in ((("A", "t", 45.0, 600.0), 6000.0), (("B", "t", s5.XE, 0.0), 2300.0), (("A", "t", -125.0, 1250.0), 6000.0)):
        res = r.solve([(key, P)])
        assert sum(res["R"].values()) == pytest.approx(P, rel=0.005)


def test_4_rura_jezdna_cale_kolo_reczne_od_zera():
    v = s5.V
    L = 2 * g.L_SEC
    Pd = g.WHEEL_KG * 9.81 / 1000 * 1.5 * 1.5
    q = 1.35 * (s5.mA + s5.mB) * 9.81 / 1000 / 2 / L
    M = Pd * L / 4 + q * L ** 2 / 8                        # kN·mm
    sigma = M * 1e3 / v["lane"][1]["W"]
    row = next(r for r in s5.ROWS if "całe koło na jednej rurze" in r["nazwa"])
    assert row["obciazenie"] == pytest.approx(sigma, rel=0.002)
    assert row["wytezenie"] < 1.0


def test_5_wskaznik_przekroju_rhs_100x40x2():
    b, h, t = 40, 100, 2
    I = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12
    assert stal.rhs(40, 100, 2)["W"] == pytest.approx(I / 50, rel=1e-9)
    assert I == pytest.approx(679125.33, rel=1e-6)


def test_6_model_3d_otwory_sruby_kolizje():
    import podglad3d as p3
    M = s5.model()
    with s5.s5_globals():
        assert p3.check(M) is True
        assert p3.check_fold(M) == []


def test_7_po_poprawce_chodnik_nie_jest_mechanizmem():
    assert -s5.SILY["przed"]["walk"] > 100.0               # przed: mechanizm
    assert -s5.SILY["po"]["walk"] < 15.0                   # po: kilka mm


def test_8_wszystkie_wytezenia_ponizej_1():
    worst = [r for r in s5.ROWS if not r["nazwa"].startswith("[INFO]") and r["wytezenie"] >= 1.0]
    assert worst == []


def test_9_sprezyny_rozlozony_lezy_pion_nie_pcha_takze_w_upale():
    import analizy_dodatkowe as a
    for r in a.springs():
        assert r["ok_lezy"], r["przypadek"]
        assert r["ok_pion"], r["przypadek"]
        if not r["przypadek"].startswith(("jedna", "obie")):
            assert r["rozlozony"] < -60.0, r["przypadek"]          # rozłożony dociśnięty do ziemi z zapasem, także w upale


def test_10_model_3d_ruch_swiatla_szczeliny():
    import kontrola3d as k
    M = s5.model()
    with s5.s5_globals():
        r = k.run(M, s5.layout())
    assert r["sprezyny"]["ok"], r["sprezyny"]                    # sprężyny w skoku w całym ruchu
    assert r["przyczepa"] == []                                  # trap nie wchodzi w przyczepę w 41 położeniach
    for x in r["swiatla"]:
        assert x["zasloniete"] == [], x                           # lampy i tablica widoczne w kątach EKG ONZ R48
    assert r["szczeliny"]["ok"], r["szczeliny"]                   # odbojnik: ≤ 4 mm albo ≥ 25 mm
