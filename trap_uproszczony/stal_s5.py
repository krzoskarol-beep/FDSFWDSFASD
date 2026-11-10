# -*- coding: utf-8 -*-
"""
Trap STALOWY S5 – optymalnie lekki: chodnik tylko z LEWEJ strony, szerokość 740 mm, bez spawania.
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
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, Polygon

import generuj as g
import podglad3d as p3
import stal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stal_S5")
V = stal.VARIANTS["S5"]
L = g.L_SEC
X0, X1 = -(g.X_LANE_OUT + 20), g.X_EDGE + 20          # -145 … +595
WID = X1 - X0                                         # 740
XS = [-g.X_LANE_OUT, -g.X_LANE_IN, g.X_LANE_IN, g.X_LANE_OUT, g.X_WALK, g.X_EDGE]
LANE_P, WALK_P, CROSS_P = V["lane"][0], V["walk"][0], V["cross"][0]

LONG_INFO = {
    "L1L": ("L1L", "Rura jezdna zewnętrzna sekcji A – LEWA (od strony chodnika)", LANE_P, "S355J2H", 1, "+125", False, "A"),
    "L1P": ("L1P", "Rura jezdna zewnętrzna sekcji A – PRAWA (krawędź trapu, z płytą sprężyny S)", LANE_P, "S355J2H", 1, "−125", False, "A"),
    "L2": ("L2", "Rura jezdna wewnętrzna sekcji A", LANE_P, "S355J2H", 2, "±45", False, "A"),
    "L3": ("L3", "Rura jezdna zewnętrzna sekcji B (zawias Z, skos przy ziemi)", LANE_P, "S355J2H", 2, "±125", True, "B"),
    "L4": ("L4", "Rura jezdna wewnętrzna sekcji B (skos przy ziemi)", LANE_P, "S355J2H", 2, "±45", True, "B"),
    "C1": ("C1", "Podłużnica chodnika sekcji A (z płytą sprężyny S)", WALK_P, "S235JRH", 1, "+345", False, "A"),
    "C2": ("C2", "Podłużnica krawędzi sekcji A (lewa krawędź)", WALK_P, "S235JRH", 1, "+575", False, "A"),
    "C3": ("C3", "Podłużnica chodnika / krawędzi sekcji B (skos)", WALK_P, "S235JRH", 2, "+345, +575", True, "B"),
}
LONGS = [(-125.0, "L1P", "L3"), (-45.0, "L2", "L4"), (45.0, "L2", "L4"), (125.0, "L1L", "L3"), (345.0, "C1", "C3"), (575.0, "C2", "C3")]


_G_HOLES = g.holes_long


def holes_long(pid):
    base = {"L1L": "L1", "L1P": "L1"}.get(pid, pid)
    h = list(_G_HOLES(base))
    if pid == "L1P":
        for (_, s, z, _) in [hh for hh in g.S_PL["holes"] if hh[0] == "M12"]:
            h.append((s, "bok", z, 18.5, "płyta S (sprężyna prawa) – M12 + tuleja Ø18"))
    return sorted(h, key=lambda r: r[0])


def layout():
    return dict(
        key="S5", longs=LONGS, xmin=X0, xmax=X1, holes_long=holes_long, long_info=LONG_INFO,
        cross_txt="RHS 60×40×2 S235JRH na płasko", tie_txt="płaskownik stal 40×5", mesh_txt="siatka stal ocynk cięto-ciągniona ~30×12×2×1,5",
        guide=(40.0, 3.0, "kątownik stal 40×40×3"),
        s_plates=[dict(sg=1, face=g.X_WALK + 20, inner=g.X_WALK - 20, tube="C1"),
                  dict(sg=-1, face=g.X_LANE_OUT + 20, inner=g.X_LANE_OUT - 20, tube="L1P")],
        springs=[dict(sg=1, s_face=g.X_WALK + 20, s_sp=22.0, k_xa=369.0, k_nm="sprężyna", k_sp=16.0),
                 dict(sg=-1, s_face=g.X_LANE_OUT + 20, s_sp=25.0, k_xa=152.0, k_nm="zawias", k_sp=16.0)],
        kbr=[("zawias", 152.0, -1), ("zawias", 152.0, 1), ("sprężyna", 369.0, 1)],
        eye=dict(size=16, w=14.0, r=12.5, sleeve="Ø25×5", body=20.0, rod=10.0, F=f"{SPR['F1_N']} N"),
        colors=("#8a96a3", "#b9c0c8", "#c9a77a", "#3f6fb0"),
    )


# ------------------------------------------------------------------ dane wariantu
(mA, cAs, cAz), (mB, cBs, cBz) = stal.masses(V)
SPR, LIFT = stal.pick_springs(mA, (cAs, cAz), mB, (cBs, cBz))
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
    Fs = SPR["F1_N"] * 1.3 * 1.5 / 1000
    cap = 2.5 * min(40 / 55.5, 1) * 470 * 18 * 2 / 1.25 / 1e3
    rows.append(dict(nazwa="Płyta S prawa – śruby M12 w rurze jezdnej 2 mm S355 (docisk)", obciazenie=round(Fs * 72 / 50 / 2 + Fs / 2, 2),
                     nosnosc=round(cap, 2), jedn="kN", wytezenie=round((Fs * 72 / 50 / 2 + Fs / 2) / cap, 3), uwagi=""))
    return rows


ROWS += s5_extra_rows()


def plates_patch():
    """otwory oczek sprężyn Ø17 (śruba M16) w płycie S i wsporniku K"""
    g.S_PL["holes"] = [(n, s, z, 17.0 if n == "oczko" else d) for (n, s, z, d) in g.S_PL["holes"]]
    g.K_PL["holes_arm"] = [(n, y, z, 17.0 if n == "sprez." else d) for (n, y, z, d) in g.K_PL["holes_arm"]]


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
    ax.text(460, -100, f"chodnik: 2 × {WALK_P}", ha="center", fontsize=7)
    ax.text(X1 - 5, 200, "LEWA – chodnik", ha="right", fontsize=10, weight="bold")
    ax.text(X0 + 5, 200, "PRAWA – krawędź", fontsize=10, weight="bold")
    ax.text(X0, 240, "Każde skrzyżowanie: M8×160 zamkowa + tuleja Ø12×1,5 dł. 139,5 (poprzeczka NA PŁASKO – 40 mm, żeby po złożeniu nakrętki nie uderzały w drugą sekcję).\nPrawa sprężyna: płyta S na zewnętrznej ściance prawej rury jezdnej (L1P),"
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
        for s in (g.CROSS_A if sec == "A" else g.CROSS_B):
            ax.add_patch(Rectangle((X0, s - 30), WID, 60, fc="#efdcbc", ec="k", lw=0.6, alpha=0.9))
            ax.text(X1 + 10, s, f"P s={s:.0f}", fontsize=7, va="center")
        if sec == "B":
            ax.add_patch(Rectangle((X0, g.TIE_B - 20), WID, 40, fc="#ddd", ec="k", lw=0.6, ls="--"))
            ax.text(X1 + 10, g.TIE_B, f"T s={g.TIE_B:.0f}", fontsize=7, va="center")
        gr = g.GUIDE_A if sec == "A" else g.GUIDE_B
        for sg in (1, -1):
            ax.add_patch(Rectangle((sg * 145 - (40 if sg > 0 else 0), gr[0]), 40, gr[1] - gr[0], fc="#9fb7d6", ec="k", lw=0.5, alpha=0.7))
        if sec == "A":
            ax.add_patch(Rectangle((365, g.S_PL["s0"]), 8, 80, fc="#a33", ec="k"))
            ax.add_patch(Rectangle((-153, g.S_PL["s0"]), 8, 80, fc="#a33", ec="k"))
            ax.text(X0, L + 150, "Czerwone: płyty S sprężyn – lewa na C1 (x +365…373), prawa na L1P (x −145…−153).\n"
                                 "Płyty H i Z na rurach ±125 jak w wersji V2.", fontsize=7)
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
    ax.text(0, -10, "← PRAWY koniec (równo z rurą L1P)", fontsize=7)
    ax.text(WID, -10, "LEWY koniec (krawędź chodnika) →", fontsize=7, ha="right")
    ax.set_xlim(-30, WID + 30)
    ax.set_ylim(95, -30)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.text(0.05, 0.50, "P: 6 otworów Ø12,5 przez górę i dół, w osi szerokiej ścianki 60 (rura leży NA PŁASKO). Wymiary od PRAWEGO końca. Tuleja Ø12×1,5 dł. 139,5 przez podłużnicę i poprzeczkę.",
             fontsize=8)
    fig.text(0.05, 0.47, "T: w tych samych miejscach po 2 otwory Ø4,9 (±10 mm od osi podłużnicy, wzdłuż listwy) – 12 nitów 4,8 w dno podłużnic B.", fontsize=8)
    ga = [s - g.GUIDE_A[0] for s in sorted(g.GUIDE_BOLTS_A + g.CROSS_A)]
    gb = [s - g.GUIDE_B[0] for s in sorted(g.GUIDE_BOLTS_B + g.CROSS_B)]
    fig.text(0.05, 0.42, f"G1: kątownik stal 40×40×3, L = {g.GUIDE_A[1] - g.GUIDE_A[0]:.0f}, 2 szt. Ø9 w półce poziomej 20 mm od grzbietu, od końca przy przyczepie: "
                         + ", ".join(f"{v:.0f}" for v in ga), fontsize=8)
    fig.text(0.05, 0.39, f"G2: kątownik stal 40×40×3, L = {g.GUIDE_B[1] - g.GUIDE_B[0]:.0f}, 2 szt. Ø9 od końca przy zawiasie: "
                         + ", ".join(f"{v:.0f}" for v in gb), fontsize=8)
    fig.text(0.05, 0.36, "Prowadnice leżą na siatce nad rurami ±125, pionową półką na zewnątrz. Prawa prowadnica jest jednocześnie krawędzią trapu.", fontsize=8)
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
    out += [["P", "Poprzeczka – rura NA PŁASKO (40 mm wysokości)", 3, "S235JRH", f"{CROSS_P}, L = {WID:.0f}", round(kg(cross) * WID / 1000, 2), 12,
             f"A: s = {g.CROSS_A}, B: s = {g.CROSS_B}"],
            ["T", "Listwa spinająca pod sekcją B (nity)", 1, "S235", f"płaskownik 40×5, L = {WID:.0f}", round(40 * 5 * WID * stal.RHO_ST, 2), 12,
             f"B: s = {g.TIE_B:.0f}"],
            ["G1", "Prowadnica koła sekcji A (na siatce nad rurą ±125)", 2, "S235", f"kątownik 40×40×3, L = {g.GUIDE_A[1] - g.GUIDE_A[0]:.0f}",
             round(V["guide"][1] * (g.GUIDE_A[1] - g.GUIDE_A[0]) / 1000, 2), 5, ""],
            ["G2", "Prowadnica koła sekcji B", 2, "S235", f"kątownik 40×40×3, L = {g.GUIDE_B[1] - g.GUIDE_B[0]:.0f}",
             round(V["guide"][1] * (g.GUIDE_B[1] - g.GUIDE_B[0]) / 1000, 2), 4, ""],
            ["H", "Płyta zawiasu przy przyczepie", 4, "S235", "płaskownik 80×6, L = 200", 0.75, 4, "po 2 na rurę L1L i L1P"],
            ["Z", "Płyta zawiasu środkowego (A i B – ta sama)", 8, "S235", "płaskownik 100×6, L = 170", 0.8, 3, "po 2 na rurę L1L, L1P, L3"],
            ["S", "Płyta zaczepu sprężyny (oczko Ø17)", 2, "S235", "płaskownik 80×8, L = 150", 0.75, 3, "lewa na C1, prawa na L1P"],
            ["K", "Wspornik na belce przyczepy (oczko sprężyny Ø17)", 3, "S235", "kątownik 100×100×10, L = 130", 1.94, 5,
             "2 × zawias (x ±152…162; prawy trzyma też sprężynę), 1 × sprężyna lewa (x +369…379)"],
            ["SIATKA", "Siatka stalowa cięto-ciągniona ocynk (pokład)", 2, "stal ocynk", f"{WID:.0f} × 1250 (LWD w poprzek)",
             round(WID * L * 1e-6 * V["mesh"][1], 2), 0, "z 1 arkusza 1250×2500"]]
    return out


def bolts():
    F = SPR["F1_N"]
    return [
        ("M8×160", "zamkowa DIN 603 kl. 8.8 + podkładka + nakrętka samohamowna", 18, "skrzyżowania (6 podłużnic × 3 poprzeczki)"),
        ("M8×130", "zamkowa DIN 603 + podkładka + nakrętka samohamowna", 12, "prowadnice"),
        ("M12×80", "sześciokątna 8.8 + 2 podkładki + nakrętka samohamowna", 12, "płyty H (4), Z sekcji A (4), S (4)"),
        ("M12×90", "sześciokątna 8.8 + 2 podkładki + nakrętka samohamowna", 4, "płyty Z sekcji B"),
        ("M12×80", "sześciokątna 8.8 (DOPASUJ do belki)", 6, "3 wsporniki K → belka przyczepy"),
        ("M16×70", "sześciokątna 8.8 + podkładka + nakrętka samohamowna", 4, "osie oczek sprężyn (2 na płytach S, 2 na wspornikach K)"),
        ("M20×110", "sześciokątna 8.8 (gładki trzpień ≥ 64 mm) = SWORZEŃ, nakrętka NIEDOKRĘCONA", 4, "zawiasy"),
        ("Ø12×40", "sworzeń ISO 2341-B ze stali 8.8 / C45 ulepszanej + zawleczka, na łańcuszku", 2, "blokada do jazdy"),
        ("podkładka M12 gr. 6", "DIN 7349 (13×30×6)", 8, "dystans płyt Z sekcji B"),
        ("nit 4,8", "nit zrywalny stalowy 4,8, szeroki kołnierz", 12 + 8, "listwa T (12) + zapięcia (8)"),
        ("wkręt 4,8×19", "wkręt samowiercący z podkładką EPDM", 70, "siatka, co ~250 mm"),
        ("tuleja Ø12×1,5 dł. 139,5", "rura stal bezszwowa ocynk", 18, "skrzyżowania"),
        ("tuleja Ø12×1,5 dł. 99,5", "rura stal bezszwowa ocynk", 12, "prowadnice"),
        ("tuleja Ø18×2,5 dł. 40", "rura stal bezszwowa ocynk", 16, "płyty H, Z, S"),
        ("tuleja Ø18×2,5 dł. 50", "rura stal bezszwowa ocynk (DOPASUJ do belki)", 6, "belka przyczepy"),
        ("tuleja Ø25×5 dł. 22 / 25 / 16 / 16", "rura stal", 4, "dystanse oczek: S lewa 22, S prawa 25, K 16 i 16"),
        (f"sprężyna gazowa 460/200 {F} N", "Ø40, oczka Ø16 (M16)", 2, "lewa: C1 ↔ K sprężyny; prawa: L1P ↔ K zawiasu"),
    ]


def buy():
    sk = stal.sticks
    return [
        (f"Rura stalowa prostokątna {LANE_P}", f"8 × 1250 mm = {sk(8 * L)} sztangi 6 m",
         "rury jezdne. MUSI być S355 (S355J2H / S355MH); zamiennik 100×40×3 S235 (+20 kg)"),
        (f"Rura stalowa prostokątna {WALK_P}", "4 × 1250 mm = 1 sztanga 6 m", "podłużnice chodnika C1–C3"),
        (f"Rura stalowa prostokątna {CROSS_P}", f"3 × {WID:.0f} mm (1 sztanga 6 m, zostaje na listwę i zapas)", "poprzeczki P"),
        ("Kątownik stalowy 40×40×3", "2 × 1095 + 2 × 715 mm (1 sztanga 6 m)", "prowadnice"),
        ("Płaskownik stalowy 40×5", f"{WID:.0f} mm", "listwa T"),
        ("Siatka cięto-ciągniona stalowa ocynk ~30×12×2×1,5 (~4 kg/m²), arkusz 1250×2500", f"1 arkusz → 2 × {WID:.0f}×1250",
         "pokład; dostawca ma potwierdzić 160 kg w punkcie na przęśle 190 mm"),
        ("Płaskownik stal 80×6 / 100×6 / 80×8", "0,85 m / 1,4 m / 0,3 m", "płyty H / Z / S"),
        ("Kątownik stal 100×100×10", "3 × 130 mm (0,4 m)", "wsporniki K"),
        ("Rura stal bezszwowa Ø12×1,5 / Ø18×2,5 / Ø25×5", "3,8 m / 1,0 m / 0,1 m", "tuleje"),
        (f"Sprężyna gazowa 460 mm / skok 200 / {SPR['F1_N']} N, Ø40, oczka Ø16", "2", "dobrana do masy trapu"),
        ("Zapięcie dźwigniowe z regulowanym kabłąkiem, zasięg ≥ 180 mm, ≥ 200 daN (lub pas z grzechotką)", "2", "spina złożone sekcje"),
        ("Pasek gumy EPDM 3–5 mm × 40 mm", "ok. 3 m", "pod skosy przy ziemi (6 × 0,5 m)"),
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
    old = (copy.deepcopy(g.S_PL), copy.deepcopy(g.K_PL), g.holes_long, g.OUT, dict(g.SPRING), g.TEMPL_NAME)
    plates_patch()
    g.K_PL["n"] = 3
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
        worst = max((r for r in ROWS if not r["nazwa"].startswith("[INFO]")), key=lambda r: r["wytezenie"])
        with PdfPages(os.path.join(OUT, "rysunki_trap_S5.pdf")) as pdf:
            g.page_text(pdf, "Trap STALOWY S5 – optymalnie lekki, chodnik z lewej, 2,5 × 0,74 m (bez spawania)", [
                f"Masa trapu ok. {mA + mB:.0f} kg (A {mA:.0f} kg, B {mB:.0f} kg) + 3 wsporniki K ok. 5,8 kg. Podłoga {g.H_FLOOR:.0f} mm, kąt {g.ALPHA:.1f}°.",
                f"Sprężyny 2 × {SPR['F1_N']} N (Ø40, oczka M16): podnoszenie ok. {SPR['max_wysilek_kg']:.0f} kg (bez sprężyn {max(r['user_kg'] for r in LIFT0):.0f} kg).",
                f"Najbardziej obciążona część: {worst['wytezenie'] * 100:.0f} % – {worst['nazwa']}.",
                "",
                "LEWA strona = patrząc od ziemi na przyczepę (od tej strony pchasz motocykl, od strony stopki). Na rysunkach x > 0.",
                "",
                "CO INNE NIŻ W WERSJI ALUMINIOWEJ V2:",
                "  • Materiał: rury jezdne RHS 100×40×2 S355J2H, podłużnice 100×40×1,5 S235, poprzeczki 60×40×2 (na płasko), kątowniki 40×40×3, siatka stalowa.",
                "  • Chodnik tylko z lewej: 2 podłużnice chodnika zamiast 4, poprzeczki i siatka 740 mm, prawa rura jezdna L1P = prawa krawędź.",
                "  • Rury L1L (lewa) i L1P (prawa) różnią się 2 otworami: L1P ma płytę S prawej sprężyny.",
                "  • Prawa sprężyna: górne oczko na płycie S na L1P, dolne na wsporniku K zawiasu (otwór „sprężyna” w K). Wsporniki K: 3 zamiast 4.",
                "  • Oczka sprężyn: śruba M16 + tuleja Ø25×5, otwór oczka w S i K Ø17 (szablony już mają Ø17).",
                "  • Sworznie blokady ze stali 8.8 / C45 ulepszanej. Bez pasty i podkładek izolujących (stal na stali).",
                "",
                "ZASADY: otwory pod tuleje Ø tulei + 0,5 mm; płyty H i Z wierć w pakiecie; zawias środkowy wierć po ułożeniu rur czołami;",
                "M8 20 N·m, M12 40 N·m, M16 60 N·m; sworznie M20 niedokręcone; CYNKOWANIE OGNIOWE PO WIERCENIU (albo farba).",
                "Wsporniki K i śruby do belki są dla PRZYKŁADOWEJ belki 50×75 – podaj swoje wymiary przed wierceniem.",
            ], fs=8)
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
        g.S_PL, g.K_PL, g.holes_long, g.OUT, g.SPRING, g.TEMPL_NAME = old


if __name__ == "__main__":
    main()
