# -*- coding: utf-8 -*-
"""
Wariant BUDŻETOWY ze stali – ten sam układ, te same wymiary zewnętrzne profili, te same otwory,
rysunki, szablony i model 3D. Zmieniają się tylko materiał i grubości ścianek, siatka i sprężyny.

  python3 stal.py   ->  stal_obliczenia.csv, stal_lista_zakupow.csv, porownanie_kosztow.csv, stal_dane.json

CENY to założenia (netto, PLN) – wpisz ceny ze swojej hurtowni w CENY poniżej i uruchom ponownie.
"""
import copy, csv, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g

OUT = os.path.dirname(os.path.abspath(__file__))
RHO_ST = 7.85e-6
G = 9.81

# ------------------------------------------------------------------ CENY (założenia – sprawdź!)
CENY = {
    "al_6082_kg": 40.0,        # rura Al 6082-T6 (PA4) – droższa od 6060
    "al_6060_kg": 34.0,        # profile Al 6060 (np. 80×40×3 ok. 63 zł/m netto ≈ 34 zł/kg)
    "st_profil_kg": 6.5,       # stal S235JRH / S235JR – profile zamknięte, kątowniki, płaskowniki
    "cynk_ogniowy_kg": 4.5,    # cynkowanie ogniowe usługowo (po wierceniu, przed montażem)
    "farba_kpl": 180.0,        # zamiast cynku: podkład epoksydowy + farba, komplet
    "siatka_al_m2": 110.0,     # siatka cięto-ciągniona Al ~43×13×3×2
    "siatka_st_m2": 75.0,      # siatka cięto-ciągniona stal ocynk ~43×13×3×2
    "sprezyna_1600": 90.0,     # sprężyna gazowa 460/200, 1600 N, Ø28
    "sprezyna_mocna": 230.0,   # sprężyna gazowa 460/200, Ø40, do ~4000 N
    "wspolne": 750.0,          # płyty stalowe, kątowniki K, tuleje, śruby, sworznie, nity, wkręty, zapięcia, guma
}
STICK = 6000.0                 # profile kupujesz w sztangach 6 m


def rhs(b, h, t):
    A = b * h - (b - 2 * t) * (h - 2 * t)
    I = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12.0
    return dict(A=A, I=I, W=I / (h / 2))


# stal: te same wymiary zewnętrzne co w wersji Al
ST = dict(
    lane=("RHS 100×40×3 S235JRH", rhs(40, 100, 3), 3.0),
    walk=("RHS 100×40×2 S235JRH", rhs(40, 100, 2), 2.0),
    cross=("RHS 60×40×2 S235JRH", rhs(40, 60, 2), 2.0),
)
ANGLE_ST = (40 + 37) * 3 * RHO_ST * 1000      # kątownik 40×40×3 [kg/m]
MESH_ST_KGM2 = 7.0                            # siatka stalowa ~43×13×3×2
FY, FU, E_ST, GM0, GM2 = 235.0, 360.0, 210000.0, 1.0, 1.25


def kgm(p):
    return p["A"] * RHO_ST * 1000


def masses_steel():
    """masa i środek ciężkości sekcji A i B (jak generuj.masses, ale stal)"""
    L, SK = g.L_SEC, g.SKOS

    def acc(items):
        m = sum(i[0] for i in items)
        return m, sum(i[0] * i[1] for i in items) / m, sum(i[0] * i[2] for i in items) / m
    lane, walk, cross = (kgm(ST[k][1]) for k in ("lane", "walk", "cross"))
    plates = [(4 * 200 * 80 * 6 * RHO_ST, 50.0, 60.0), (4 * 170 * 100 * 6 * RHO_ST, L - 55.0, -10.0),
              (2 * 150 * 80 * 8 * RHO_ST, 259.0, 25.0), (3.2, L / 2, 50.0)]
    A = [(4 * lane * L / 1000, L / 2, 50.0), (4 * walk * L / 1000, L / 2, 50.0)]
    A += [(cross * g.WIDTH / 1000, s, -30.0) for s in g.CROSS_A]
    A += [(g.WIDTH * L * 1e-6 * MESH_ST_KGM2, L / 2, 101.5), (2 * ANGLE_ST * (g.GUIDE_A[1] - g.GUIDE_A[0]) / 1000, sum(g.GUIDE_A) / 2, 115.0)]
    A += plates
    B = []
    for k, t in ((lane, 3.0), (walk, 2.0)):
        full = k * L / 1000
        cut = (SK * 40 * t + SK * 100 * t) * RHO_ST
        B += [(4 * full, L / 2, 50.0), (-4 * cut, L - SK / 3, 25.0)]
    B += [(cross * g.WIDTH / 1000, s, -30.0) for s in g.CROSS_B]
    B += [(40 * 5 * g.WIDTH * RHO_ST, g.TIE_B, -2.5), (g.WIDTH * L * 1e-6 * MESH_ST_KGM2, L / 2, 101.5),
          (2 * ANGLE_ST * (g.GUIDE_B[1] - g.GUIDE_B[0]) / 1000, sum(g.GUIDE_B) / 2, 115.0),
          (4 * 170 * 100 * 6 * RHO_ST + 0.26, 55.0, -10.0), (1.6, 500.0, 50.0)]
    return acc(A), acc(B)


def lift(mA, cA, mB, cB, F1, n):
    old = copy.deepcopy(g.SPRING)
    g.SPRING.update(F1=F1, n=n)
    try:
        return g.lift_table(mA, cA[0], cA[1], mB, cB[0], cB[1], n > 0)
    finally:
        g.SPRING.clear()
        g.SPRING.update(old)


def calcs_steel(mA, mB, F1):
    rows = []

    def add(name, load, cap, unit, note=""):
        rows.append(dict(nazwa=name, obciazenie=round(load, 2), nosnosc=round(cap, 2), jedn=unit, wytezenie=round(load / cap, 3), uwagi=note))
    L = 2 * g.L_SEC
    Pk = g.WHEEL_KG * G / 1000
    Pd = Pk * g.PHI * g.GAMMA_F
    Fd = g.FOOT_KG * G / 1000 * g.PHI * g.GAMMA_F
    f = FY / GM0
    q_d = g.GAMMA_G * (mA + mB) * G / 1000 / 2 / L
    lane, walk, cross = ST["lane"][1], ST["walk"][1], ST["cross"][1]
    M75 = 0.75 * Pd * L / 4 + q_d * L ** 2 / 8
    M100 = Pd * L / 4 + q_d * L ** 2 / 8
    add("Rura jezdna RHS 100×40×3 S235 – zginanie, rozpiętość 2,5 m (75 % koła)", M75 * 1e3 / lane["W"], f, "MPa", "jak w wersji Al + większy ciężar własny")
    add("To samo – całe koło na jednej rurze", M100 * 1e3 / lane["W"], f, "MPa", "")
    qk = (mA + mB) * G / 1000 / 2 / L
    dk = 0.75 * Pk * 1e3 * L ** 3 / (48 * E_ST * lane["I"]) + 5 * qk * 1e3 * L ** 4 / (384 * E_ST * lane["I"])
    add("Ugięcie w środku (charakterystyczne)", dk, L / 200, "mm", "stal jest 3× sztywniejsza od Al")
    add(f"Rura jezdna wewnętrzna – wspornik przy zawiasie {g.L_SEC - g.CROSS_A[-1]:.0f} mm", Pd * (g.L_SEC - g.CROSS_A[-1]) * 1e3 / lane["W"], f, "MPa", "")
    add("Poprzeczka RHS 60×40×2 S235 – stopa na samej krawędzi", Fd * (g.X_EDGE - g.X_LANE_OUT) * 1e3 / cross["W"], f, "MPa", "")
    add(f"Podłużnica chodnika RHS 100×40×2 S235 – wspornik {g.L_SEC - g.CROSS_A[-1]:.0f} mm", Fd * (g.L_SEC - g.CROSS_A[-1]) * 1e3 / walk["W"], f, "MPa", "")
    arm = 135.0
    F = M75 / arm
    add("Zawias środkowy: sworzeń M20 8.8 – ścinanie", F / 2, 0.6 * 800 * math.pi * 100 / GM2 / 1e3, "kN", "")
    Rb = math.hypot(F / 2 * 55 / 65, F / 4)
    add("Zawias środkowy: śruba M12 8.8 – ścinanie", Rb, 0.6 * 800 * 84.3 / GM2 / 1e3, "kN", "")
    add("Zawias środkowy: tuleja Ø18 → ścianka stalowa 3 mm (docisk)", Rb, 2.5 * min(45 / 55.5, 1) * FU * 18 * 3 / GM2 / 1e3, "kN", "")
    Fb = (mA + mB) * G * 0.8 * 1.5 / 1000
    Fpin = Fb * 620.0 / 30.0 / 2
    add("Blokada do jazdy: sworzeń Ø12 – ścinanie (stal 8.8 / C45 ulepszana)", Fpin, 0.6 * 800 * math.pi * 36 / GM2 / 1e3, "kN",
        f"trap w pionie {mA + mB:.0f} kg, hamowanie 0,8 g ×1,5 – zwykły sworzeń St (400 MPa) NIE wystarczy")
    add("Blokada: docisk sworznia Ø12 w płycie H 6 mm", Fpin, 2.5 * min(25 / 39, 1) * FU * 12 * 6 / GM2 / 1e3, "kN",
        "płyta H 6 mm – w wariancie stalowym płyty H z płaskownika 80×8")
    Fs = F1 * 1.3 * 1.5 / 1000
    eye = (20, 12, "Ø20×4, śruba M12") if F1 <= 2500 else (25, 15, "Ø25×5, śruba M16 (otwory oczek w K i S rozwierć do Ø17)")
    add(f"Oczko sprężyny: tuleja {eye[2]} – zginanie", Fs * 1e3 * 23 / (math.pi * (eye[0] ** 4 - eye[1] ** 4) / (32 * eye[0])), FY, "MPa",
        f"sprężyna {F1:.0f} N, ramię 23 mm")
    add("Płyta S – śruby M12 w ściance stalowej 2 mm (docisk)", Fs * 72 / 50 / 2 + Fs / 2, 2.5 * min(40 / 55.5, 1) * FU * 18 * 2 / GM2 / 1e3, "kN", "")
    return rows


def sticks(total_mm):
    return math.ceil(total_mm / (STICK - 30))


def costs(mA_al, mB_al, mA_st, mB_st, n_spr_st, spr_st_strong):
    c = CENY
    L = g.L_SEC
    # długości (mm) z zapasem na sztangi
    lane_mm, walk_mm = 8 * L, 8 * L
    cross_mm = 3 * g.WIDTH
    guide_mm = 2 * (g.GUIDE_A[1] - g.GUIDE_A[0]) + 2 * (g.GUIDE_B[1] - g.GUIDE_B[0])
    mesh_m2 = 1.25 * 2.5
    al = g.P_LANE["kgm"], g.P_WALK["kgm"], g.P_CROSS["kgm"], g.ANGLE_KGM
    st = kgm(ST["lane"][1]), kgm(ST["walk"][1]), kgm(ST["cross"][1]), ANGLE_ST
    rows = []

    def line(name, al_val, st_val, note=""):
        rows.append([name, round(al_val), round(st_val), note])
    line("Rury jezdne (8 × 1250)", sticks(lane_mm) * STICK / 1000 * al[0] * c["al_6082_kg"], sticks(lane_mm) * STICK / 1000 * st[0] * c["st_profil_kg"],
         f"{sticks(lane_mm)} sztangi 6 m: Al 100×40×3 6082 / stal 100×40×3")
    line("Podłużnice chodnika (8 × 1250)", sticks(walk_mm) * 6 * al[1] * c["al_6060_kg"], sticks(walk_mm) * 6 * st[1] * c["st_profil_kg"],
         f"{sticks(walk_mm)} sztangi: 100×40×2")
    line("Poprzeczki (3 × 1190)", 6 * al[2] * c["al_6060_kg"], 6 * st[2] * c["st_profil_kg"], "1 sztanga: Al 60×40×3 / stal 60×40×2")
    line("Prowadnice + listwa T", (6 * al[3] + 1.2 * 0.54) * c["al_6060_kg"], (6 * st[3] + 1.2 * 1.57) * c["st_profil_kg"],
         "kątownik 40×40×4 Al / 40×40×3 stal, płaskownik 40×5")
    line("Siatka (arkusz 1250×2500)", mesh_m2 * c["siatka_al_m2"], mesh_m2 * c["siatka_st_m2"], "Al / stal ocynkowana")
    frame_st = (mA_st + mB_st) - 2 * 1250 * 1190 * 1e-6 * MESH_ST_KGM2
    line("Ochrona przed korozją", 0, frame_st * c["cynk_ogniowy_kg"], f"stal: cynkowanie ogniowe ok. {frame_st:.0f} kg (albo farba ~{c['farba_kpl']:.0f} zł)")
    line("Sprężyny gazowe", 2 * c["sprezyna_1600"], n_spr_st * (c["sprezyna_mocna"] if spr_st_strong else c["sprezyna_1600"]),
         f"Al: 2 × 1600 N / stal: {n_spr_st} × mocniejsze")
    line("Wspólne (płyty, wsporniki K, tuleje, śruby, sworznie, nity, zapięcia)", c["wspolne"], c["wspolne"] + 40,
         "stal: sworznie blokady 8.8, oś oczek M16; bez pasty i podkładek izolujących")
    tot_al = sum(r[1] for r in rows)
    tot_st = sum(r[2] for r in rows)
    rows.append(["RAZEM (netto, orientacyjnie)", tot_al, tot_st, f"różnica {tot_al - tot_st:+.0f} zł; z farbą zamiast cynku stal: "
                 f"{tot_st - rows[5][2] + c['farba_kpl']:.0f} zł"])
    return rows, tot_al, tot_st


def main():
    (mA, cAs, cAz), (mB, cBs, cBz) = masses_steel()
    (aA, aAs, aAz), (aB, aBs, aBz) = g.masses()
    l0 = lift(mA, (cAs, cAz), mB, (cBs, cBz), 0, 0)
    # dobór sprężyn: ta sama geometria; szukamy najmniejszej siły, przy której max wysiłek ≤ 25 kg,
    # a rozłożony trap dalej leży na ziemi (moment w dół) i w pionie nie pcha do przyczepy za mocno
    cands = []
    for n, fmax in ((2, 5000), (4, 2500)):          # Ø28 do ~2500 N, mocniejsze Ø40
        for F1 in range(1600, fmax + 1, 100):
            lt = lift(mA, (cAs, cAz), mB, (cBs, cBz), F1, n)
            mx, down, top = max(r["user_kg"] for r in lt), lt[0]["Tg"] + lt[0]["Ts"], lt[-1]["Tg"] + lt[-1]["Ts"]
            if down < -60 and top < 60:             # rozłożony leży na ziemi, w pionie nie pcha mocno
                cands.append((mx + (1.5 if n == 4 else 0), n, F1, lt, mx, down, top))
    _, n_spr, F1, lt, mx, down, top = min(cands, key=lambda c: c[0])
    best = (n_spr, F1, lt, mx, down, top)
    n_spr, F1, lt, mx, down, top = best
    rows = calcs_steel(mA, mB, F1)
    cost_rows, tot_al, tot_st = costs(aA, aB, mA, mB, n_spr, F1 > 2500)
    with open(os.path.join(OUT, "stal_obliczenia.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["element", "obciążenie", "nośność", "jedn.", "wytężenie", "uwagi"])
        for r in rows:
            w.writerow([r["nazwa"], r["obciazenie"], r["nosnosc"], r["jedn"], r["wytezenie"], r["uwagi"]])
    with open(os.path.join(OUT, "porownanie_kosztow.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pozycja", "aluminium V2 [zł]", "stal (budżet) [zł]", "uwagi"])
        w.writerows(cost_rows)
        w.writerow([])
        w.writerow(["założone ceny netto (zmień w stal.py → CENY)"] + [f"{k}={v:g}" for k, v in CENY.items()])
    buy = [
        ("Rura stalowa prostokątna 100×40×3, S235JRH", f"8 × 1250 mm = {sticks(8 * g.L_SEC)} sztangi 6 m", "rury jezdne L1–L4 (zamiast Al 6082)"),
        ("Rura stalowa prostokątna 100×40×2, S235JRH", f"8 × 1250 mm = {sticks(8 * g.L_SEC)} sztangi 6 m", "podłużnice chodnika C1–C3"),
        ("Rura stalowa prostokątna 60×40×2, S235JRH", "3 × 1190 mm (1 sztanga)", "poprzeczki P"),
        ("Kątownik stalowy 40×40×3", "2 × 1095 + 2 × 715 mm (1 sztanga)", "prowadnice G1/G2"),
        ("Płaskownik stalowy 40×5", "1190 mm", "listwa T"),
        ("Siatka cięto-ciągniona STALOWA ocynkowana ~43×13×3×2 (~7 kg/m²)", "1 arkusz 1250×2500", "pokład"),
        (f"Sprężyna gazowa 460 mm / skok 200 / {F1:.0f} N, oczka M12" + (" (Ø40)" if F1 > 2500 else ""), str(n_spr),
         "dobrana do masy stalowego trapu" + ("; 4 sztuki = drugi komplet wsporników K i płyt S" if n_spr == 4 else "")),
        ("Sworzeń blokady Ø12×40 ze stali 8.8 / C45 ulepszanej", "2", "zwykła stal automatowa za słaba przy tej masie"),
        ("Oś oczek sprężyn: śruba M16×70 8.8 + tuleja Ø25×5 dł. 18 / 12 (zamiast M12 i Ø20×4)", "4",
         "otwór oczka w K i S rozwierć z Ø13 do Ø17 – reszta otworów bez zmian"),
        ("Cynkowanie ogniowe wszystkich części stalowych PO wierceniu (albo podkład epoksydowy + farba)", "", "bez tego stal szybko rdzewieje"),
        ("Pozostałe: płyty Z i S, wsporniki K, tuleje, śruby, nity, wkręty, zapięcia, guma", "jak lista_zakupow.csv",
         "bez pasty / podkładek izolujących – stal na stali nie koroduje galwanicznie"),
    ]
    with open(os.path.join(OUT, "stal_lista_zakupow.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pozycja", "ilość", "uwagi"])
        w.writerows(buy)
    worst = max(rows, key=lambda r: r["wytezenie"])
    summary = dict(masa_al=round(aA + aB, 1), masa_stal=round(mA + mB, 1), masa_stal_A=round(mA, 1), masa_stal_B=round(mB, 1),
                   wysilek_bez_sprezyn_stal=max(r["user_kg"] for r in l0),
                   sprezyny_stal=dict(sztuk=n_spr, F1_N=F1, max_wysilek_kg=mx, moment_rozlozony_Nm=round(down, 1), moment_pion_Nm=round(top, 1)),
                   koszt_al=round(tot_al), koszt_stal=round(tot_st), najwieksze_wytezenie=dict(element=worst["nazwa"], wartosc=worst["wytezenie"]))
    with open(os.path.join(OUT, "stal_dane.json"), "w", encoding="utf-8") as f:
        json.dump(dict(podsumowanie=summary, obliczenia=rows, koszty=cost_rows, zakupy=buy, ceny=CENY,
                       podnoszenie=lt, podnoszenie_bez_sprezyn=l0), f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        print(f"{r['wytezenie']:5.2f}  {r['nazwa']}")
    for r in cost_rows:
        print(r)
    return summary


if __name__ == "__main__":
    main()
