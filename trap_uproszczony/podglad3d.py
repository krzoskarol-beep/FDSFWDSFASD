# -*- coding: utf-8 -*-
"""
Podgląd 3D trapu V2 – model warsztatowy: profile z prawdziwymi ściankami i OTWORAMI,
wszystkie śruby, podkładki, nakrętki, tuleje, sworznie, nity i wkręty – w miejscach z tabel otworów (generuj.py).

  python3 podglad3d.py            okno 3D (matplotlib) z suwakiem „pozycja” – rozłożony ↔ do jazdy
  python3 podglad3d.py --png      zapisuje zrzuty podglad_*.png (całość, zawiasy, skrzyżowanie, same otwory)
  python3 podglad3d.py --gltf     zapisuje www/trap_v2.glb (glTF 2.0 z animacją „skladanie”)
  python3 podglad3d.py --www      eksport glTF + strona http://localhost:8000 (www/index.html)
  python3 podglad3d.py --sprawdz  sprawdza, czy każdy otwór ma śrubę/nit i czy śruby trafiają w otwory

Wymaga: pip install matplotlib numpy mapbox-earcut
Podgląd w Pythonie rysuje własny renderer (numpy, bufor głębokości) – widać śruby, tuleje i otwory.
Układy: część (x w poprzek, s wzdłuż sekcji, z od spodu rur) – jak na rysunkach; glTF: metry, Y w górę.
"""
import json, math, os, struct, sys
from collections import defaultdict

import numpy as np
import mapbox_earcut as earcut

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g

OUT = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(OUT, "www")

C_LANE, C_WALK, C_CROSS = "#8fa9c9", "#c9cfd6", "#d8b98a"
C_MESH, C_GUIDE, C_STEEL, C_TRAILER = "#5f6b78", "#3f6fb0", "#3a3a3a", "#b04a3a"
C_BOLT, C_SLEEVE, C_HOLE, C_RIVET = "#a9afb6", "#d4b030", "#e01b1b", "#e8e8e8"
C_SPRING, C_ROD = "#151515", "#e0e0e0"
U_MID, V_MID = g.L_SEC + 25.0, -110.0          # zawias środkowy względem osi zawiasu przy przyczepie
SPRING_X = 396.0                               # płaszczyzna sprężyn (środek oczek)
L, SK = g.L_SEC, g.SKOS
XO = g.X_LANE_OUT + 20.0                       # zewnętrzna ścianka rury jezdnej zewnętrznej (145)

# wymiary złączy: (średnica, rozwartość klucza, wys. łba, podkładka Ø×gr., wys. nakrętki samohamownej)
BOLT = {8: (8.0, 13.0, 5.3, 16.0, 1.6, 8.0), 12: (12.0, 18.0, 7.5, 24.0, 2.5, 12.0), 20: (20.0, 30.0, 12.5, 37.0, 3.0, 20.0)}


def fmt(v):
    return f"{v:g}".replace(".", ",")


# ================================================================== BUDOWA BRYŁ
class Model:
    """zbiór siatek: klucz -> dict(grp, kolor, krycie, rodzaj, opis, trójkąty w układzie części (x, s, z))"""

    def __init__(self):
        self.m = {}
        self.hole_txt = defaultdict(list)
        self.hole_dia = {}
        self.bolt_axes = []          # (klucz otworu, rodzaj) – do kontroli
        self.shanks = []             # (grupa, oś, c1, c2, a0, a1, średnica) – trzpienie do kontroli kolizji

    def mesh(self, key, grp, col, kind, info, op=1.0):
        if key not in self.m:
            self.m[key] = dict(grp=grp, c=col, o=op, kind=kind, info=info, tris=[])
        return self.m[key]["tris"]

    def hole(self, key, txt, d):
        if txt not in self.hole_txt[key]:
            self.hole_txt[key].append(txt)
        self.hole_dia[key] = max(self.hole_dia.get(key, 0), d)


def P(plane, a, b, w):
    """punkt płaszczyzny (a, b) przesunięty o w wzdłuż normalnej -> (x, s, z)"""
    if plane == "sz":
        return (w, a, b)
    if plane == "sx":
        return (b, a, w)
    return (a, w, b)                                  # "xz"


def ring(ca, cb, d, n=None):
    n = n or (24 if d >= 9 else 10)
    return [(ca + d / 2 * math.cos(2 * math.pi * k / n), cb + d / 2 * math.sin(2 * math.pi * k / n)) for k in range(n)]


def slab(M, grp, plane, poly, holes, w0, w1, body):
    """płyta (wielokąt `poly` w płaszczyźnie) grubości w0..w1 z okrągłymi otworami
    holes: [(a, b, d, klucz_otworu, opis)] ; ściany otworów trafiają do osobnych siatek „otwór”"""
    rings = [list(poly)] + [ring(a, b, d) for (a, b, d, _, _) in holes]
    pts = np.array([p for r in rings for p in r], float)
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    idx = earcut.triangulate_float64(pts, ends).reshape(-1, 3)
    for w in (w0, w1):
        for i, j, k in idx:
            body.append([P(plane, *pts[i], w), P(plane, *pts[j], w), P(plane, *pts[k], w)])

    def walls(r, out):
        for i in range(len(r)):
            a, b = r[i], r[(i + 1) % len(r)]
            q = [P(plane, *a, w0), P(plane, *b, w0), P(plane, *b, w1), P(plane, *a, w1)]
            out += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    walls(rings[0], body)
    for r, (a, b, d, key, txt) in zip(rings[1:], holes):
        walls(r, M.mesh(f"otw:{grp}:{key}", grp, C_HOLE, "otwór", key))
        M.hole(key, txt, d)


def solid(plane, poly, w0, w1, out):
    """graniastosłup z wypukłego wielokąta (bez otworów)"""
    n = len(poly)
    for w in (w0, w1):
        for i in range(1, n - 1):
            out.append([P(plane, *poly[0], w), P(plane, *poly[i], w), P(plane, *poly[i + 1], w)])
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        q = [P(plane, *a, w0), P(plane, *b, w0), P(plane, *b, w1), P(plane, *a, w1)]
        out += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]


AX = {"x": "sz", "s": "xz", "z": "sx"}     # oś walca -> płaszczyzna przekroju (c1, c2)


def cyl(axis, c1, c2, a0, a1, r, out, n=16):
    solid(AX[axis], ring(c1, c2, 2 * r, n), min(a0, a1), max(a0, a1), out)


def hexa(axis, c1, c2, a0, a1, af, out):
    R = af / math.sqrt(3)
    solid(AX[axis], [(c1 + R * math.cos(math.pi / 6 + k * math.pi / 3), c2 + R * math.sin(math.pi / 6 + k * math.pi / 3))
                     for k in range(6)], min(a0, a1), max(a0, a1), out)


def bolt(out, axis, c1, c2, face0, dirn, Lb, size, grip, head="hex", washer_head=True):
    """śruba: łeb przy face0 (po stronie -dirn), trzpień Lb w kierunku dirn, podkładka + nakrętka po `grip` mm"""
    d, af, k, dw, tw, hn = BOLT[size]
    if head == "carriage":                    # śruba zamkowa: łeb grzybkowy Ø20 × 4,4
        cyl(axis, c1, c2, face0, face0 - dirn * 4.4, 10.0, out)
        s0 = face0
    else:
        hw = tw if washer_head else 0.0
        if washer_head:
            cyl(axis, c1, c2, face0, face0 - dirn * tw, dw / 2, out)
        hexa(axis, c1, c2, face0 - dirn * hw, face0 - dirn * (hw + k), af, out)
        s0 = face0 - dirn * hw
    cyl(axis, c1, c2, s0, s0 + dirn * Lb, d / 2, out, 12)
    g1 = face0 + dirn * grip
    if CUR is not None:
        grp = next(m["grp"] for m in CUR.m.values() if m["tris"] is out)
        CUR.shanks.append((grp, axis, c1, c2, s0, g1, d, next(k for k, m in CUR.m.items() if m["tris"] is out)))
    cyl(axis, c1, c2, g1, g1 + dirn * tw, dw / 2, out)
    hexa(axis, c1, c2, g1 + dirn * tw, g1 + dirn * (tw + hn), af, out)
    return s0, s0 + dirn * Lb, g1 + dirn * (tw + hn)


def xr(a, b, sg):
    return (min(a * sg, b * sg), max(a * sg, b * sg))


# ================================================================== MODEL
LONG_ID = {("A", g.X_LANE_OUT): "L1", ("A", g.X_LANE_IN): "L2", ("A", g.X_WALK): "C1", ("A", g.X_EDGE): "C2",
           ("B", g.X_LANE_OUT): "L3", ("B", g.X_LANE_IN): "L4", ("B", g.X_WALK): "C3", ("B", g.X_EDGE): "C3"}
LONG_INFO = {p[0]: p for p in g.LONG_PARTS}
SFROM = {"A": "od końca przy przyczepie", "B": "od zawiasu środkowego"}


CUR = None


def build():
    global CUR
    M = Model()
    CUR = M
    cross = {"A": g.CROSS_A, "B": g.CROSS_B}
    guides = {"A": (g.GUIDE_A, g.GUIDE_BOLTS_A), "B": (g.GUIDE_B, g.GUIDE_BOLTS_B)}

    # ---------------------------------------------------------- podłużnice (rury z otworami)
    for grp in "AB":
        for xa in (g.X_LANE_IN, g.X_LANE_OUT, g.X_WALK, g.X_EDGE):
            pid = LONG_ID[(grp, xa)]
            _, name, prof, mat, q, xs, skos, _ = LONG_INFO[pid]
            t = 3.0 if "×3" in prof else 2.0
            col = C_LANE if xa < 200 else C_WALK
            table = g.holes_long(pid)
            for sg in (-1, 1):
                xc = sg * xa
                lst = "\n".join(f"  s={fmt(s)} {w}{'' if z is None else f' z={fmt(z)}'} Ø{fmt(d)} – {n}" for (s, w, z, d, n) in table)
                info = (f"{pid} – {name}\n{prof} {mat}, L = {fmt(L)}{f', skos {SK:.0f}' if skos else ''}\n"
                        f"x = {xc:+.0f} mm. Otwory (s {SFROM[grp]}):\n{lst}")
                body = M.mesh(f"{grp}:{pid}:{xc:+.0f}", grp, col, "profil", info)
                vh = [(s, xc, d, f"{grp}v:{s:g}:{xc:+.0f}",
                       f"{pid} (x={xc:+.0f}): Ø{fmt(d)} przez górę i dół, s={fmt(s)} {SFROM[grp]}, w osi ścianki")
                      for (s, w, z, d, n) in table if w == "g/d"]
                rv = [(s, xc + dx, d, f"{grp}r:{s:g}:{xc + dx:+.0f}",
                       f"{pid} (x={xc:+.0f}): Ø{fmt(d)} w dnie pod nit, s={fmt(s)}, {dx:+.0f} mm od osi ścianki")
                      for (s, w, z, d, n) in table if w == "dół" for dx in (-10, 10)]
                sh = [(s, z, d, f"{grp}h:{s:g}:{z:g}:{sg}",
                       f"{pid} (x={xc:+.0f}): Ø{fmt(d)} przez oba boki, s={fmt(s)} {SFROM[grp]}, z={fmt(z)} od spodu")
                      for (s, w, z, d, n) in table if w == "bok"]
                slab(M, grp, "sx", [(0, xc - 20 + t), (L, xc - 20 + t), (L, xc + 20 - t), (0, xc + 20 - t)],
                     vh, 100 - t, 100, body)
                lb = L - SK if skos else L
                slab(M, grp, "sx", [(0, xc - 20 + t), (lb, xc - 20 + t), (lb, xc + 20 - t), (0, xc + 20 - t)],
                     vh + rv, 0, t, body)
                side = [(0, 0), (lb, 0), (L, 100), (0, 100)] if skos else [(0, 0), (L, 0), (L, 100), (0, 100)]
                slab(M, grp, "sz", side, sh, xc - 20, xc - 20 + t, body)
                slab(M, grp, "sz", side, sh, xc + 20 - t, xc + 20, body)

    # ---------------------------------------------------------- poprzeczki RHS 60×40×3 (na stojąco)
    for grp in "AB":
        for sc in cross[grp]:
            info = f"P – poprzeczka RHS 60×40×3 (6060), L = {fmt(g.WIDTH)}\nsekcja {grp}, s = {fmt(sc)} {SFROM[grp]}\n" + \
                   "otwory Ø12,5 przez górę i dół: " + ", ".join(f"{x + g.WIDTH / 2:.0f}" for x in g.LONG_X) + " od lewego końca"
            body = M.mesh(f"{grp}:P:{sc:g}", grp, C_CROSS, "profil", info)
            hv = [(sc, x, 12.5, f"{grp}v:{sc:g}:{x:+.0f}", f"poprzeczka P (s={fmt(sc)}): Ø12,5 przez górę i dół, "
                   f"{x + g.WIDTH / 2:.0f} mm od lewego końca") for x in g.LONG_X]
            W2 = g.WIDTH / 2
            for z0, z1 in ((-3, 0), (-60, -57)):
                slab(M, grp, "sx", [(sc - 17, -W2), (sc + 17, -W2), (sc + 17, W2), (sc - 17, W2)], hv, z0, z1, body)
            for w0, w1 in ((sc - 20, sc - 17), (sc + 17, sc + 20)):
                solid("xz", [(-W2, -60), (W2, -60), (W2, 0), (-W2, 0)], w0, w1, body)

    # ---------------------------------------------------------- listwa T pod sekcją B (nity)
    body = M.mesh("B:T", "B", C_WALK, "profil", f"T – listwa spinająca, płaskownik Al 40×5, L = {fmt(g.WIDTH)}\n"
                  f"pod sekcją B, s = {fmt(g.TIE_B)} od zawiasu; 16 otworów Ø4,9 (±10 mm od osi każdej podłużnicy)")
    rv = [(g.TIE_B, x + dx, 4.9, f"Br:{g.TIE_B:g}:{x + dx:+.0f}",
           f"listwa T: Ø4,9, {x + dx + g.WIDTH / 2:.0f} mm od lewego końca") for x in g.LONG_X for dx in (-10, 10)]
    slab(M, "B", "sx", [(g.TIE_B - 20, -g.WIDTH / 2), (g.TIE_B + 20, -g.WIDTH / 2), (g.TIE_B + 20, g.WIDTH / 2),
                        (g.TIE_B - 20, g.WIDTH / 2)], rv, -5, 0, body)
    riv = M.mesh("B:nity", "B", C_RIVET, "śruba", "nity zrywalne 4,8 z szerokim kołnierzem – listwa T → dno podłużnic B (16 szt.)")
    for x in g.LONG_X:
        for dx in (-10, 10):
            cyl("z", g.TIE_B, x + dx, -5, -6.5, 4.8, riv, 10)
            cyl("z", g.TIE_B, x + dx, -6.5, 5, 2.4, riv, 8)
            cyl("z", g.TIE_B, x + dx, 2.5, 6, 3.2, riv, 8)
            M.bolt_axes.append((f"Br:{g.TIE_B:g}:{x + dx:+.0f}", "nit"))

    # ---------------------------------------------------------- siatka + wkręty
    for grp in "AB":
        solid("sx", [(0, -g.WIDTH / 2), (L, -g.WIDTH / 2), (L, g.WIDTH / 2), (0, g.WIDTH / 2)], 100, 103,
              M.mesh(f"{grp}:siatka", grp, C_MESH, "siatka",
                     "siatka Al cięto-ciągniona 43×13×3×2, 1190 × 1250, LWD w poprzek\nprzykręcona wkrętami 4,8×19 co ~250 mm", 0.45))
        scr = M.mesh(f"{grp}:wkrety", grp, C_BOLT, "śruba", "wkręty samowiercące 4,8×19 nierdzewne z podkładką EPDM Ø16 – mocowanie siatki")
        (ga, gb), _ = guides[grp]
        for xa in (g.X_LANE_IN, g.X_LANE_OUT, g.X_WALK, g.X_EDGE):
            taken = [s for (s, w, z, d, n) in g.holes_long(LONG_ID[(grp, xa)]) if w == "g/d"]
            for s in (60.0, 300.0, 560.0, 800.0, 1060.0, 1200.0):
                if any(abs(s - q) < 45 for q in taken) or (xa == g.X_LANE_OUT and ga - 20 <= s <= gb + 20):
                    continue
                for sg in (-1, 1):
                    cyl("z", s, sg * xa, 103, 106, 8.0, scr, 10)
                    cyl("z", s, sg * xa, 103, 100 - 15, 2.4, scr, 8)

    # ---------------------------------------------------------- prowadnice + śruby M8 (pion)
    for grp in "AB":
        (ga, gb), gbolts = guides[grp]
        pid = "G1" if grp == "A" else "G2"
        pos = sorted([s for s in gbolts + cross[grp] if ga <= s <= gb])
        for sg in (-1, 1):
            xh = sg * (XO - 20)
            info = (f"{pid} – prowadnica koła, kątownik Al 40×40×4, L = {fmt(gb - ga)}, leży na siatce nad rurą zewnętrzną\n"
                    f"otwory Ø9 w półce poziomej, 20 mm od grzbietu, od końca: " + ", ".join(f"{s - ga:.0f}" for s in pos))
            body = M.mesh(f"{grp}:{pid}:{sg}", grp, C_GUIDE, "profil", info)
            hh = [(s, xh, 9.0, f"{grp}v:{s:g}:{xh:+.0f}", f"prowadnica {pid}: Ø9, {s - ga:.0f} mm od jej końca, 20 mm od grzbietu")
                  for s in pos]
            x0, x1 = xr(XO - 40, XO, sg)
            slab(M, grp, "sx", [(ga, x0), (gb, x0), (gb, x1), (ga, x1)], hh, 103, 107, body)
            x0, x1 = xr(XO - 4, XO, sg)
            solid("sz", [(ga, 107), (gb, 107), (gb, 143), (ga, 143)], x0, x1, body)
            for s in gbolts:
                if s in cross[grp]:
                    continue
                b = M.mesh(f"{grp}:M8g:{s:g}:{sg}", grp, C_BOLT, "śruba",
                           f"śruba zamkowa M8×130 DIN 603 + podkładka + nakrętka samohamowna\nprowadnica {pid} → rura "
                           f"{'L1' if grp == 'A' else 'L3'} (x={xh:+.0f}), s={fmt(s)} {SFROM[grp]}\ntuleja Ø12×1,5 dł. 99,5 w rurze")
                bolt(b, "z", s, xh, 107, -1, 130, 8, 107, head="carriage")
                cyl("z", s, xh, 0.25, 99.75, 6.0, M.mesh(f"{grp}:tul100", grp, C_SLEEVE, "tuleja",
                                                        "tuleje Ø12×1,5 dł. 99,5 (prowadnice)"), 12)
                M.bolt_axes.append((f"{grp}v:{s:g}:{xh:+.0f}", "M8"))

    # ---------------------------------------------------------- skrzyżowania: M8×200 + tuleja 159,5
    for grp in "AB":
        for sc in cross[grp]:
            for x in g.LONG_X:
                top = 107 if (abs(x) == g.X_LANE_OUT) else 103
                pid = LONG_ID[(grp, abs(x))]
                b = M.mesh(f"{grp}:M8x:{sc:g}:{x:+.0f}", grp, C_BOLT, "śruba",
                           f"śruba zamkowa M8×200 DIN 603 kl. 8.8 + podkładka + nakrętka samohamowna\n"
                           f"{pid} (x={x:+.0f}) + poprzeczka P, s={fmt(sc)} {SFROM[grp]}\ntuleja Ø12×1,5 dł. 159,5 na wylot (rura 100 + poprzeczka 60)")
                bolt(b, "z", sc, x, top, -1, 200, 8, top + 60)
                cyl("z", sc, x, 99.75, -59.75, 6.0, M.mesh(f"{grp}:tul160", grp, C_SLEEVE, "tuleja",
                                                           "tuleje Ø12×1,5 dł. 159,5 (skrzyżowania)"), 12)
                M.bolt_axes.append((f"{grp}v:{sc:g}:{x:+.0f}", "M8"))

    # ---------------------------------------------------------- płyty stalowe z otworami
    def plate(grp, key, rect_, holes, xs, info, body_key):
        body = M.mesh(body_key, grp, C_STEEL, "płyta", info)
        slab(M, grp, "sz", rect_, holes, xs[0], xs[1], body)

    w, h, phol, _ = g.plate_outline("H")
    for sg in (-1, 1):
        for lay, (a, b) in (("wewn.", (XO - 46, XO - 40)), ("zewn.", (XO, XO + 6))):
            holes = []
            for (n, s, z, d), (_, pa, pb, _) in zip(g.H_PL["holes"], phol):
                key = {"pin": f"Apin:tr:{sg}", "blok": f"Ablok:{sg}"}.get(n, f"Ah:{s:g}:{z:g}:{sg}")
                holes.append((s, z, d, key, f"płyta H {lay} (x {'+' if sg > 0 else '−'}): Ø{fmt(d)} ({n}), ({fmt(pa)}; {fmt(pb)}) od lewego dolnego rogu"))
            plate("A", "H", [(g.H_PL["s0"], g.H_PL["z0"]), (g.H_PL["s0"] + w, g.H_PL["z0"]), (g.H_PL["s0"] + w, g.H_PL["z0"] + h),
                             (g.H_PL["s0"], g.H_PL["z0"] + h)], holes, xr(a, b, sg),
                  f"H – płyta zawiasu przy przyczepie, płaskownik 80×6 S235, dł. 200 ({lay}, x {'+' if sg > 0 else '−'})\n"
                  f"otwory od lewego dolnego rogu: " + "; ".join(f"{n} Ø{fmt(d)} ({fmt(pa)}; {fmt(pb)})" for (n, pa, pb, d) in phol),
                  f"A:H:{lay}:{sg}")
    w, h, zhol, _ = g.plate_outline("Z")
    for grp, sgn, s_of in (("A", -1, lambda d: L - d), ("B", 1, lambda d: d)):
        lays = (("wewn.", (XO - 46, XO - 40)), ("zewn.", (XO, XO + 6))) if grp == "A" else \
               (("wewn.", (XO - 52, XO - 46)), ("zewn.", (XO + 6, XO + 12)))
        for sg in (-1, 1):
            for lay, (a, b) in lays:
                holes = []
                for (n, d_, z, dd), (_, pa, pb, _) in zip(g.Z_PL["holes"], zhol):
                    key = f"pin:mid:{sg}" if n == "pin" else f"{grp}h:{s_of(d_):g}:{z:g}:{sg}"
                    holes.append((s_of(d_), z, dd, key, f"płyta Z ({grp}, {lay}, x {'+' if sg > 0 else '−'}): Ø{fmt(dd)}, ({fmt(pa)}; {fmt(pb)}) od rogu przy sworzniu"))
                d0, d1 = g.Z_PL["d0"], g.Z_PL["d0"] + w
                sa, sb = sorted((s_of(d0), s_of(d1)))
                plate(grp, "Z", [(sa, g.Z_PL["z0"]), (sb, g.Z_PL["z0"]), (sb, g.Z_PL["z0"] + h), (sa, g.Z_PL["z0"] + h)],
                      holes, xr(a, b, sg),
                      f"Z – płyta zawiasu środkowego, płaskownik 100×6 S235, dł. 170 (sekcja {grp}, {lay}, x {'+' if sg > 0 else '−'})\n"
                      f"otwory od rogu przy sworzniu: " + "; ".join(f"{n} Ø{fmt(d)} ({fmt(pa)}; {fmt(pb)})" for (n, pa, pb, d) in zhol),
                      f"{grp}:Z:{lay}:{sg}")
    w, h, shol, _ = g.plate_outline("S")
    for sg in (-1, 1):
        holes = []
        for (n, s, z, d), (_, pa, pb, _) in zip(g.S_PL["holes"], shol):
            key = f"Aeye:{sg}" if n == "oczko" else f"Ah:{s:g}:{z:g}:{sg}"
            holes.append((s, z, d, key, f"płyta S (x {'+' if sg > 0 else '−'}): Ø{fmt(d)} ({n}), ({fmt(pa)}; {fmt(pb)}) od lewego dolnego rogu"))
        s0, z0 = g.S_PL["s0"], g.S_PL["z0"]
        plate("A", "S", [(s0, z0), (s0 + w, z0), (s0 + w, z0 + h), (s0, z0 + h)], holes, xr(g.X_WALK + 20, g.X_WALK + 28, sg),
              "S – płyta zaczepu sprężyny, płaskownik 80×8 S235, dł. 150, na podłużnicy C1\notwory od lewego dolnego rogu: " +
              "; ".join(f"{n} Ø{fmt(d)} ({fmt(pa)}; {fmt(pb)})" for (n, pa, pb, d) in shol), f"A:S:{sg}")

    # ---------------------------------------------------------- śruby M12 poziome (płyty H, Z, S) + tuleje Ø18
    def m12_through_tube(grp, s, z, sg, face_in, grip, Lb, txt, hkey):
        b = M.mesh(f"{grp}:M12:{s:g}:{z:g}:{sg}", grp, C_BOLT, "śruba", txt)
        bolt(b, "x", s, z, sg * face_in, sg, Lb, 12, grip)
        M.bolt_axes.append((hkey, "M12"))

    for sg in (-1, 1):
        for (n, s, z, d) in g.H_PL["holes"]:
            if n == "M12":
                m12_through_tube("A", s, z, sg, XO - 46, 52, 80, f"śruba M12×80 8.8 + 2 podkładki + nakrętka samohamowna\n"
                                 f"płyta H – rura L1 – płyta H, s={fmt(s)} od przyczepy, z={fmt(z)}\ntuleja Ø18×2,5 dł. 40", f"Ah:{s:g}:{z:g}:{sg}")
                cyl("x", s, z, sg * (XO - 40), sg * XO, 9.0, M.mesh("A:tul40", "A", C_SLEEVE, "tuleja", "tuleje Ø18×2,5 dł. 40 (M12)"), 14)
        for grp, s_of in (("A", lambda d: L - d), ("B", lambda d: d)):
            for (n, d_, z, dd) in g.Z_PL["holes"]:
                if n != "M12":
                    continue
                s = s_of(d_)
                if grp == "A":
                    m12_through_tube("A", s, z, sg, XO - 46, 52, 80, f"śruba M12×80 8.8 + 2 podkładki + nakrętka samohamowna\n"
                                     f"płyta Z – rura L1 – płyta Z, s={fmt(s)} od przyczepy, z={fmt(z)}\ntuleja Ø18×2,5 dł. 40", f"Ah:{s:g}:{z:g}:{sg}")
                else:
                    m12_through_tube("B", s, z, sg, XO - 52, 64, 90, f"śruba M12×90 8.8 + 2 podkładki + nakrętka samohamowna\n"
                                     f"płyta Z – podkładka 6 mm – rura L3 – podkładka 6 mm – płyta Z, s={fmt(s)} od zawiasu, z={fmt(z)}\n"
                                     f"tuleja Ø18×2,5 dł. 40", f"Bh:{s:g}:{z:g}:{sg}")
                    wsh = M.mesh(f"B:pk6:{s:g}:{sg}", "B", C_BOLT, "śruba", "podkładka dystansowa DIN 7349 M12 (13×30×6)")
                    cyl("x", s, z, sg * (XO - 46), sg * (XO - 40), 15.0, wsh, 18)
                    cyl("x", s, z, sg * XO, sg * (XO + 6), 15.0, wsh, 18)
                cyl("x", s, z, sg * (XO - 40), sg * XO, 9.0, M.mesh(f"{grp}:tul40", grp, C_SLEEVE, "tuleja", "tuleje Ø18×2,5 dł. 40 (M12)"), 14)
        for (n, s, z, d) in g.S_PL["holes"]:
            if n == "M12":
                m12_through_tube("A", s, z, sg, g.X_WALK - 20, 48, 80, f"śruba M12×80 8.8 + 2 podkładki + nakrętka samohamowna\n"
                                 f"podłużnica C1 – płyta S, s={fmt(s)}, z={fmt(z)}\ntuleja Ø18×2,5 dł. 40", f"Ah:{s:g}:{z:g}:{sg}")
                cyl("x", s, z, sg * (g.X_WALK - 20), sg * (g.X_WALK + 20), 9.0, M.mesh("A:tul40", "A", C_SLEEVE, "tuleja", ""), 14)
        # oczko sprężyny na płycie S: M12×60, tuleja dystansowa Ø20×4 dł. 18
        es, ez = g.SPRING["eye_up_sz"]
        b = M.mesh(f"A:M12oko:{sg}", "A", C_BOLT, "śruba", "śruba M12×60 8.8 – oś górnego oczka sprężyny\n"
                   "płyta S 8 + tuleja dystansowa Ø20×4 dł. 18 + oczko 10 + podkładka + nakrętka samohamowna")
        bolt(b, "x", es, ez, sg * (g.X_WALK + 20), sg, 60, 12, 36)
        cyl("x", es, ez, sg * (g.X_WALK + 28), sg * (g.X_WALK + 46), 10.0, b, 16)
        M.bolt_axes.append((f"Aeye:{sg}", "M12"))
        # sworzeń zawiasu przy przyczepie: M20×110 – H wewn. … wspornik K
        b = M.mesh(f"A:pinTr:{sg}", "A", "#d0d0d0", "śruba", "SWORZEŃ zawiasu przy przyczepie: śruba M20×110 8.8 (gładki trzpień ≥ 64 mm)\n"
                   "H wewn. – (pusto) – H zewn. – wspornik K; podkładki + nakrętka samohamowna NIEDOKRĘCONA (ma się obracać)\n"
                   "25 mm przed końcem rury, 25 mm pod pokładem")
        bolt(b, "x", -25.0, 75.0, sg * (XO - 46), sg, 110, 20, 63)
        M.bolt_axes += [(f"Apin:tr:{sg}", "M20"), (f"Tpin:zawias:{sg}", "M20")]
        # sworzeń zawiasu środkowego (w sekcji A, przez 4 płyty)
        b = M.mesh(f"A:pinMid:{sg}", "A", "#d0d0d0", "śruba", "SWORZEŃ zawiasu środkowego: śruba M20×110 8.8 (gładki trzpień ≥ 64 mm)\n"
                   "Z(B) – Z(A) – (pod rurą) – Z(A) – Z(B); nakrętka samohamowna NIEDOKRĘCONA\n35 mm pod spodem rur, na styku rur")
        bolt(b, "x", L, -35.0, sg * (XO - 52), sg, 110, 20, 64)
        M.bolt_axes.append((f"pin:mid:{sg}", "M20"))

    # ---------------------------------------------------------- przyczepa (poglądowo) + wsporniki K z otworami
    T = "T"
    solid("sx", [(-1400, -650), (-50, -650), (-50, 650), (-1400, 650)], -18, 0,
          M.mesh("T:podloga", T, "#9a8f80", "przyczepa", "podłoga przyczepy (przykład: 480 mm nad ziemią)"))
    beam = M.mesh("T:belka", T, "#7d7d7d", "przyczepa", "tylna belka przyczepy – PRZYKŁAD 50×75×3 (dopasuj!)\n"
                  "otwory Ø18,5 na wylot pod tuleje Ø18×2,5 dł. 50 i śruby M12×80 wsporników K")
    kx = {"zawias": 152.0, "sprężyna": 369.0}
    bh = []
    for nm, xa in kx.items():
        for sg in (-1, 1):
            for (n, xx, z, d) in g.K_PL["holes_beam"]:
                X = sg * (xa + xx)
                bh.append((X, z, 18.5, f"Tb:{X:+.0f}:{z:g}", f"belka przyczepy: Ø18,5 na wylot, x={X:+.0f}, {fmt(-z)} mm pod podłogą"))
    for w0, w1 in ((-50, -47), (-3, 0)):
        slab(M, T, "xz", [(-700, -75), (700, -75), (700, 0), (-700, 0)], bh, w0, w1, beam)
    for z0, z1 in ((-75, -72), (-3, 0)):
        solid("sx", [(-47, -700), (-3, -700), (-3, 700), (-47, 700)], z0, z1, beam)
    solid("sz", [(-1400, 0), (-40, 0), (-40, 350), (-1400, 350)], 650, 670, M.mesh("T:burta+", T, "#9a8f80", "przyczepa", "burta (poglądowo)", 0.35))
    solid("sz", [(-1400, 0), (-40, 0), (-40, 350), (-1400, 350)], -670, -650, M.mesh("T:burta-", T, "#9a8f80", "przyczepa", "burta (poglądowo)", 0.35))
    for sg in (-1, 1):
        solid("sz", ring(-900, -480 + 165, 330, 24), *xr(700, 880, sg), M.mesh(f"T:kolo:{sg}", T, "#222222", "przyczepa", "koło przyczepy (poglądowo)"))
    for nm, xa in kx.items():
        for sg in (-1, 1):
            info = (f"K – wspornik ({nm}), kątownik stal 100×100×10, dł. 130, x {'+' if sg > 0 else '−'}{xa:.0f}…{xa + 10:.0f}\n"
                    "ramię odstające (y od ściany belki; z od podłogi): " +
                    "; ".join(f"{n} Ø{fmt(d)} (y={fmt(y)}, z={fmt(z)})" for (n, y, z, d) in g.K_PL["holes_arm"]) +
                    "\nramię na belce: 2 × Ø13, 55 mm od grzbietu, z = −30 i −60")
            body = M.mesh(f"T:K:{nm}:{sg}", T, C_TRAILER, "płyta", info)
            arm = []
            for (n, y, z, d) in g.K_PL["holes_arm"]:
                key = {"pin": f"Tpin:{nm}:{sg}", "blok": f"Tblok:{nm}:{sg}", "sprez.": f"Tspr:{nm}:{sg}"}[n]
                used = (nm == "zawias" and n in ("pin", "blok")) or (nm == "sprężyna" and n == "sprez.")
                arm.append((y, z, d, key, f"wspornik K ({nm}, x {'+' if sg > 0 else '−'}): Ø{fmt(d)} ({n}), y={fmt(y)} od ściany belki, z={fmt(z)} od podłogi"
                            + ("" if used else " – tu nieużywany (część identyczna)")))
            slab(M, T, "sz", [(0, -130), (100, -130), (100, 0), (0, 0)], arm, *xr(xa, xa + 10, sg), body)
            bl = [(sg * (xa + xx), z, d, f"Tb:{sg * (xa + xx):+.0f}:{z:g}", f"wspornik K ({nm}): Ø13, 55 mm od grzbietu, z={fmt(z)}")
                  for (n, xx, z, d) in g.K_PL["holes_beam"]]
            slab(M, T, "xz", [(*xr(xa, xa + 100, sg)[:1], -130), (xr(xa, xa + 100, sg)[1], -130), (xr(xa, xa + 100, sg)[1], 0),
                              (xr(xa, xa + 100, sg)[0], 0)], bl, 0, 10, body)
            for (n, xx, z, d) in g.K_PL["holes_beam"]:
                X = sg * (xa + xx)
                b = M.mesh(f"T:M12K:{X:+.0f}:{z:g}", T, C_BOLT, "śruba", f"śruba M12×80 8.8 – wspornik K ({nm}) → belka przyczepy\n"
                           f"x={X:+.0f}, {fmt(-z)} mm pod podłogą; tuleja Ø18×2,5 dł. 50 w belce (DOPASUJ do swojej belki)")
                bolt(b, "s", X, z, -50, 1, 80, 12, 60)
                cyl("s", X, z, -50, 0, 9.0, M.mesh("T:tul50", T, C_SLEEVE, "tuleja", "tuleje Ø18×2,5 dł. 50 (belka)"), 14)
                M.bolt_axes.append((f"Tb:{X:+.0f}:{z:g}", "M12"))
            if nm == "sprężyna":
                y, z = 30.0, -100.0
                b = M.mesh(f"T:M12oko:{sg}", T, C_BOLT, "śruba", "śruba M12×60 8.8 – oś dolnego oczka sprężyny\n"
                           "ramię K 10 + tuleja dystansowa Ø20×4 dł. 12 + oczko 10 + podkładka + nakrętka samohamowna")
                bolt(b, "x", y, z, sg * xa, sg, 60, 12, 32)
                cyl("x", y, z, sg * (xa + 10), sg * (xa + 22), 10.0, b, 16)
                M.bolt_axes.append((f"Tspr:{nm}:{sg}", "M12"))
            else:
                lp = M.mesh(f"L:blok:{sg}", "L", "#e0c040", "śruba", "sworzeń blokady Ø12×40 ISO 2341-B + zawleczka (tylko do jazdy)\n"
                            "przez wspornik K i płytę H zewn., 30 mm za osią zawiasu")
                cyl("x", 70.0, -25.0, sg * (xa + 10), sg * (xa + 13), 9.0, lp, 14)
                cyl("x", 70.0, -25.0, sg * (xa + 10), sg * (xa - 30), 6.0, lp, 14)
                M.bolt_axes += [(f"Tblok:{nm}:{sg}", "Ø12"), (f"Ablok:{sg}", "Ø12")]
    # opisy otworów
    for key in list(M.m):
        if key.startswith("otw:"):
            k = M.m[key]["info"]
            M.m[key]["info"] = f"OTWÓR – miejsce wiercenia (Ø{fmt(M.hole_dia[k])} max)\n" + "\n".join(M.hole_txt[k])
    return M


# ================================================================== RUCH
_TH0 = None


def pose(t):
    """t: 0 = rozłożony, 1 = do jazdy  ->  (kąt sekcji A, kąt B względem A) [rad]"""
    global _TH0
    (mA, cAs, cAz), (mB, cBs, cBz) = g.masses()
    if _TH0 is None:
        _TH0 = math.radians(g.lift_table(mA, cAs, cAz, mB, cBs, cBz, False)[0]["deg"])
    zg = -(g.H_FLOOR + g.PIN_Z)
    cBu, cBv, tipu, tipv = cBs, cBz + 35.0, g.L_SEC, 135.0
    th = _TH0 + (math.pi / 2 - _TH0) * t
    pm = g.rot(th, U_MID, V_MID)
    ph = math.atan2(cBu, cBv)
    if g.rot(ph, cBu, cBv)[1] > 0:
        ph += math.pi
    ph = math.atan2(math.sin(ph), math.cos(ph))
    if pm[1] + g.rot(ph, tipu, tipv)[1] <= zg:
        a, b = 1e-5, abs(ph)
        for _ in range(80):
            m = (a + b) / 2
            if pm[1] + g.rot(-m, tipu, tipv)[1] - zg > 0:
                a = m
            else:
                b = m
        ph = -(a + b) / 2
    rel = ph - th
    while rel > 0:
        rel -= 2 * math.pi
    return th, max(rel, -math.pi)


def springs(th):
    lo = (g.PIN_Z + g.SPRING["eye_low"][1], -(g.PIN_Y + g.SPRING["eye_low"][0]))
    u, v = g.SPRING["eye_up_sz"][0] + 25.0, g.SPRING["eye_up_sz"][1] - 75.0
    y, z = g.rot(th, u, v)
    return lo, (g.PIN_Z + z, -(g.PIN_Y + y))


def spring_segments(th):
    lo, hi = springs(th)
    out = []
    for sg in (-1, 1):
        a = np.array((sg * SPRING_X, *lo))
        b = np.array((sg * SPRING_X, *hi))
        mid = a + 0.55 * (b - a)
        out += [(a, mid, 14.0, C_SPRING), (mid, b, 7.0, C_ROD)]
    return out


def local(grp, p):
    """(x, s, z) części -> układ lokalny węzła glTF [mm]"""
    x, s, z = p
    if grp in ("T", "L"):
        return (x, z, -s)
    if grp == "A":
        return (x, z - 75.0, -(s + 25.0))
    return (x, z + 35.0, -s)


def rot_x(p, a):
    c, s = math.cos(a), math.sin(a)
    return np.array((p[..., 0], p[..., 1] * c - p[..., 2] * s, p[..., 1] * s + p[..., 2] * c)).transpose(
        list(range(1, p.ndim)) + [0])


def _quat_from_y(d):
    y = np.array((0.0, 1.0, 0.0))
    c = np.cross(y, d)
    w = 1.0 + float(np.dot(y, d))
    if w < 1e-8:
        return np.array((0.0, 0.0, 1.0, 0.0))
    q = np.array((c[0], c[1], c[2], w))
    return q / np.linalg.norm(q)


def _qrot(q, v):
    u, w = np.array(q[:3]), q[3]
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def cyl_y(r, n=16):
    """walec r, y = 0…1 (do sprężyn) – trójkąty"""
    out = []
    cyl("z", 0, 0, 0, 1, r, out, n)            # w układzie (x, s, z): oś z
    return [[(p[0], p[2], p[1]) for p in t] for t in out]


# ================================================================== glTF 2.0 (GLB)
def write_gltf(path, frames=61, seconds=6.0, M=None):
    M = M or build()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bin_ = bytearray()
    views, accs, meshes, mats, nodes = [], [], [], [], []
    mat_idx = {}

    def accessor(arr, typ, target=None, minmax=False):
        arr = np.ascontiguousarray(arr, dtype="<f4")
        while len(bin_) % 4:
            bin_.append(0)
        v = dict(buffer=0, byteOffset=len(bin_), byteLength=arr.nbytes)
        if target:
            v["target"] = target
        bin_.extend(arr.tobytes())
        views.append(v)
        a = dict(bufferView=len(views) - 1, componentType=5126, count=int(arr.shape[0]), type=typ)
        if minmax:
            a["min"] = [float(x) for x in np.atleast_1d(arr.min(axis=0))]
            a["max"] = [float(x) for x in np.atleast_1d(arr.max(axis=0))]
        accs.append(a)
        return len(accs) - 1

    def material(col, op):
        if (col, op) not in mat_idx:
            rgb = [int(col[k:k + 2], 16) / 255 for k in (1, 3, 5)]
            m = dict(name="kolor_" + col[1:], doubleSided=True,
                     pbrMetallicRoughness=dict(baseColorFactor=rgb + [op], metallicFactor=0.3, roughnessFactor=0.55))
            if op < 1:
                m["alphaMode"] = "BLEND"
            mats.append(m)
            mat_idx[(col, op)] = len(mats) - 1
        return mat_idx[(col, op)]

    def mesh(tris, col, op, name):
        Pp = np.asarray(tris, float).reshape(-1, 3, 3)
        n = np.cross(Pp[:, 1] - Pp[:, 0], Pp[:, 2] - Pp[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        N = np.repeat(n, 3, axis=0)
        prim = dict(attributes=dict(POSITION=accessor(Pp.reshape(-1, 3), "VEC3", 34962, True),
                                    NORMAL=accessor(N, "VEC3", 34962)), material=material(col, op))
        meshes.append(dict(name=name[:60], primitives=[prim]))
        return len(meshes) - 1

    def node(name, **kw):
        nodes.append(dict(name=name, **kw))
        return len(nodes) - 1

    groups = defaultdict(list)
    for key, m in M.m.items():
        if not m["tris"]:
            continue
        loc = np.array([[local(m["grp"], p) for p in t] for t in m["tris"]]) / 1000.0
        groups[m["grp"]].append(node(key, mesh=mesh(loc, m["c"], m["o"], m["info"].split("\n")[0]),
                                     extras=dict(nazwa=m["info"], rodzaj=m["kind"], id=key)))
    nB = node("sekcja_B", children=groups["B"], translation=[0.0, V_MID / 1000, -U_MID / 1000], extras=dict(nazwa="sekcja B"))
    nA = node("sekcja_A", children=groups["A"] + [nB], translation=[0.0, g.PIN_Z / 1000, -g.PIN_Y / 1000], extras=dict(nazwa="sekcja A"))
    nL = node("blokada", children=groups["L"], scale=[1e-4, 1e-4, 1e-4], extras=dict(nazwa="blokada do jazdy"))
    nT = node("przyczepa", children=groups["T"] + [nL], extras=dict(nazwa="przyczepa (poglądowo)"))
    mmy = np.array((1e-3, 1.0, 1e-3))
    cylm = {(14.0, C_SPRING): mesh(np.array(cyl_y(14.0)) * mmy, C_SPRING, 1.0, "sprężyna – cylinder"),
            (7.0, C_ROD): mesh(np.array(cyl_y(7.0)) * mmy, C_ROD, 1.0, "sprężyna – tłoczysko")}
    seg0 = spring_segments(pose(0)[0])
    spr = [node(f"sprezyna_{'LLPP'[k]}_{'ct'[k % 2]}", mesh=cylm[(r, col)],
                extras=dict(nazwa="sprężyna gazowa 460 mm / skok 200 / 1600 N, oczka M12", rodzaj="sprężyna"))
           for k, (_, _, r, col) in enumerate(seg0)]
    root = node("trap_v2", children=[nT, nA] + spr, extras=dict(nazwa="trap V2"))

    ts = np.linspace(0.0, 1.0, frames)
    qa, qb, sl, trs = [], [], [], [([], [], []) for _ in spr]
    for t in ts:
        th, rel = pose(t)
        qa.append((math.sin(th / 2), 0.0, 0.0, math.cos(th / 2)))
        qb.append((math.sin(rel / 2), 0.0, 0.0, math.cos(rel / 2)))
        sl.append((1.0,) * 3 if t > 0.98 else (1e-4,) * 3)
        for k, (a, b, r, col) in enumerate(spring_segments(th)):
            d = (b - a) / 1000
            Ld = float(np.linalg.norm(d))
            trs[k][0].append(a / 1000)
            trs[k][1].append(_quat_from_y(d / Ld))
            trs[k][2].append((1.0, Ld, 1.0))
    t_acc = accessor(ts * seconds, "SCALAR", minmax=True)
    samplers, channels = [], []

    def anim(ni, path_, vals, typ, interp="LINEAR"):
        samplers.append(dict(input=t_acc, output=accessor(np.array(vals, float), typ), interpolation=interp))
        channels.append(dict(sampler=len(samplers) - 1, target=dict(node=ni, path=path_)))
    anim(nA, "rotation", qa, "VEC4")
    anim(nB, "rotation", qb, "VEC4")
    anim(nL, "scale", sl, "VEC3", "STEP")
    for k, ni in enumerate(spr):
        anim(ni, "translation", trs[k][0], "VEC3")
        anim(ni, "rotation", trs[k][1], "VEC4")
        anim(ni, "scale", trs[k][2], "VEC3")
    nodes[nA]["rotation"] = [float(x) for x in qa[0]]
    nodes[nB]["rotation"] = [float(x) for x in qb[0]]
    for k, ni in enumerate(spr):
        nodes[ni].update(translation=[float(x) for x in trs[k][0][0]], rotation=[float(x) for x in trs[k][1][0]],
                         scale=[float(x) for x in trs[k][2][0]])
    gl = dict(asset=dict(version="2.0", generator="trap_uproszczony/podglad3d.py"),
              scene=0, scenes=[dict(name="trap", nodes=[root])], nodes=nodes, meshes=meshes, materials=mats,
              accessors=accs, bufferViews=views, buffers=[dict(byteLength=0)],
              animations=[dict(name="skladanie", samplers=samplers, channels=channels)],
              extras=dict(opis="Trap aluminiowy V2 2,5 × 1,19 m, bez spawania – model warsztatowy (otwory, śruby, tuleje). "
                               "Animacja: 0 s rozłożony → 6 s do jazdy.", kat_najazdu_deg=round(g.ALPHA, 1)))
    while len(bin_) % 4:
        bin_.append(0)
    gl["buffers"][0]["byteLength"] = len(bin_)
    js = json.dumps(gl, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(bin_), 0x004E4942) + bytes(bin_))
    return path


def export_holes(M, path):
    """lista wszystkich otworów z modelu (te same dane co w 3D): miejsce wiercenia w każdej części"""
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["nr", "Ø max [mm]", "złącze", "miejsca wiercenia (każda część, przez którą przechodzi)"])
        kinds = dict(M.bolt_axes)
        for i, k in enumerate(sorted(M.hole_dia), 1):
            w.writerow([i, fmt(M.hole_dia[k]), kinds.get(k, "–"), " | ".join(M.hole_txt[k])])
    return path


# ================================================================== KONTROLA
def check(M=None):
    """każdy otwór pod śrubę ma śrubę/nit/sworzeń i każda śruba ma otwór we wszystkich częściach"""
    M = M or build()
    holes = set(M.hole_dia)
    used = {k for (k, _) in M.bolt_axes}
    free = sorted(k for k in holes - used if not (k.startswith("Tpin:sprężyna") or k.startswith("Tblok:sprężyna")
                                                 or k.startswith("Tspr:zawias")))
    missing = sorted(used - holes)
    print(f"otworów: {len(holes)}, złączy: {len(M.bolt_axes)}")
    print("otwory bez śruby:", free or "brak")
    print("śruby bez otworu:", missing or "brak")
    multi = {k: v for k, v in M.hole_txt.items() if len(v) > 1}
    print(f"otwory wspólne dla kilku części (wiercić razem / zgrać): {len(multi)}")
    # kolizje: czy trzpień śruby przechodzi przez materiał (profil / płytę) – czyli brak lub przesunięty otwór
    bodies = defaultdict(list)
    for k, m in M.m.items():
        if m["kind"] in ("profil", "płyta", "przyczepa") and m["tris"]:
            bodies[m["grp"]].append(np.asarray(m["tris"], float))
    bodies = {gk: np.concatenate(v) for gk, v in bodies.items()}
    idx = {"x": 0, "s": 1, "z": 2}
    other = {"x": (1, 2), "s": (0, 2), "z": (1, 0)}
    bad = []
    for (grp, axis, c1, c2, a0, a1, d, key) in M.shanks:
        T = bodies[grp]
        v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
        lo, hi = sorted((a0, a1))
        lo, hi = lo + 0.3, hi - 0.3
        for ang in range(0, 360, 45):
            p0 = np.zeros(3)
            p0[other[axis][0]] = c1 + 0.9 * d / 2 * math.cos(math.radians(ang))
            p0[other[axis][1]] = c2 + 0.9 * d / 2 * math.sin(math.radians(ang))
            p0[idx[axis]] = lo
            dv = np.zeros(3)
            dv[idx[axis]] = hi - lo
            h = np.cross(dv, e2)
            a = np.einsum("ij,ij->i", e1, h)
            ok = np.abs(a) > 1e-9
            f = np.where(ok, 1.0 / np.where(ok, a, 1), 0)
            sv = p0 - v0
            u = f * np.einsum("ij,ij->i", sv, h)
            q = np.cross(sv, e1)
            v = f * (q @ dv)
            tt = f * np.einsum("ij,ij->i", e2, q)
            hit = ok & (u >= 0) & (u <= 1) & (v >= 0) & (u + v <= 1) & (tt > 0) & (tt < 1)
            if hit.any():
                bad.append(key)
                break
    print("śruby przechodzące przez materiał (zły otwór):", sorted(set(bad)) or "brak")
    return not free and not missing and not bad


# ================================================================== PODGLĄD W PYTHONIE (matplotlib)
def world_tris(M, t):
    """trójkąty w układzie świata [mm] (Y w górę): [(tablica n×3×3, kolor, krycie, rodzaj, klucz)]"""
    th, rel = pose(t)
    oA = np.array((0.0, g.PIN_Z, -g.PIN_Y))
    oB = np.array((0.0, V_MID, -U_MID))
    out = []
    for key, m in M.m.items():
        if not m["tris"] or (m["grp"] == "L" and t < 0.98):
            continue
        loc = np.array([[local(m["grp"], p) for p in tr] for tr in m["tris"]])
        if m["grp"] == "A":
            loc = oA + rot_x(loc, th)
        elif m["grp"] == "B":
            loc = oA + rot_x(oB + rot_x(loc, rel), th)
        out.append((loc, m["c"], m["o"], m["kind"], key))
    for k, (a, b, r, col) in enumerate(spring_segments(th)):
        d = b - a
        q = _quat_from_y(d / np.linalg.norm(d))
        tri = np.array(cyl_y(r)) * np.array((1.0, np.linalg.norm(d), 1.0))
        out.append((a + np.array([[_qrot(q, v) for v in t_] for t_ in tri]), col, 1.0, "sprężyna", f"spr{k}"))
    return out


def _rgb(c):
    return np.array([int(c[k:k + 2], 16) / 255 for k in (1, 3, 5)])


# ================================================================== RENDERER (numpy, bufor głębokości)
VIEWS = {   # nazwa: (oko, cel) w mm, układ świata (x w poprzek, y w górę, -z do tyłu)
    "3d": ((3600, 1800, -4400), (0, -150, -1100)),
    "bok": ((5200, -100, -1100), (0, -100, -1100)),
    "gora": ((1, 5000, -1250), (0, -200, -1300)),
    "spod": ((1200, -2200, -1600), (0, -300, -1300)),
    "jazda": ((2600, 900, -3600), (0, 400, -300)),
    "zawias_przyczepa": ((640, 260, -520), (150, -40, -70)),
    "zawias_srodkowy": ((600, -150, -1700), (130, -300, -1290)),
    "skrzyzowanie": ((650, 120, -950), (180, -130, -390)),
    "sprezyna": ((900, -80, -620), (395, -150, -170)),
}


def render(M, t=0.0, view="3d", W=1280, H=860, fov=40.0, hide=(), transparent=False, cut=None, tris=None):
    """obraz RGB (H×W×3, uint8) – perspektywa, bufor głębokości, cieniowanie, kontury części"""
    eye, tgt = (np.array(v, float) for v in (VIEWS[view] if isinstance(view, str) else view))
    f = tgt - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, (0.0, 1.0, 0.0))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    fp = (H / 2) / math.tan(math.radians(fov / 2))
    zbuf = np.full((H, W), np.inf)
    img = np.zeros((H, W, 3))
    ids = np.full((H, W), -1, int)
    sky = np.linspace(1.0, 0.86, H)[:, None, None] * np.array((0.95, 0.96, 0.98))
    img[:] = sky
    L1, L2 = np.array((0.45, 0.8, -0.4)), np.array((-0.6, -0.3, 0.75))
    L1 /= np.linalg.norm(L1)
    L2 /= np.linalg.norm(L2)
    items = tris if tris is not None else world_tris(M, t)
    # ziemia
    gy = -(g.H_FLOOR)
    ground = np.array([[(-6000, gy, -6000), (6000, gy, -6000), (6000, gy, 6000)], [(-6000, gy, -6000), (6000, gy, 6000), (-6000, gy, 6000)]], float)
    items = [(ground, "#cfd8c3", 1.0, "ziemia", "ziemia")] + list(items)
    passes = [[], []]
    for i, (P, col, op, kind, key) in enumerate(items):
        if kind in hide:
            continue
        P = np.asarray(P, float)
        if transparent and kind in ("profil", "płyta"):
            op = 0.3
        if cut is not None and kind != "ziemia":
            P = P[P[:, :, 0].min(axis=1) <= cut]
            if not len(P):
                continue
        passes[op < 1].append((i, P, _rgb(col), op))
    for transparent_pass in (0, 1):
        for i, P, col, op in passes[transparent_pass]:
            rel = P - eye
            xv, yv, zv = rel @ r, rel @ u, rel @ f
            n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            shade = 0.38 + 0.5 * np.abs(n @ L1) + 0.2 * np.abs(n @ L2)
            ok = (zv > 30).all(axis=1)
            sx = W / 2 + xv / np.maximum(zv, 1e-6) * fp
            sy = H / 2 - yv / np.maximum(zv, 1e-6) * fp
            for k in np.nonzero(ok)[0]:
                x0, x1 = int(max(0, math.floor(sx[k].min()))), int(min(W - 1, math.ceil(sx[k].max())))
                y0, y1 = int(max(0, math.floor(sy[k].min()))), int(min(H - 1, math.ceil(sy[k].max())))
                if x1 < x0 or y1 < y0:
                    continue
                ax_, ay_, bx_, by_, cx_, cy_ = sx[k, 0], sy[k, 0], sx[k, 1], sy[k, 1], sx[k, 2], sy[k, 2]
                den = (by_ - cy_) * (ax_ - cx_) + (cx_ - bx_) * (ay_ - cy_)
                if abs(den) < 1e-9:
                    continue
                yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
                w0 = ((by_ - cy_) * (xx - cx_) + (cx_ - bx_) * (yy - cy_)) / den
                w1 = ((cy_ - ay_) * (xx - cx_) + (ax_ - cx_) * (yy - cy_)) / den
                w2 = 1 - w0 - w1
                m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
                if not m.any():
                    continue
                iz = w0 / zv[k, 0] + w1 / zv[k, 1] + w2 / zv[k, 2]
                z = 1.0 / iz
                zb = zbuf[y0:y1 + 1, x0:x1 + 1]
                m &= z < zb - 0.05
                if not m.any():
                    continue
                c = np.clip(col * shade[k], 0, 1)
                sub = img[y0:y1 + 1, x0:x1 + 1]
                if op >= 1:
                    sub[m] = c
                    zb[m] = z[m]
                    ids[y0:y1 + 1, x0:x1 + 1][m] = i
                else:
                    sub[m] = sub[m] * (1 - op) + c * op
    # kontury: granica między różnymi częściami
    e = np.zeros((H, W), bool)
    e[:, 1:] |= ids[:, 1:] != ids[:, :-1]
    e[1:, :] |= ids[1:, :] != ids[:-1, :]
    e &= ids >= 0
    img[e] *= 0.45
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def _legend(fig):
    items = [(C_LANE, "rury jezdne 100×40×3 6082-T6"), (C_WALK, "podłużnice 100×40×2"), (C_CROSS, "poprzeczki 60×40×3"),
             (C_GUIDE, "prowadnice"), (C_STEEL, "płyty H/Z/S"), (C_TRAILER, "wsporniki K"), (C_HOLE, "otwory"),
             (C_BOLT, "śruby, podkładki, nakrętki"), (C_SLEEVE, "tuleje")]
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c, label=l) for c, l in items], loc="lower left", fontsize=8, ncol=3, frameon=True)


def show_window():
    """okno: obraz z renderera, suwak pozycji, przyciski widoków i warstw"""
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, Button, CheckButtons
    M = build()
    st = dict(t=0.0, view="3d", hide=set(), tr=False)
    fig = plt.figure("Trap V2 – podgląd 3D (Python)", figsize=(13, 8.6))
    ax = fig.add_axes([0.0, 0.16, 0.82, 0.84])
    ax.axis("off")
    im = ax.imshow(render(M, 0.0, "3d", 1100, 740))
    title = fig.text(0.01, 0.97, "", fontsize=10, weight="bold")

    def redraw():
        title.set_text("renderuję…")
        fig.canvas.draw_idle()
        plt.pause(0.01)
        im.set_data(render(M, st["t"], st["view"], 1100, 740, hide=st["hide"], transparent=st["tr"]))
        title.set_text(f"Trap V2 – pozycja {st['t']:.2f} (0 = rozłożony, 1 = do jazdy) · widok: {st['view']}")
        fig.canvas.draw_idle()

    s = Slider(fig.add_axes([0.08, 0.10, 0.5, 0.025]), "pozycja", 0.0, 1.0, valinit=0.0)
    s.on_changed(lambda v: (st.update(t=v), redraw()))
    btns = []
    for i, (lab, vw) in enumerate((("3D", "3d"), ("z boku", "bok"), ("z góry", "gora"), ("od spodu", "spod"),
                                   ("zawias przy\nprzyczepie", "zawias_przyczepa"), ("zawias\nśrodkowy", "zawias_srodkowy"),
                                   ("skrzyżowanie", "skrzyzowanie"), ("sprężyna", "sprezyna"), ("do jazdy", "jazda"))):
        b = Button(fig.add_axes([0.84, 0.90 - i * 0.065, 0.14, 0.055]), lab)
        b.on_clicked(lambda e, vw=vw: (st.update(view=vw, t=1.0 if vw == "jazda" else st["t"]),
                                       s.set_val(st["t"]) if vw == "jazda" else redraw()))
        btns.append(b)
    chk = CheckButtons(fig.add_axes([0.84, 0.16, 0.14, 0.17]), ["śruby", "tuleje", "siatka", "przyczepa", "przezroczyste"],
                       [True, True, True, True, False])

    def toggle(lab):
        kind = {"śruby": "śruba", "tuleje": "tuleja", "siatka": "siatka", "przyczepa": "przyczepa"}.get(lab)
        if kind:
            st["hide"] ^= {kind}
        else:
            st["tr"] = not st["tr"]
        redraw()
    chk.on_clicked(toggle)
    _legend(fig)
    redraw()
    plt.show()


def save_png():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    M = build()
    shots = [(0.0, "podglad_rozlozony.png", "3d", {}), (0.55, "podglad_skladanie.png", "3d", {}),
             (1.0, "podglad_do_jazdy.png", "jazda", {}),
             (0.0, "podglad_zawias_przyczepa.png", "zawias_przyczepa", {}),
             (0.0, "podglad_zawias_srodkowy.png", "zawias_srodkowy", {}),
             (0.0, "podglad_skrzyzowanie.png", "skrzyzowanie", dict(transparent=True)),
             (0.0, "podglad_otwory_zawias.png", "zawias_przyczepa", dict(hide=("śruba", "tuleja", "siatka", "sprężyna")))]
    for t, name, view, kw in shots:
        img = render(M, t, view, 1400, 940, **kw)
        plt.imsave(os.path.join(OUT, name), img)
        print(name)



def serve(port=8000):
    import functools, http.server, webbrowser
    write_gltf(os.path.join(WWW, "trap_v2.glb"))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WWW)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    print(f"Podgląd w przeglądarce: http://localhost:{port}   (Ctrl+C kończy)")
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass
    srv.serve_forever()


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--gltf" in a:
        M = build()
        print(write_gltf(os.path.join(WWW, "trap_v2.glb"), M=M))
        print(export_holes(M, os.path.join(OUT, "otwory_z_modelu.csv")))
    elif "--png" in a:
        save_png()
    elif "--www" in a:
        serve()
    elif "--sprawdz" in a:
        sys.exit(0 if check() else 1)
    else:
        show_window()
