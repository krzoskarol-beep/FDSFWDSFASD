#!/usr/bin/env python3
"""Analiza przyczepy (v5 lub v6): kolizje statyczne STEP, kolizje w ruchu rampy, luzy kół,
masa / środek ciężkości / nacisk na hak.  Wynik: JSON + wydruk.

    python3 analiza.py v5 <v5.step> <v5.glb> wynik.json
    python3 analiza.py v6 <v6.step> <v6_transport.glb> wynik.json
"""
import json
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import occ  # noqa: E402
from glbio import load as load_glb  # noqa: E402

RHO = {'rama_czarna': 7.85e-6, 'ocynk': 7.85e-6, 'siatka': 7.85e-6, 'polos': 7.85e-6, 'sklejka': 0.68e-6}  # kg/mm3
# masy części kupnych [kg] (szacunek katalogowy - w modelu są uproszczone bryły)
KUPNE = {'KUPNE_opony': 27.0, 'KUPNE_felgi': 0.0, 'KUPNE_polosie': 22.0, 'KUPNE_blotniki': 5.0,
         'KUPNE_mocowania': 1.0, 'KUPNE_obrysowe': 0.4, 'KUPNE_odblaski': 0.1, 'KUPNE_lampy': 2.4,
         'KUPNE_belka': 0.6, 'KUPNE_zaczep': 3.5, 'KUPNE_kolko': 5.5, 'KUPNE_ucha': 0.0, 'KUPNE_pret': 0.85,
         'MOTOCYKL': 0.0}
KULA_X = -75.0   # środek kuli zaczepu (z geometrii gniazda kuli KUPNE_zaczep)
MOTO = [(150, 2060), (200, 1990), (250, 1960), (300, 1890)]   # (masa kg, X środka ciężkości motocykla mm)


def meshes_from_glb(path):
    _, parts = load_glb(path)
    return {p['name']: (p['V'] * 1000.0, p['F'], p['mat']) for p in parts}


def name_step(sols, M):
    """Nazwy brył STEP (v5 nie ma nazw) przez dopasowanie prostopadłościanów do GLB."""
    cand = {n: np.r_[V.min(0), V.max(0)] for n, (V, F, m) in M.items()
            if not n.startswith(('KUPNE', 'SRUBY', 'MOTOCYKL', 'TRAP_tr', 'K-UCHO', 'K-POL', 'K-ZACZ', 'K-KOLKO'))
            and 'SRUBY' not in n and 'SIATKA' not in n}
    out = {}
    for s in sols:
        b = occ.bbox(s)
        n = min(cand, key=lambda k: np.abs(cand[k] - b).max())
        out[n.replace('TRAP_zal_', 'RAMPA_')] = s
    return out


def overlap(a, b, g=0.5):
    return all(a[i] - g <= b[i + 3] and b[i] - g <= a[i + 3] for i in range(3))


def static_clashes(S):
    names = list(S)
    bb = {n: occ.bbox(S[n]) for n in names}
    res = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if overlap(bb[a], bb[b]):
                v = occ.common_volume(S[a], S[b])
                if v > 1.0:
                    res.append((a, b, round(v, 1)))
    return res


def ramp_kinematics(M):
    def kabsch(A, B):
        ca, cb = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        R = Vt.T @ D @ U.T
        return R, cb - R @ ca
    R1, t1 = kabsch(M['TRAP_zal_T1-Z-1#11'][0], M['TRAP_tr_T1-Z-1#11'][0])
    R2, t2 = kabsch(M['TRAP_zal_T1-Z-2#21'][0], M['TRAP_tr_T1-Z-2#21'][0])
    pin = np.linalg.solve(np.eye(2) - R1[:2, :2], t1[:2])
    Rr, tr = R1.T @ R2, R1.T @ (t2 - t1)
    mid = np.linalg.solve(np.eye(2) - Rr[:2, :2], tr[:2])
    a1 = np.degrees(np.arctan2(R1[1, 0], R1[0, 0]))
    return pin, mid, a1


def motion_clashes(S, pin, mid, a1, step=6.0):
    """Składanie segmentu 2 pod segment 1 (0..-180 st.), potem podnoszenie całości na sworzniu (0..a1)."""
    seg1 = [n for n in S if n.startswith('RAMPA_') and n.split('#')[-1].startswith('1')]
    seg2 = [n for n in S if n.startswith('RAMPA_') and n.split('#')[-1].startswith('2')]
    frame = [n for n in S if not n.startswith('RAMPA_')]
    out = {'skladanie': [], 'podnoszenie': []}
    bb1 = {n: occ.bbox(S[n]) for n in seg1}
    for ang in np.arange(-step, -180.0 - 1e-6, -step):
        for n2 in seg2:
            m = occ.rotate_z(S[n2], *mid, ang)
            b = occ.bbox(m)
            for n1 in seg1:
                if overlap(b, bb1[n1]):
                    v = occ.common_volume(m, S[n1])
                    if v > 1.0:
                        out['skladanie'].append((round(float(ang)), n2, n1, round(v, 1)))
    moving = {n: S[n] for n in seg1}
    moving.update({n: occ.rotate_z(S[n], *mid, -180.0) for n in seg2})
    bbf = {n: occ.bbox(S[n]) for n in frame}
    for ang in list(np.arange(step, a1, step)) + [a1]:
        for n, s in moving.items():
            m = occ.rotate_z(s, *pin, ang)
            b = occ.bbox(m)
            for f in frame:
                if overlap(b, bbf[f]):
                    v = occ.common_volume(m, S[f])
                    if v > 1.0:
                        out['podnoszenie'].append((round(float(ang), 1), n, f, round(v, 1)))
    return out


def min_dist(M, a, b):
    cm = trimesh.collision.CollisionManager()
    cm.add_object('a', trimesh.Trimesh(*M[a][:2], process=False))
    return float(cm.min_distance_single(trimesh.Trimesh(*M[b][:2], process=False)))


def fender_gap(M):
    f = trimesh.Trimesh(*M['KUPNE_blotniki'][:2], process=False)
    t = trimesh.Trimesh(*M['KUPNE_opony'][:2], process=False)
    top = t.bounds[1, 1]
    xc = t.bounds[:, 0].mean()
    o = np.array([[xc + dx, top + 0.5, 733.0] for dx in (-100, 0, 100)])
    loc, ir, _ = f.ray.intersects_location(o, np.tile([0, 1, 0], (len(o), 1)))
    return float(min(loc[ir == i][:, 1].min() for i in range(len(o))) - top)


def mass_budget(M, S_step_names=None):
    tot_m, tot_mc, groups = 0.0, np.zeros(3), {}
    for n, (V, F, mat) in M.items():
        if n.startswith('TRAP_zal'):
            continue  # rampa liczona raz (położenie transportowe)
        if n in KUPNE:
            m = KUPNE[n]
            c = V.mean(0)
        else:
            tm = trimesh.Trimesh(V, F, process=False)
            vol = abs(tm.volume)
            m = vol * RHO[mat]
            c = tm.center_mass if tm.volume != 0 else V.mean(0)
        g = ('rampa' if n.startswith('TRAP') else 'sruby' if ('SRUBY' in n or n.startswith('K-UCHO'))
             else 'kupne' if n.startswith('KUPNE') else 'sklejka' if n.startswith('P1') else 'rama')
        groups[g] = groups.get(g, 0.0) + m
        tot_m += m
        tot_mc += m * np.asarray(c)
    return tot_m, tot_mc / tot_m, groups


def main(tag, step, glb, out_json):
    M = meshes_from_glb(glb)
    if tag == 'v6':
        zal = glb.replace('_transport.glb', '_zaladunek.glb')
        M.update({k: v for k, v in meshes_from_glb(zal).items() if k.startswith('TRAP_zal')})
        S = occ.read_named(step)
    else:
        S = name_step(occ.read_solids(step), M)
    R = {'wersja': tag}
    R['kolizje_statyczne'] = static_clashes(S)
    pin, mid, a1 = ramp_kinematics(M)
    R['kinematyka'] = dict(sworzen=pin.round(2).tolist(), zawias_srodkowy=mid.round(2).tolist(), kat_podnoszenia=round(a1, 2))
    R['kolizje_ruch'] = motion_clashes(S, pin, mid, a1)
    xa = M['KUPNE_opony'][0][:, 0].mean()
    R['os_x'] = round(float(xa), 1)
    R['luz_opona_blotnik_pion'] = round(fender_gap(M), 1)
    R['luz_opona_blotnik_min'] = round(min_dist(M, 'KUPNE_opony', 'KUPNE_blotniki'), 1)
    R['luz_opona_wspornik_B1'] = round(min(min_dist(M, 'KUPNE_opony', f'B1#{i}') for i in (1, 2)), 1)
    R['odblask_sruby'] = round(min(min_dist(M, 'KUPNE_odblaski', n) for n in M if n.startswith('SRUBY_W5')), 1)
    m, c, groups = mass_budget(M)
    R['masa_wlasna'] = round(m, 1)
    R['masa_grupy'] = {k: round(v, 1) for k, v in groups.items()}
    R['srodek_ciezkosci'] = c.round(0).tolist()
    L = xa - KULA_X
    t0 = m * (xa - c[0]) / L
    R['nacisk_pusta'] = round(float(t0), 1)
    R['nacisk_z_motocyklem'] = []
    for mb, xm in MOTO:
        t = t0 + mb * (xa - xm) / L
        R['nacisk_z_motocyklem'].append(dict(moto_kg=mb, moto_cg_x=xm, dmc=round(m + mb), hak_kg=round(float(t), 1),
                                             procent=round(float(100 * t / (m + mb)), 1), os_kg=round(float(m + mb - t))))
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(R, f, ensure_ascii=False, indent=1)
    print(json.dumps(R, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:5])
