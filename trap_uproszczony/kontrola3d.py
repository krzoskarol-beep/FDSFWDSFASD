# -*- coding: utf-8 -*-
"""
Kontrole modelu 3D w całym ruchu trapu – liczone na geometrii, nie oceniane na oko.

  1. skok sprężyn gazowych: długość oczko–oczko w całym ruchu mieści się w 260–460 mm (z zapasem 2 mm),
  2. trap ↔ przyczepa: żadna część sekcji A/B nie wchodzi w belkę, podłogę, odbojnik, wysięgniki lamp,
     oparcia chodnika (guma oparcia może się ugiąć ≤ 2 mm) – w 41 położeniach od rozłożonego do pionu,
  3. widoczność świateł i tablicy przy złożonym trapie: promienie z każdej lampy w kątach z regulaminu EKG ONZ nr 48
     (poziomo 45° do środka / 80° na zewnątrz, pionowo ±15°; tablica ±30°, −5…+15°) nie trafiają w trap,
  4. szczeliny zgniatające (EN ISO 13854 / 13857): pokład ↔ odbojnik na belce w pionie ≤ 4 mm albo ≥ 25 mm.
"""
import math
import numpy as np

import generuj as g
import podglad3d as p3

TRAILER_KEYS = ("T:belka", "T:podloga", "T:odbojnik", "T:wl:", "T:oparcie", "T:epdm")


def spring_stroke(n=41):
    Ls = []
    for t in np.linspace(0, 1, n):
        lo, hi = p3.springs(p3.pose(t)[0])
        Ls.append(math.hypot(hi[0] - lo[0], hi[1] - lo[1]))
    lo_lim = g.SPRING["L_ext"] - g.SPRING["stroke"] + 2
    hi_lim = g.SPRING["L_ext"] - 2
    return dict(min=min(Ls), max=max(Ls), ok=min(Ls) >= lo_lim and max(Ls) <= hi_lim, lim=(lo_lim, hi_lim))


def _boxes(M, t, pred):
    out = {}
    for (T, _c, _o, kind, key) in p3.world_tris(M, t):
        if pred(key, kind):
            v = T.reshape(-1, 3)
            out[key] = (v.min(0), v.max(0))
    return out


def trailer_clearance(M, n=41):
    """najgłębsze wejście części ruchomych w prostopadłościany części przyczepy (mm); <0 = luz"""
    tb = _boxes(M, 0.0, lambda k, kd: k.startswith(TRAILER_KEYS))
    worst = []
    for t in np.linspace(0, 1, n):
        for (T, _c, _o, kind, key) in p3.world_tris(M, t):
            if key[:2] not in ("A:", "B:") or kind not in ("profil", "płyta", "siatka"):
                continue
            v = T.reshape(-1, 3)
            for tk, (lo, hi) in tb.items():
                inside = np.all((v > lo + 0.01) & (v < hi - 0.01), axis=1)
                if inside.any():
                    pen = np.minimum(v[inside] - lo, hi - v[inside]).min(axis=1).max()
                    allow = 2.0 if ("epdm" in tk or "oparcie" in tk) else 0.0
                    if pen > allow:
                        worst.append((round(float(t), 3), key, tk, round(float(pen), 1)))
    return worst


def _rays_hit(orig, dirs, tris, length=5000.0):
    """Möller–Trumbore: czy któryś promień z orig w kierunkach dirs trafia w trójkąty (n×3×3) w odległości < length"""
    v0, e1, e2 = tris[:, 0], tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    hits = []
    for d in dirs:
        h = np.cross(d, e2)
        a = np.einsum("ij,ij->i", e1, h)
        ok = np.abs(a) > 1e-9
        f = np.where(ok, 1.0 / np.where(ok, a, 1.0), 0.0)
        sv = orig - v0
        u = f * np.einsum("ij,ij->i", sv, h)
        q = np.cross(sv, e1)
        vv = f * (q @ d)
        tt = f * np.einsum("ij,ij->i", e2, q)
        hit = ok & (u >= 0) & (u <= 1) & (vv >= 0) & (u + vv <= 1) & (tt > 1.0) & (tt < length)
        hits.append(bool(hit.any()))
    return hits


def light_visibility(M, Ly):
    """trap złożony (t = 1): czy z lamp i tablicy widać wymagane kąty"""
    tris = np.concatenate([T for (T, _c, _o, kind, key) in p3.world_tris(M, 1.0)
                           if key[:2] in ("A:", "B:", "L:") or key.startswith("spr")]).reshape(-1, 3, 3)
    out = []
    for lh in Ly.get("light_holders", []):
        d = lh["depth"]
        for (nm, x0, x1, y0, y1, col, th, info) in lh["items"]:
            if nm not in ("lampa", "tablica"):
                continue
            xc, yc = (x0 + x1) / 2, (y0 + y1) / 2 - g.H_FLOOR
            orig = np.array((xc, yc, -(d + 3 + th + 1)))                   # przed powierzchnią świetlną
            sgn_out = -1.0 if xc < 0 else 1.0
            hs = range(-45, 81, 5) if nm == "lampa" else range(-30, 31, 5)
            vs = (-15, -5, 0, 5, 15) if nm == "lampa" else (-5, 0, 5, 15)
            dirs, lab = [], []
            for hdeg in hs:                                               # + na zewnątrz pojazdu, − do środka
                for vdeg in vs:
                    h, v = math.radians(hdeg), math.radians(vdeg)
                    dirs.append(np.array((sgn_out * math.sin(h) * math.cos(v), math.sin(v), -math.cos(h) * math.cos(v))))
                    lab.append((hdeg, vdeg))
            hit = _rays_hit(orig, dirs, tris)
            blocked = [l for l, hb in zip(lab, hit) if hb]
            out.append(dict(element=f"{lh['key']}:{nm}", promienie=len(dirs), zasloniete=blocked))
    return out


def pinch_gaps(M, Ly, n=21):
    """najmniejsza odległość pokładu A od odbojnika na belce (punkt–prostopadłościan) w końcówce ruchu i w pionie"""
    SF = Ly.get("safety")
    if not SF:
        return None
    boxes = [(np.array((xa, -20.0, -SF["bumper_t"])), np.array((xb, 0.0, 0.0))) for (xa, xb) in SF["bumper"]]
    gap = 1e9
    for t in np.linspace(0.8, 1.0, n):
        for (T, _c, _o, kind, key) in p3.world_tris(M, t):
            if key[:2] != "A:" or kind not in ("profil", "płyta", "siatka", "śruba") or ":H:" in key or "pinTr" in key:
                continue
            v = T.reshape(-1, 3)
            for lo, hi in boxes:
                d = np.linalg.norm(np.maximum(np.maximum(lo - v, v - hi), 0.0), axis=1)
                gap = min(gap, float(d.min()))
    return dict(szczelina=gap, ok=(gap <= 4.0 or gap >= 25.0) and gap > 0)


def run(M, Ly):
    return dict(sprezyny=spring_stroke(), przyczepa=trailer_clearance(M), swiatla=light_visibility(M, Ly), szczeliny=pinch_gaps(M, Ly))
