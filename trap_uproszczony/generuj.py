# -*- coding: utf-8 -*-
"""
Trap aluminiowy do przyczepki 2,5 x 1,19 m  -  WERSJA UPROSZCZONA (V2)
Cala konstrukcja skrecana / nitowana, BEZ SPAWANIA i bez giecia.
Wszystkie plyty stalowe to PROSTOKATY z plaskownika / katownika (tylko proste ciecia).

Uruchom:   pip install matplotlib ezdxf
           python3 generuj.py
Wynik (w tym samym katalogu): rysunki_trap_v2.pdf, szablony_1do1_v2.pdf, DXF/*.dxf,
lista_czesci.csv, lista_srub.csv, lista_zakupow.csv, obliczenia.csv, trap_v2_dane.json

Uklad wspolrzednych:
  x  - w poprzek trapu, 0 = os trapu
  s  - wzdluz sekcji: sekcja A od konca przy przyczepie, sekcja B od zawiasu srodkowego
  z  - w gore od spodu podluznic (0 = spod rur 100 mm = gora poprzeczek, 100 = pokład)
"""
import csv, json, math, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, Polygon
import ezdxf

OUT = os.path.dirname(os.path.abspath(__file__))
G = 9.81

# ------------------------------------------------------------------ PARAMETRY
H_FLOOR = 480.0          # wysokosc podlogi przyczepy nad ziemia [mm]
L_SEC = 1250.0           # dlugosc sekcji A i B
PIN_Y, PIN_Z = 40.0, -25.0   # os zawiasu przy przyczepie: za tylna sciana belki / pod podloga
WIDTH = 1190.0

# obciazenia (jak w oryginale)
WHEEL_KG = 273.0         # tylne kolo: 60 % z (350 kg motocykl + 105 kg kierowca)
FOOT_KG = 105.0
PHI, GAMMA_F, GAMMA_G = 1.5, 1.5, 1.35

# materialy [MPa]
AL6082 = dict(f0=250.0, fu=290.0)
AL6060 = dict(f0=150.0, fu=170.0)
S235 = dict(fy=235.0, fu=360.0)
B88 = dict(fyb=640.0, fub=800.0)
E_AL = 70000.0
GM1, GM2 = 1.1, 1.25

RHO_AL, RHO_ST = 2.70e-6, 7.85e-6   # kg/mm3

# ---------------------------------------------------------------- GEOMETRIA
X_LANE_IN, X_LANE_OUT = 45.0, 125.0      # rury jezdne 100x40x3 (6082)
X_WALK, X_EDGE = 345.0, 575.0            # podluznice chodnika / krawedzi 100x40x2 (6060)
LONG_X = [-X_EDGE, -X_WALK, -X_LANE_OUT, -X_LANE_IN, X_LANE_IN, X_LANE_OUT, X_WALK, X_EDGE]

CROSS_A = [340.0, 830.0]                 # poprzeczki 60x40x3 w sekcji A (s od przyczepy)
CROSS_B = [260.0]                        # poprzeczka w sekcji B (s od zawiasu)
TIE_B = 650.0                            # plaskownik spinajacy pod sekcja B (nitowany)
GUIDE_A = (150.0, 1245.0)                # prowadnice (katownik 40x40x4 na siatce)
GUIDE_B = (5.0, 720.0)
GUIDE_BOLTS_A = [200.0, 580.0, 1000.0]
GUIDE_BOLTS_B = [180.0, 450.0, 680.0]

ALPHA = math.degrees(math.asin((H_FLOOR + PIN_Z + 25.0) / (2 * L_SEC + 25.0)))
SKOS = 100.0 / math.tan(math.radians(ALPHA))        # dlugosc skosu rury 100 mm przy ziemi

# zawias przy przyczepie: plyta H (plaskownik 80x6, dl. 200) na obu sciankach rur L1
# pin: s=-25, z=75 ; blokada: s=-25, z=45 ; sruby M12: s=40 i 120, z=60
H_PL = dict(w=200.0, h=80.0, t=6.0, s0=-50.0, z0=20.0,
            holes=[("pin", -25.0, 75.0, 21.0), ("blok", -25.0, 45.0, 13.0),
                   ("M12", 40.0, 60.0, 13.0), ("M12", 120.0, 60.0, 13.0)])
# zawias srodkowy: plyta Z (plaskownik 100x6, dl. 170) - 4 szt. na A, 4 szt. na B (te same!)
# d = odleglosc od styku rur ; pin: d=0, z=-35 ; sruby: d=45 i 110, z=20
Z_PL = dict(w=170.0, h=100.0, t=6.0, d0=-30.0, z0=-60.0,
            holes=[("pin", 0.0, -35.0, 21.0), ("M12", 45.0, 20.0, 13.0), ("M12", 110.0, 20.0, 13.0)])
# zaczep gornego oczka sprezyny gazowej: plyta S (plaskownik 80x8, dl. 150) na podluznicy chodnika A
S_PL = dict(w=80.0, h=150.0, t=8.0, s0=219.0, z0=-50.0,
            holes=[("oczko", 259.0, -22.0, 13.0), ("M12", 259.0, 25.0, 13.0), ("M12", 259.0, 75.0, 13.0)])
# wspornik na belce przyczepy: K = katownik stalowy 100x100x10, odcinek 130 mm (4 szt. identyczne)
# ramie odstajace (w plaszczyznie y-z): y od tylnej sciany belki, z od podlogi
K_PL = dict(a=100.0, t=10.0, L=130.0,
            holes_arm=[("pin", 40.0, -25.0, 21.0), ("blok", 70.0, -25.0, 13.0), ("sprez.", 30.0, -100.0, 13.0)],
            holes_beam=[("M12", 55.0, -30.0, 13.0), ("M12", 55.0, -60.0, 13.0)])
TEMPL_NAME = "szablony_1do1_v2.pdf"
SPRING = dict(F1=1600.0, L_ext=460.0, stroke=200.0, n=2, prog=0.30,
              eye_low=(30.0 - PIN_Y, -100.0 - PIN_Z),   # wzgledem osi zawiasu (y,z)
              eye_up_sz=(259.0, -22.0))                  # w ukladzie rury sekcji A


def rhs(b, h, t):
    """prostokatny profil zamkniety: b szer., h wys. (os zginania pozioma)"""
    A = b * h - (b - 2 * t) * (h - 2 * t)
    I = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12.0
    return dict(A=A, I=I, W=I / (h / 2), kgm=A * RHO_AL * 1000)


P_LANE = rhs(40, 100, 3)       # RHS 100x40x3 EN AW-6082-T6
P_WALK = rhs(40, 100, 2)       # RHS 100x40x2 6060
P_CROSS = rhs(40, 60, 3)       # RHS 60x40x3 6060 (na stojaco)
ANGLE_KGM = (40 + 36) * 4 * RHO_AL * 1000
MESH_KGM2 = 2.5

# ------------------------------------------------------------------ OTWORY
# (s, scianka, z_lub_none, srednica, opis) ; scianka: 'g/d' = przez gore i dol (pion), 'bok' = przez oba boki
def holes_long(kind):
    h = []
    if kind in ("L1", "L2", "C1", "C2"):          # sekcja A
        for s in CROSS_A:
            h.append((s, "g/d", None, 12.5, "poprzeczka – M8 + tuleja 160"))
    else:                                         # sekcja B
        for s in CROSS_B:
            h.append((s, "g/d", None, 12.5, "poprzeczka – M8 + tuleja 160"))
        h.append((TIE_B, "dół", None, 4.9, "2 nity listwy T (x ±10)"))
    if kind == "L1":
        for s in GUIDE_BOLTS_A:
            h.append((s, "g/d", None, 12.5, "prowadnica – M8 + tuleja 100"))
        for (_, s, z, _) in [hh for hh in H_PL["holes"] if hh[0] == "M12"]:
            h.append((s, "bok", z, 18.5, "płyta H – M12 + tuleja Ø18"))
        for (_, d, z, _) in [hh for hh in Z_PL["holes"] if hh[0] == "M12"]:
            h.append((L_SEC - d, "bok", z, 18.5, "płyta Z – M12 + tuleja Ø18"))
    if kind == "L3":
        for s in GUIDE_BOLTS_B:
            h.append((s, "g/d", None, 12.5, "prowadnica – M8 + tuleja 100"))
        for (_, d, z, _) in [hh for hh in Z_PL["holes"] if hh[0] == "M12"]:
            h.append((d, "bok", z, 18.5, "płyta Z – M12 + tuleja Ø18"))
    if kind == "C1":
        for (_, s, z, _) in [hh for hh in S_PL["holes"] if hh[0] == "M12"]:
            h.append((s, "bok", z, 18.5, "płyta S – M12 + tuleja Ø18"))
    return sorted(h, key=lambda r: r[0])


# ------------------------------------------------------------------ CZESCI
LONG_PARTS = [
    # id, nazwa, profil, material, szt, x-polozenia, skos?, sekcja
    ("L1", "Rura jezdna ZEWNĘTRZNA sekcji A (z zawiasami H i Z)", "RHS Al 100×40×3", "EN AW-6082-T6", 2, "±125", False, "A"),
    ("L2", "Rura jezdna WEWNĘTRZNA sekcji A", "RHS Al 100×40×3", "EN AW-6082-T6", 2, "±45", False, "A"),
    ("L3", "Rura jezdna ZEWNĘTRZNA sekcji B (zawias Z, skos przy ziemi)", "RHS Al 100×40×3", "EN AW-6082-T6", 2, "±125", True, "B"),
    ("L4", "Rura jezdna WEWNĘTRZNA sekcji B (skos przy ziemi)", "RHS Al 100×40×3", "EN AW-6082-T6", 2, "±45", True, "B"),
    ("C1", "Podłużnica chodnika sekcji A (z płytą sprężyny S)", "RHS Al 100×40×2", "6060-T6", 2, "±345", False, "A"),
    ("C2", "Podłużnica krawędzi sekcji A", "RHS Al 100×40×2", "6060-T6", 2, "±575", False, "A"),
    ("C3", "Podłużnica chodnika / krawędzi sekcji B (skos)", "RHS Al 100×40×2", "6060-T6", 4, "±345, ±575", True, "B"),
]


def tube_mass(kgm, skos, t):
    m = kgm * L_SEC / 1000
    if skos:   # usuniety dol + trojkaty bokow
        m -= (SKOS * 40 * t + 2 * 0.5 * SKOS * 100 * t) * RHO_AL
    return m


def build_bom():
    bom = []
    for pid, name, prof, mat, q, xs, skos, sec in LONG_PARTS:
        kgm = P_LANE["kgm"] if "×3" in prof else P_WALK["kgm"]
        t = 3 if "×3" in prof else 2
        bom.append(dict(pid=pid, name=name, qty=q, material=mat, size=f"{prof}, L = {L_SEC:.0f}" + (f", skos {SKOS:.0f}" if skos else ""),
                        mass=round(tube_mass(kgm, skos, t), 2), holes=sum(2 if h[1] in ("g/d", "bok") else 2 for h in holes_long(pid)),
                        how="profil cięty na długość, otwory wg tabeli" + ("; skos przy ziemi wg rysunku" if skos else ""),
                        where=f"x = {xs}"))
    n_cross = len(CROSS_A) + len(CROSS_B)
    bom.append(dict(pid="P", name="Poprzeczka – rura na stojąco", qty=n_cross, material="6060-T6",
                    size=f"RHS Al 60×40×3, L = {WIDTH:.0f}", mass=round(P_CROSS["kgm"] * WIDTH / 1000, 2), holes=16,
                    how="8 otworów Ø12,5 przez górę i dół", where=f"A: s = {CROSS_A}, B: s = {CROSS_B}"))
    bom.append(dict(pid="T", name="Listwa spinająca pod sekcją B (nitowana)", qty=1, material="6060",
                    size=f"płaskownik Al 40×5, L = {WIDTH:.0f}", mass=round(40 * 5 * WIDTH * RHO_AL, 2), holes=16,
                    how="16 otworów Ø4,9 pod nity", where=f"B: s = {TIE_B:.0f}"))
    for pid, (a, b), sec in (("G1", GUIDE_A, "A"), ("G2", GUIDE_B, "B")):
        nb = len(GUIDE_BOLTS_A if sec == "A" else GUIDE_BOLTS_B) + len(CROSS_A if sec == "A" else CROSS_B)
        bom.append(dict(pid=pid, name=f"Prowadnica koła sekcji {sec} – leży na siatce nad rurą zewnętrzną", qty=2,
                        material="6060", size=f"kątownik Al 40×40×4, L = {b - a:.0f}", mass=round(ANGLE_KGM * (b - a) / 1000, 2),
                        holes=nb, how="otwory Ø9 w półce poziomej, 20 mm od grzbietu; końce ścięte 45°",
                        where=f"s = {a:.0f}…{b:.0f}"))
    st = lambda w, h, t: round(w * h * t * RHO_ST, 2)
    bom += [
        dict(pid="H", name="Płyta zawiasu przy przyczepie", qty=4, material="S235", size=f"płaskownik 80×6, L = 200",
             mass=st(200, 80, 6), holes=4, how="prostokąt, 4 otwory (wiercić 4 szt. w pakiecie)", where="po 2 na rurę L1"),
        dict(pid="Z", name="Płyta zawiasu środkowego (A i B – ta sama)", qty=8, material="S235", size="płaskownik 100×6, L = 170",
             mass=st(170, 100, 6), holes=3, how="prostokąt, 3 otwory (wiercić 8 szt. w pakiecie)", where="po 2 na rurę L1 i L3"),
        dict(pid="S", name="Płyta zaczepu sprężyny gazowej", qty=2, material="S235", size="płaskownik 80×8, L = 150",
             mass=st(150, 80, 8), holes=3, how="prostokąt, 3 otwory", where="na C1, s = 219…299"),
        dict(pid="K", name="Wspornik na belce przyczepy (zawias / sprężyna)", qty=4, material="S235",
             size="kątownik 100×100×10, L = 130", mass=round(1.9e3 * 130 * RHO_ST, 2), holes=5,
             how="odcinek kątownika, 5 otworów, BEZ gięcia", where="2 × zawias (x ±152…162), 2 × sprężyna (x ±369…379)"),
        dict(pid="SIATKA", name="Siatka cięto-ciągniona Al (pokład)", qty=2, material="Al",
             size=f"{WIDTH:.0f} × {L_SEC:.0f} (LWD w poprzek)", mass=round(WIDTH * L_SEC * 1e-6 * MESH_KGM2, 2), holes=0,
             how="z 1 arkusza 1250×2500", where="cały pokład A i B"),
    ]
    return bom


def build_bolts():
    nA, nB = len(CROSS_A), len(CROSS_B)
    n_cross = 8 * (nA + nB)
    n_guide = 2 * (len(GUIDE_BOLTS_A) + len(GUIDE_BOLTS_B))
    bolts = [
        ("M8×200", "zamkowa DIN 603 kl. 8.8 (łbem do góry, przez siatkę) + podkładka + nakrętka samohamowna", n_cross, "skrzyżowania podłużnic z poprzeczkami"),
        ("M8×130", "zamkowa DIN 603 (łbem do góry, przez prowadnicę i siatkę) + podkładka + nakr. samoham.", n_guide, "prowadnice"),
        ("M12×80", "sześciokątna ISO 4014/4017 8.8 + 2 podkł. + nakr. samoham.", 4 + 4 + 4, "płyty H (4), płyty Z sekcji A (4), płyty S (4)"),
        ("M12×90", "sześciokątna ISO 4014 8.8 + 2 podkł. + nakr. samoham.", 4, "płyty Z sekcji B (z podkładkami dystansowymi)"),
        ("M12×60", "sześciokątna 8.8 + podkł. + nakr. samoham.", 4, "oczka sprężyn gazowych (2 na K, 2 na S)"),
        ("M12×80", "sześciokątna 8.8 + 2 podkł. + nakr. samoham. (DOPASUJ do belki)", 8, "wsporniki K → tylna belka przyczepy"),
        ("M20×110", "sześciokątna ISO 4014 8.8 (gładki trzpień ≥ 64 mm) = SWORZEŃ zawiasu + 2 podkł. + nakr. samoham. (nie dokręcać na sztywno)", 4, "2 × zawias przy przyczepie, 2 × zawias środkowy"),
        ("Ø12×40", "sworzeń ISO 2341-B + zawleczka sprężynowa, na łańcuszku", 2, "blokada trapu w pionie (transport)"),
        ("podkładka M12 gr. 6", "DIN 7349 (13×30×6) – dystans płyt Z sekcji B", 8, "zawias środkowy"),
        ("nit 4,8", "nit zrywalny stalowy/nierdzewny 4,8 mm, szeroki kołnierz", 16 + 8, "listwa T (16) + zapięcia (8)"),
        ("wkręt 4,8×19", "wkręt samowiercący nierdzewny z podkładką EPDM Ø16", 100, "mocowanie siatki co ~250 mm do każdej podłużnicy"),
    ]
    sleeves = [
        ("Ø12×1,5", 159.5, n_cross, "M8 – przez rurę 100 + poprzeczkę 60 (jedna tuleja na wylot)"),
        ("Ø12×1,5", 99.5, n_guide, "M8 – prowadnice, przez rurę 100"),
        ("Ø18×2,5", 40.0, 4 + 8 + 4, "M12 – płyty H, Z, S (przez rurę 40 mm)"),
        ("Ø18×2,5", 50.0, 8, "M12 – przez belkę przyczepy 50×75 (DOPASUJ do belki)"),
        ("Ø20×4", 12.0, 2, "dystans oczka sprężyny na wsporniku K"),
        ("Ø20×4", 18.0, 2, "dystans oczka sprężyny na płycie S"),
    ]
    return bolts, sleeves


# ------------------------------------------------------------------ MASY
def masses():
    """masa i srodek ciezkosci sekcji A i B (w ukladzie rury: s, z)"""
    def acc(items):
        m = sum(i[0] for i in items)
        return m, sum(i[0] * i[1] for i in items) / m, sum(i[0] * i[2] for i in items) / m

    def skos_tube(kgm, t):
        full = kgm * L_SEC / 1000
        cut = (SKOS * 40 * t + SKOS * 100 * t) * RHO_AL
        s_cut = L_SEC - SKOS / 3
        return [(full, L_SEC / 2, 50.0), (-cut, s_cut, 25.0)]

    A = []
    A += [(4 * P_LANE["kgm"] * L_SEC / 1000, L_SEC / 2, 50.0), (4 * P_WALK["kgm"] * L_SEC / 1000, L_SEC / 2, 50.0)]
    A += [(P_CROSS["kgm"] * WIDTH / 1000, s, -30.0) for s in CROSS_A]
    A += [(WIDTH * L_SEC * 1e-6 * MESH_KGM2, L_SEC / 2, 101.5)]
    A += [(2 * ANGLE_KGM * (GUIDE_A[1] - GUIDE_A[0]) / 1000, sum(GUIDE_A) / 2, 115.0)]
    A += [(4 * 200 * 80 * 6 * RHO_ST, 50.0, 60.0), (4 * 170 * 100 * 6 * RHO_ST, L_SEC - 55.0, -10.0),
          (2 * 150 * 80 * 8 * RHO_ST, 259.0, 25.0), (3.2, L_SEC / 2, 50.0)]       # 3,2 kg = sruby, tuleje, sworznie
    B = []
    for kgm, t, n in ((P_LANE["kgm"], 3, 4), (P_WALK["kgm"], 2, 4)):
        B += [(n * m, s, z) for (m, s, z) in skos_tube(kgm, t)]
    B += [(P_CROSS["kgm"] * WIDTH / 1000, s, -30.0) for s in CROSS_B]
    B += [(40 * 5 * WIDTH * RHO_AL, TIE_B, -2.5), (WIDTH * L_SEC * 1e-6 * MESH_KGM2, L_SEC / 2, 101.5)]
    B += [(2 * ANGLE_KGM * (GUIDE_B[1] - GUIDE_B[0]) / 1000, sum(GUIDE_B) / 2, 115.0)]
    B += [(4 * 170 * 100 * 6 * RHO_ST + 8 * 0.033, 55.0, -10.0), (1.6, 500.0, 50.0)]
    return acc(A), acc(B)


# ------------------------------------------------------------------ OBLICZENIA
def calcs(mA, mB):
    rows = []

    def add(name, load, cap, unit, note=""):
        rows.append(dict(nazwa=name, obciazenie=round(load, 2), nosnosc=round(cap, 2), jedn=unit,
                         wytezenie=round(load / cap, 3), uwagi=note))

    L = 2 * L_SEC
    Pk = WHEEL_KG * G / 1000                  # kN charakterystyczne
    Pd = Pk * PHI * GAMMA_F                   # kN obliczeniowe
    Fd = FOOT_KG * G / 1000 * PHI * GAMMA_F   # stopa obliczeniowa
    m_tot = mA + mB
    q_d = GAMMA_G * m_tot * G / 1000 / 2 / L  # kN/mm na jedna rure z zawiasem
    fA82 = AL6082["f0"] / GM1
    fA60 = AL6060["f0"] / GM1

    # 1 rura jezdna zewnetrzna - zginanie calej rozpietosci
    M75 = (0.75 * Pd * L / 4 + q_d * L ** 2 / 8)          # kN*mm
    add("Rura jezdna L1/L3 100×40×3 (6082-T6) – zginanie, rozpiętość 2,5 m", M75 * 1e3 / P_LANE["W"], fA82, "MPa",
        f"koło {WHEEL_KG:.0f} kg ×φ{PHI} ×γ{GAMMA_F}, 75 % na jedną rurę, w środku + ciężar własny ×1,35")
    M100 = (1.0 * Pd * L / 4 + q_d * L ** 2 / 8)
    add("To samo – CAŁE koło na jednej rurze (sprawdzenie skrajne)", M100 * 1e3 / P_LANE["W"], fA82, "MPa",
        "gdyby siatka i poprzeczki nic nie rozkładały")
    add("[INFO] Ta sama rura, gdyby była z 6060-T6 (75 %) – NIE WOLNO", M75 * 1e3 / P_LANE["W"], fA60, "MPa",
        "pokazuje, dlaczego rury jezdne muszą być 6082-T6 (PA4)")
    qk = m_tot * G / 1000 / 2 / L
    dk = 0.75 * Pk * 1e3 * L ** 3 / (48 * E_AL * P_LANE["I"]) + 5 * qk * 1e3 * L ** 4 / (384 * E_AL * P_LANE["I"])
    add("Ugięcie w środku (charakterystyczne)", dk, L / 200, "mm", "limit L/200")
    # 2 wsporniki rur wewnetrznych
    for nm, a in (("przy przyczepie", CROSS_A[0]), ("przy zawiasie (sekcja A)", L_SEC - CROSS_A[-1]),
                  ("przy zawiasie (sekcja B)", CROSS_B[0])):
        add(f"Rura jezdna wewnętrzna – wspornik {nm} {a:.0f} mm, całe koło na końcu", Pd * a * 1e3 / P_LANE["W"], fA82, "MPa",
            "rury wewnętrzne nie mają zawiasów – opierają się na poprzeczkach")
    # 3 zawias srodkowy
    arm = 100.0 + 35.0
    F = M75 / arm              # kN na jedna rure z zawiasem
    Fp = F / 2                 # na jedna plyte (dwie strony rury)
    add("Zawias środkowy: sworzeń M20 8.8 – ścinanie (2 płaszczyzny na rurę)", Fp,
        0.6 * B88["fub"] * math.pi * 10 ** 2 / GM2 / 1e3, "kN",
        f"moment {M75 / 1e3:.2f} kN·m / ramię {arm:.0f} mm (styk góry rur ↔ sworzeń pod rurą)")
    Mpin = Fp * 1e3 * 6.0
    add("Zawias środkowy: sworzeń M20 – zginanie (płyty A i B przylegają)", Mpin / 1e3,
        1.5 * math.pi * 20 ** 3 / 32 * B88["fyb"] / 1e3, "N·m", "EN 1993-1-8 tab. 3.10")
    e1 = 30.0
    ab = min(e1 / (3 * 21), S235["fu"] / S235["fu"], 1.0)
    add("Zawias środkowy: docisk sworznia w płycie Z 6 mm", Fp, 2.5 * ab * S235["fu"] * 20 * 6 / GM2 / 1e3, "kN",
        "S235, odl. otworu od końca 30 mm")
    # grupa srub plyty Z
    ez = 20.0 - (-35.0)
    Mg = Fp * ez
    Vb = Mg / 65.0
    Hb = Fp / 2
    Rb = math.hypot(Vb, Hb)
    add("Zawias środkowy: śruba M12 8.8 płyty Z – ścinanie", Rb, 0.6 * B88["fub"] * 84.3 / GM2 / 1e3, "kN",
        f"mimośród {ez:.0f} mm, rozstaw śrub 65 mm")
    ab = min(45.0 / (3 * 18.5), 1.0)
    add("Zawias środkowy: tuleja Ø18 → ścianka rury Al 3 mm (docisk)", Rb, 2.5 * ab * AL6082["fu"] * 18 * 3 / GM2 / 1e3, "kN",
        "tuleja stalowa Ø18×2,5 w otworze Ø18,5; 45 mm od końca rury")
    add("Zawias środkowy: docisk górnych krawędzi rur (styk)", 2 * F, 4 * (2 * 40 + 2 * 94) * 3 * 0.25 * fA82 / 1e3, "kN",
        "4 rury stykają się czołami; liczona ¼ obwodu ścianek")
    # 4 zawias przy przyczepie
    R = 0.75 * Pd + q_d * L / 2
    add("Zawias przy przyczepie: sworzeń M20 – zginanie (ramię do wspornika K)", R / 2 * 51.0,
        1.5 * math.pi * 20 ** 3 / 32 * B88["fyb"] / 1e3, "N·m", f"reakcja {R:.1f} kN na rurę, 2 płyty H")
    add("Zawias przy przyczepie: docisk sworznia w płycie H 6 mm", R / 2,
        2.5 * min(25 / 63, 1) * S235["fu"] * 20 * 6 / GM2 / 1e3, "kN", "krawędź 25 mm")
    MH = R / 2 * (80.0 + 25.0)
    VH = MH / 80.0
    add("Zawias przy przyczepie: śruba M12 płyty H → rura (docisk Al)", math.hypot(VH, R / 4),
        2.5 * min(40 / 55.5, 1) * AL6082["fu"] * 18 * 3 / GM2 / 1e3, "kN", "mimośród 105 mm, rozstaw 80 mm")
    add("Wspornik K (kątownik 100×100×10) – zginanie ramienia", R * 40 * 1e3 / (10 * 130 ** 2 / 6), S235["fy"], "MPa",
        "ramię 40 mm od ściany belki")
    # 5 poprzeczka
    Mc = Fd * (X_EDGE + 20 - (X_LANE_OUT + 20))
    add("Poprzeczka 60×40×3 (6060) – stopa na samej krawędzi, cała na jednej poprzeczce", Mc * 1e3 / P_CROSS["W"], fA60, "MPa",
        f"wspornik {X_EDGE + 20 - X_LANE_OUT - 20:.0f} mm od rury jezdnej")
    Rin = Pd * CROSS_A[1] / (CROSS_A[1] - CROSS_A[0])
    Mt = Rin * (X_LANE_OUT - X_LANE_IN) * (X_LANE_OUT - X_LANE_IN) / (2 * X_LANE_OUT) * (X_LANE_OUT + X_LANE_IN) / (X_LANE_OUT - X_LANE_IN)
    Mt = Rin * (X_LANE_OUT - X_LANE_IN) / (2 * X_LANE_OUT) * (X_LANE_OUT + X_LANE_IN)
    add("Poprzeczka – przenosi nacisk rury wewnętrznej na zewnętrzne (koło na końcu przy przyczepie)",
        Mt * 1e3 / P_CROSS["W"], fA60, "MPa", f"reakcja rury wewn. {Rin:.1f} kN")
    T = Rin * (X_LANE_OUT + X_LANE_IN) / (2 * X_LANE_OUT)
    add("Śruba M8 8.8 na skrzyżowaniu – rozciąganie (poprzeczka wisi na rurze zewn.)", T,
        0.9 * B88["fub"] * 36.6 / GM2 / 1e3, "kN", "")
    add("Przeciąganie łba / podkładki przez ściankę poprzeczki 3 mm", T, 0.6 * math.pi * 20 * 3 * AL6060["fu"] / GM2 / 1e3, "kN",
        "podkładka Ø24 pod nakrętką")
    # 6 podluznice chodnika
    for nm, a, kind in (("wspornik przy zawiasie A", L_SEC - CROSS_A[-1], "c"),
                        ("przęsło między poprzeczkami A", CROSS_A[1] - CROSS_A[0], "s"),
                        ("wspornik przy przyczepie", CROSS_A[0], "c"),
                        ("B: od poprzeczki do oparcia skosu na ziemi", L_SEC - SKOS - CROSS_B[0], "s")):
        M = Fd * a * (1 if kind == "c" else 0.25)
        add(f"Podłużnica chodnika 100×40×2 (6060) – {nm} {a:.0f} mm", M * 1e3 / P_WALK["W"], fA60, "MPa", "stopa 105 kg ×1,5 ×1,5")
    # 7 prowadnica
    Fl = 0.3 * Pd
    Mg_ = Fl * 1e3 * 35.0
    add("Prowadnica – kątownik 40×40×4: zginanie półki pionowej od bocznego pchnięcia opony", Mg_ / (300 * 4 ** 2 / 6), fA60, "MPa",
        "0,3 × koło na wys. 35 mm, współpracuje ~300 mm półki")
    add("Prowadnica – śruba M8 rozrywana (dźwignia 35/20 mm)", Fl * 35 / 20, 0.9 * 400 * 36.6 / GM2 / 1e3, "kN",
        "cała siła na jednej śrubie, liczona kl. 4.6")
    # 8 blokada transportowa
    mt = mA + mB
    Fb = mt * G * 0.8 * 1.5 / 1000
    Mb = Fb * 620.0
    Fpin = Mb / 30.0 / 2
    add("Blokada w transporcie: sworzeń Ø12 – ścinanie", Fpin, 0.6 * 400 * math.pi * 36 / GM2 / 1e3, "kN",
        f"trap w pionie {mt:.0f} kg, hamowanie 0,8 g ×1,5, ramię 30 mm, 2 sworznie (sworzeń ze stali ≥ 400 MPa)")
    add("Blokada: docisk sworznia Ø12 w płycie H 6 mm", Fpin, 2.5 * min(25 / 39, 1) * S235["fu"] * 12 * 6 / GM2 / 1e3, "kN", "")
    # 9 sprezyna
    Fs = SPRING["F1"] * (1 + SPRING["prog"]) * 1.5 / 1000
    add("Oczko sprężyny: śruba M12 + tuleja Ø20×4 L18 – zginanie tulei", Fs * 1e3 * 23 / (math.pi * (20 ** 4 - 12 ** 4) / (32 * 20)),
        S235["fy"], "MPa", "ramię 23 mm od blachy")
    add("Płyta S 8 mm – śruby M12 w podłużnicy 100×40×2 (docisk Al 2 mm)", Fs * 72 / 50 / 2 + Fs / 2,
        2.5 * min(40 / 55.5, 1) * AL6060["fu"] * 18 * 2 / GM2 / 1e3, "kN", "mimośród 72 mm, rozstaw 50 mm")
    return rows


# ------------------------------------------------------------------ PODNOSZENIE
def rot(th, u, v):
    c, s = math.cos(th), math.sin(th)
    return (u * c - v * s, u * s + v * c)


def lift_table(mA, cA_s, cA_z, mB, cB_s, cB_z, springs=True):
    z_ground = -(H_FLOOR + PIN_Z)
    uM, vM = L_SEC + 25.0, -35.0 - 75.0          # zawias srodkowy wzgl. zawiasu przy przyczepie
    cAu, cAv = cA_s + 25.0, cA_z - 75.0
    cBu, cBv = cB_s, cB_z + 35.0                 # srodek B wzgl. zawiasu srodkowego
    tipu, tipv = L_SEC, 100.0 + 35.0
    eu = (SPRING["eye_up_sz"][0] + 25.0, SPRING["eye_up_sz"][1] - 75.0)
    el = SPRING["eye_low"]

    def th0():
        lo, hi = math.radians(-30), 0.0
        for _ in range(60):
            mid = (lo + hi) / 2
            pm = rot(mid, uM, vM)
            tip = rot(mid, tipu, tipv)
            if pm[1] + tip[1] > z_ground:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2
    t0 = th0()
    rows = []
    n = 60
    for i in range(n + 1):
        th = t0 + (math.radians(90.0) - t0) * i / n
        pm = rot(th, uM, vM)
        cgA = rot(th, cAu, cAv)
        # B wisi swobodnie?
        ph_h = math.atan2(cBu, cBv)
        if rot(ph_h, cBu, cBv)[1] > 0:
            ph_h += math.pi
        ph_h = math.atan2(math.sin(ph_h), math.cos(ph_h))
        tip_h = rot(ph_h, tipu, tipv)
        hang = pm[1] + tip_h[1] > z_ground
        if hang:
            Vm = mB * G
        else:
            lo, hi = 0.0, -ph_h if ph_h < 0 else math.radians(98)
            g = lambda psi: pm[1] + rot(-psi, tipu, tipv)[1] - z_ground
            a, b = 1e-4, abs(ph_h)
            for _ in range(80):
                mid = (a + b) / 2
                if g(mid) > 0:
                    a = mid
                else:
                    b = mid
            ph = -(a + b) / 2
            tip = rot(ph, tipu, tipv)
            cgB = rot(ph, cBu, cBv)
            ytip, ycg = pm[0] + tip[0], pm[0] + cgB[0]
            Vm = mB * G * (ytip - ycg) / (ytip - pm[0])
        Tg = (mA * G * cgA[0] + Vm * pm[0]) / 1000.0          # N*m, opuszcza trap
        Ts = 0.0
        L = 0.0
        if springs:
            pe = rot(th, *eu)
            dx, dz = pe[0] - el[0], pe[1] - el[1]
            L = math.hypot(dx, dz)
            Fsp = SPRING["F1"] * (1 + SPRING["prog"] * (SPRING["L_ext"] - L) / SPRING["stroke"])
            lever = (pe[0] * dz - pe[1] * dx) / L
            Ts = SPRING["n"] * Fsp * lever / 1000.0
        Fu = (Tg - Ts) / ((L_SEC + 25.0) / 1000.0) / G
        rows.append(dict(deg=round(math.degrees(th), 1), L=round(L, 1), Tg=round(-Tg, 1), Ts=round(Ts, 1),
                         user_kg=round(Fu, 1), hang=hang))
    return rows


# ------------------------------------------------------------------ DXF / SZABLONY
def plate_outline(kind):
    """prostokat + otwory w ukladzie plyty (mm, 0,0 = lewy dolny rog)"""
    if kind == "H":
        p = H_PL
        holes = [(n, s - p["s0"], z - p["z0"], d) for (n, s, z, d) in p["holes"]]
        return p["w"], p["h"], holes, "H – płyta zawiasu przy przyczepie, S235 6 mm, 4 szt."
    if kind == "Z":
        p = Z_PL
        holes = [(n, d - p["d0"], z - p["z0"], dd) for (n, d, z, dd) in p["holes"]]
        return p["w"], p["h"], holes, "Z – płyta zawiasu środkowego, S235 6 mm, 8 szt."
    if kind == "S":
        p = S_PL
        holes = [(n, s - p["s0"], z - p["z0"], d) for (n, s, z, d) in p["holes"]]
        return p["w"], p["h"], holes, "S – płyta zaczepu sprężyny, S235 8 mm, 2 szt."
    if kind == "K_ramie":
        holes = [(n, y, K_PL["L"] + z, d) for (n, y, z, d) in K_PL["holes_arm"]]
        return K_PL["a"], K_PL["L"], holes, "K – ramię odstające (płaszczyzna zawiasu), kątownik 100×100×10, " + f"{K_PL.get('n', 4)} szt."
    if kind == "K_belka":
        holes = [(n, x, K_PL["L"] + z, d) for (n, x, z, d) in K_PL["holes_beam"]]
        return K_PL["a"], K_PL["L"], holes, "K – ramię na belce (2 × M12 do belki), x od grzbietu"


def write_dxf():
    os.makedirs(os.path.join(OUT, "DXF"), exist_ok=True)
    for kind in ("H", "Z", "S", "K_ramie", "K_belka"):
        w, h, holes, title = plate_outline(kind)
        doc = ezdxf.new("R2010")
        doc.units = ezdxf.units.MM
        doc.layers.add("CIECIE", color=7)
        doc.layers.add("OPIS", color=3)
        msp = doc.modelspace()
        msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True, dxfattribs={"layer": "CIECIE"})
        for (_, x, y, d) in holes:
            msp.add_circle((x, y), d / 2, dxfattribs={"layer": "CIECIE"})
        msp.add_text(title, height=4, dxfattribs={"layer": "OPIS"}).set_placement((0, h + 6))
        doc.saveas(os.path.join(OUT, "DXF", f"{kind}.dxf"))


def draw_plate(ax, ox, oy, kind, scale=1.0, dims=True, label=True):
    w, h, holes, title = plate_outline(kind)
    ax.add_patch(Rectangle((ox, oy), w * scale, h * scale, fill=True, fc="#eef1f4", ec="k", lw=0.8))
    for (n, x, y, d) in holes:
        ax.add_patch(Circle((ox + x * scale, oy + y * scale), d / 2 * scale, fill=False, ec="#c00000", lw=0.8))
        ax.plot([ox + x * scale - 3, ox + x * scale + 3], [oy + y * scale] * 2, "k-", lw=0.3)
        ax.plot([ox + x * scale] * 2, [oy + y * scale - 3, oy + y * scale + 3], "k-", lw=0.3)
        if dims:
            ax.text(ox + x * scale + d / 2 * scale + 1, oy + y * scale + 1, f"Ø{d:g}\n({x:g}; {y:g})", fontsize=6, color="#c00000")
    if label:
        ax.text(ox, oy + h * scale + 4, title, fontsize=7, weight="bold")
        ax.text(ox, oy - 6, f"wymiary {w:g} × {h:g} mm, otwory (x; y) od lewego dolnego rogu", fontsize=6)


def templates_pdf(path):
    with PdfPages(path) as pdf:
        layouts = [([("H", 5, 180), ("Z", 5, 50)], (150, 5)),
                   ([("S", 5, 110), ("K_ramie", 100, 148), ("K_belka", 100, 9)], (5, 30))]
        for page, (qx, qy) in layouts:
            fig = plt.figure(figsize=(210 / 25.4, 297 / 25.4))
            ax = fig.add_axes([0, 0, 1, 1])
            ax.set_xlim(0, 210)
            ax.set_ylim(0, 297)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.add_patch(Rectangle((qx, qy), 50, 50, fill=False, lw=0.8))
            ax.text(qx + 2, qy + 22, "KONTROLA:\nkwadrat\n50 × 50 mm", fontsize=6)
            ax.text(5, 290, "SZABLONY 1:1 – drukuj „rzeczywisty rozmiar / 100 %”, sprawdź kwadrat 50 mm", fontsize=7, weight="bold")
            ax.text(5, 285, "Przyklej na stal, wypunktuj środki otworów. Wszystkie płyty to PROSTOKĄTY – tniesz tylko prosto.", fontsize=6)
            for (k, x, y) in page:
                draw_plate(ax, x, y, k, 1.0, dims=True)
            pdf.savefig(fig)
            plt.close(fig)


# ------------------------------------------------------------------ RYSUNKI
def page_text(pdf, title, lines, fs=8):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.95, title, fontsize=15, weight="bold")
    y = 0.90
    for ln in lines:
        fig.text(0.04, y, ln, fontsize=fs, family="DejaVu Sans")
        y -= 0.028 if fs <= 8 else 0.033
    pdf.savefig(fig)
    plt.close(fig)


def page_section(pdf):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.set_title("Przekrój poprzeczny (sekcja A, w miejscu poprzeczki) – wymiary od osi trapu [mm]", fontsize=11, loc="left")
    for x in LONG_X:
        lane = abs(x) < 200
        ax.add_patch(Rectangle((x - 20, 0), 40, 100, fc="#cfd8e3" if lane else "#e6e9ee", ec="k", lw=0.8))
        ax.add_patch(Rectangle((x - 20 + (3 if lane else 2), (3 if lane else 2)), 40 - 2 * (3 if lane else 2),
                               100 - 2 * (3 if lane else 2), fc="white", ec="k", lw=0.4))
        ax.plot([x, x], [-60, 103], "k:", lw=0.4)
        ax.text(x, -75, f"{x:+.0f}", ha="center", fontsize=7)
    ax.add_patch(Rectangle((-WIDTH / 2, -60), WIDTH, 60, fc="#f3e2c7", ec="k", lw=0.8))
    ax.text(0, -45, "poprzeczka RHS 60×40×3 (6060), dł. 1190", ha="center", fontsize=8)
    ax.plot([-WIDTH / 2, WIDTH / 2], [101.5, 101.5], color="#6a6a6a", lw=2.5)
    ax.text(-590, 108, "siatka Al na całej szerokości (1 arkusz / sekcję)", fontsize=7)
    for sg in (1, -1):
        xg = sg * (X_LANE_OUT + 20)
        ax.add_patch(Polygon([(xg, 103), (xg, 143), (xg - sg * 4, 143), (xg - sg * 4, 107), (xg - sg * 40, 107), (xg - sg * 40, 103)],
                             fc="#9fb7d6", ec="k", lw=0.6))
    ax.text(150, 150, "prowadnica: kątownik 40×40×4 na siatce,\nśruba M8 w dół przez rurę zewnętrzną", fontsize=7)
    ax.annotate("", xy=(-X_LANE_OUT - 20 + 4, 165), xytext=(X_LANE_OUT + 20 - 4, 165), arrowprops=dict(arrowstyle="<->", lw=0.6))
    ax.text(0, 170, f"pas koła {2 * (X_LANE_OUT + 20 - 4):.0f} mm", ha="center", fontsize=8)
    ax.text(0, 40, "4 × RHS 100×40×3\nEN AW-6082-T6", ha="center", fontsize=7)
    ax.text(X_WALK + 30, 40, "RHS 100×40×2\n6060", fontsize=7)
    ax.plot([0, 0], [-60, 103], "r-", lw=0.6)
    ax.text(-600, 200, "Śruba na każdym skrzyżowaniu: M8×200 zamkowa (łeb na siatce) + JEDNA tuleja Ø12×1,5 dł. 159,5 przez rurę 100 i poprzeczkę 60.",
            fontsize=8)
    ax.text(-600, 185, "Szczeliny między rurami jezdnymi 40–50 mm (pod siatką). Siatka oparta co ≤ 190 mm.", fontsize=8)
    ax.set_xlim(-640, 640)
    ax.set_ylim(-100, 220)
    ax.set_aspect("equal")
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def page_plan(pdf):
    fig, axs = plt.subplots(1, 2, figsize=(11.69, 8.27))
    for ax, sec in zip(axs, "AB"):
        ax.set_title(f"Sekcja {sec} – widok z góry (bez siatki). s = " + ("od przyczepy" if sec == "A" else "od zawiasu środkowego"),
                     fontsize=9, loc="left")
        for x in LONG_X:
            lane = abs(x) < 200
            ax.add_patch(Rectangle((x - 20, 0), 40, L_SEC, fc="#cfd8e3" if lane else "#e6e9ee", ec="k", lw=0.6))
            if sec == "B":
                ax.add_patch(Rectangle((x - 20, L_SEC - SKOS), 40, SKOS, fc="none", ec="#c00000", lw=0.6, hatch="///"))
        for s in (CROSS_A if sec == "A" else CROSS_B):
            ax.add_patch(Rectangle((-WIDTH / 2, s - 20), WIDTH, 40, fc="#f3e2c7", ec="k", lw=0.6, alpha=0.9))
            ax.text(WIDTH / 2 + 10, s, f"P s={s:.0f}", fontsize=7, va="center")
        if sec == "B":
            ax.add_patch(Rectangle((-WIDTH / 2, TIE_B - 20), WIDTH, 40, fc="#ddd", ec="k", lw=0.6, ls="--"))
            ax.text(WIDTH / 2 + 10, TIE_B, f"T s={TIE_B:.0f}\n(pod spodem)", fontsize=7, va="center")
            ax.text(-WIDTH / 2, L_SEC - SKOS / 2, f"skos {SKOS:.0f} mm\n(leży na ziemi)", fontsize=7, color="#c00000")
        g = GUIDE_A if sec == "A" else GUIDE_B
        for sg in (1, -1):
            ax.add_patch(Rectangle((sg * (X_LANE_OUT + 20) - (40 if sg > 0 else 0), g[0]), 40, g[1] - g[0], fc="#9fb7d6", ec="k", lw=0.5, alpha=0.7))
            xo = sg * (X_LANE_OUT + 20)
            if sec == "A":
                ax.add_patch(Rectangle((xo if sg > 0 else xo - 6, -50), 6, 200, fc="#555", ec="k"))
                ax.add_patch(Rectangle((sg * (X_LANE_OUT - 20) - (6 if sg > 0 else 0), -50), 6, 200, fc="#555", ec="k"))
                ax.add_patch(Rectangle((xo if sg > 0 else xo - 6, L_SEC - 140), 6, 170, fc="#555", ec="k"))
                ax.add_patch(Rectangle((sg * (X_LANE_OUT - 20) - (6 if sg > 0 else 0), L_SEC - 140), 6, 170, fc="#555", ec="k"))
                ax.add_patch(Rectangle((sg * (X_WALK + 20) - (0 if sg > 0 else 8), S_PL["s0"]), 8, 80, fc="#a33", ec="k"))
                ax.plot([sg * 157], [-25], "ko", ms=3)
            else:
                ax.add_patch(Rectangle((xo + (6 if sg > 0 else -12), -30), 6, 170, fc="#555", ec="k"))
                ax.add_patch(Rectangle((sg * (X_LANE_OUT - 20) - (12 if sg > 0 else -6), -30), 6, 170, fc="#555", ec="k"))
        if sec == "A":
            ax.text(-560, L_SEC + 140, "H – płyty zawiasu przy przyczepie (s −50…150)\nZ – płyty zawiasu środkowego\nS – płyta sprężyny (czerwona) na C1",
                    fontsize=7)
        else:
            ax.text(-560, L_SEC + 140, "Z – płyty zawiasu środkowego sekcji B leżą NA ZEWNĄTRZ płyt A\n(podkładka 6 mm między płytą a rurą)", fontsize=7)
        ax.set_xlim(-700, 700)
        ax.set_ylim(L_SEC + 200, -100)
        ax.set_aspect("equal")
        ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def page_side(pdf, lift):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.set_title("Widok z boku: trap rozłożony (niebieski) i w pozycji do jazdy (szary). Wymiary od tylnej ściany belki i podłogi [mm]",
                 fontsize=9, loc="left")
    t0 = math.radians(lift[0]["deg"])
    pin = (PIN_Y, PIN_Z)

    def tr(th, u, v):
        p = rot(th, u, v)
        return (pin[0] + p[0], pin[1] + p[1])

    # przyczepa
    ax.add_patch(Rectangle((-600, -75), 600, 75, fc="#ddd", ec="k"))
    ax.add_patch(Rectangle((-50, -75), 50, 75, fc="#bbb", ec="k"))
    ax.plot([-600, 0], [0, 0], "k-", lw=2)
    ax.text(-580, 10, f"podłoga {H_FLOOR:.0f} nad ziemią", fontsize=8)
    ax.plot([-600, 2700], [-H_FLOOR, -H_FLOOR], color="#7a5", lw=2)
    # wspornik K
    ax.add_patch(Rectangle((0, -K_PL["L"]), K_PL["a"], K_PL["L"], fc="#c9a", ec="k", alpha=0.6))
    # trap rozlozony
    uM, vM = L_SEC + 25.0, -110.0

    def sect_poly(th, sec, folded=False):
        pts = []
        if sec == "A":
            loc = [(25, 25), (25 + L_SEC, 25), (25 + L_SEC, -75), (25, -75)]
            return [tr(th, u, v) for (u, v) in loc]
        loc = [(0, 135), (L_SEC, 135), (L_SEC - SKOS, 35), (0, 35)]
        out = []
        for (du, dv) in loc:
            if folded:
                du, dv = -du, -dv
            out.append((uM + du, vM + dv))
        return [tr(th, u, v) for (u, v) in out]

    ax.add_patch(Polygon(sect_poly(t0, "A"), fc="#cfe0f5", ec="#1f5aa6"))
    ax.add_patch(Polygon(sect_poly(t0, "B"), fc="#cfe0f5", ec="#1f5aa6"))
    th = math.radians(90)
    ax.add_patch(Polygon(sect_poly(th, "A"), fc="#ddd", ec="#555", alpha=0.8))
    ax.add_patch(Polygon(sect_poly(th, "B", folded=True), fc="#ddd", ec="#555", alpha=0.8))
    ax.plot(*pin, "ro")
    pm = tr(t0, uM, vM)
    ax.plot(*pm, "ro")
    ax.text(pm[0] + 20, pm[1] - 40, "zawias środkowy\n(sworzeń POD rurami,\ngóra rur styka się)", fontsize=7)
    ax.text(pin[0] + 30, pin[1] + 30, f"oś zawiasu: {PIN_Y:.0f} za belką,\n{-PIN_Z:.0f} pod podłogą", fontsize=7)
    # sprezyna
    for thx, col in ((t0, "#c00000"), (th, "#888")):
        eu = tr(thx, SPRING["eye_up_sz"][0] + 25, SPRING["eye_up_sz"][1] - 75)
        el = (pin[0] + SPRING["eye_low"][0], pin[1] + SPRING["eye_low"][1])
        ax.plot([el[0], eu[0]], [el[1], eu[1]], color=col, lw=3, alpha=0.7)
    ax.text(300, -260, f"sprężyna gazowa 460/200 mm, {SPRING['F1']:.0f} N (×2)\noczko dolne na wsporniku K, górne na płycie S", fontsize=7, color="#c00000")
    ax.text(150, 1300, f"do jazdy: wys. ok. {H_FLOOR + 25 + L_SEC:.0f} nad ziemią,\nwystaje ok. 330 mm za belkę", fontsize=8)
    ax.text(1400, -300, f"kąt najazdu {ALPHA:.1f}°", fontsize=9)
    ax.set_xlim(-650, 2750)
    ax.set_ylim(-560, 1450)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    pdf.savefig(fig)
    plt.close(fig)


def page_hinges(pdf):
    fig, axs = plt.subplots(1, 2, figsize=(11.69, 8.27))
    ax = axs[0]
    ax.set_title("Zawias przy przyczepie – widok z boku na rurę L1\n(układ rury: s od końca rury, z od spodu)", fontsize=9, loc="left")
    ax.add_patch(Rectangle((0, 0), 300, 100, fc="#cfd8e3", ec="k"))
    ax.add_patch(Rectangle((H_PL["s0"], H_PL["z0"]), H_PL["w"], H_PL["h"], fc="#999", ec="k", alpha=0.6))
    for (n, s, z, d) in H_PL["holes"]:
        ax.add_patch(Circle((s, z), d / 2, fill=False, ec="#c00000"))
        ax.text(s + d / 2 + 2, z - 4, f"{n} Ø{d:g}\ns={s:g}, z={z:g}", fontsize=6)
    ax.text(-110, -75, "Na rurze L1: płyta H po OBU stronach (wewn. i zewn.), 2 × M12 + tuleje Ø18×2,5 dł. 40.\n"
            "Sworzeń M20 (25 mm pod pokładem, 25 mm przed końcem rury) przechodzi:\nH wewn. – (pusto) – H zewn. – wspornik K.\n"
            "Blokada Ø12 do jazdy: przez K i H zewn. (otwór „blok”).", fontsize=7, va="top")
    ax.set_xlim(-120, 320)
    ax.set_ylim(-170, 130)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax = axs[1]
    ax.set_title("Zawias środkowy – widok z boku na styk rur L1 | L3\n(d od styku, z od spodu rur)", fontsize=9, loc="left")
    ax.add_patch(Rectangle((-300, 0), 299, 100, fc="#cfd8e3", ec="k"))
    ax.add_patch(Rectangle((1, 0), 299, 100, fc="#dfe8d3", ec="k"))
    ax.text(-250, 80, "sekcja A", fontsize=8)
    ax.text(200, 80, "sekcja B", fontsize=8)
    ax.add_patch(Rectangle((-Z_PL["d0"] - Z_PL["w"], Z_PL["z0"]), Z_PL["w"], Z_PL["h"], fc="#999", ec="k", alpha=0.5))
    ax.add_patch(Rectangle((Z_PL["d0"], Z_PL["z0"]), Z_PL["w"], Z_PL["h"], fc="#666", ec="k", alpha=0.5))
    for sg in (-1, 1):
        for (n, d, z, dd) in Z_PL["holes"]:
            ax.add_patch(Circle((sg * d, z), dd / 2, fill=False, ec="#c00000"))
    for (n, d, z, dd) in Z_PL["holes"][1:]:
        ax.text(d - 10, z + 14, f"d={d:g}\nz={z:g}", fontsize=6)
    ax.text(12, -40, "sworzeń M20\nd=0, z=−35", fontsize=6)
    ax.text(-300, -75, "Płyty Z sekcji A: na ściankach rury L1 (wewn. + zewn.).\n"
            "Płyty Z sekcji B: na rurze L3 przez podkładkę 6 mm → leżą NA ZEWNĄTRZ płyt A.\n"
            "Sworzeń M20 (35 mm pod rurami) przechodzi przez 4 płyty.\n"
            "Rozłożony: górne krawędzie rur A i B STYKAJĄ SIĘ (przenoszą ściskanie).\n"
            "Składanie: B obraca się w dół, pod sekcję A.", fontsize=7, va="top")
    ax.set_xlim(-320, 320)
    ax.set_ylim(-200, 130)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    pdf.savefig(fig)
    plt.close(fig)


def page_tube(pdf, pid, name, prof, mat, q, skos):
    holes = holes_long(pid)
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.94, f"{pid} – {name}", fontsize=13, weight="bold")
    fig.text(0.04, 0.905, f"{prof}  {mat}  L = {L_SEC:.0f} mm  ilość {q} szt.", fontsize=9)
    ax = fig.add_axes([0.06, 0.45, 0.9, 0.42])
    faces = [("góra", 40, 0), ("bok", 100, 60), ("dół", 40, 180)]
    for (fn, hgt, y0) in faces:
        if skos and fn == "bok":
            ax.add_patch(Polygon([(0, y0), (L_SEC, y0), (L_SEC - SKOS, y0 + hgt), (0, y0 + hgt)], fc="#eef1f4", ec="k"))
        elif skos and fn == "dół":
            ax.add_patch(Rectangle((0, y0), L_SEC - SKOS, hgt, fc="#eef1f4", ec="k"))
        else:
            ax.add_patch(Rectangle((0, y0), L_SEC, hgt, fc="#eef1f4", ec="k"))
        ax.text(-60, y0 + hgt / 2, fn, fontsize=8, va="center")
        for (s, w, z, d, _) in holes:
            if (w == "g/d" and fn in ("góra", "dół")) or (w == "dół" and fn == "dół"):
                if w == "dół":
                    for dx in (-10, 10):
                        ax.add_patch(Circle((s, y0 + 20 + dx), 2.5, fill=False, ec="#c00000"))
                else:
                    ax.add_patch(Circle((s, y0 + 20), d / 2, fill=False, ec="#c00000"))
            if w == "bok" and fn == "bok":
                ax.add_patch(Circle((s, y0 + 100 - z), d / 2, fill=False, ec="#c00000"))
    ax.set_xlim(-80, L_SEC + 20)
    ax.set_ylim(240, -20)
    ax.set_aspect("equal")
    ax.axis("off")
    txt = "Otwory: s od końca " + ("przy przyczepie" if pid in ("L1", "L1L", "L1P", "L2", "C1", "C2") else "przy zawiasie środkowym") + \
          ". „g/d” = przez górę i dół w osi ścianki (20/20). „bok” = przez oba boki, z od spodu rury."
    fig.text(0.04, 0.42, txt, fontsize=8)
    if skos:
        fig.text(0.04, 0.39, f"ŚCIĘCIE PRZY ZIEMI: góra na pełnej długości {L_SEC:.0f}; dół utnij na {L_SEC - SKOS:.0f}; boki tnij prostą ukośną "
                             f"od ({L_SEC - SKOS:.0f}, dół) do ({L_SEC:.0f}, góra) – skos {SKOS:.0f} mm, {ALPHA:.1f}°. Pod skos pasek gumy EPDM.",
                 fontsize=8, color="#c00000", weight="bold")
    rows = [[f"{s:.0f}", w, "–" if z is None else f"{z:.0f}", f"{d:g}", n] for (s, w, z, d, n) in holes]
    tab = fig.add_axes([0.04, 0.03, 0.92, 0.33])
    tab.axis("off")
    t = tab.table(cellText=rows, colLabels=["s [mm]", "ścianka", "z od spodu", "Ø", "do czego"], loc="upper left",
                  colWidths=[0.1, 0.1, 0.1, 0.08, 0.5])
    t.auto_set_font_size(False)
    t.set_fontsize(7)
    pdf.savefig(fig)
    plt.close(fig)


def page_cross(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.94, "P – poprzeczka RHS 60×40×3 (6060), L = 1190, 3 szt.  |  T – listwa Al 40×5, L = 1190, 1 szt.  |  G1/G2 – prowadnice",
             fontsize=11, weight="bold")
    ax = fig.add_axes([0.05, 0.55, 0.9, 0.3])
    ax.add_patch(Rectangle((0, 0), WIDTH, 40, fc="#f3e2c7", ec="k"))
    ax.text(-40, 20, "góra/dół", fontsize=8, va="center")
    for x in LONG_X:
        ax.add_patch(Circle((x + WIDTH / 2, 20), 6.25, fill=False, ec="#c00000"))
        ax.text(x + WIDTH / 2, 50, f"{x + WIDTH / 2:.0f}", ha="center", fontsize=7)
    ax.set_xlim(-60, WIDTH + 20)
    ax.set_ylim(70, -20)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.text(0.05, 0.52, "P: 8 otworów Ø12,5 przez górę i dół, w osi ścianki 40 mm. Wymiary od lewego końca. "
                         "Tuleja Ø12×1,5 dł. 159,5 przechodzi przez podłużnicę (100) i poprzeczkę (60).", fontsize=8)
    fig.text(0.05, 0.49, "T: te same położenia, w każdym miejscu 2 otwory Ø4,9 (±10 mm w poprzek listwy... wzdłuż listwy) – nity 4,8 w dno podłużnic B.",
             fontsize=8)
    ga = [s - GUIDE_A[0] for s in sorted(GUIDE_BOLTS_A + CROSS_A)]
    gb = [s - GUIDE_B[0] for s in sorted(GUIDE_BOLTS_B + CROSS_B)]
    fig.text(0.05, 0.43, f"G1 (sekcja A): kątownik Al 40×40×4, L = {GUIDE_A[1] - GUIDE_A[0]:.0f}, 2 szt. Otwory Ø9 w półce poziomej, "
                         f"20 mm od grzbietu, od końca przy przyczepie: {', '.join(f'{v:.0f}' for v in ga)}", fontsize=8)
    fig.text(0.05, 0.40, f"G2 (sekcja B): kątownik Al 40×40×4, L = {GUIDE_B[1] - GUIDE_B[0]:.0f}, 2 szt. Otwory Ø9 od końca przy zawiasie: "
                         f"{', '.join(f'{v:.0f}' for v in gb)}", fontsize=8)
    fig.text(0.05, 0.37, "Prowadnice leżą NA siatce nad rurą zewnętrzną, pionową półką na zewnątrz (x = ±141…145). Końce półki pionowej ściąć 45°.",
             fontsize=8)
    pdf.savefig(fig)
    plt.close(fig)


def page_plates(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.95, f"Płyty stalowe S235 – SAME PROSTOKĄTY (tylko proste cięcia). Pełna skala: {TEMPL_NAME} / DXF",
             fontsize=11, weight="bold")
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.88])
    draw_plate(ax, 0, 230, "H")
    draw_plate(ax, 260, 230, "Z")
    draw_plate(ax, 0, 20, "S")
    draw_plate(ax, 140, 20, "K_ramie")
    draw_plate(ax, 290, 20, "K_belka")
    ax.set_xlim(-10, 470)
    ax.set_ylim(-20, 370)
    ax.set_aspect("equal")
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def page_calc(pdf, rows, lift, lift0):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.95, "Obliczenia (wytężenie ≤ 1,0 = OK)", fontsize=13, weight="bold")
    tab = fig.add_axes([0.02, 0.05, 0.96, 0.87])
    tab.axis("off")
    cells = [[r["nazwa"][:95], f"{r['obciazenie']}", f"{r['nosnosc']}", r["jedn"], f"{r['wytezenie']:.2f}"] for r in rows]
    t = tab.table(cellText=cells, colLabels=["element", "obciążenie", "nośność", "", "wytęż."], loc="upper left",
                  colWidths=[0.70, 0.08, 0.08, 0.05, 0.06])
    t.auto_set_font_size(False)
    t.set_fontsize(6.5)
    for i, r in enumerate(rows, start=1):
        if r["wytezenie"] > 1.0:
            for j in range(5):
                t[i, j].set_facecolor("#dddddd" if r["nazwa"].startswith("[INFO]") else "#f5b7b1")
    pdf.savefig(fig)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.plot([r["deg"] for r in lift], [r["user_kg"] for r in lift], label=f"ze sprężynami 2 × {SPRING['F1']:.0f} N")
    ax.plot([r["deg"] for r in lift0], [r["user_kg"] for r in lift0], label="bez sprężyn")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("kąt sekcji A [°] (ujemny = rozłożony na ziemi, 90 = pionowo)")
    ax.set_ylabel("siła na końcu sekcji A, prostopadle [kg]")
    ax.set_title("Podnoszenie trapu do jazdy (podnosisz za zawias środkowy, B wlecze się, potem wisi)", fontsize=10, loc="left")
    ax.grid(alpha=0.3)
    ax.legend()
    pdf.savefig(fig)
    plt.close(fig)


# ------------------------------------------------------------------ MAIN
def main():
    (mA, cAs, cAz), (mB, cBs, cBz) = masses()
    rows = calcs(mA, mB)
    lift = lift_table(mA, cAs, cAz, mB, cBs, cBz, True)
    lift0 = lift_table(mA, cAs, cAz, mB, cBs, cBz, False)
    bom = build_bom()
    bolts, sleeves = build_bolts()

    with open(os.path.join(OUT, "lista_czesci.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["nr", "nazwa", "szt.", "materiał", "wymiar", "masa szt. [kg]", "otwory", "wykonanie", "gdzie"])
        for b in bom:
            w.writerow([b["pid"], b["name"], b["qty"], b["material"], b["size"], b["mass"], b["holes"], b["how"], b["where"]])
    with open(os.path.join(OUT, "lista_srub.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["śruba / element", "rodzaj", "szt.", "gdzie"])
        for b in bolts:
            w.writerow(b)
        for (tb, L, q, why) in sleeves:
            w.writerow([f"tuleja stal {tb} dł. {L:g}", "rura stalowa bezszwowa ocynk / cynk w sprayu", q, why])
    with open(os.path.join(OUT, "obliczenia.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["element", "obciążenie", "nośność", "jedn.", "wytężenie", "uwagi"])
        for r in rows:
            w.writerow([r["nazwa"], r["obciazenie"], r["nosnosc"], r["jedn"], r["wytezenie"], r["uwagi"]])

    tube_m = lambda L: math.ceil(L / 1000 * 10) / 10
    buy = [
        ("Rura Al prostokątna 100×40×3, EN AW-6082-T6 (PA4) – NIE 6060", "8 × 1250 mm = 2 sztangi 6 m",
         "rury jezdne L1–L4 (z 1 sztangi 4 kawałki)"),
        ("Rura Al prostokątna 100×40×2, 6060-T6", "8 × 1250 mm = 2 sztangi 6 m", "podłużnice chodnika i krawędzi C1–C3"),
        ("Rura Al prostokątna 60×40×3, 6060-T6", f"3 × {WIDTH:.0f} mm (3,6 m)", "poprzeczki P"),
        ("Kątownik Al 40×40×4, 6060", f"2 × {GUIDE_A[1] - GUIDE_A[0]:.0f} + 2 × {GUIDE_B[1] - GUIDE_B[0]:.0f} mm (3,7 m)", "prowadnice G1/G2"),
        ("Płaskownik Al 40×5", f"1 × {WIDTH:.0f} mm", "listwa T"),
        ("Siatka cięto-ciągniona ALUMINIOWA ok. 43×13×3×2 (~2,5 kg/m²), arkusz 1250×2500, LWD wzdłuż boku 1250",
         "1 arkusz → 2 × 1190×1250", "pokład. Siatka niesie TYLKO stopy (koło jedzie po rurach). Przęsła ≤ 190 mm."),
        ("Płaskownik stal S235 80×6", "4 × 200 mm (0,85 m)", "płyty H"),
        ("Płaskownik stal S235 100×6", "8 × 170 mm (1,4 m)", "płyty Z"),
        ("Płaskownik stal S235 80×8", "2 × 150 mm (0,3 m)", "płyty S"),
        ("Kątownik stal 100×100×10", "4 × 130 mm (0,55 m)", "wsporniki K na belce przyczepy"),
        ("Rura stal bezszwowa Ø12×1,5", f"{tube_m(24 * 162.5 + 12 * 102.5)} m", "tuleje M8 (160 i 100)"),
        ("Rura stal bezszwowa Ø18×2,5", f"{tube_m(16 * 43 + 8 * 53)} m", "tuleje M12 (40 i 50)"),
        ("Rura stal Ø20×4", "0,1 m", "dystanse oczek sprężyn (12 i 18 mm)"),
        ("Sprężyna gazowa 460 mm / skok 200 mm / 1600 N, oczka Ø12 (M12)", "2", "zalecane – bez nich ok. 35–40 kg na końcu trapu"),
        ("Zapięcie dźwigniowe z regulowanym kabłąkiem, zasięg ≥ 180 mm, ≥ 200 daN (lub pas z grzechotką 25 mm)", "2",
         "spina złożone sekcje do jazdy"),
        ("Pasek gumy EPDM 3–5 mm × 40 mm", "ok. 4 m", "pod skosy przy ziemi (8 × 0,5 m)"),
        ("Podkładki izolujące (nylon/EPDM) pod płyty stalowe + pasta cynkowa / Duralac", "~30 + 1 tubka",
         "stal ↔ aluminium – przeciw korozji galwanicznej"),
        ("Śruby, nakrętki, nity, wkręty – wg lista_srub.csv", "", ""),
    ]
    with open(os.path.join(OUT, "lista_zakupow.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pozycja", "ilość", "uwagi"])
        for b in buy:
            w.writerow(b)

    write_dxf()
    templates_pdf(os.path.join(OUT, "szablony_1do1_v2.pdf"))

    n_holes = sum(b["holes"] * b["qty"] for b in bom)
    worst = max([r for r in rows if not r["nazwa"].startswith("[INFO]")], key=lambda r: r["wytezenie"])
    summary = dict(
        alpha_deg=round(ALPHA, 2), skos_mm=round(SKOS, 1), masa_A=round(mA, 1), masa_B=round(mB, 1),
        masa_trapu=round(mA + mB, 1), masa_wspornikow_K=round(4 * 1.9e3 * 130 * RHO_ST, 1),
        cgA=[round(cAs), round(cAz)], cgB=[round(cBs), round(cBz)],
        max_wysilek_ze_sprezynami_kg=max(r["user_kg"] for r in lift), max_wysilek_bez_sprezyn_kg=max(r["user_kg"] for r in lift0),
        moment_rozlozony_Nm=lift[0]["Tg"] + lift[0]["Ts"], moment_pion_Nm=lift[-1]["Tg"] + lift[-1]["Ts"],
        sprezyna_L_min=min(r["L"] for r in lift), sprezyna_L_max=max(r["L"] for r in lift),
        najwieksze_wytezenie=dict(element=worst["nazwa"], wartosc=worst["wytezenie"]),
        typy_czesci=len(bom), sztuk_czesci=sum(b["qty"] for b in bom), otwory=n_holes,
        typy_srub=len(bolts), typy_tulei=len(sleeves), tuleje_szt=sum(s[2] for s in sleeves),
    )
    with open(os.path.join(OUT, "trap_v2_dane.json"), "w", encoding="utf-8") as f:
        json.dump(dict(podsumowanie=summary, obliczenia=rows, czesci=bom, podnoszenie=lift, podnoszenie_bez_sprezyn=lift0),
                  f, ensure_ascii=False, indent=1)

    with PdfPages(os.path.join(OUT, "rysunki_trap_v2.pdf")) as pdf:
        page_text(pdf, "Trap aluminiowy 2,5 × 1,19 m – WERSJA UPROSZCZONA (bez spawania, bez gięcia)", [
            f"Dwie sekcje po {L_SEC:.0f} mm, składane na zawiasie środkowym, przykręcone do tylnej belki. Masa trapu ok. {mA + mB:.0f} kg "
            f"(A {mA:.0f} kg, B {mB:.0f} kg) + wsporniki K {summary['masa_wspornikow_K']:.1f} kg.",
            f"Policzony dla podłogi {H_FLOOR:.0f} mm: kąt {ALPHA:.1f}°. Koło {WHEEL_KG:.0f} kg (60 % z 350 + 105 kg) ×1,5 ×1,5; stopa 105 kg ×1,5 ×1,5.",
            "",
            "CO JEST PROSTSZE niż w poprzedniej wersji:",
            "  • 5 profili Al zamiast 7; wszystkie podłużnice mają tę samą wysokość 100 mm – leżą wprost na poprzeczkach (nie ma 30 tulejek dystansowych D1).",
            "  • Na każdym skrzyżowaniu ta sama śruba M8×200 i JEDNA tuleja dł. 159,5 (zamiast 9 rodzajów tulei – teraz 4).",
            "  • Płyty stalowe: 4 rodzaje i wszystkie to PROSTOKĄTY z płaskownika/kątownika – zero gięcia (stary M2), zero ośmiokątów.",
            "  • Zawias środkowy: 8 IDENTYCZNYCH płyt Z (wierć w pakiecie), sworzeń = śruba M20×110 8.8. Zawias przy przyczepie: płyty H + odcinek kątownika K.",
            "  • Te same 4 wsporniki K służą do zawiasu i do sprężyn. Sworzeń wszystkich zawiasów – ta sama śruba M20.",
            "  • Siatka w jednym kawałku na sekcję (z 1 arkusza 1250×2500), przykręcana wkrętami samowiercącymi – bez nitownicy do siatki.",
            "  • Bez pręta gwintowanego z 18 nakrętkami na końcu B – zamiast niego płaskownik nitowany od spodu.",
            "  • Prowadnice koła = kątownik położony na siatce (nie potrzeba osobnej podłużnicy pod prowadnicą).",
            "",
            "ZASADA DZIAŁANIA: koło jedzie po 4 rurach 100×40×3 z 6082-T6 (pas 282 mm między prowadnicami). Siatka niesie tylko stopy.",
            "Zawias środkowy ma sworzeń POD rurami; po rozłożeniu górne krawędzie rur stykają się – zawias przenosi zginanie bez blokad.",
            "Składanie: podnosisz sekcję A za zawias środkowy, B wlecze się i potem sama zawisa pod A. W pionie: blokada Ø12 przez K i H.",
            "",
            "ZASADY WYKONANIA:",
            "  1. Rury jezdne L1–L4 MUSZĄ być z EN AW-6082-T6 (PA4). Z 6060 trap jest za słaby (patrz obliczenia).",
            "  2. Otwory pod tuleje: Ø tulei + 0,5 mm (Ø12,5 dla Ø12, Ø18,5 dla Ø18). Tuleja = wysokość/szerokość profilu – nie zgniata aluminium.",
            "  3. Płyty H i Z wierć w pakiecie (ścisk + wiertarka stołowa). Otwory w rurach pod płyty: zaznacz PRZEZ płytę jako szablon.",
            "  4. Zawias środkowy: ułóż L1 i L3 czołami na płaskiej podłodze (górne krawędzie stykają się), włóż sworzeń, dopiero wtedy wierć rury.",
            "  5. Stal ↔ aluminium: pasta cynkowa / Duralac i podkładki izolujące. Płyty stalowe ocynkuj (spray lub ogniowo).",
            "  6. Śruby 8.8 ocynk, nakrętki samohamowne. M8 20 N·m, M12 40 N·m (na tulejach). Sworznie M20 – NIE dokręcać, mają się obracać.",
            f"  7. Wsporniki K i śruby do belki są dla PRZYKŁADOWEJ belki 50×75 – podaj swój przekrój belki i wysokość podłogi przed wierceniem.",
        ], fs=8)
        page_section(pdf)
        page_plan(pdf)
        page_side(pdf, lift)
        page_hinges(pdf)
        for pid, name, prof, mat, q, xs, skos, sec in LONG_PARTS:
            page_tube(pdf, pid, name, prof, mat, q, skos)
        page_cross(pdf)
        page_plates(pdf)
        page_calc(pdf, rows, lift, lift0)

    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        flag = "  <-- !!!" if r["wytezenie"] > 1 and not r["nazwa"].startswith("[INFO]") else ""
        print(f"{r['wytezenie']:5.2f}  {r['nazwa']}{flag}")


if __name__ == "__main__":
    main()
