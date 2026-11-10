# -*- coding: utf-8 -*-
"""
Podgląd 3D trapu V2 – w Pythonie i eksport do glTF.

  python3 podglad3d.py            okno 3D (matplotlib) z suwakiem „pozycja” – rozłożony ↔ do jazdy
  python3 podglad3d.py --png      zapisuje podglad_rozlozony.png, podglad_skladanie.png, podglad_do_jazdy.png
  python3 podglad3d.py --gltf     zapisuje www/trap_v2.glb (model glTF 2.0 z animacją „skladanie”)
  python3 podglad3d.py --www      eksport glTF + uruchamia stronę http://localhost:8000 (www/index.html)

Wymaga tylko: pip install matplotlib numpy   (wymiary bierze z generuj.py)
Układ glTF: metry, oś Y do góry, X w poprzek trapu, -Z = do tyłu za przyczepę.
"""
import json, math, os, struct, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generuj as g

OUT = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(OUT, "www")

C_LANE, C_WALK, C_CROSS = "#8fa9c9", "#c9cfd6", "#d8b98a"
C_MESH, C_GUIDE, C_STEEL, C_TRAILER = "#5f6b78", "#3f6fb0", "#3a3a3a", "#b04a3a"
C_PIN, C_SPRING, C_ROD = "#d0d0d0", "#151515", "#e0e0e0"
U_MID, V_MID = g.L_SEC + 25.0, -110.0          # zawias środkowy względem osi zawiasu przy przyczepie
SPRING_X = 396.0


# ------------------------------------------------------------------ GEOMETRIA
def rect(s0, s1, z0, z1):
    return [(s0, z0), (s1, z0), (s1, z1), (s0, z1)]


def circle(sc, zc, r, n=14):
    return [(sc + r * math.cos(2 * math.pi * k / n), zc + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def parts():
    """bryły: grupa T (przyczepa, a=y, b=z), A (a=s, b=z sekcji A), B (a=s, b=z sekcji B); wielokąt wypukły × zakres x"""
    P = []

    def add(grp, poly, x0, x1, col, name, mirror=True, op=1.0):
        P.append(dict(g=grp, p=poly, x0=x0, x1=x1, c=col, n=name, o=op))
        if mirror and not (x0 <= 0 <= x1):
            P.append(dict(g=grp, p=poly, x0=-x1, x1=-x0, c=col, n=name, o=op))

    L, SK = g.L_SEC, g.SKOS
    for x in (g.X_LANE_IN, g.X_LANE_OUT, g.X_WALK, g.X_EDGE):
        col = C_LANE if x < 200 else C_WALK
        nm = "rura jezdna 100×40×3 (6082-T6)" if x < 200 else "podłużnica 100×40×2 (6060)"
        add("A", rect(0, L, 0, 100), x - 20, x + 20, col, nm + " – sekcja A")
        add("B", [(0, 0), (L - SK, 0), (L, 100), (0, 100)], x - 20, x + 20, col, nm + " – sekcja B, skos przy ziemi")
    for s in g.CROSS_A:
        add("A", rect(s - 20, s + 20, -60, 0), -g.WIDTH / 2, g.WIDTH / 2, C_CROSS, "poprzeczka 60×40×3", False)
    for s in g.CROSS_B:
        add("B", rect(s - 20, s + 20, -60, 0), -g.WIDTH / 2, g.WIDTH / 2, C_CROSS, "poprzeczka 60×40×3", False)
    add("B", rect(g.TIE_B - 20, g.TIE_B + 20, -5, 0), -g.WIDTH / 2, g.WIDTH / 2, C_WALK, "listwa spinająca T 40×5 (nity)", False)
    for grp in "AB":
        add(grp, rect(0, L, 100, 103), -g.WIDTH / 2, g.WIDTH / 2, C_MESH, "siatka Al cięto-ciągniona", False, 0.45)
    xo = g.X_LANE_OUT + 20
    for grp, (a, b) in (("A", g.GUIDE_A), ("B", g.GUIDE_B)):
        add(grp, rect(a, b, 103, 107), xo - 40, xo, C_GUIDE, "prowadnica koła 40×40×4")
        add(grp, rect(a, b, 107, 143), xo - 4, xo, C_GUIDE, "prowadnica koła 40×40×4")
    hp = rect(g.H_PL["s0"], g.H_PL["s0"] + g.H_PL["w"], g.H_PL["z0"], g.H_PL["z0"] + g.H_PL["h"])
    add("A", hp, xo, xo + 6, C_STEEL, "płyta H – zawias przy przyczepie")
    add("A", hp, xo - 46, xo - 40, C_STEEL, "płyta H – zawias przy przyczepie")
    zA = rect(L - 140, L + 30, -60, 40)
    add("A", zA, xo, xo + 6, C_STEEL, "płyta Z – zawias środkowy (A)")
    add("A", zA, xo - 46, xo - 40, C_STEEL, "płyta Z – zawias środkowy (A)")
    zB = rect(-30, 140, -60, 40)
    add("B", zB, xo + 6, xo + 12, C_STEEL, "płyta Z – zawias środkowy (B, na podkładce 6 mm)")
    add("B", zB, xo - 52, xo - 46, C_STEEL, "płyta Z – zawias środkowy (B, na podkładce 6 mm)")
    add("A", rect(g.S_PL["s0"], g.S_PL["s0"] + 80, -50, 100), g.X_WALK + 20, g.X_WALK + 28, C_STEEL, "płyta S – zaczep sprężyny")
    add("A", circle(-25.0, 75.0, 10.0), xo - 46, xo + 17, C_PIN, "sworzeń M20 – zawias przy przyczepie")
    add("A", circle(L, -35.0, 10.0), xo - 52, xo + 12, C_PIN, "sworzeń M20 – zawias środkowy")
    # przyczepa (poglądowo): a = y od tylnej ściany belki do tyłu, b = z od podłogi
    add("T", rect(-1400, 0, -18, 0), -650, 650, "#9a8f80", "podłoga przyczepy (przykład)", False)
    add("T", rect(-50, 0, -75, -18), -700, 700, "#7d7d7d", "tylna belka 50×75 (przykład)", False)
    add("T", rect(-1400, -40, 0, 350), 650, 670, "#9a8f80", "burta (poglądowo)", True, 0.35)
    add("T", circle(-900, -480 + 165, 165, 20), 700, 880, "#222222", "koło przyczepy (poglądowo)")
    for xa, nm in ((152.0, "wspornik K – zawias"), (369.0, "wspornik K – sprężyna")):
        add("T", rect(0, 100, -130, 0), xa, xa + 10, C_TRAILER, nm + " (kątownik 100×100×10)")
        add("T", rect(0, 10, -130, 0), xa, xa + 100, C_TRAILER, nm + " (kątownik 100×100×10)")
    return P


def local_tf(grp):
    """(x, a, b) [mm] -> współrzędne lokalne węzła glTF [mm] (Y w górę, -Z do tyłu)"""
    if grp == "T":
        return lambda x, a, b: (x, b, -a)
    if grp == "A":                       # węzeł A ma początek w osi zawiasu przy przyczepie
        return lambda x, s, z: (x, z - 75.0, -(s + 25.0))
    return lambda x, s, z: (x, z + 35.0, -s)   # węzeł B ma początek w osi zawiasu środkowego


def prism_faces(poly, x0, x1, tf):
    """ściany (wielokąty 3D) graniastosłupa, zorientowane na zewnątrz"""
    n = len(poly)
    lo = [np.array(tf(x0, a, b), float) for (a, b) in poly]
    hi = [np.array(tf(x1, a, b), float) for (a, b) in poly]
    faces = [lo[::-1], hi] + [[lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]] for i in range(n)]
    c = sum(lo + hi) / (2 * n)
    out = []
    for f in faces:
        nrm = np.cross(f[1] - f[0], f[2] - f[0])
        if np.dot(nrm, sum(f) / len(f) - c) < 0:
            f = f[::-1]
        out.append(f)
    return out


def cylinder_y(r, n=14):
    """walec o promieniu r, od y=0 do y=1 (długość nadaje skala) – ściany na zewnątrz"""
    ring = [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    lo = [np.array((a, 0.0, b)) for a, b in ring]
    hi = [np.array((a, 1.0, b)) for a, b in ring]
    faces = [lo, hi[::-1]] + [[lo[i], hi[i], hi[(i + 1) % n], lo[(i + 1) % n]] for i in range(n)]
    c = np.array((0.0, 0.5, 0.0))
    out = []
    for f in faces:
        nrm = np.cross(f[1] - f[0], f[2] - f[0])
        out.append(f if np.dot(nrm, sum(f) / len(f) - c) >= 0 else f[::-1])
    return out


# ------------------------------------------------------------------ RUCH
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
    if pm[1] + g.rot(ph, tipu, tipv)[1] <= zg:            # koniec B jeszcze leży na ziemi
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
    """(dolne, górne oczko) sprężyny w układzie glTF [mm], bez współrzędnej x"""
    lo = (g.PIN_Z + g.SPRING["eye_low"][1], -(g.PIN_Y + g.SPRING["eye_low"][0]))
    u, v = g.SPRING["eye_up_sz"][0] + 25.0, g.SPRING["eye_up_sz"][1] - 75.0
    y, z = g.rot(th, u, v)
    return lo, (g.PIN_Z + z, -(g.PIN_Y + y))


def rot_x(p, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return np.array((x, y * c - z * s, y * s + z * c))


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


def spring_segments(th):
    """4 odcinki (2 sprężyny × cylinder + tłoczysko): (początek, koniec, promień, kolor) [mm]"""
    lo, hi = springs(th)
    out = []
    for sg in (-1, 1):
        a = np.array((sg * SPRING_X, *lo))
        b = np.array((sg * SPRING_X, *hi))
        mid = a + 0.55 * (b - a)
        out += [(a, mid, 14.0, C_SPRING), (mid, b, 7.0, C_ROD)]
    return out


def world_faces(t):
    """wszystkie ściany w układzie świata [mm] (glTF: Y w górę) – do podglądu w Pythonie"""
    th, rel = pose(t)
    oA = np.array((0.0, g.PIN_Z, -g.PIN_Y))
    oB = np.array((0.0, V_MID, -U_MID))
    out = []
    for p in parts():
        for f in prism_faces(p["p"], p["x0"], p["x1"], local_tf(p["g"])):
            if p["g"] == "A":
                f = [oA + rot_x(v, th) for v in f]
            elif p["g"] == "B":
                f = [oA + rot_x(oB + rot_x(v, rel), th) for v in f]
            out.append((f, p["c"], p["o"]))
    for a, b, r, col in spring_segments(th):
        d = b - a
        q = _quat_from_y(d / np.linalg.norm(d))
        for f in cylinder_y(r):
            out.append(([a + _qrot(q, v * np.array((1.0, np.linalg.norm(d), 1.0))) for v in f], col, 1.0))
    return out


# ------------------------------------------------------------------ glTF 2.0 (GLB)
def write_gltf(path, frames=61, seconds=6.0):
    """węzły: przyczepa / sekcja_A (obrót wokół zawiasu) / sekcja_B (obrót wokół zawiasu środkowego) / sprężyny,
    animacja „skladanie”: 0 s rozłożony → 6 s do jazdy"""
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
                     pbrMetallicRoughness=dict(baseColorFactor=rgb + [op], metallicFactor=0.3, roughnessFactor=0.6))
            if op < 1:
                m["alphaMode"] = "BLEND"
            mats.append(m)
            mat_idx[(col, op)] = len(mats) - 1
        return mat_idx[(col, op)]

    def mesh(faces, col, op, name, scale):
        P, N = [], []
        for f in faces:
            f = [np.asarray(v, float) * scale for v in f]
            nrm = np.cross(f[1] - f[0], f[2] - f[0])
            nrm = nrm / (np.linalg.norm(nrm) or 1.0)
            for i in range(1, len(f) - 1):
                P += [f[0], f[i], f[i + 1]]
                N += [nrm] * 3
        prim = dict(attributes=dict(POSITION=accessor(np.array(P), "VEC3", 34962, True),
                                    NORMAL=accessor(np.array(N), "VEC3", 34962)), material=material(col, op))
        meshes.append(dict(name=name, primitives=[prim]))
        return len(meshes) - 1

    def node(name, **kw):
        nodes.append(dict(name=name, **kw))
        return len(nodes) - 1

    groups = {"T": [], "A": [], "B": []}
    for i, p in enumerate(parts()):
        m = mesh(prism_faces(p["p"], p["x0"], p["x1"], local_tf(p["g"])), p["c"], p["o"], p["n"], 1e-3)
        groups[p["g"]].append(node(f"{p['n']} #{i}", mesh=m, extras=dict(nazwa=p["n"])))
    nB = node("sekcja_B", children=groups["B"], translation=[0.0, V_MID / 1000, -U_MID / 1000], extras=dict(nazwa="sekcja B"))
    nA = node("sekcja_A", children=groups["A"] + [nB], translation=[0.0, g.PIN_Z / 1000, -g.PIN_Y / 1000],
              extras=dict(nazwa="sekcja A"))
    nT = node("przyczepa", children=groups["T"], extras=dict(nazwa="przyczepa (poglądowo)"))
    cyl = {(14.0, C_SPRING): mesh(cylinder_y(14.0), C_SPRING, 1.0, "sprężyna – cylinder", 1.0),
           (7.0, C_ROD): mesh(cylinder_y(7.0), C_ROD, 1.0, "sprężyna – tłoczysko", 1.0)}
    seg0 = spring_segments(pose(0)[0])
    spr = [node(f"sprezyna_{'LLPP'[k]}_{'ct'[k % 2]}", mesh=cyl[(r, col)], extras=dict(nazwa="sprężyna gazowa 460/200 mm, 1600 N"))
           for k, (_, _, r, col) in enumerate(seg0)]
    root = node("trap_v2", children=[nT, nA] + spr, extras=dict(nazwa="trap V2"))

    ts = np.linspace(0.0, 1.0, frames)
    qa, qb, trs = [], [], [([], [], []) for _ in spr]
    for t in ts:
        th, rel = pose(t)
        qa.append((math.sin(th / 2), 0.0, 0.0, math.cos(th / 2)))
        qb.append((math.sin(rel / 2), 0.0, 0.0, math.cos(rel / 2)))
        for k, (a, b, r, col) in enumerate(spring_segments(th)):
            d = (b - a) / 1000
            L = float(np.linalg.norm(d))
            trs[k][0].append(a / 1000)
            trs[k][1].append(_quat_from_y(d / L))
            trs[k][2].append((1e-3, L, 1e-3))
    t_acc = accessor(ts * seconds, "SCALAR", minmax=True)
    samplers, channels = [], []

    def anim(ni, path_, vals, typ):
        samplers.append(dict(input=t_acc, output=accessor(np.array(vals, float), typ), interpolation="LINEAR"))
        channels.append(dict(sampler=len(samplers) - 1, target=dict(node=ni, path=path_)))
    anim(nA, "rotation", qa, "VEC4")
    anim(nB, "rotation", qb, "VEC4")
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
              extras=dict(opis="Trap aluminiowy V2 2,5 × 1,19 m, bez spawania. Animacja: 0 s rozłożony → 6 s do jazdy.",
                          kat_najazdu_deg=round(g.ALPHA, 1), czas_animacji_s=seconds))
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


# ------------------------------------------------------------------ PODGLĄD W PYTHONIE (matplotlib)
def _rgba(c, o):
    return tuple(int(c[k:k + 2], 16) / 255 for k in (1, 3, 5)) + (o,)


def draw(ax, t, view=None):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    ax.cla()
    faces = world_faces(t)
    # glTF (X, Y w górę, Z) -> matplotlib (x w poprzek, y do tyłu za belkę, z w górę)
    polys = [[(v[0], -v[2], v[1]) for v in f] for (f, c, o) in faces]
    pc = Poly3DCollection(polys, facecolors=[_rgba(c, o) for (f, c, o) in faces],
                          edgecolors=(0.15, 0.15, 0.15, 0.25), linewidths=0.2)
    ax.add_collection3d(pc)
    ax.set_xlim(-1100, 1100)
    ax.set_ylim(-1300, 2700)
    ax.set_zlim(-480, 1500)
    ax.set_box_aspect((2200, 4000, 1980))
    ax.set_xlabel("x [mm]")
    ax.set_ylabel("za belką [mm]")
    ax.set_zlabel("od podłogi [mm]")
    if view:
        ax.view_init(*view)
    ax.set_title(f"Trap V2 – pozycja {t:.2f}  (0 = rozłożony, 1 = do jazdy)", fontsize=10)


def show_window():
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, Button
    fig = plt.figure("Trap V2 – podgląd 3D", figsize=(11, 8))
    ax = fig.add_axes([0.0, 0.1, 1.0, 0.9], projection="3d")
    draw(ax, 0.0, (24, 128))
    s = Slider(fig.add_axes([0.15, 0.04, 0.5, 0.03]), "pozycja", 0.0, 1.0, valinit=0.0)
    b0 = Button(fig.add_axes([0.70, 0.03, 0.12, 0.05]), "rozłożony")
    b1 = Button(fig.add_axes([0.84, 0.03, 0.12, 0.05]), "do jazdy")

    def upd(_):
        draw(ax, s.val, (ax.elev, ax.azim))
        fig.canvas.draw_idle()
    s.on_changed(upd)
    b0.on_clicked(lambda e: s.set_val(0.0))
    b1.on_clicked(lambda e: s.set_val(1.0))
    plt.show()


def save_png():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for t, name, view in ((0.0, "podglad_rozlozony.png", (24, 128)), (0.55, "podglad_skladanie.png", (16, 120)),
                          (1.0, "podglad_do_jazdy.png", (14, 140))):
        fig = plt.figure(figsize=(11, 8))
        ax = fig.add_axes([0, 0, 1, 1], projection="3d")
        draw(ax, t, view)
        fig.savefig(os.path.join(OUT, name), dpi=110)
        plt.close(fig)
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
        print(write_gltf(os.path.join(WWW, "trap_v2.glb")))
    elif "--png" in a:
        save_png()
    elif "--www" in a:
        serve()
    else:
        show_window()
