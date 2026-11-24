# -*- coding: utf-8 -*-
"""
Trap S5 – analizy, o które nikt nie pytał, a które zrobiłby specjalista:
  1. sprężyny gazowe w temperaturze −20…+50 °C, z tolerancją siły i z jedną sprężyną zepsutą,
  2. ergonomia podnoszenia – równanie NIOSH wzdłuż całego ruchu,
  3. trap złożony w czasie jazdy – podskoki, hamowanie, zakręt (sworznie, blokada, wsporniki K),
  4. prześwit motocykla na krawędzi przyczepy i szerokość opon (dane producenta),
  5. miejsca zgniecenia wg EN ISO 13854,
  6. przewidywane wartości do PROTOKOŁU BADAŃ prototypu (ugięcia przy obciążeniu charakterystycznym, masa, siła podnoszenia).

  python3 analizy_dodatkowe.py   ->  stal_S5/analizy_dodatkowe.csv, .md, protokol_badan_S5.pdf

Surowe dane wejściowe (źródła w raporcie):
  Harley-Davidson Fat Boy 114 (MY2024, karta producenta): masa gotowa do jazdy 317 kg, rozstaw osi 1665 mm,
  prześwit statyczny 115 mm, opony 160/60R18 i 240/40R18;
  sprężyny gazowe (azot): siła zmienia się o ok. 3,5–3,6 % na każde 10 °C (dane producentów);
  EN ISO 13854: minimalne szczeliny – palec 25 mm, dłoń 100 mm, stopa 120 mm, palce stopy 50 mm.
"""
import csv, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import generuj as g
import stal
import stal_s5 as s5
import sily

OUT = s5.OUT
G = 9.81
BIKE = dict(nazwa="Harley-Davidson Fat Boy 114", masa=317.0, rozstaw=1665.0, przeswit=115.0, opona_p=160.0, opona_t=240.0,
            zrodlo="H-D, Model Year 2024 Fat Boy 114 – specifications (h-dmediakit.com)")
GAS_PER_K = 0.0036                     # względna zmiana siły sprężyny na 1 K
R_HAND = g.L_SEC + 25.0                # ręka na końcu sekcji A, od osi zawiasu przy przyczepie [mm]
PIN_H = g.H_FLOOR + g.PIN_Z            # oś zawiasu nad ziemią [mm]


# ------------------------------------------------------------------ 1. sprężyny
def springs():
    v, mA, mB = s5.V, s5.mA, s5.mB
    cA, cB = (s5.cAs, s5.cAz), (s5.cBs, s5.cBz)
    F20, n = s5.SPR["F1_N"], s5.SPR["sztuk"]
    rows = []
    for T in (-20, 0, 20, 40, 50):
        for tol, tn in ((1.0, "nominalna"), (0.95, "−5 %"), (1.05, "+5 %")):
            if tn != "nominalna" and T not in (-20, 50):
                continue
            F = F20 * (1 + GAS_PER_K * (T - 20)) * tol
            lt = stal.lift(mA, cA, mB, cB, F, n, s5.EYE_LOW)
            rows.append(dict(przypadek=f"{T:+d} °C, siła {tn}", F=round(F), wysilek=max(r["user_kg"] for r in lt),
                             rozlozony=lt[0]["Tg"] + lt[0]["Ts"], pion=lt[-1]["Tg"] + lt[-1]["Ts"]))
    lt1 = stal.lift(mA, cA, mB, cB, F20, n - 1, s5.EYE_LOW)
    rows.append(dict(przypadek="jedna sprężyna zepsuta (20 °C)", F=F20, wysilek=max(r["user_kg"] for r in lt1),
                     rozlozony=lt1[0]["Tg"] + lt1[0]["Ts"], pion=lt1[-1]["Tg"] + lt1[-1]["Ts"]))
    lt0 = stal.lift(mA, cA, mB, cB, 0, 0)
    rows.append(dict(przypadek="obie zepsute / zdjęte", F=0, wysilek=max(r["user_kg"] for r in lt0),
                     rozlozony=lt0[0]["Tg"] + lt0[0]["Ts"], pion=lt0[-1]["Tg"] + lt0[-1]["Ts"]))
    for r in rows:
        r["ok_lezy"] = r["rozlozony"] < 0              # rozłożony trap nie podnosi się sam
        r["ok_pion"] = r["pion"] < 60.0                # w pionie nie pcha w stronę przyczepy mocniej niż 60 N·m
    return rows


# ------------------------------------------------------------------ 2. NIOSH
def niosh(lift_rows, H=40.0, D=120.0, CM=0.95, FM=1.0):
    """Revised NIOSH Lifting Equation (1991): RWL = 23·(25/H)·(1−0,003|V−75|)·(0,82+4,5/D)·(1−0,0032A)·FM·CM [kg], H, V, D w cm"""
    out = []
    for r in lift_rows:
        V = (PIN_H + R_HAND * math.sin(math.radians(r["deg"]))) / 10.0
        rwl = 23.0 * (25.0 / H) * max(0.0, 1 - 0.003 * abs(V - 75.0)) * (0.82 + 4.5 / D) * 1.0 * FM * CM
        L = max(r["user_kg"], 0.0)
        out.append(dict(deg=r["deg"], V=V, L=L, RWL=rwl, LI=L / rwl if rwl > 0 else 0.0))
    return out


# ------------------------------------------------------------------ 3. trap złożony w jeździe
def transport():
    m = s5.mA + s5.mB
    xg, yg = 139.0, 697.0                  # środek masy złożonego trapu: za tylną ścianą belki, nad podłogą (model 3D)
    xp, yp = 40.0, -25.0                   # oś zawiasu
    xl = 70.0                              # oś sworznia blokady (30 mm za osią zawiasu, ta sama wysokość)
    arm = xl - xp
    gam = 1.5
    Msp = s5.SPR["moment_pion_Nm"]         # sprężyny w pionie (+ do tyłu)
    cases = [("podskok 2,0 g w pionie", 2.0, 0.0), ("hamowanie 0,8 g + ciężar", 1.0, -0.8),
             ("ruszanie / cofanie 0,5 g + ciężar", 1.0, 0.5)]
    out = []
    for nm, av, ah in cases:
        # moment wokół osi zawiasu [N·m], + = trap odchyla się do tyłu (od przyczepy);
        # ah > 0: siła bezwładności do tyłu (ruszanie), ah < 0: do przodu (hamowanie)
        M = m * G * av * (xg - xp) / 1000.0 + m * G * ah * (yg - yp) / 1000.0 + Msp
        Fl = abs(M) * gam / (arm / 1000.0) / 2 / 1000.0               # na jeden sworzeń blokady [kN]
        R = math.hypot(m * G * av, m * G * ah) * gam / 2 / 1000.0     # na jeden sworzeń zawiasu [kN] (bez udziału blokady)
        Rp = math.hypot(R, Fl)                                        # sworzeń zawiasu przenosi też reakcję blokady
        out.append(dict(przypadek=nm, M=M, F_blokada=Fl, F_zawias=Rp))
    lat = m * G * 0.5 * gam / 1000.0
    cap_lock = 0.6 * 600 * math.pi * 36 / 1.25 / 1000.0               # Ø12 C45, jedna płaszczyzna
    cap_bear = 2.5 * min(25 / 39, 1) * 360 * 12 * 6 / 1.25 / 1000.0   # docisk w płycie H 6 mm
    cap_pin = 0.6 * 600 * math.pi * 100 / 1.25 / 1000.0               # Ø20
    return out, lat, dict(blokada=min(cap_lock, cap_bear), zawias=cap_pin)


# ------------------------------------------------------------------ 4. motocykl
def bike():
    a = math.radians(g.ALPHA)
    crest = BIKE["rozstaw"] / 2 * math.tan(a / 2)                     # utrata prześwitu na krawędzi podłogi (koła na dwóch płaszczyznach)
    lane = s5.V["lane_mm"]
    return dict(kat=g.ALPHA, utrata=crest, zapas=BIKE["przeswit"] - crest,
                luz_tyl=(lane - BIKE["opona_t"]) / 2, luz_przod=(lane - BIKE["opona_p"]) / 2,
                masa_ok=BIKE["masa"] <= 350.0)


# ------------------------------------------------------------------ 5. zgniecenia (EN ISO 13854)
PINCH = [
    ("Styk rur A | B na zawiasie środkowym (góra)", "0 mm przy rozkładaniu", "palec 25 / dłoń 100",
     "nie do spełnienia konstrukcyjnie (styk przenosi ściskanie)",
     "chwyt tylko za uchwyty / rurę ≥ 250 mm od zawiasu; naklejka ISO 7010 W024 (zgniecenie dłoni) przy zawiasie"),
    ("Pokład A ↔ krawędź podłogi przy trapie w pionie", "15 mm", "palec 25",
     "za mało – palec może wejść i zostać ściśnięty",
     "nie trzymać krawędzi podłogi przy domykaniu; naklejka W024 na krawędzi; zderzak gumowy 15 mm na krawędzi podłogi zostawia ≤ 4 mm (palec nie wejdzie)"),
    ("Płyta H ↔ wspornik K (oś zawiasu przy przyczepie)", "1 mm", "palec 25",
     "szczelina ≤ 4 mm – palec nie wejdzie (EN ISO 13857)", "bez zmian"),
    ("Sekcja B wlecze się po ziemi (koniec ze skosem)", "0 mm do podłoża", "palce stopy 50, stopa 120",
     "stopa pod końcem B", "stać z boku, nie przed końcem B; buty z noskiem"),
    ("Sprężyna gazowa: tłoczysko / oczko przy wsporniku K", "zmienna", "palec 25", "ręka na sprężynie przy składaniu",
     "nie chwytać za sprężyny; przy przeglądzie tylko trap zablokowany sworzniami"),
]


# ------------------------------------------------------------------ 6. przewidywania do protokołu badań
def predictions():
    """ugięcia przy obciążeniu CHARAKTERYSTYCZNYM (bez współczynników) – do porównania z pomiarem czujnikiem zegarowym"""
    r = s5.ruszt(True)
    Pk_w = g.WHEEL_KG * G
    Pk_f = g.FOOT_KG * G
    sw = r.self_weight(0.0, 0.0)
    pts = [("P1", "koło 273 kg na L2 (x +45), środek A (s = 600)", ("A", "t", 45.0, 600.0), Pk_w),
           ("P2", "koło 273 kg na L2 przy zawiasie (A, s = 1250)", ("A", "t", 45.0, g.L_SEC), Pk_w),
           ("P3", "koło 273 kg na L4 w środku B (s = 600)", ("B", "t", 45.0, 600.0), Pk_w),
           ("P4", "stopa 105 kg na C2 przy zawiasie (A, s = 1250)", ("A", "t", s5.XE, g.L_SEC), Pk_f),
           ("P5", "stopa 105 kg na C2 w środku A (s = 600)", ("A", "t", s5.XE, 600.0), Pk_f),
           ("P6", "stopa 105 kg na C3 krawędź, środek B (s = 600)", ("B", "t", s5.XE, 600.0), Pk_f)]
    out = []
    for pid, nm, key, P in pts:
        res = r.solve([(key, P)])
        out.append(dict(pid=pid, opis=nm, ugiecie=-res["W"][key], skok=res["W"][("A", "t", key[2], g.L_SEC)] - res["W"][("B", "t", key[2], 0.0)]))
    return out


def fmt(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def main():
    S = springs()
    N = niosh(s5.LIFT)
    N0 = niosh(s5.LIFT0)
    Tr, lat, cap = transport()
    B = bike()
    P = predictions()
    nmax = max(N, key=lambda r: r["LI"])

    rows = []
    for r in S:
        rows.append(["sprężyny", r["przypadek"], f"siła {r['F']} N", f"podnoszenie max {fmt(r['wysilek'])} kg",
                     f"rozłożony {fmt(r['rozlozony'], 0)} N·m ({'leży' if r['ok_lezy'] else 'PODNOSI SIĘ'})",
                     f"pion {fmt(r['pion'], 0)} N·m ({'OK' if r['ok_pion'] else 'PCHA'})"])
    rows.append(["NIOSH", "ze sprężynami", f"max LI {fmt(nmax['LI'], 2)} przy {nmax['deg']:.0f}°", f"V = {nmax['V']:.0f} cm, L = {fmt(nmax['L'])} kg",
                 f"RWL = {fmt(nmax['RWL'])} kg", "LI ≤ 1 bez ryzyka, 1–3 podwyższone, > 3 wysokie"])
    n0 = max(N0, key=lambda r: r["LI"])
    rows.append(["NIOSH", "bez sprężyn", f"max LI {fmt(n0['LI'], 2)} przy {n0['deg']:.0f}°", f"L = {fmt(n0['L'])} kg", f"RWL = {fmt(n0['RWL'])} kg", ""])
    for t in Tr:
        rows.append(["jazda", t["przypadek"], f"moment {fmt(t['M'], 0)} N·m", f"sworzeń blokady {fmt(t['F_blokada'], 2)} kN (nośność {fmt(cap['blokada'], 1)})",
                     f"sworzeń zawiasu {fmt(t['F_zawias'], 2)} kN (nośność {fmt(cap['zawias'], 1)})",
                     f"wytężenie {fmt(max(t['F_blokada'] / cap['blokada'], t['F_zawias'] / cap['zawias']) * 100, 0)} %"])
    rows.append(["jazda", "zakręt 0,5 g w bok", f"{fmt(lat, 2)} kN wzdłuż sworzni", "przenoszą łby, podkładki i zawleczki", "", ""])
    rows.append(["motocykl", BIKE["nazwa"], f"utrata prześwitu na krawędzi podłogi {fmt(B['utrata'], 0)} mm",
                 f"zapas {fmt(B['zapas'], 0)} mm z {BIKE['przeswit']:.0f}", f"opona tył 240: luz {fmt(B['luz_tyl'], 0)} mm/stronę",
                 f"przód 160: {fmt(B['luz_przod'], 0)} mm/stronę"])
    for p in P:
        rows.append(["protokół", p["pid"], p["opis"], f"ugięcie przewidywane {fmt(p['ugiecie'])} mm", f"skok na styku {fmt(p['skok'])} mm", ""])
    with open(os.path.join(OUT, "analizy_dodatkowe.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["obszar", "przypadek", "wynik 1", "wynik 2", "wynik 3", "wynik 4"])
        w.writerows(rows)

    # ---------------------------------------------------------- raport
    sp = s5.SPR
    lines = [f"# Trap S5 – analizy dodatkowe (sprężyny, ergonomia, jazda, motocykl, zgniecenia)\n",
             "Wygenerowane przez `analizy_dodatkowe.py`. Dane wejściowe: model S5 (masa, środek masy, krzywa podnoszenia), "
             f"karta producenta motocykla ({BIKE['zrodlo']}), dane producentów sprężyn gazowych (3,6 % na 10 °C), EN ISO 13854.\n",
             "## 1. Sprężyny gazowe: temperatura, tolerancja, awaria\n",
             f"Nominalnie 2 × {sp['F1_N']} N (Ø28) przy 20 °C.\n",
             "| przypadek | siła [N] | podnoszenie max [kg] | rozłożony trap | trap w pionie |", "|---|---|---|---|---|"]
    for r in S:
        lines.append(f"| {r['przypadek']} | {r['F']} | {fmt(r['wysilek'])} | {fmt(r['rozlozony'], 0)} N·m – {'leży' if r['ok_lezy'] else '**podnosi się**'} "
                     f"| {fmt(r['pion'], 0)} N·m – {'OK' if r['ok_pion'] else '**pcha**'} |")
    cold = max(r["wysilek"] for r in S if r["przypadek"].startswith("-20"))
    one = next(r for r in S if r["przypadek"].startswith("jedna"))
    lines += ["", f"- W mrozie −20 °C podnoszenie rośnie do **{fmt(cold)} kg**. W upale (+50 °C) rozłożony trap nadal leży.",
              f"- Gdy jedna sprężyna padnie, podnoszenie rośnie do **{fmt(one['wysilek'])} kg**. Trap nie spada, bo sprężyna tylko pomaga, a trzymają sworznie. "
              "Wymieniaj sprężyny parami co ok. 5 lat albo gdy jedna słabnie.", ""]
    lines += ["## 2. Ergonomia podnoszenia – równanie NIOSH (1991)\n",
              "Ręka na końcu sekcji A. V to wysokość dłoni z geometrii, H = 40 cm (trap przed sobą), D = 120 cm, uchwyt „dostateczny” (CM 0,95), rzadkie podnoszenie (FM 1). "
              "To ocena przesiewowa, bo ruch jest obrotem, a nie czystym podnoszeniem.\n",
              f"- **Ze sprężynami:** największy wskaźnik **LI = {fmt(nmax['LI'], 2)}** przy kącie {nmax['deg']:.0f}° "
              f"(siła {fmt(nmax['L'])} kg, dłonie na {nmax['V']:.0f} cm, zalecana granica RWL {fmt(nmax['RWL'])} kg).",
              f"- **Bez sprężyn:** LI = {fmt(n0['LI'], 2)}.",
              "- LI ≤ 1: brak ryzyka; 1–3: ryzyko podwyższone (dla zdrowej, wprawnej osoby, z techniką); > 3: wysokie.",
              "- Wniosek: dwa **uchwyty** (uchwyt dobry, CM 1,0) i podnoszenie przodem do trapu obniżają LI o ok. 5 %. Sprężyny Ø40 2 × 2800 N "
              "obniżyłyby siłę do ok. 20 kg, czyli LI o ok. 15 %.", ""]
    lines += ["## 3. Trap złożony w czasie jazdy\n",
              f"Środek masy złożonego trapu jest 139 mm za tylną ścianą belki i 697 mm nad podłogą. Oś zawiasu jest 40 mm za belką, "
              f"a sworzeń blokady 30 mm za osią. Współczynnik obciążenia 1,5.\n",
              "| przypadek | moment wokół osi [N·m] | sworzeń blokady [kN] | sworzeń zawiasu [kN] |", "|---|---|---|---|"]
    for t in Tr:
        lines.append(f"| {t['przypadek']} | {fmt(t['M'], 0)} | {fmt(t['F_blokada'], 2)} / {fmt(cap['blokada'], 1)} | {fmt(t['F_zawias'], 2)} / {fmt(cap['zawias'], 1)} |")
    lines += ["", f"- Najgorsze jest hamowanie: sworzeń blokady **{fmt(max(t['F_blokada'] for t in Tr) / cap['blokada'] * 100, 0)} %** nośności. "
              "Sworzeń Ø12 ma luz w otworze Ø13, więc na drodze trap stuka i wyrabia otwory (zmęczenie, hałas). Pas z grzechotką dociąga trap "
              "do jednej strony luzu i to stukanie usuwa. Pas zakładaj zawsze, nie tylko jako zapas.",
              f"- W zakręcie {fmt(lat, 2)} kN działa wzdłuż sworzni i przenoszą to łby, podkładki i zawleczki. Zawleczki ze stali nierdzewnej, nowe co sezon.", ""]
    lines += [f"## 4. Motocykl ({BIKE['nazwa']}, dane producenta)\n",
              f"- Kąt trapu {fmt(g.ALPHA)}°. Na krawędzi podłogi motocykl traci prześwit **{fmt(B['utrata'], 0)} mm** "
              f"(rozstaw osi / 2 × tg(α/2)). Zapas wynosi **{fmt(B['zapas'], 0)} mm** ze {BIKE['przeswit']:.0f} mm prześwitu statycznego. "
              "Z kierowcą na siodle zawieszenie siada o ok. 20–30 mm i zapas spada prawie do zera, dlatego **wprowadzaj motocykl bez kierowcy, pchając**.",
              f"- Szerokość pasa 282 mm: tylna opona 240 mm ma luz **{fmt(B['luz_tyl'], 0)} mm** na stronę, przednia 160 mm – {fmt(B['luz_przod'], 0)} mm. "
              "Trzeba celować, ale się mieści.",
              f"- Masa 317 kg (gotowy do jazdy) < 350 kg przyjętych w obliczeniach ✅.", ""]
    lines += ["## 5. Miejsca zgniecenia (EN ISO 13854: palec 25 mm, dłoń 100 mm, stopa 120 mm, palce stopy 50 mm)\n",
              "| miejsce | szczelina | wymagane | ocena | co zrobić |", "|---|---|---|---|---|"]
    for p in PINCH:
        lines.append("| " + " | ".join(p) + " |")
    lines += ["", "## 6. Przewidywania do protokołu badań (obciążenie charakterystyczne, bez współczynników)\n",
              "| punkt | obciążenie | ugięcie z modelu [mm] | skok na styku [mm] |", "|---|---|---|---|"]
    for p in P:
        lines.append(f"| {p['pid']} | {p['opis']} | {fmt(p['ugiecie'])} | {fmt(p['skok'])} |")
    lines += ["", "Pomiar: czujnik zegarowy na statywie, ugięcie względem podpór (sworznie przy przyczepie i koniec na ziemi). "
              "Kryteria i formularz: `protokol_badan_S5.pdf`."]
    with open(os.path.join(OUT, "analizy_dodatkowe.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    protocol(P, S, N)
    return dict(springs=S, niosh=nmax, niosh0=n0, transport=Tr, cap=cap, bike=B, pred=P)


# ------------------------------------------------------------------ protokół badań prototypu
def protocol(P, S, N):
    path = os.path.join(OUT, "protokol_badan_S5.pdf")
    lift = {round(r["deg"]): r["user_kg"] for r in s5.LIFT}
    near = lambda d: min(s5.LIFT, key=lambda r: abs(r["deg"] - d))["user_kg"]
    with PdfPages(path) as pdf:
        def page(title, blocks):
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.06, 0.965, title, fontsize=13, weight="bold")
            y = 0.935
            for kind, data in blocks:
                if kind == "t":
                    for ln in data:
                        fig.text(0.06, y, ln, fontsize=8)
                        y -= 0.017
                    y -= 0.008
                else:
                    head, rows, widths = data
                    xs = [0.06]
                    for wdt in widths[:-1]:
                        xs.append(xs[-1] + wdt)
                    for i, h in enumerate(head):
                        fig.text(xs[i], y, h, fontsize=7.5, weight="bold")
                    y -= 0.018
                    for r in rows:
                        for i, c in enumerate(r):
                            fig.text(xs[i], y, str(c), fontsize=7.5)
                        fig.lines.append(plt.Line2D([0.06, 0.94], [y - 0.006, y - 0.006], transform=fig.transFigure, color="#cccccc", lw=0.5))
                        y -= 0.02
                    y -= 0.012
            pdf.savefig(fig)
            plt.close(fig)

        page("PROTOKÓŁ BADAŃ PROTOTYPU – TRAP S5", [
            ("t", ["Cel: niezależny, fizyczny dowód, że trap jest taki, jak w obliczeniach. Wypełnij ręcznie, podpisz, zachowaj ze zdjęciami.",
                   "Przyrządy: waga hakowa / łazienkowa (±0,5 kg), czujnik zegarowy 0,01 mm na statywie magnetycznym, szczelinomierz, klucz dynamometryczny,",
                   "waga hakowa / dynamometr (±0,2 kg), worki z piaskiem lub ciężarki (zważone), miara 5 m, poziomica kątowa, aparat.",
                   "Przed próbą: przyczepa podpięta do auta, hamulec ręczny, podłoże twarde i równe. Nikt pod trapem i przy jego bokach.",
                   "",
                   "Data: ............................  Miejsce: ............................  Wykonał: ............................  Świadek: ............................"]),
            ("tab", (["Nr", "Sprawdzenie", "Wartość z modelu", "Kryterium", "Wynik", "OK?"],
                     [["1", "Masa sekcji A + B (bez wsporników)", f"{fmt(s5.mA + s5.mB)} kg", "±5 %", "......", "☐"],
                      ["2", "Atest 3.1 rur jezdnych: S355, ścianka", "S355 / 2,0 mm", "Re ≥ 355, t ≥ 1,9", "......", "☐"],
                      ["3", "Ścianka poprzeczek (suwmiarka)", "3,0 mm", "≥ 2,8 mm", "......", "☐"],
                      ["4", "Luz po złożeniu (szczelinomierz, 6 miejsc)", "≥ 13 mm", "≥ 8 mm", "......", "☐"],
                      ["5", "Trap obraca się ręką bez zacięć", "–", "bez zacięć", "......", "☐"],
                      ["6", "Rozłożony leży sam na ziemi", f"{fmt(s5.SPR['moment_rozlozony_Nm'], 0)} N·m", "nie unosi się", "......", "☐"],
                      ["7", "Momenty: M8 20 N·m, M12 40 N·m (znacznik farbą)", "–", "100 % śrub", "......", "☐"]],
                     [0.04, 0.33, 0.14, 0.15, 0.13, 0.06])),
            ("t", ["SIŁA PODNOSZENIA – waga hakowa zaczepiona na końcu sekcji A, ciągnij prostopadle do trapu, odczyt przy kącie (poziomica kątowa):"]),
            ("tab", (["Kąt sekcji A", "Model [kg]", "Kryterium", "Pomiar [kg]", "OK?"],
                     [[f"{d}°", fmt(near(d)), "±25 %", "......", "☐"] for d in (0, 20, 45, 60, 80)],
                     [0.15, 0.15, 0.15, 0.15, 0.1])),
        ])
        page("PRÓBA OBCIĄŻENIA (ugięcia) – porównanie z modelem", [
            ("t", ["1. Czujnik zegarowy pod punktem pomiaru, zero przy trapie bez obciążenia. 2. Obciążenie charakterystyczne (tabela), odczyt po 1 min.",
                   "3. Zdejmij, odczyt powrotu. 4. Próba 1,5 × (koło 410 kg, stopa 160 kg) w P2 i P4: 10 min, bez trwałego odkształcenia.",
                   "Kryteria: ugięcie ≤ 1,3 × wartość z modelu (niepewność modelu rusztu); powrót do zera ≤ 0,3 mm;",
                   "brak widocznych odkształceń i pęknięć ocynku przy otworach.",
                   "Obciążenie koła: worki ułożone na odcinku 120 mm wzdłuż pasa (ślad opony), stopy: na kwadracie 100 × 100 mm."]),
            ("tab", (["Punkt", "Obciążenie", "Model [mm]", "Granica [mm]", "Pomiar [mm]", "Powrót [mm]", "OK?"],
                     [[p["pid"], p["opis"], fmt(p["ugiecie"], 2), fmt(1.3 * p["ugiecie"], 2), "......", "......", "☐"] for p in P],
                     [0.04, 0.43, 0.09, 0.1, 0.1, 0.1, 0.05])),
            ("tab", (["Próba 1,5 ×", "Obciążenie", "10 min", "Trwałe odkształcenie [mm]", "OK?"],
                     [["P2", "410 kg na L2 przy zawiasie (A)", "☐", "......", "☐"], ["P4", "160 kg na C2 przy zawiasie (A)", "☐", "......", "☐"]],
                     [0.1, 0.35, 0.1, 0.25, 0.08])),
            ("t", ["PIERWSZY WJAZD: bez kierowcy, pchając, z asekuracją drugiej osoby. Prześwit na krawędzi podłogi (model: zapas ok. 35 mm):",
                   "podłóż tekturę i zobacz, czy została zarysowana. Po 5 wjazdach: dokręć śruby, sprawdź znaczniki, luz sworzni.",
                   "",
                   "ŚWIATŁA (trap złożony): pozycja ☐  stop ☐  kierunkowskaz L ☐  P ☐  tablica oświetlona ☐  nic nie zasłonięte z tyłu i z boków ☐",
                   "",
                   "Wynik końcowy:  ☐ ZGODNY     ☐ NIEZGODNY – co: ...........................................................................",
                   "",
                   "Podpis wykonującego: ............................      Podpis sprawdzającego (rzeczoznawca / inżynier): ............................"]),
        ])
    return path


if __name__ == "__main__":
    r = main()
    print("NIOSH max LI", round(r["niosh"]["LI"], 2), "przy", r["niosh"]["deg"], "°; bez sprężyn", round(r["niosh0"]["LI"], 2))
    for s in r["springs"]:
        print(f"  {s['przypadek']:28s} F={s['F']:5d} N  max {s['wysilek']:5.1f} kg  rozł. {s['rozlozony']:7.1f}  pion {s['pion']:6.1f}")
    for t in r["transport"]:
        print(f"  {t['przypadek']:32s} M={t['M']:7.1f} N·m  blokada {t['F_blokada']:.2f} kN  zawias {t['F_zawias']:.2f} kN")
    print("  motocykl:", {k: round(v, 1) if isinstance(v, float) else v for k, v in r["bike"].items()})
    for p in r["pred"]:
        print(f"  {p['pid']}: {p['ugiecie']:.2f} mm, skok {p['skok']:.2f} mm")
