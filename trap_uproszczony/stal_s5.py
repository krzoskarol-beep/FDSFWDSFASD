# -*- coding: utf-8 -*-
"""
Trap STALOWY S5 – lekki i tani: chodnik 340 mm tylko z LEWEJ strony, szerokość 630 mm, bez spawania.
Komplet w katalogu stal_S5/: rysunki z tabelami otworów, szablony 1:1, DXF, listy, obliczenia,
model 3D glTF z otworami i śrubami, zrzuty, kontrola otworów, strona z modelem.

  python3 stal_s5.py

LEWA strona = patrząc od ziemi na przyczepę (od tej strony pchasz motocykl, od strony stopki) = x > 0.
"""
import copy, csv, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, Polygon

import generuj as g
import podglad3d as p3
import stal
import sily

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stal_S5")
V = stal.VARIANTS["S5L"]
XW, XE = stal.S5_WALK, stal.S5_EDGE                    # podłużnice chodnika C1 / C2: x = 305 / 465
L = g.L_SEC
X0, X1 = -(g.X_LANE_OUT + 20), XE + 20                 # -145 … +485
WID = X1 - X0                                         # 630
XS = [-g.X_LANE_OUT, -g.X_LANE_IN, g.X_LANE_IN, g.X_LANE_OUT, XW, XE]
LANE_P, WALK_P, CROSS_P = V["lane"][0], V["walk"][0], V["cross"][0]

LONG_INFO = {
    "L1": ("L1", "Rura jezdna zewnętrzna sekcji A – OBIE IDENTYCZNE (lewa i prawa; prawa niesie płytę S sprężyny, w lewej te 2 otwory zaślepione śrubą)",
           LANE_P, "S355J2H", 2, "±125", False, "A"),
    "L2": ("L2", "Rura jezdna wewnętrzna sekcji A", LANE_P, "S355J2H", 2, "±45", False, "A"),
    "L3": ("L3", "Rura jezdna zewnętrzna sekcji B (zawias Z, skos przy ziemi)", LANE_P, "S355J2H", 2, "±125", True, "B"),
    "L4": ("L4", "Rura jezdna wewnętrzna sekcji B (skos przy ziemi)", LANE_P, "S355J2H", 2, "±45", True, "B"),
    "C1": ("C1", "Podłużnica chodnika sekcji A (z płytą sprężyny S)", WALK_P, "S235JRH", 1, f"+{XW:.0f}", False, "A"),
    "C2": ("C2", "Podłużnica krawędzi sekcji A (lewa krawędź, z płytą Z zawiasu chodnika)", WALK_P, "S235JRH", 1, f"+{XE:.0f}", False, "A"),
    "C3": ("C3", "Podłużnica chodnika / krawędzi sekcji B (skos; obie identyczne – na krawędzi płyta Z, w drugiej zaślepka)",
           WALK_P, "S235JRH", 2, f"+{XW:.0f}, +{XE:.0f}", True, "B"),
}
LONGS = [(-125.0, "L1", "L3"), (-45.0, "L2", "L4"), (45.0, "L2", "L4"), (125.0, "L1", "L3"), (XW, "C1", "C3"), (XE, "C2", "C3")]
S_M12 = [(s, z) for (n, s, z, d) in g.S_PL["holes"] if n == "M12"]
Z_M12 = [(d, z) for (n, d, z, dd) in g.Z_PL["holes"] if n == "M12"]
# po analizie dróg sił (sily.py): 4 poprzeczki (B: 260 i 650 zamiast listwy T), śruby prowadnic omijają nakrętki po złożeniu
CROSS_B_S5 = [260.0, 650.0]
GUIDE_BOLTS_A_S5 = [200.0, 540.0, 1040.0]
GUIDE_BOLTS_B_S5 = [180.0, 450.0]


_G_HOLES = g.holes_long


def holes_long(pid):
    h = list(_G_HOLES(pid))
    if pid == "L1":
        for (s, z) in S_M12:
            h.append((s, "bok", z, 18.5, "płyta S prawej sprężyny (w rurze lewej: zaślepka M12×60 + tuleja Ø18)"))
    if pid == "C2":
        for (d, z) in Z_M12:
            h.append((L - d, "bok", z, 18.5, "płyta Z zawiasu chodnika – M12 + tuleja Ø18"))
    if pid == "C3":
        for (d, z) in Z_M12:
            h.append((d, "bok", z, 18.5, "płyta Z zawiasu chodnika (w C3 x +" + f"{XW:.0f}" + ": zaślepka M12×60 + tuleja Ø18)"))
    return sorted(h, key=lambda r: r[0])


def side_key(grp, s, z, sg, xc):
    """lewa rura L1 ma otwory płyty S w tym samym (s, z) co podłużnica C1 – osobny klucz otworu"""
    k = f"{grp}h:{s:g}:{z:g}:{sg}"
    if grp == "A" and xc == g.X_LANE_OUT and (s, z) in S_M12:
        return k + ":L1"
    if xc in (XW, XE) and (s, z) in ([(L - d, zz) for (d, zz) in Z_M12] if grp == "A" else Z_M12):
        return k + f":C{xc:.0f}"
    return k


def layout():
    return dict(
        key="S5", longs=LONGS, xmin=X0, xmax=X1, holes_long=holes_long, long_info=LONG_INFO, side_key=side_key,
        s_dummy=[dict(sg=1, inner=g.X_LANE_OUT - 20, face=g.X_LANE_OUT + 20, tube="L1 lewa (x +125)",
                      key=lambda s, z: f"Ah:{s:g}:{z:g}:1:L1")],
        cross_txt="RHS 60×40×3 S235JRH na płasko",
        walk_hinge=dict(x=XE, key=lambda grp, s, z: f"{grp}h:{s:g}:{z:g}:1:C{XE:.0f}"),
        walk_plugs=[dict(grp="B", x=XW, key=lambda s, z: f"Bh:{s:g}:{z:g}:1:C{XW:.0f}")],
        walk_rest=[XW, XE], tie_txt="płaskownik stal 40×5", mesh_txt="siatka stal ocynk cięto-ciągniona ~30×12×2×1,5",
        guide=(40.0, 3.0, "kątownik stal 40×40×3"),
        single_plates=V["single_plates"],
        s_plates=[dict(sg=1, face=XW + 20, inner=XW - 20, tube="C1"),
                  dict(sg=-1, face=g.X_LANE_OUT + 20, inner=g.X_LANE_OUT - 20, tube="L1 prawa (x −125)")],
        springs=[dict(sg=1, s_face=XW + 20, s_sp=22.0, k_xa=XW + 24, k_nm="sprężyna", k_sp=16.0),
                 dict(sg=-1, s_face=g.X_LANE_OUT + 20, s_sp=25.0, k_xa=152.0, k_nm="zawias", k_sp=16.0)],
        kbr=[("zawias", 152.0, -1), ("zawias", 152.0, 1), ("sprężyna", XW + 24, 1)],
        eye=dict(size=12, w=10.0, r=11.0, sleeve="Ø22×5", body=14.0, rod=7.0, F=f"{SPR['F1_N']} N"),
        colors=("#8a96a3", "#b9c0c8", "#c9a77a", "#3f6fb0"),
    )


# ------------------------------------------------------------------ dane wariantu
(mA, cAs, cAz), (mB, cBs, cBz) = stal.masses(V)
SPR, LIFT = stal.pick_springs(mA, (cAs, cAz), mB, (cBs, cBz), V["spring_max"])
LIFT0 = stal.lift(mA, (cAs, cAz), mB, (cBs, cBz), 0, 0)
ROWS = stal.calcs(V, mA, mB, SPR["F1_N"])


def s5_extra_rows():
    rows = []
    Pd = g.WHEEL_KG * g.G / 1000 * g.PHI * g.GAMMA_F             # kN, koło obliczeniowo
    Fl = 0.3 * Pd                                                 # boczne pchnięcie opony
    hg, tg, beff = 37.0, 3.0, 300.0                               # wys. półki nad siatką, grubość, współpracująca długość
    sg_ = Fl * 1e3 * hg / (beff * tg ** 2 / 6)
    rows.append(dict(nazwa="Prowadnica – kątownik 40×40×3 S235: zginanie półki pionowej od bocznego pchnięcia opony", obciazenie=round(sg_, 1),
                     nosnosc=235.0, jedn="MPa", wytezenie=round(sg_ / 235, 3), uwagi="0,3 × koło obl. na wys. 37 mm, współpracuje ~300 mm półki"))
    Ft = Fl * hg / 20.0
    FtR = 0.9 * 800 * 36.6 / g.GM2 / 1e3
    rows.append(dict(nazwa="Prowadnica – śruba M8 8.8 rozrywana (dźwignia 37/20 mm)", obciazenie=round(Ft, 2), nosnosc=round(FtR, 2), jedn="kN",
                     wytezenie=round(Ft / FtR, 3), uwagi="cała siła boczna na jednej śrubie"))
    rows.append(dict(nazwa="[INFO] Siatka – koło zamiast stopy (dlaczego są prowadnice)", obciazenie=round(Pd, 2),
                     nosnosc=round(g.FOOT_KG * g.G / 1000 * g.PHI * g.GAMMA_F, 2), jedn="kN",
                     wytezenie=round(Pd / (g.FOOT_KG * g.G / 1000 * g.PHI * g.GAMMA_F), 3), uwagi="siatka liczona na stopę 105 kg; koło to 2,6 × więcej"))
    # rura L1 osłabiona 2 otworami Ø18,5 płyty S (w obu rurach – są identyczne)
    W = V["lane"][1]["W"]; I = W * 50.0; t = 2.0; d = 18.5
    I_net = I - 2 * sum(t * d * y * y + t * d ** 3 / 12 for y in (25.0, -25.0))
    Lsp = 2 * L + 25.0; a = 259.0 + 25.0
    Mw = Pd * a * (Lsp - a) / Lsp                                   # kN·m·1e3 (kN·mm)
    sgn = Mw * 1e3 * 50.0 / I_net
    rows.append(dict(nazwa="Rura L1 w miejscu 2 otworów Ø18,5 płyty S (całe koło na jednej rurze, s = 259)", obciazenie=round(sgn, 1),
                     nosnosc=355.0, jedn="MPa", wytezenie=round(sgn / 355, 3),
                     uwagi=f"przekrój netto {I_net / I * 100:.0f} % pełnego; w lewej rurze otwory zaślepione tuleją i śrubą"))
    # pas transportowy – druga, niezależna blokada (gdy zapomnisz sworzni Ø12)
    hcg = (mA * (cAs + 25.0) + mB * (L - cBs + 25.0)) / (mA + mB)
    Mo = SPR["moment_pion_Nm"] + 0.5 * 1.5 * (mA + mB) * g.G * hcg / 1000
    Fp = Mo / ((g.CROSS_A[1] + 25.0) / 1000 * math.cos(math.radians(45))) / 1000
    rows.append(dict(nazwa="Pas transportowy 25 mm (LC 400 daN) – trzyma trap bez sworzni Ø12", obciazenie=round(Fp, 2), nosnosc=4.0, jedn="kN",
                     wytezenie=round(Fp / 4.0, 3), uwagi=f"przyspieszenie 0,5 g ×1,5 do tyłu + sprężyny; pas na poprzeczce P (s = 830), 45° w dół do przodu"))
    Rs = (Pd * (2 * L - 100) / (2 * L) + g.GAMMA_G * (mA + mB) * g.G / 1000 / 2) / 2      # reakcja na stronę [kN]
    Vh = math.hypot(Rs * 105 / 80, Rs / 2)
    Vr = 0.6 * 800 * 84.3 / 1.25 / 1e3
    rows.append(dict(nazwa="Zawias przy przyczepie: śruba M12 płyty H (jedna płyta, jednocięta)", obciazenie=round(Vh, 2),
                     nosnosc=round(Vr, 2), jedn="kN", wytezenie=round(Vh / Vr, 3), uwagi="mimośród 105 mm, rozstaw 80 mm"))
    Fb = 2.5 * min(25 / 63, 1) * 360 * 20 * 6 / 1.25 / 1e3
    rows.append(dict(nazwa="Zawias przy przyczepie: sworzeń Ø20 – docisk w płycie H 6 mm", obciazenie=round(Rs, 2), nosnosc=round(Fb, 2), jedn="kN",
                     wytezenie=round(Rs / Fb, 3), uwagi="koło przy przyczepie + ciężar trapu"))
    Fs = SPR["F1_N"] * 1.3 * 1.5 / 1000
    cap = 2.5 * min(40 / 55.5, 1) * 470 * 18 * 2 / 1.25 / 1e3
    rows.append(dict(nazwa="Płyta S prawa – śruby M12 w rurze jezdnej 2 mm S355 (docisk)", obciazenie=round(Fs * 72 / 50 / 2 + Fs / 2, 2),
                     nosnosc=round(cap, 2), jedn="kN", wytezenie=round((Fs * 72 / 50 / 2 + Fs / 2) / cap, 3), uwagi=""))
    return rows


ROWS += s5_extra_rows()


# ------------------------------------------------------------------ drogi sił (ruszt) – przed i po poprawce
P_WHEEL = g.WHEEL_KG * g.G * g.PHI * g.GAMMA_F
P_FOOT = g.FOOT_KG * g.G * g.PHI * g.GAMMA_F


def face_NRd(fy, t, b0, b1):
    """ścianka profilu pod podkładką / łbem – mechanizm linii załomów (jak EN 1993-1-8 tab. 7.11, β ≤ 0,85) [N]"""
    beta = b1 / b0
    return fy * t * t / (1 - beta) * (2 * beta + 4 * math.sqrt(1 - beta))


def ruszt(after=True):
    xs = [-g.X_LANE_OUT, -g.X_LANE_IN, g.X_LANE_IN, g.X_LANE_OUT, XW, XE]
    lane, walk = sily.rhs_IJ(40, 100, 2), sily.rhs_IJ(40, 100, 1.5)
    if after:
        return sily.Ruszt(xs, X0, X1, L, lane, walk, sily.rhs_IJ(60, 40, 3), list(g.CROSS_A), CROSS_B_S5,
                          hinges=(-g.X_LANE_OUT, g.X_LANE_OUT, XE), walk_rest=(XW, XE))
    return sily.Ruszt(xs, X0, X1, L, lane, walk, sily.rhs_IJ(60, 40, 2), list(g.CROSS_A), list(g.CROSS_B),
                      tie=g.TIE_B, tie_IJ=(40 * 5 ** 3 / 12, 40 * 5 ** 3 / 3))


SILY = {}
for _k in ("przed", "po"):
    _rows, _worst = sily.analyse(ruszt(_k == "po"), mA, mB, P_WHEEL, P_FOOT)
    SILY[_k] = dict(rows=_rows, worst=_worst,
                    walk=min(r["ugiecie"] for r in _rows if r["przypadek"].startswith("stopa")),
                    lane=min(r["ugiecie"] for r in _rows if r["przypadek"].startswith("koło")),
                    step=max(abs(r["skok"]) for r in _rows),
                    tmax=max(_worst.items(), key=lambda kv: kv[1][0]))


def sily_rows():
    S = SILY["po"]
    rows = []
    (tag, (T, case)) = S["tmax"]
    FtRd = 0.9 * 800 * 36.6 / g.GM2
    rows.append(dict(nazwa="Skrzyżowanie: śruba M8 8.8 – rozciąganie (poprzeczka wisi na rurze; ruszt)", obciazenie=round(T / 1e3, 2),
                     nosnosc=round(FtRd / 1e3, 2), jedn="kN", wytezenie=round(T / FtRd, 3), uwagi=f"{tag[1]} s={tag[2]:.0f} x={tag[3]:+.0f}; {case}"))
    Nf = face_NRd(235, 3.0, 60, 16)
    rows.append(dict(nazwa="Poprzeczka 60×40×3 – ścianka pod podkładką M8 (linie załomów)", obciazenie=round(T / 1e3, 2), nosnosc=round(Nf / 1e3, 2),
                     jedn="kN", wytezenie=round(T / Nf, 3), uwagi=f"przy ściance 2 mm nośność {face_NRd(235, 2.0, 60, 16) / 1e3:.1f} kN – za mało"))
    Tin = max(v for k, (v, c) in S["worst"].items() if abs(k[3]) == g.X_LANE_IN)
    Nh = face_NRd(355, 2.0, 40, 20)
    rows.append(dict(nazwa="Rura jezdna L2/L4 – ścianka górna pod łbem M8 (bez prowadnicy)", obciazenie=round(Tin / 1e3, 2), nosnosc=round(Nh / 1e3, 2),
                     jedn="kN", wytezenie=round(Tin / Nh, 3), uwagi="łeb zamkowy Ø20 przez siatkę"))
    rows.append(dict(nazwa="[INFO] Ugięcie chodnika pod stopą (obliczeniowo), najgorsze miejsce", obciazenie=round(-S["walk"], 1),
                     nosnosc=round(-SILY["przed"]["walk"], 1), jedn="mm", wytezenie=round(S["walk"] / SILY["przed"]["walk"], 3),
                     uwagi="nośność = wartość PRZED poprawką (mechanizm: chodnik bez podparcia przy zawiasie)"))
    rows.append(dict(nazwa="[INFO] Skok na styku sekcji pod kołem (obliczeniowo)", obciazenie=round(S["step"], 1), nosnosc=round(SILY["przed"]["step"], 1),
                     jedn="mm", wytezenie=round(S["step"] / SILY["przed"]["step"], 3), uwagi="nośność = wartość PRZED poprawką"))
    return rows


ROWS += sily_rows()


def plot_sily(path=None, fig=None):
    """słupki: największe rozciąganie śrub skrzyżowań przed / po poprawce + nośność ścianki poprzeczki"""
    BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e6e5e0"
    keys = sorted(set(SILY["przed"]["worst"]) | set(SILY["po"]["worst"]),
                  key=lambda k: -max(SILY["przed"]["worst"].get(k, (0,))[0], SILY["po"]["worst"].get(k, (0,))[0]))[:10]
    lab = [f"{'skrz.' if k[0].startswith('skrz') else 'nity T'} {k[1]} s={k[2]:.0f}\nx={k[3]:+.0f}" for k in keys]
    vb = [SILY["przed"]["worst"].get(k, (0,))[0] / 1e3 for k in keys]
    va = [SILY["po"]["worst"].get(k, (0,))[0] / 1e3 if k in SILY["po"]["worst"] else 0 for k in keys]
    own = fig is None
    if own:
        fig = plt.figure(figsize=(11.69, 5.2), facecolor="#fcfcfb")
    ax = fig.add_axes([0.07, 0.2, 0.9, 0.62], facecolor="#fcfcfb")
    xs = np.arange(len(keys))
    ax.bar(xs - 0.2, vb, 0.38, color=ORANGE, label="przed poprawką", zorder=3)
    ax.bar(xs + 0.2, va, 0.38, color=BLUE, label="po poprawce", zorder=3)
    for y, t in ((face_NRd(235, 2.0, 60, 16) / 1e3, "nośność ścianki poprzeczki 2 mm"), (face_NRd(235, 3.0, 60, 16) / 1e3, "nośność ścianki 3 mm (po poprawce)")):
        ax.axhline(y, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=2)
        ax.text(len(keys) - 0.5, y + 0.2, t, ha="right", va="bottom", fontsize=8, color=MUTED)
    for x, v in zip(xs, vb):
        ax.text(x - 0.2, v + 0.15, f"{v:.1f}" if v > 0 else "–\n(nie było)", ha="center", fontsize=7, color=INK if v > 0 else MUTED)
    for x, v in zip(xs, va):
        ax.text(x + 0.2, v + 0.15, f"{v:.1f}" if v > 0 else "–\n(usunięte)", ha="center", fontsize=7, color=INK if v > 0 else MUTED)
    ax.set_xticks(xs)
    ax.set_xticklabels(lab, fontsize=7, color=MUTED)
    ax.set_ylabel("rozciąganie śruby [kN], obliczeniowo", fontsize=8, color=MUTED)
    ax.tick_params(axis="y", labelsize=8, colors=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.legend(frameon=False, fontsize=8, loc="upper right", bbox_to_anchor=(1, 1.13), ncol=2)
    fig.text(0.07, 0.93, "Siła w śrubach skrzyżowań – 10 najbardziej obciążonych miejsc", fontsize=11, weight="bold", color=INK)
    if own:
        fig.savefig(path, dpi=150, facecolor="#fcfcfb")
        plt.close(fig)


def page_sily(pdf):
    fig = plt.figure(figsize=(11.69, 8.27), facecolor="#fcfcfb")
    fig.text(0.04, 0.95, "DROGI SIŁ W POKŁADZIE (model rusztu: rury + poprzeczki, skrzyżowania na jednej śrubie)", fontsize=12, weight="bold")
    B, A = SILY["przed"], SILY["po"]
    lines = [
        "Co pokazał model PRZED poprawką:",
        f"  • stopa na krawędzi chodnika przy zawiasie: MECHANIZM (w obliczeniach ugięcie bez granic, trzyma tylko siatka). Rury chodnika w A i B kończą się na zawiasie bez podpory,",
        "    a sekcja B miała tylko 1 poprzeczkę + słabą listwę T: rura B obraca się na tej jednej poprzeczce, gdy jej koniec odrywa się od ziemi.",
        f"  • koło przy zawiasie na rurze wewnętrznej: skok między A i B {B['step'] if B['step'] < 50 else 4.5:.1f} mm; śruby „wieszające” poprzeczki do {B['tmax'][1][0] / 1e3:.1f} kN,",
        f"    a ścianka poprzeczki 2 mm pod podkładką M8 przenosi ok. {face_NRd(235, 2.0, 60, 16) / 1e3:.1f} kN.",
        "",
        "Poprawka:",
        "  1. Sekcja B: druga poprzeczka (s = 650) zamiast nitowanej listwy T.",
        "  2. Krawędź chodnika (C2 | C3) ma własny zawias środkowy: płyta Z + sworzeń Ø20 na tej samej osi co zawias główny.",
        "  3. Oparcia chodnika na przyczepie: 2 kątowniki z gumą pod końcami C1 i C2 (rura tylko się opiera, przy składaniu odchodzi).",
        f"  4. Poprzeczki 60×40×3 (ścianka pod nakrętką: {face_NRd(235, 3.0, 60, 16) / 1e3:.1f} kN). Śruby prowadnic przesunięte (A: 540; B: bez 680).",
        "",
        f"PO poprawce: ugięcie chodnika max {-A['walk']:.1f} mm, koła max {-A['lane']:.1f} mm, skok na styku {A['step']:.1f} mm, "
        f"śruba max {A['tmax'][1][0] / 1e3:.1f} kN ({A['tmax'][0][1]} s={A['tmax'][0][2]:.0f} x={A['tmax'][0][3]:+.0f}).",
        "Obciążenia obliczeniowe: koło 273 kg ×1,5 ×1,5, stopa 105 kg ×1,5 ×1,5, ciężar własny ×1,35; 36 położeń koła i stopy.",
    ]
    for i, t in enumerate(lines):
        fig.text(0.04, 0.9 - i * 0.026, t, fontsize=8.2)
    sub = fig.add_axes([0, 0, 1, 0.5])
    sub.axis("off")
    plot_sily(fig=_SubFig(fig))
    pdf.savefig(fig)
    plt.close(fig)


class _SubFig:
    """rysuje wykres słupkowy w dolnej połowie strony PDF"""
    def __init__(self, fig):
        self.fig = fig

    def add_axes(self, r, **kw):
        return self.fig.add_axes([r[0], r[1] * 0.5, r[2], r[3] * 0.5], **kw)

    def text(self, x, y, *a, **kw):
        return self.fig.text(x, y * 0.5, *a, **kw)


# ------------------------------------------------------------------ rysunki S5
def page_section(pdf):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.set_title("S5 – przekrój poprzeczny (sekcja A, w miejscu poprzeczki). Patrzysz od ziemi na przyczepę: chodnik po LEWEJ (x > 0)",
                 fontsize=10, loc="left")
    for x in XS:
        lane = abs(x) < 200
        t = 2.0 if lane else 1.5
        ax.add_patch(Rectangle((x - 20, 0), 40, 100, fc="#b8c3cf" if lane else "#dde1e6", ec="k", lw=0.8))
        ax.add_patch(Rectangle((x - 20 + 3 * t, 3 * t), 40 - 6 * t, 100 - 6 * t, fc="white", ec="k", lw=0.3))
        ax.text(x, -78, f"{x:+.0f}", ha="center", fontsize=8)
    ax.add_patch(Rectangle((X0, -g.CROSS_H), WID, g.CROSS_H, fc="#efdcbc", ec="k", lw=0.8))
    ax.text((X0 + X1) / 2, -25, f"poprzeczka {CROSS_P}, dł. {WID:.0f}", ha="center", fontsize=8)
    ax.plot([X0, X1], [101.5, 101.5], color="#6a6a6a", lw=2.5)
    ax.text(160, 125, f"siatka stalowa ocynk, {WID:.0f} × 1250 (1 arkusz 1250×2500 → 2 kawałki)", fontsize=8)
    for sg in (1, -1):
        xg = sg * 145
        ax.add_patch(Polygon([(xg, 103), (xg, 143), (xg - sg * 3, 143), (xg - sg * 3, 106), (xg - sg * 40, 106), (xg - sg * 40, 103)],
                             fc="#9fb7d6", ec="k", lw=0.6))
    ax.annotate("", xy=(-141, 165), xytext=(141, 165), arrowprops=dict(arrowstyle="<->", lw=0.6))
    ax.text(0, 170, "pas koła 282 mm", ha="center", fontsize=8)
    ax.text(0, -100, f"rury jezdne: 4 × {LANE_P}", ha="center", fontsize=7)
    ax.text((XW + XE) / 2, -100, f"chodnik: 2 × {WALK_P}", ha="center", fontsize=7)
    ax.text(X1 - 5, 200, "LEWA – chodnik", ha="right", fontsize=10, weight="bold")
    ax.text(X0 + 5, 200, "PRAWA – krawędź", fontsize=10, weight="bold")
    ax.text(X0, 240, "Każde skrzyżowanie: M8×160 zamkowa + tuleja Ø12×1,5 dł. 139,5 (poprzeczka NA PŁASKO – 40 mm, żeby po złożeniu nakrętki nie uderzały w drugą sekcję).\nPrawa sprężyna: płyta S na zewnętrznej ściance prawej rury jezdnej L1,"
            " dolne oczko na wsporniku K zawiasu.", fontsize=8)
    ax.set_xlim(-260, 700)
    ax.set_ylim(-120, 270)
    ax.set_aspect("equal")
    ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def page_plan(pdf):
    fig, axs = plt.subplots(1, 2, figsize=(11.69, 8.27))
    for ax, sec in zip(axs, "AB"):
        ax.set_title(f"S5 – sekcja {sec} z góry (bez siatki); s " + ("od przyczepy" if sec == "A" else "od zawiasu"), fontsize=9, loc="left")
        for x in XS:
            ax.add_patch(Rectangle((x - 20, 0), 40, L, fc="#b8c3cf" if abs(x) < 200 else "#dde1e6", ec="k", lw=0.6))
            if sec == "B":
                ax.add_patch(Rectangle((x - 20, L - g.SKOS), 40, g.SKOS, fc="none", ec="#c00000", lw=0.6, hatch="///"))
        for s in (g.CROSS_A if sec == "A" else CROSS_B_S5):
            ax.add_patch(Rectangle((X0, s - 30), WID, 60, fc="#efdcbc", ec="k", lw=0.6, alpha=0.9))
            ax.text(X1 + 10, s, f"P s={s:.0f}", fontsize=7, va="center")
        if sec == "B":
            ax.add_patch(Rectangle((XE + 20, -30), 12, 170, fc="#a33", ec="k"))
            ax.text(XE + 40, 60, "Z chodnika", fontsize=6)
        gr = g.GUIDE_A if sec == "A" else g.GUIDE_B
        for sg in (1, -1):
            ax.add_patch(Rectangle((sg * 145 - (40 if sg > 0 else 0), gr[0]), 40, gr[1] - gr[0], fc="#9fb7d6", ec="k", lw=0.5, alpha=0.7))
        if sec == "A":
            ax.add_patch(Rectangle((XW + 20, g.S_PL["s0"]), 8, 80, fc="#a33", ec="k"))
            ax.add_patch(Rectangle((-153, g.S_PL["s0"]), 8, 80, fc="#a33", ec="k"))
            ax.text(X0, L + 150, f"Czerwone: płyty S sprężyn – lewa na C1 (x +{XW + 20:.0f}…{XW + 28:.0f}), prawa na prawej L1 (x −145…−153).\n"
                                 "Płyty H i Z: po JEDNEJ na zewnętrznej ściance rur ±125.", fontsize=7)
        ax.text(X1, -60, "LEWA", ha="right", fontsize=9, weight="bold")
        ax.text(X0, -60, "PRAWA", fontsize=9, weight="bold")
        ax.set_xlim(-300, 760)
        ax.set_ylim(L + 220, -100)
        ax.set_aspect("equal")
        ax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def page_cross(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.94, f"P – poprzeczka {CROSS_P}, L = {WID:.0f}, 3 szt.  |  T – płaskownik stal 40×5, L = {WID:.0f}  |  G1/G2 – kątownik 40×40×3",
             fontsize=11, weight="bold")
    ax = fig.add_axes([0.05, 0.55, 0.9, 0.3])
    ax.add_patch(Rectangle((0, 0), WID, 60, fc="#efdcbc", ec="k"))
    for x in XS:
        ax.add_patch(Circle((x - X0, 30), 6.25, fill=False, ec="#c00000"))
        ax.text(x - X0, 74, f"{x - X0:.0f}", ha="center", fontsize=8)
    ax.text(0, -10, "← PRAWY koniec (równo z prawą rurą L1)", fontsize=7)
    ax.text(WID, -10, "LEWY koniec (krawędź chodnika) →", fontsize=7, ha="right")
    ax.set_xlim(-30, WID + 30)
    ax.set_ylim(95, -30)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.text(0.05, 0.50, "P: 6 otworów Ø13 przez górę i dół, w osi szerokiej ścianki 60 (rura leży NA PŁASKO). Wymiary od PRAWEGO końca. Tuleja Ø12×1,5 dł. 139,5 przez podłużnicę i poprzeczkę.",
             fontsize=8)
    fig.text(0.05, 0.47, "4 poprzeczki: A s = 340 i 830 od przyczepy, B s = 260 i 650 od zawiasu (druga w B zastępuje nitowaną listwę T).", fontsize=8)
    ga = [s - g.GUIDE_A[0] for s in sorted(GUIDE_BOLTS_A_S5 + g.CROSS_A)]
    gb = [s - g.GUIDE_B[0] for s in sorted(GUIDE_BOLTS_B_S5 + CROSS_B_S5)]
    fig.text(0.05, 0.42, f"G1: kątownik stal 40×40×3, L = {g.GUIDE_A[1] - g.GUIDE_A[0]:.0f}, 2 szt. Ø9 w półce poziomej 20 mm od grzbietu, od końca przy przyczepie: "
                         + ", ".join(f"{v:.0f}" for v in ga), fontsize=8)
    fig.text(0.05, 0.39, f"G2: kątownik stal 40×40×3, L = {g.GUIDE_B[1] - g.GUIDE_B[0]:.0f}, 2 szt. Ø9 od końca przy zawiasie: "
                         + ", ".join(f"{v:.0f}" for v in gb), fontsize=8)
    fig.text(0.05, 0.36, "Prowadnice leżą na siatce nad rurami ±125, pionową półką na zewnątrz. Prawa prowadnica jest jednocześnie krawędzią trapu.", fontsize=8)
    pdf.savefig(fig)
    plt.close(fig)



# ------------------------------------------------------------------ wykonanie krok po kroku + lista kontrolna
STEPS = [
    ("0. Narzędzia", ["Wiertarka STOŁOWA (albo statyw do wiertarki) – bez niej nie wiercisz otworów pionowych przez rurę 100 mm.",
                      "Przecinarka / piła taśmowa z ogranicznikiem, imadło, ścisk stolarski × 4, punktak, wiertła Ø6, Ø9, Ø13, Ø18,5, Ø21.",
                      "Klucze 13, 18, klucz dynamometryczny 20–60 N·m, marker, kątownik stolarski."]),
    ("1. Materiał", ["Rury jezdne S355: atest 3.1 i oznaczenie na sztandze. Zaraz po zakupie pomaluj końce tych 8 rur sprayem na ŻÓŁTO.",
                     "Nie masz pewności, że to S355? Kup 100×40×3 S235 (+20 kg) – wtedy pomyłka jest niemożliwa."]),
    ("2. Cięcie", ["Ustaw ogranicznik na 1250 mm i tnij WSZYSTKIE rury podłużne z jednego ustawienia (różnica długości max 0,5 mm).",
                   f"Poprzeczki {WID:.0f} mm też z jednego ustawienia. Gratuj krawędzie. Skosy sekcji B (116 mm) na końcu."]),
    ("3. Otwory skrzyżowań (najważniejsze)", ["Połóż poprzeczkę NA PŁASKO pod rurą, zaciśnij ściskiem pod kątem 90° (kątownik).",
                   "Punktak w osi rury. Wiertło Ø6 PRZEZ CAŁY PAKIET (4 ścianki) jednym przejściem na wiertarce stołowej, potem Ø13 tak samo.",
                   "Oznacz parę markerem (np. A-P1-L2) – ta rura i ta poprzeczka już zawsze razem.",
                   "Tolerancja: miejsce wzdłuż rury ±2 mm nie ma znaczenia, bo wiercisz w pakiecie. Wiercone osobno – nie trafisz."]),
    ("4. Otwory boczne Ø18,5", ["Przez oba boki rury jednym przejściem na wiertarce stołowej. Płyty H i Z wierć w pakiecie (2 i 4 szt. razem) i użyj ich jako szablonu.",
                   "Obie rury L1 są identyczne – wierć je razem albo z tego samego szablonu."]),
    ("5. Zawias środkowy", ["L1 i L3 czołami na płaskiej podłodze, górne krawędzie dosunięte. Płyty Z ściskami, sworzeń Ø20 włożony.",
                   "Dopiero teraz wierć Ø18,5 w rurach przez otwory płyt. Ten krok sam koryguje wcześniejsze błędy."]),
    ("6. Próbny montaż (przed cynkowaniem!)", ["Skręć wszystko na sucho bez siatki. Złóż sekcje na stole jak do jazdy – nic nie może się dotykać.",
                   "Dopiero gdy wszystko pasuje: rozbierz, cynkuj."]),
    ("7. Cynkowanie", ["Cynkownia ogniowa (rury mają otwarte końce – tak ma być). Po cynkowaniu przetrzyj otwory wiertłem Ø13 / Ø18,5 ręcznie."]),
    ("8. Montaż", ["Każde skrzyżowanie: tuleja w otworze, ZANIM włożysz śrubę (bez tulei M8 zgniecie ściankę). M8 20 N·m, M12 40 N·m.",
                   f"Zaślepki: śruba M12×60 + tuleja w 2 nieużywanych otworach lewej rury L1 i w 2 otworach rury C3 przy x +{XW:.0f}.", "Sworznie zawiasów Ø20: podkładka + zawleczka – nic nie dokręcasz."]),
    ("9. Wsporniki K i oparcia chodnika", ["Przełóż PRĘT Ø20 przez oba wsporniki zawiasu i płyty H, dopiero wtedy wierć belkę i przykręcaj K – osie będą współosiowe.",
                   "Sprawdź: trap obraca się ręką bez zacięć w całym zakresie (także zawias chodnika – ten sam pręt przez 3 płyty Z na stole).",
                   "Oparcia chodnika: rozłóż trap, podłóż kątownik z gumą pod końce C1 i C2 tak, by rury lekko na nim leżały, zaznacz i przykręć do belki."]),
    ("10. Próba", ["400 kg (worki) przy zawiasie środkowym nad każdą rurą jezdną – nic nie może zostać wygięte, pomiar ugięcia przed/po.",
                   "Pierwszy wjazd bez kierowcy, przyczepa podpięta do auta."]),
]
TOL = [("Długość rur podłużnych", "±0,5 mm między sobą", "ogranicznik / cięcie z jednego ustawienia"),
       ("Otwór skrzyżowania Ø13 (tuleja Ø12)", "pakiet wiercony razem", "wiertarka stołowa, Ø6 → Ø13"),
       ("Położenie poprzeczki wzdłuż rury", "±3 mm", "bez wpływu na nośność i składanie"),
       ("Płyty H, Z, S – położenie", "±2 mm", "pakiet; Z wiercone na złożonym zawiasie"),
       ("Osie zawiasu przy przyczepie (L i P)", "współosiowo ±1 mm", "pręt Ø20 jako przyrząd"),
       ("Kąt cięcia rur", "±1°", "kątownik; styk zawiasu środkowego toleruje"),
       ("Luz po złożeniu (nakrętki / druga sekcja)", "min. 13 mm w modelu", "błąd ±10 mm położenia jeszcze nie koliduje")]
CHECK_BEFORE_LOAD = ["Przyczepa PODPIĘTA do auta, auto na hamulcu ręcznym (albo podpora pod tył przyczepy).",
                     "Podłoże pod końcem trapu twarde; pod zawiasem środkowym brak garbu / kamienia.",
                     "Sworznie Ø12 blokady WYJĘTE i zawieszone na łańcuszkach. Pas transportowy zdjęty.",
                     "Trap leży na ziemi całą krawędzią (gumy EPDM), oba sworznie Ø20 na miejscu, zawleczki są.",
                     "Koło ustawione w osi pasa, prowadnice po obu stronach. Idziesz po chodniku z LEWEJ.",
                     "Nikt nie stoi z prawej strony trapu."]
CHECK_BEFORE_DRIVE = ["Trap w pionie: OBA sworznie Ø12 przez wspornik K i płytę H, zawleczki założone.",
                      "Zapięcia sekcji A–B zapięte.",
                      "PAS TRANSPORTOWY założony na poprzeczce P i dociągnięty (druga, niezależna blokada).",
                      "Motocykl przypięty pasami do uch przyczepy, nie opiera się o trap.",
                      "Co 5 wjazdów / po zimie: dokręć M8 i M12, sprawdź sprężyny i sworznie Ø20 (luz, rdza, zawleczki)."]


def page_steps(pdf):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.06, 0.965, "WYKONANIE KROK PO KROKU (dla amatora) i tolerancje", fontsize=13, weight="bold")
    y = 0.94
    for t, xs in STEPS:
        fig.text(0.06, y, t, fontsize=8.5, weight="bold"); y -= 0.0155
        for x in xs:
            fig.text(0.08, y, "• " + x, fontsize=7.2); y -= 0.0145
        y -= 0.004
    y -= 0.01
    fig.text(0.06, y, "TOLERANCJE – ile wolno się pomylić", fontsize=9.5, weight="bold"); y -= 0.02
    for a, b, c in TOL:
        fig.text(0.08, y, a, fontsize=7.2); fig.text(0.46, y, b, fontsize=7.2, weight="bold"); fig.text(0.66, y, c, fontsize=7); y -= 0.0145
    pdf.savefig(fig)
    plt.close(fig)


def checklist_pdf(path):
    with PdfPages(path) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.06, 0.95, "TRAP S5 – LISTA KONTROLNA", fontsize=18, weight="bold")
        fig.text(0.06, 0.925, "Wydrukuj, zalaminuj, przyklej na przyczepie.", fontsize=9)
        y = 0.88
        for title, items in (("PRZED WJAZDEM / ZJAZDEM", CHECK_BEFORE_LOAD), ("PRZED JAZDĄ", CHECK_BEFORE_DRIVE)):
            fig.text(0.06, y, title, fontsize=14, weight="bold", color="#b00000"); y -= 0.04
            for it in items:
                fig.patches.append(Rectangle((0.065, y - 0.004), 0.022, 0.016, transform=fig.transFigure, fill=False, lw=1.2, figure=fig))
                fig.text(0.1, y, it, fontsize=10.5, wrap=True); y -= 0.045
            y -= 0.03
        fig.text(0.06, y, "Składając: trzymaj za rurę z dala od zawiasu środkowego, NIGDY za zawias – szczelina zgniata palce.", fontsize=10, weight="bold")
        pdf.savefig(fig)
        plt.close(fig)


# ------------------------------------------------------------------ listy
def bom():
    kg = lambda p: p["kgm"]
    lane, walk, cross = V["lane"][1], V["walk"][1], V["cross"][1]
    out = []
    for pid, (_, name, prof, mat, q, xs, skos, sec) in LONG_INFO.items():
        p = lane if prof == LANE_P else walk
        m = kg(p) * L / 1000 - ((g.SKOS * 40 * p["t"] + g.SKOS * 100 * p["t"]) * stal.RHO_ST if skos else 0)
        nh = 2 * len(holes_long(pid))
        out.append([pid, name, q, mat, f"{prof}, L = {L:.0f}" + (f", skos {g.SKOS:.0f}" if skos else ""), round(m, 2), nh, f"x = {xs}"])
    out += [["P", "Poprzeczka – rura NA PŁASKO (40 mm wysokości), ścianka 3 mm", 4, "S235JRH", f"{CROSS_P}, L = {WID:.0f}", round(kg(cross) * WID / 1000, 2), 12,
             f"A: s = {g.CROSS_A}, B: s = {CROSS_B_S5}"],
            ["G1", "Prowadnica koła sekcji A (na siatce nad rurą ±125)", 2, "S235", f"kątownik 40×40×3, L = {g.GUIDE_A[1] - g.GUIDE_A[0]:.0f}",
             round(V["guide"][1] * (g.GUIDE_A[1] - g.GUIDE_A[0]) / 1000, 2), 5, ""],
            ["G2", "Prowadnica koła sekcji B", 2, "S235", f"kątownik 40×40×3, L = {g.GUIDE_B[1] - g.GUIDE_B[0]:.0f}",
             round(V["guide"][1] * (g.GUIDE_B[1] - g.GUIDE_B[0]) / 1000, 2), 4, ""],
            ["O", "Oparcie chodnika przy przyczepie (część PRZYCZEPY)", 2, "S235", "kątownik 100×100×10, L = 40 + guma EPDM 5 mm", 0.6, 2,
             f"pod końcami rur C1 i C2 (x +{XW:.0f}, +{XE:.0f}); rura tylko się opiera – DOPASUJ wysokość do belki"],
            ["H", "Płyta zawiasu przy przyczepie", 2, "S235", "płaskownik 80×6, L = 200", 0.75, 4, "1 na każdą rurę L1, po stronie zewnętrznej"],
            ["Z", "Płyta zawiasu środkowego (A i B – ta sama)", 6, "S235", "płaskownik 100×6, L = 170", 0.8, 3,
             f"1 na każdą rurę L1 i L3 + 1 na C2 i C3 krawędzi chodnika (x +{XE:.0f}), po stronie zewnętrznej"],
            ["S", "Płyta zaczepu sprężyny (oczko Ø13)", 2, "S235", "płaskownik 80×8, L = 150", 0.75, 3, "lewa na C1, prawa na prawej L1"],
            ["K", "Wspornik na belce przyczepy (oczko sprężyny Ø13)", 3, "S235", "kątownik 100×100×10, L = 130", 1.94, 5,
             f"2 × zawias (x ±152…162; prawy trzyma też sprężynę), 1 × sprężyna lewa (x +{XW + 24:.0f}…{XW + 34:.0f})"],
            ["SIATKA", "Siatka stalowa cięto-ciągniona ocynk (pokład)", 2, "stal ocynk", f"{WID:.0f} × 1250 (LWD w poprzek)",
             round(WID * L * 1e-6 * V["mesh"][1], 2), 0, "z 1 arkusza 1250×2500"]]
    return out


def bolts():
    F = SPR["F1_N"]
    return [
        ("M8×160", "zamkowa DIN 603 kl. 8.8 + podkładka + nakrętka samohamowna", 24, "skrzyżowania (6 podłużnic × 4 poprzeczki)"),
        ("M8×130", "zamkowa DIN 603 + podkładka + nakrętka samohamowna", 10, "prowadnice"),
        ("M12×70", "sześciokątna 8.8 + 2 podkładki + nakrętka samohamowna", 10, "płyty H (4), Z sekcji A (4), Z chodnika A (2)"),
        ("M12×80", "sześciokątna 8.8 + 2 podkładki + nakrętka samohamowna", 10, "płyty S (4), Z sekcji B (4), Z chodnika B (2)"),
        ("M12×60", "sześciokątna 8.8 + 2 podkładki + nakrętka samohamowna", 4, "ZAŚLEPKI: lewa L1 (płyta S) i C3 x +305 (płyta Z)"),
        ("M12×80 (oparcie)", "sześciokątna 8.8 (DOPASUJ do belki)", 4, "2 oparcia chodnika → belka przyczepy"),
        ("M12×80", "sześciokątna 8.8 (DOPASUJ do belki)", 6, "3 wsporniki K → belka przyczepy"),
        ("M12×60 / M12×70", "sześciokątna 8.8 + podkładka + nakrętka samohamowna", "3 / 1", "osie oczek sprężyn (×70: płyta S prawa)"),
        ("sworzeń Ø20×40", "ISO 2341-B, stal C45 / 8.8, + podkładka 21 + zawleczka 4×36", 2, "zawias przy przyczepie (H – K)"),
        ("sworzeń Ø20×35", "ISO 2341-B, stal C45 / 8.8, + podkładka 21 + zawleczka 4×36", 3, "zawias środkowy: 2 × rury jezdne + 1 × krawędź chodnika"),
        ("Ø12×40", "sworzeń ISO 2341-B ze stali 8.8 / C45 ulepszanej + zawleczka, na łańcuszku", 2, "blokada do jazdy"),
        ("podkładka M12 gr. 6", "DIN 7349 (13×30×6)", 6, "dystans płyt Z sekcji B"),
        ("nit 4,8", "nit zrywalny stalowy 4,8, szeroki kołnierz", 8, "zapięcia"),
        ("wkręt 4,8×19", "wkręt samowiercący z podkładką EPDM", 70, "siatka, co ~250 mm"),
        ("tuleja Ø12×1,5 dł. 139,5", "rura stal bezszwowa ocynk", 24, "skrzyżowania"),
        ("tuleja Ø12×1,5 dł. 99,5", "rura stal bezszwowa ocynk", 10, "prowadnice"),
        ("tuleja Ø18×2,5 dł. 40", "rura stal bezszwowa ocynk", 24, "płyty H, Z, S + 4 zaślepki"),
        ("tuleja Ø18×2,5 dł. 50", "rura stal bezszwowa ocynk (DOPASUJ do belki)", 6, "belka przyczepy"),
        ("tuleja Ø22×5 dł. 22 / 25 / 16 / 16", "rura stal bezszwowa", 4, "dystanse oczek: S lewa 22, S prawa 25, K 16 i 16"),
        (f"sprężyna gazowa 460/200 {F} N", "Ø28, oczka Ø12,2 (M12) – tania, standardowa", 2, "lewa: C1 ↔ K sprężyny; prawa: prawa L1 ↔ K zawiasu"),
        ("pas z grzechotką 25 mm, LC ≥ 400 daN, 2 haki", "DRUGA blokada do jazdy, niezależna od sworzni Ø12", 1, "opasuje złożony trap na poprzeczce P (s = 830), haki do uch z przodu przyczepy"),
    ]


def buy():
    sk = stal.sticks
    return [
        (f"Rura stalowa prostokątna {LANE_P}", f"8 × 1250 mm = {sk(8 * L)} sztangi 6 m",
         "rury jezdne. MUSI być S355 (S355J2H / S355MH) – żądaj atestu 3.1 i oznacz sztangi farbą; bez atestu kup 100×40×3 S235 (+20 kg)"),
        (f"Rura stalowa prostokątna {WALK_P}", "4 × 1250 mm = 1 sztanga 6 m", "podłużnice chodnika C1–C3"),
        (f"Rura stalowa prostokątna {CROSS_P}", f"4 × {WID:.0f} mm (1 sztanga 6 m)", "poprzeczki P – ścianka 3 mm (nie 2!)"),
        ("Kątownik stalowy 40×40×3", "2 × 1095 + 2 × 715 mm (1 sztanga 6 m)", "prowadnice"),
        ("Siatka cięto-ciągniona stalowa ocynk ~30×12×2×1,5 (~4 kg/m²), arkusz 1250×2500", f"1 arkusz → 2 × {WID:.0f}×1250",
         "pokład; dostawca ma potwierdzić 160 kg w punkcie na przęśle 190 mm"),
        ("Płaskownik stal 80×6 / 100×6 / 80×8", "0,45 m / 1,05 m / 0,3 m", "płyty H / Z / S"),
        ("Kątownik stal 100×100×10", "3 × 130 + 2 × 40 mm (0,5 m)", "wsporniki K + oparcia chodnika"),
        ("Rura stal bezszwowa Ø12×1,5 / Ø18×2,5 / Ø22×5", "4,5 m / 1,1 m / 0,1 m", "tuleje"),
        (f"Sprężyna gazowa 460 mm / skok 200 / {SPR['F1_N']} N, Ø28, oczka Ø12,2", "2", "dobrana do masy trapu; standardowa Ø28 (tańsza niż Ø40)"),
        ("Zapięcie dźwigniowe z regulowanym kabłąkiem, zasięg ≥ 180 mm, ≥ 200 daN (lub pas z grzechotką)", "2", "spina złożone sekcje"),
        ("Pasek gumy EPDM 3–5 mm × 40 mm", "ok. 3 m", "pod skosy przy ziemi (6 × 0,5 m)"),
        ("Pas z grzechotką 25 mm, LC ≥ 400 daN, z hakami", "1", "DRUGA blokada do jazdy (gdyby sworznie Ø12 zostały w kieszeni)"),
        ("Pręt stalowy gładki Ø20 h9 (lub sworzeń M20 z gładkim trzpieniem), dł. ok. 400 mm", "1", "PRZYRZĄD: przekładasz przez oba wsporniki K przy ich przykręcaniu – osie zawiasu współosiowe"),
        ("Rozwiertak / wiertło Ø13 i Ø18,5", "po 1", "przetarcie otworów po cynkowaniu"),
        ("Cynkowanie ogniowe wszystkich części stalowych PO wierceniu (albo podkład epoksydowy + farba)", f"ok. {mA + mB - 2 * WID * L * 1e-6 * V['mesh'][1]:.0f} kg",
         "bez tego stal rdzewieje"),
        ("Śruby, nakrętki, tuleje, nity, wkręty – wg lista_srub.csv", "", ""),
    ]


def write_csv(name, head, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(head)
        w.writerows(rows)


# ------------------------------------------------------------------ MAIN
def main():
    os.makedirs(OUT, exist_ok=True)
    old = (copy.deepcopy(g.S_PL), copy.deepcopy(g.K_PL), g.holes_long, g.OUT, dict(g.SPRING), g.TEMPL_NAME, g.SINGLE_PLATES,
           list(g.CROSS_B), g.TIE_B, list(g.GUIDE_BOLTS_A), list(g.GUIDE_BOLTS_B))
    g.CROSS_B, g.TIE_B = list(CROSS_B_S5), None
    g.GUIDE_BOLTS_A, g.GUIDE_BOLTS_B = list(GUIDE_BOLTS_A_S5), list(GUIDE_BOLTS_B_S5)
    g.K_PL["n"] = 3
    g.SINGLE_PLATES = V["single_plates"]
    g.SPRING["F1"] = float(SPR["F1_N"])
    g.TEMPL_NAME = "szablony_1do1_S5.pdf"
    g.holes_long = holes_long
    g.OUT = OUT
    try:
        write_csv("lista_czesci.csv", ["nr", "nazwa", "szt.", "materiał", "wymiar", "masa szt. [kg]", "otwory", "gdzie"], bom())
        write_csv("lista_srub.csv", ["śruba / element", "rodzaj", "szt.", "gdzie"], bolts())
        write_csv("lista_zakupow.csv", ["pozycja", "ilość", "uwagi"], buy())
        write_csv("obliczenia.csv", ["element", "obciążenie", "nośność", "jedn.", "wytężenie", "uwagi"],
                  [[r["nazwa"], r["obciazenie"], r["nosnosc"], r["jedn"], r["wytezenie"], r["uwagi"]] for r in ROWS])
        g.write_dxf()
        g.templates_pdf(os.path.join(OUT, "szablony_1do1_S5.pdf"))
        checklist_pdf(os.path.join(OUT, "lista_kontrolna_S5.pdf"))
        plot_sily(os.path.join(OUT, "sily_sruby_S5.png"))
        with open(os.path.join(OUT, "sily_S5.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["złącze", "sekcja", "s [mm]", "x [mm]", "rozciąganie PRZED [kN]", "rozciąganie PO [kN]", "przypadek (po)"])
            for k in sorted(set(SILY["przed"]["worst"]) | set(SILY["po"]["worst"]), key=lambda k: (k[1], k[2], k[3])):
                b_, a_ = SILY["przed"]["worst"].get(k, (0, "")), SILY["po"]["worst"].get(k, (0, ""))
                w.writerow([k[0], k[1], f"{k[2]:.0f}", f"{k[3]:+.0f}", round(b_[0] / 1e3, 2), round(a_[0] / 1e3, 2), a_[1]])
        worst = max((r for r in ROWS if not r["nazwa"].startswith("[INFO]")), key=lambda r: r["wytezenie"])
        with PdfPages(os.path.join(OUT, "rysunki_trap_S5.pdf")) as pdf:
            g.page_text(pdf, f"Trap STALOWY S5 – lekki i tani, chodnik z lewej, 2,5 × {WID / 1000:.2f} m (bez spawania)".replace(".", ","), [
                f"Masa trapu ok. {mA + mB:.0f} kg (A {mA:.0f} kg, B {mB:.0f} kg) + 3 wsporniki K ok. 5,8 kg. Podłoga {g.H_FLOOR:.0f} mm, kąt {g.ALPHA:.1f}°.",
                f"Sprężyny 2 × {SPR['F1_N']} N (Ø28, oś M12): podnoszenie ok. {SPR['max_wysilek_kg']:.0f} kg (bez sprężyn {max(r['user_kg'] for r in LIFT0):.0f} kg).",
                f"Najbardziej obciążona część: {worst['wytezenie'] * 100:.0f} % – {worst['nazwa']}.",
                "",
                "LEWA strona = patrząc od ziemi na przyczepę (od tej strony pchasz motocykl, od strony stopki). Na rysunkach x > 0.",
                "",
                "CO INNE NIŻ W WERSJI ALUMINIOWEJ V2:",
                "  • Materiał: rury jezdne RHS 100×40×2 S355J2H, podłużnice 100×40×1,5 S235, poprzeczki 60×40×2 (na płasko), kątowniki 40×40×3, siatka stalowa.",
                f"  • Chodnik tylko z lewej, 340 mm: 2 podłużnice (x +{XW:.0f}, +{XE:.0f}), poprzeczki i siatka {WID:.0f} mm, prawa rura jezdna L1 = prawa krawędź.",
                "  • Obie rury L1 są IDENTYCZNE (nie da się ich pomylić). Prawa niesie płytę S prawej sprężyny, w lewej te 2 otwory zaślepia śruba M12×60 z tuleją.",
                "  • Prawa sprężyna: górne oczko na płycie S na prawej L1, dolne na wsporniku K zawiasu (otwór „sprężyna” w K). Wsporniki K: 3 zamiast 4.",
                "  • Płyty H i Z: po JEDNEJ na rurę (zewnętrzna ścianka), sworznie zawiasów Ø20 ISO 2341-B z zawleczką. Oczka sprężyn: M12 + tuleja Ø22×5.",
                "  • Sworznie blokady ze stali 8.8 / C45 ulepszanej. Bez pasty i podkładek izolujących (stal na stali).",
                "",
                "ZASADY: otwory Ø13 pod tuleje Ø12, Ø18,5 pod tuleje Ø18; płyty H i Z wierć w pakiecie; zawias środkowy wierć po ułożeniu rur czołami;",
                "M8 20 N·m, M12 40 N·m; sworznie Ø20 z zawleczką; CYNKOWANIE OGNIOWE PO WIERCENIU (albo farba).",
                "Wsporniki K i śruby do belki są dla PRZYKŁADOWEJ belki 50×75 – podaj swoje wymiary przed wierceniem.",
            ], fs=8)
            page_steps(pdf)
            page_sily(pdf)
            page_section(pdf)
            page_plan(pdf)
            g.page_side(pdf, LIFT)
            g.page_hinges(pdf)
            for pid, (_, name, prof, mat, q, xs, skos, sec) in LONG_INFO.items():
                g.page_tube(pdf, pid, name, prof, mat, q, skos)
            page_cross(pdf)
            g.page_plates(pdf)
            g.page_calc(pdf, ROWS, LIFT, LIFT0)
        # model 3D
        M = p3.build(layout())
        ok = p3.check(M)
        p3.write_gltf(os.path.join(OUT, "trap_s5.glb"), M=M)
        p3.export_holes(M, os.path.join(OUT, "otwory_z_modelu.csv"))
        for t, name, view, kw in ((0.0, "podglad_rozlozony.png", ((-2600, 1500, -4300), (200, -150, -1100)), {}),
                                  (1.0, "podglad_do_jazdy.png", ((-1900, 900, -3600), (200, 400, -300)), {}),
                                  (0.0, "podglad_sprezyna_prawa.png", ((-900, -50, -650), (-185, -150, -170)), {}),
                                  (0.0, "podglad_przezroczysty.png", ((900, 250, -1100), (150, -130, -300)), dict(transparent=True))):
            plt.imsave(os.path.join(OUT, name), p3.render(M, t, view, 1300, 880, **kw))
        summary = dict(wariant="S5", masa=round(mA + mB, 1), masa_A=round(mA, 1), masa_B=round(mB, 1), sprezyny=SPR,
                       wysilek_bez_sprezyn=max(r["user_kg"] for r in LIFT0), najwieksze_wytezenie=dict(element=worst["nazwa"], wartosc=worst["wytezenie"]),
                       otwory=len(M.hole_dia), zlacza=len(M.bolt_axes), kontrola_ok=ok)
        with open(os.path.join(OUT, "dane_S5.json"), "w", encoding="utf-8") as f:
            json.dump(dict(podsumowanie=summary, obliczenia=ROWS, podnoszenie=LIFT, podnoszenie_bez=LIFT0), f, ensure_ascii=False, indent=1)
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return M, summary
    finally:
        (g.S_PL, g.K_PL, g.holes_long, g.OUT, g.SPRING, g.TEMPL_NAME, g.SINGLE_PLATES,
         g.CROSS_B, g.TIE_B, g.GUIDE_BOLTS_A, g.GUIDE_BOLTS_B) = old


if __name__ == "__main__":
    main()
