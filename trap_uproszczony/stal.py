# -*- coding: utf-8 -*-
"""
Warianty STALOWE trapu. Ten sam układ, te same wymiary zewnętrzne profili, te same otwory, rysunki,
szablony i model 3D (poza wariantem „1 chodnik”, który jest węższy).

  python3 stal.py   ->  stal_warianty.csv, stal_obliczenia.csv, stal_lista_zakupow.csv, porownanie_kosztow.csv, stal_dane.json

Warianty:
  S1  stal ciężka     – S235, ścianki 3/2/2 mm, siatka stalowa 7 kg/m²         (pierwsze przeliczenie)
  S2  stal LEKKA      – rury jezdne S355 2 mm, podłużnice 1,5 mm, lżejsza siatka stalowa  ← POLECANA stalowa
  S3  stal lekka, 1 chodnik – jak S2, ale chodnik tylko po lewej stronie (szer. 740 mm) – wymaga nowych rysunków

CENY to założenia (netto, PLN) – wpisz ceny ze swojej hurtowni i uruchom ponownie.
"""
import copy, csv, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g

OUT = os.path.dirname(os.path.abspath(__file__))
RHO_ST = 7.85e-6
G = 9.81
STICK = 6000.0

CENY = {
    "al_6082_kg": 40.0,        # rura Al 6082-T6 (PA4)
    "al_6060_kg": 34.0,        # profile Al 6060 (np. 80×40×3 ok. 63 zł/m netto ≈ 34 zł/kg)
    "st_s235_kg": 6.5,         # stal S235JRH – profile zamknięte, kątowniki, płaskowniki
    "st_s355_kg": 7.5,         # stal S355J2H – profile zamknięte (rzadziej na stanie, zapytaj hurtownię)
    "cynk_ogniowy_kg": 4.5,    # cynkowanie ogniowe po wierceniu
    "farba_kpl": 180.0,        # zamiast cynku: podkład epoksydowy + farba
    "siatka_al_m2": 110.0,     # siatka cięto-ciągniona Al ~43×13×3×2 (2,5 kg/m²)
    "siatka_st_m2": 75.0,      # siatka cięto-ciągniona stal ocynk ~43×13×3×2 (7 kg/m²)
    "siatka_st_lekka_m2": 65.0,  # siatka cięto-ciągniona stal ocynk ~30×12×2×1,5 (~4 kg/m²)
    "sprezyna_28": 90.0,       # sprężyna gazowa 460/200, Ø28, do ~2500 N
    "sprezyna_40": 230.0,      # sprężyna gazowa 460/200, Ø40, do ~5000 N
    "wspolne": 750.0,          # płyty, wsporniki K, tuleje, śruby, sworznie, nity, wkręty, zapięcia, guma
}


def rhs(b, h, t):
    A = b * h - (b - 2 * t) * (h - 2 * t)
    I = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12.0
    return dict(A=A, I=I, W=I / (h / 2), kgm=A * RHO_ST * 1000, t=t)


def angle_kgm(a, t):
    return (2 * a - t) * t * RHO_ST * 1000


VARIANTS = {
    "S1": dict(nazwa="stal ciężka (S235, ścianki 3/2/2 mm)", lane=("RHS 100×40×3 S235JRH", rhs(40, 100, 3), 235, 360, "st_s235_kg"),
               walk=("RHS 100×40×2 S235JRH", rhs(40, 100, 2), 235, 360), cross=("RHS 60×40×2 S235JRH (na płasko)", rhs(60, 40, 2), 235, 360),
               guide=("kątownik 40×40×3", angle_kgm(40, 3)), mesh=("siatka stal ocynk ~43×13×3×2", 7.0, "siatka_st_m2"),
               n_walk=4, width=g.WIDTH),
    "S2": dict(nazwa="stal LEKKA (rury jezdne S355 2 mm, podłużnice 1,5 mm, lżejsza siatka)",
               lane=("RHS 100×40×2 S355J2H", rhs(40, 100, 2), 355, 470, "st_s355_kg"),
               walk=("RHS 100×40×1,5 S235JRH", rhs(40, 100, 1.5), 235, 360), cross=("RHS 60×40×2 S235JRH (na płasko)", rhs(60, 40, 2), 235, 360),
               guide=("kątownik 40×40×3", angle_kgm(40, 3)), mesh=("siatka stal ocynk ~30×12×2×1,5", 4.0, "siatka_st_lekka_m2"),
               n_walk=4, width=g.WIDTH),
    "S3": dict(nazwa="stal lekka, chodnik tylko z lewej (szer. 740 mm)",
               lane=("RHS 100×40×2 S355J2H", rhs(40, 100, 2), 355, 470, "st_s355_kg"),
               walk=("RHS 100×40×1,5 S235JRH", rhs(40, 100, 1.5), 235, 360), cross=("RHS 60×40×2 S235JRH (na płasko)", rhs(60, 40, 2), 235, 360),
               guide=("kątownik 40×40×3", angle_kgm(40, 3)), mesh=("siatka stal ocynk ~30×12×2×1,5", 4.0, "siatka_st_lekka_m2"),
               n_walk=2, width=g.X_LANE_OUT + 20 + g.X_EDGE + 20),
}
# warianty ze ZMIENIONĄ konstrukcją (optymalizacja masy) – wymagają nowych rysunków
_light = dict(lane=("RHS 100×40×2 S355J2H", rhs(40, 100, 2), 355, 470, "st_s355_kg"),
              walk=("RHS 100×40×1,5 S235JRH", rhs(40, 100, 1.5), 235, 360), cross=("RHS 60×40×2 S235JRH (na płasko)", rhs(60, 40, 2), 235, 360),
              guide=("kątownik 40×40×3", angle_kgm(40, 3)), mesh=("siatka stal ocynk ~30×12×2×1,5", 4.0, "siatka_st_lekka_m2"))
VARIANTS["S4"] = dict(nazwa="stal optymalna, pełna szerokość 1190 mm", n_walk=4, width=g.WIDTH, lane_mm=282, **_light)
VARIANTS["S5"] = dict(nazwa="stal optymalna, chodnik tylko z lewej (szer. 740 mm)", n_walk=2, width=g.X_LANE_OUT + 20 + g.X_EDGE + 20,
                      lane_mm=282, eye_lever=32.0, **_light)
# S5 po odchudzeniu: chodnik 340 mm (C1 x=305, C2 x=465), pojedyncze płyty H/Z, tanie sprężyny Ø28 z osią M12 i tuleją Ø22×5
S5_WALK, S5_EDGE = 305.0, 465.0
VARIANTS["S5L"] = dict(nazwa="S5 lekki i tani: chodnik 340 mm, pojedyncze płyty zawiasów, sprężyny Ø28", n_walk=2,
                       width=g.X_LANE_OUT + 20 + S5_EDGE + 20, edge_x=S5_EDGE, lane_mm=282, single_plates=True, spring_max=2500,
                       eye_lever=34.0, eye_tube=(22, 12, "Ø22×5 + M12"), wspolne_delta=-60.0, **_light)
VARIANTS["S6"] = dict(nazwa="stal optymalna, chodnik z lewej + 3 rury pod koło (szer. 660 mm, pas 222 mm) – tylko opony do ~180 mm, NIE dla tylnej opony 240", n_walk=2, n_lane=3,
                      width=120 + g.X_EDGE - g.X_WALK + g.X_WALK + 20, lane_mm=222, **_light)
RECOMMENDED = "S2"
FY_PL = 235.0


def masses(v):
    L, SK = g.L_SEC, g.SKOS

    def acc(items):
        m = sum(i[0] for i in items)
        return m, sum(i[0] * i[1] for i in items) / m, sum(i[0] * i[2] for i in items) / m
    lane, walk, cross = v["lane"][1], v["walk"][1], v["cross"][1]
    W = v["width"]
    npl = 2 if v.get("single_plates") else 4            # płyty H i Z: po 1 albo po 2 na rurę zewnętrzną
    plates = [(npl * 200 * 80 * 6 * RHO_ST, 50.0, 60.0), (npl * 170 * 100 * 6 * RHO_ST, L - 55.0, -10.0),
              (2 * 150 * 80 * 8 * RHO_ST, 259.0, 25.0), (3.2, L / 2, 50.0)]
    nl = v.get("n_lane", 4)
    A = [(nl * lane["kgm"] * L / 1000, L / 2, 50.0), (v["n_walk"] * walk["kgm"] * L / 1000, L / 2, 50.0)]
    A += [(cross["kgm"] * W / 1000, s, -g.CROSS_H / 2) for s in g.CROSS_A]
    A += [(W * L * 1e-6 * v["mesh"][1], L / 2, 101.5), (2 * v["guide"][1] * (g.GUIDE_A[1] - g.GUIDE_A[0]) / 1000, sum(g.GUIDE_A) / 2, 115.0)]
    A += plates
    B = []
    for p, n in ((lane, nl), (walk, v["n_walk"])):
        full = p["kgm"] * L / 1000
        cut = (SK * 40 * p["t"] + SK * 100 * p["t"]) * RHO_ST
        B += [(n * full, L / 2, 50.0), (-n * cut, L - SK / 3, 25.0)]
    B += [(cross["kgm"] * W / 1000, s, -g.CROSS_H / 2) for s in g.CROSS_B]
    B += [(40 * 5 * W * RHO_ST, g.TIE_B, -2.5), (W * L * 1e-6 * v["mesh"][1], L / 2, 101.5),
          (2 * v["guide"][1] * (g.GUIDE_B[1] - g.GUIDE_B[0]) / 1000, sum(g.GUIDE_B) / 2, 115.0),
          (npl * 170 * 100 * 6 * RHO_ST + (0.13 if npl == 2 else 0.26), 55.0, -10.0), (1.6, 500.0, 50.0)]
    return acc(A), acc(B)


def lift(mA, cA, mB, cB, F1, n):
    old = copy.deepcopy(g.SPRING)
    g.SPRING.update(F1=F1, n=n)
    try:
        return g.lift_table(mA, cA[0], cA[1], mB, cB[0], cB[1], n > 0)
    finally:
        g.SPRING.clear()
        g.SPRING.update(old)


def pick_springs(mA, cA, mB, cB, fmax_all=5000):
    """najmniejszy wysiłek przy: rozłożony leży na ziemi (moment w dół ≥ 60 N·m), w pionie nie pcha (< 60 N·m);
    fmax_all = 2500 -> tylko tanie sprężyny Ø28"""
    cands = []
    for n, fmax in ((2, min(5000, fmax_all)), (4, 2500)):
        for F1 in range(1600, fmax + 1, 100):
            lt = lift(mA, cA, mB, cB, F1, n)
            mx, down, top = max(r["user_kg"] for r in lt), lt[0]["Tg"] + lt[0]["Ts"], lt[-1]["Tg"] + lt[-1]["Ts"]
            if down < -60 and top < 60:
                cands.append((mx + (1.5 if n == 4 else 0), n, F1, lt, mx, down, top))
    _, n, F1, lt, mx, down, top = min(cands, key=lambda c: c[0])
    return dict(sztuk=n, F1_N=F1, max_wysilek_kg=mx, moment_rozlozony_Nm=round(down, 1), moment_pion_Nm=round(top, 1)), lt


def calcs(v, mA, mB, F1):
    rows = []

    def add(name, load, cap, unit, note=""):
        rows.append(dict(nazwa=name, obciazenie=round(load, 2), nosnosc=round(cap, 2), jedn=unit, wytezenie=round(load / cap, 3), uwagi=note))
    L = 2 * g.L_SEC
    Pk = g.WHEEL_KG * G / 1000
    Pd = Pk * g.PHI * g.GAMMA_F
    Fd = g.FOOT_KG * G / 1000 * g.PHI * g.GAMMA_F
    (ln, lane, lfy, lfu, _), (wn, walk, wfy, wfu), (cn, cross, cfy, cfu) = v["lane"], v["walk"], v["cross"]
    q_d = g.GAMMA_G * (mA + mB) * G / 1000 / 2 / L
    M75 = 0.75 * Pd * L / 4 + q_d * L ** 2 / 8
    M100 = Pd * L / 4 + q_d * L ** 2 / 8
    add(f"Rura jezdna {ln} – zginanie, rozpiętość 2,5 m (75 % koła)", M75 * 1e3 / lane["W"], lfy, "MPa", "")
    add("To samo – całe koło na jednej rurze", M100 * 1e3 / lane["W"], lfy, "MPa", "")
    qk = (mA + mB) * G / 1000 / 2 / L
    dk = 0.75 * Pk * 1e3 * L ** 3 / (48 * 210000 * lane["I"]) + 5 * qk * 1e3 * L ** 4 / (384 * 210000 * lane["I"])
    add("Ugięcie w środku (charakterystyczne)", dk, L / 200, "mm", "")
    add(f"Rura jezdna wewnętrzna – wspornik przy zawiasie {g.L_SEC - g.CROSS_A[-1]:.0f} mm", Pd * (g.L_SEC - g.CROSS_A[-1]) * 1e3 / lane["W"], lfy, "MPa", "")
    t = lane["t"]
    add(f"Rura jezdna – ścianka górna {fmt(t)} mm pod oponą (zginanie poprzeczne)", Pd * 1e3 / 2 * 34 / 8 / (120 * t ** 2 / 6), lfy, "MPa",
        "pół koła na rurę, ślad opony 120 mm wzdłuż, ścianka 34 mm między bokami")
    add(f"Poprzeczka {cn} – stopa na samej krawędzi", Fd * (v.get("edge_x", g.X_EDGE) - g.X_LANE_OUT) * 1e3 / cross["W"], cfy, "MPa", "")
    add(f"Podłużnica chodnika {wn} – wspornik {g.L_SEC - g.CROSS_A[-1]:.0f} mm", Fd * (g.L_SEC - g.CROSS_A[-1]) * 1e3 / walk["W"], wfy, "MPa", "")
    F = M75 / 135.0
    Rb = math.hypot(F / 2 * 55 / 65, F / 4)
    if v.get("single_plates"):
        # jedna płyta Z na zewnątrz rury: sworzeń jednocięty + zginanie, śruby M12 jednocięte, skręcanie rury od mimośrodu
        add("Zawias środkowy: sworzeń Ø20 C45 – ścinanie (jedna płaszczyzna)", F / 2, 0.6 * 600 * math.pi * 100 / 1.25 / 1e3, "kN",
            "jedna płyta Z na rurę, płyty A i B stykają się")
        Mp = F / 2 * 1e3 * 6.0
        add("Zawias środkowy: sworzeń Ø20 C45 – zginanie (ramię 6 mm)", Mp / (math.pi * 20 ** 3 / 32), 355.0, "MPa", "C45 ulepszana ≥ 355 MPa")
        add("Zawias środkowy: śruba M12 8.8 – ścinanie (jednocięta)", 2 * Rb, 0.6 * 800 * 84.3 / 1.25 / 1e3, "kN", "jedna płyta Z")
        add(f"Zawias środkowy: tuleja Ø18 → ścianka rury {fmt(t)} mm (docisk, 75 % na ściankę zewn.)", 1.5 * Rb,
            2.5 * min(45 / 55.5, 1) * lfu * 18 * t / 1.25 / 1e3, "kN", "")
        Tt = F / 2 * 1e3 * 23.0
        add("Rura jezdna zewnętrzna – skręcanie od mimośrodu płyty Z (23 mm)", Tt / (2 * (100 - t) * (40 - t) * t) * math.sqrt(3), lfy, "MPa",
            "naprężenie zastępcze od ścinania przy skręcaniu")
    else:
        add("Zawias środkowy: sworzeń M20 8.8 – ścinanie", F / 2, 0.6 * 800 * math.pi * 100 / 1.25 / 1e3, "kN", "")
        add("Zawias środkowy: śruba M12 8.8 – ścinanie", Rb, 0.6 * 800 * 84.3 / 1.25 / 1e3, "kN", "")
        add(f"Zawias środkowy: tuleja Ø18 → ścianka rury {fmt(t)} mm (docisk)", Rb, 2.5 * min(45 / 55.5, 1) * lfu * 18 * t / 1.25 / 1e3, "kN", "")
    Fpin = (mA + mB) * G * 0.8 * 1.5 / 1000 * 620.0 / 30.0 / 2
    add("Blokada do jazdy: sworzeń Ø12 8.8 / C45 – ścinanie", Fpin, 0.6 * 800 * math.pi * 36 / 1.25 / 1e3, "kN", f"trap w pionie {mA + mB:.0f} kg, hamowanie 0,8 g ×1,5")
    add("Blokada: docisk sworznia Ø12 w płycie H 6 mm", Fpin, 2.5 * min(25 / 39, 1) * 360 * 12 * 6 / 1.25 / 1e3, "kN", "")
    Fs = F1 * 1.3 * 1.5 / 1000
    eye = v.get("eye_tube") or ((20, 12, "Ø20×4 + M12") if F1 <= 2500 else (25, 15, "Ø25×5 + M16"))
    lev = v.get("eye_lever", 23.0)
    add(f"Oczko sprężyny: tuleja {eye[2]} – zginanie", Fs * 1e3 * lev / (math.pi * (eye[0] ** 4 - eye[1] ** 4) / (32 * eye[0])), FY_PL, "MPa",
        f"sprężyna {F1:.0f} N, ramię {lev:g} mm od blachy")
    add(f"Płyta S – śruby M12 w ściance podłużnicy {fmt(walk['t'])} mm (docisk)", Fs * 72 / 50 / 2 + Fs / 2,
        2.5 * min(40 / 55.5, 1) * wfu * 18 * walk["t"] / 1.25 / 1e3, "kN", "")
    return rows


def fmt(x):
    return f"{x:g}".replace(".", ",")


def sticks(total_mm):
    return math.ceil(total_mm / (STICK - 30))


def cost(v, mA, mB, spr):
    c = CENY
    L = g.L_SEC
    W = v["width"]
    mesh_m2 = 1.25 * 2.5
    gd = 2 * (g.GUIDE_A[1] - g.GUIDE_A[0]) + 2 * (g.GUIDE_B[1] - g.GUIDE_B[0])
    nl, nw = sticks(2 * v.get("n_lane", 4) * L), sticks(2 * v["n_walk"] * L)
    out = [("Rury jezdne", nl * 6 * v["lane"][1]["kgm"] * c[v["lane"][4]], f"{nl} sztangi {v['lane'][0]}"),
           ("Podłużnice chodnika", nw * 6 * v["walk"][1]["kgm"] * c["st_s235_kg"], f"{nw} sztangi {v['walk'][0]}"),
           ("Poprzeczki", math.ceil(3 * W / 5970) * 6 * v["cross"][1]["kgm"] * c["st_s235_kg"], v["cross"][0]),
           ("Prowadnice + listwa T", (math.ceil(gd / 5970) * 6 * v["guide"][1] + W / 1000 * 1.57) * c["st_s235_kg"], f"{v['guide'][0]}, płaskownik 40×5"),
           ("Siatka", mesh_m2 * c[v["mesh"][2]], v["mesh"][0]),
           ("Ochrona przed korozją", (mA + mB - 2 * W * L * 1e-6 * v["mesh"][1]) * c["cynk_ogniowy_kg"], "cynkowanie ogniowe po wierceniu"),
           ("Sprężyny gazowe", spr["sztuk"] * (c["sprezyna_40"] if spr["F1_N"] > 2500 else c["sprezyna_28"]),
            f"{spr['sztuk']} × {spr['F1_N']} N" + (" Ø40" if spr["F1_N"] > 2500 else " Ø28")),
           ("Wspólne (płyty, wsporniki K, tuleje, śruby, sworznie, nity, zapięcia)", c["wspolne"] + 40 + v.get("wspolne_delta", 0.0),
            "sworznie blokady 8.8" + ("; 6 płyt H/Z mniej, sworznie Ø20 z zawleczką" if v.get("single_plates") else ""))]
    return out


def cost_al(mA, mB):
    c = CENY
    L = g.L_SEC
    gd = 2 * (g.GUIDE_A[1] - g.GUIDE_A[0]) + 2 * (g.GUIDE_B[1] - g.GUIDE_B[0])
    return [("Rury jezdne", sticks(8 * L) * 6 * g.P_LANE["kgm"] * c["al_6082_kg"], "Al 100×40×3 6082-T6"),
            ("Podłużnice chodnika", sticks(8 * L) * 6 * g.P_WALK["kgm"] * c["al_6060_kg"], "Al 100×40×2"),
            ("Poprzeczki", 6 * g.P_CROSS["kgm"] * c["al_6060_kg"], "Al 60×40×4"),
            ("Prowadnice + listwa T", (math.ceil(gd / 5970) * 6 * g.ANGLE_KGM + 1.2 * 0.54) * c["al_6060_kg"], "Al 40×40×4, 40×5"),
            ("Siatka", 1.25 * 2.5 * c["siatka_al_m2"], "Al 43×13×3×2"),
            ("Ochrona przed korozją", 0.0, "niepotrzebna"),
            ("Sprężyny gazowe", 2 * c["sprezyna_28"], "2 × 1600 N Ø28"),
            ("Wspólne (płyty, wsporniki K, tuleje, śruby, sworznie, nity, zapięcia)", c["wspolne"], "")]


def main():
    (aA, aAs, aAz), (aB, aBs, aBz) = g.masses()
    al_l0 = max(r["user_kg"] for r in g.lift_table(aA, aAs, aAz, aB, aBs, aBz, False))
    al_l = max(r["user_kg"] for r in g.lift_table(aA, aAs, aAz, aB, aBs, aBz, True))
    al_cost = cost_al(aA, aB)
    res = {}
    for key, v in VARIANTS.items():
        (mA, cAs, cAz), (mB, cBs, cBz) = masses(v)
        l0 = lift(mA, (cAs, cAz), mB, (cBs, cBz), 0, 0)
        spr, lt = pick_springs(mA, (cAs, cAz), mB, (cBs, cBz), v.get("spring_max", 5000))
        rows = calcs(v, mA, mB, spr["F1_N"])
        cst = cost(v, mA, mB, spr)
        res[key] = dict(v=v, mA=mA, mB=mB, l0=max(r["user_kg"] for r in l0), spr=spr, lt=lt, rows=rows, cost=cst,
                        tot=sum(c[1] for c in cst), worst=max(rows, key=lambda r: r["wytezenie"]))
    tot_al = sum(c[1] for c in al_cost)

    with open(os.path.join(OUT, "stal_warianty.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["wariant", "masa [kg]", "podnoszenie bez sprężyn [kg]", "sprężyny", "podnoszenie ze sprężynami [kg]",
                    "koszt materiału z cynkiem [zł]", "najbardziej obciążona część"])
        w.writerow(["Al V2 – aluminium", round(aA + aB), round(al_l0), "2 × 1600 N", round(al_l), round(tot_al), "88%"])
        for k, r in res.items():
            w.writerow([f"{k} – {r['v']['nazwa']}", round(r["mA"] + r["mB"]), round(r["l0"]), f"{r['spr']['sztuk']} × {r['spr']['F1_N']} N",
                        round(r["spr"]["max_wysilek_kg"]), round(r["tot"]), f"{r['worst']['wytezenie'] * 100:.0f}% – {r['worst']['nazwa']}"])
    R = res[RECOMMENDED]
    with open(os.path.join(OUT, "stal_obliczenia.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([f"wariant {RECOMMENDED}: {R['v']['nazwa']}"])
        w.writerow(["element", "obciążenie", "nośność", "jedn.", "wytężenie", "uwagi"])
        for r in R["rows"]:
            w.writerow([r["nazwa"], r["obciazenie"], r["nosnosc"], r["jedn"], r["wytezenie"], r["uwagi"]])
    cost_rows = []
    for i, (name, val, note) in enumerate(al_cost):
        cost_rows.append([name, round(val), round(res["S1"]["cost"][i][1]), round(R["cost"][i][1]), R["cost"][i][2]])
    cost_rows.append(["RAZEM (netto, orientacyjnie)", round(tot_al), round(res["S1"]["tot"]), round(R["tot"]),
                      f"z farbą zamiast cynku: S2 ok. {R['tot'] - R['cost'][5][1] + CENY['farba_kpl']:.0f} zł"])
    with open(os.path.join(OUT, "porownanie_kosztow.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pozycja", "aluminium V2 [zł]", "stal ciężka S1 [zł]", f"stal lekka {RECOMMENDED} [zł]", "uwagi (S2)"])
        w.writerows(cost_rows)
        w.writerow([])
        w.writerow(["założone ceny netto (zmień w stal.py → CENY)"] + [f"{k}={v:g}" for k, v in CENY.items()])
    v = R["v"]
    sp = R["spr"]
    buy = [
        (f"Rura stalowa prostokątna {v['lane'][0]}", f"8 × 1250 mm = {sticks(8 * g.L_SEC)} sztangi 6 m",
         "rury jezdne L1–L4. MUSI być S355 (S355J2H / S355MH) – z S235 przy 2 mm za słaba. Zamiennik: 100×40×3 S235 (+20 kg)"),
        (f"Rura stalowa prostokątna {v['walk'][0]}", f"8 × 1250 mm = {sticks(8 * g.L_SEC)} sztangi 6 m", "podłużnice chodnika C1–C3"),
        (f"Rura stalowa prostokątna {v['cross'][0]}", "3 × 1190 mm (1 sztanga)", "poprzeczki P"),
        (f"Kątownik stalowy 40×40×3", "2 × 1095 + 2 × 715 mm (1 sztanga)", "prowadnice G1/G2"),
        ("Płaskownik stalowy 40×5", "1190 mm", "listwa T"),
        (f"{v['mesh'][0]} (~{fmt(v['mesh'][1])} kg/m²)", "1 arkusz 1250×2500",
         "pokład – niesie tylko stopy; dostawca ma potwierdzić 160 kg w punkcie na przęśle 190 mm"),
        (f"Sprężyna gazowa 460 mm / skok 200 / {sp['F1_N']} N" + (" Ø40" if sp["F1_N"] > 2500 else " Ø28"), str(sp["sztuk"]),
         "dobrana do masy" + ("; oś oczek M16 + tuleja Ø25×5, otwory oczek w K i S rozwierć do Ø17" if sp["F1_N"] > 2500 else "")),
        ("Sworzeń blokady Ø12×40 ze stali 8.8 / C45 ulepszanej", "2", "zwykła stal automatowa za słaba przy tej masie"),
        ("Cynkowanie ogniowe części stalowych PO wierceniu (albo podkład epoksydowy + farba)", "", "bez tego stal rdzewieje"),
        ("Pozostałe: płyty H, Z, S, wsporniki K, tuleje, śruby, nity, wkręty, zapięcia, guma", "jak lista_zakupow.csv",
         "bez pasty i podkładek izolujących – stal na stali nie koroduje galwanicznie"),
    ]
    with open(os.path.join(OUT, "stal_lista_zakupow.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pozycja", "ilość", "uwagi"])
        w.writerows(buy)
    variants = [dict(klucz="Al", nazwa="aluminium V2", masa=round(aA + aB, 1), bez=round(al_l0, 1), sprezyny="2 × 1600 N (Ø28)",
                     ze=round(al_l, 1), koszt=round(tot_al), wyt=0.88, rysunki="bez zmian")]
    for k, r in res.items():
        variants.append(dict(klucz=k, nazwa=r["v"]["nazwa"], masa=round(r["mA"] + r["mB"], 1), bez=round(r["l0"], 1),
                             sprezyny=f"{r['spr']['sztuk']} × {r['spr']['F1_N']} N ({'Ø40' if r['spr']['F1_N'] > 2500 else 'Ø28'})",
                             ze=round(r["spr"]["max_wysilek_kg"], 1), koszt=round(r["tot"]), wyt=r["worst"]["wytezenie"],
                             rysunki="nowe rysunki (węższy trap)" if k == "S3" else "bez zmian"))
    summary = dict(polecany=RECOMMENDED, masa_al=round(aA + aB, 1), masa_stal=round(R["mA"] + R["mB"], 1),
                   wysilek_bez_sprezyn_stal=round(R["l0"], 1), sprezyny_stal=sp, koszt_al=round(tot_al), koszt_stal=round(R["tot"]),
                   najwieksze_wytezenie=dict(element=R["worst"]["nazwa"], wartosc=R["worst"]["wytezenie"]))
    with open(os.path.join(OUT, "stal_dane.json"), "w", encoding="utf-8") as f:
        json.dump(dict(podsumowanie=summary, warianty=variants, obliczenia=R["rows"], koszty=cost_rows, zakupy=buy, ceny=CENY,
                       podnoszenie=R["lt"]), f, ensure_ascii=False, indent=1)
    for x in variants:
        print(x)
    for r in R["rows"]:
        print(f"{r['wytezenie']:5.2f}  {r['nazwa']}")
    for r in cost_rows:
        print(r)
    return summary


if __name__ == "__main__":
    main()
