#!/usr/bin/env python3
"""Generuje przyczepę v6 z plików v5 (STEP + GLB), wprowadzając poprawki opisane w RAPORT.md.

Użycie:
    python3 popraw_v6.py <v5_zlozenie.step> <v5.glb> <katalog_wyjściowy>

Układ współrzędnych (taki jak w v5): X wzdłuż przyczepy (0 ~ czoło zaczepu, +X do tyłu),
Y w górę (0 = podłoże), Z w poprzek. STEP w mm, GLB w metrach.
"""
import json
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import occ  # noqa: E402
from glbio import load as load_glb  # noqa: E402

# --------------------------------------------------------------------------------------
# Parametry poprawek
# --------------------------------------------------------------------------------------
DX_OS = -150.0          # przesunięcie osi (półosie, koła, błotniki, poprzeczka R4) do przodu [mm]
DY_BLOTNIK = 60.0       # podniesienie błotników -> luz nad oponą ~80 mm zamiast ~20-36 mm
D1_KONIEC = 2250.0 + DX_OS   # nowy koniec dyszla D1 = przednia ściana przesuniętej poprzeczki R4
ODBLASK_X0 = 1827.0     # nowe położenie odblasków bocznych (wolne miejsce między śrubami)
PIN = (3345.0, 318.0)   # oś sworznia zawiasu rampy (KUPNE_pret)
LUZ_ZAWIAS = 2.0        # luz montażowy przy wycięciu przekładki T4P [mm]

COL = {  # kolory STEP (RGB 0..1) zgodne z materiałami GLB
    'rama_czarna': (0.05, 0.05, 0.055), 'ocynk': (0.78, 0.79, 0.80), 'sklejka': (0.11, 0.11, 0.12),
}


def log(*a):
    print(*a, flush=True)


def main(step_in, glb_in, out):
    os.makedirs(out, exist_ok=True)
    changes = []

    # ---------------------------------------------------------------- wczytanie
    sols = occ.read_solids(step_in)
    gj, gparts = load_glb(glb_in)
    G = {}
    for p in gparts:
        G[p['name']] = dict(V=p['V'] * 1000.0, F=p['F'].astype(np.int64), mat=p['mat'])
    gmats = {m['name']: m for m in gj['materials']}

    # nazwy brył STEP z dopasowania prostopadłościanów do GLB
    gb = {n: np.r_[d['V'].min(0), d['V'].max(0)] for n, d in G.items()
          if not n.startswith(('KUPNE', 'SRUBY', 'MOTOCYKL', 'TRAP_tr', 'K-UCHO', 'K-POL', 'K-ZACZ', 'K-KOLKO'))
          and 'SRUBY' not in n and 'SIATKA' not in n}
    S = {}
    for s in sols:
        b = occ.bbox(s)
        best = min(gb, key=lambda n: np.abs(gb[n] - b).max())
        err = np.abs(gb[best] - b).max()
        assert err < 2.5 and best not in S, (best, err)
        S[best] = s
    log(f"STEP: {len(S)} brył nazwanych z GLB")

    # kinematyka rampy z v5: transformacje segmentów załadunek -> transport (Kabsch)
    def kabsch(A, B):
        ca, cb = A.mean(0), B.mean(0)
        U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
        R = Vt.T @ D @ U.T
        return R, cb - R @ ca
    TF = {1: kabsch(G['TRAP_zal_T1-Z-1#11']['V'], G['TRAP_tr_T1-Z-1#11']['V']),
          2: kabsch(G['TRAP_zal_T1-Z-2#21']['V'], G['TRAP_tr_T1-Z-2#21']['V'])}
    Rrel = TF[1][0].T @ TF[2][0]
    trel = TF[1][0].T @ (TF[2][1] - TF[1][1])
    HINGE_MID = tuple(np.linalg.solve(np.eye(2) - Rrel[:2, :2], trel[:2]))
    pin = np.linalg.solve(np.eye(2) - TF[1][0][:2, :2], TF[1][1][:2])
    log(f"zawias główny {pin.round(2)} (KUPNE_pret {PIN}), zawias środkowy {np.round(HINGE_MID, 2)}, "
        f"obrót segm.1 {np.degrees(np.arctan2(TF[1][0][1, 0], TF[1][0][0, 0])):.2f} st.")

    seg1 = [n for n in G if n.startswith('TRAP_zal') and n.split('#')[-1].startswith('1')]
    seg2 = [n for n in G if n.startswith('TRAP_zal') and n.split('#')[-1].startswith('2')]

    # -------------------------------------------------- 1. przesunięcie osi do przodu
    os_step = ['R4#1', 'W6#1', 'W6#2', 'W6#3', 'W6#4'] + [f'B1#{i}' for i in range(1, 5)] + [f'B2#{i}' for i in range(1, 5)]
    for n in os_step:
        S[n] = occ.translate(S[n], DX_OS)
    os_glb_dx = os_step + ['K-POL-P#1', 'K-POL-L#1', 'KUPNE_opony', 'KUPNE_felgi', 'KUPNE_polosie',
                           'KUPNE_obrysowe', 'SRUBY_W6aP', 'SRUBY_W6bP', 'SRUBY_W6aL', 'SRUBY_W6bL',
                           'SRUBY_W12-przódP', 'SRUBY_W12-tyłP', 'SRUBY_W12-przódL', 'SRUBY_W12-tyłL']
    for n in os_glb_dx:
        G[n]['V'] = G[n]['V'] + [DX_OS, 0, 0]
    changes.append(f"Oś (półosie, koła, R4, wsporniki W6, B1/B2, obrysówki) przesunięta o {DX_OS:+.0f} mm w X "
                   f"(środek koła 2400 -> {2400 + DX_OS:.0f} mm).")

    # poprzeczka R5-5 koliduje z przesuniętym W6 -> usunięta razem z narożnikami i śrubami
    for n in ['R5-5_9#1', 'K1#9', 'K1#10']:
        S.pop(n)
        G.pop(n)
    for n in ['SRUBY_W5-5P', 'SRUBY_W5-5L']:
        G.pop(n)
    changes.append("Usunięta poprzeczka R5-5 (X 2008-2048) z narożnikami K1#9/K1#10 i śrubami W5-5 - "
                   "w jej miejscu stoi teraz poprzeczka osi R4.")

    # wkręty podłogi W14: usuń te w R5-5, przesuń te w R4
    m = trimesh.Trimesh(G['SRUBY_W14']['V'], G['SRUBY_W14']['F'], process=False)
    keep = []
    for c in m.split(only_watertight=False):
        cx = c.bounds[:, 0].mean()
        if 2000 <= cx <= 2056:
            continue
        if 2245 <= cx <= 2305:
            c.apply_translation([DX_OS, 0, 0])
        keep.append(c)
    w14 = trimesh.util.concatenate(keep)
    G['SRUBY_W14'].update(V=np.asarray(w14.vertices), F=np.asarray(w14.faces))

    # -------------------------------------------------- 2. dyszel D1 przedłużony do R4
    d1b = occ.bbox(S['D1#1'])
    ext = occ.cut(occ.box(d1b[3] - 5, 212, -50, D1_KONIEC, 252, 50), occ.box(d1b[3] - 6, 216, -46, D1_KONIEC + 1, 248, 46))
    S['D1#1'] = occ.fuse(S['D1#1'], ext)
    k2dx = (D1_KONIEC - 50.0) - occ.bbox(S['K2-P#4'])[0]
    S['K2-P#5'] = occ.translate(S['K2-P#4'], k2dx)
    S['K2-L#5'] = occ.translate(S['K2-L#4'], k2dx)
    for n in ['K2-P#5', 'K2-L#5']:
        G[n] = dict(G[n.replace('#5', '#4')])
        G[n]['V'] = G[n]['V'] + [k2dx, 0, 0]
    changes.append(f"Dyszel D1 100x40x4 przedłużony z X={d1b[3]:.0f} do X={D1_KONIEC:.0f} (dosunięty do poprzeczki osi R4), "
                   "dodane kątowniki K2-P#5/K2-L#5 łączące D1 z R4 - siła z zaczepu idzie prosto do belki osi, "
                   "a nie tylko przez cztery cienkie poprzeczki 80x40x2.")

    # -------------------------------------------------- 3. błotniki wyżej, wspornik B1 wyższy
    for i in range(1, 5):
        b = occ.bbox(S[f'B1#{i}'])
        S[f'B1#{i}'] = occ.fuse(S[f'B1#{i}'], occ.box(b[0], b[4] - 5, b[2], b[3], b[4] + DY_BLOTNIK, b[5]))
    G['KUPNE_blotniki']['V'] = G['KUPNE_blotniki']['V'] + [DX_OS, DY_BLOTNIK, 0]
    m = trimesh.Trimesh(G['KUPNE_mocowania']['V'], G['KUPNE_mocowania']['F'], process=False)
    parts = []
    for c in m.split(only_watertight=False):
        if c.bounds[:, 0].mean() < 3000:
            c.apply_translation([DX_OS, DY_BLOTNIK, 0])
        parts.append(c)
    mm = trimesh.util.concatenate(parts)
    G['KUPNE_mocowania'].update(V=np.asarray(mm.vertices), F=np.asarray(mm.faces))
    changes.append(f"Błotniki podniesione o {DY_BLOTNIK:.0f} mm (wsporniki B1 wydłużone w górę o {DY_BLOTNIK:.0f} mm) - "
                   "luz nad oponą ok. 80 mm zamiast 21-36 mm, miejsce na ugięcie półosi gumowych.")

    # -------------------------------------------------- 4. odblaski boczne poza łbami śrub
    dxo = ODBLASK_X0 - G['KUPNE_odblaski']['V'][:, 0].min()
    G['KUPNE_odblaski']['V'] = G['KUPNE_odblaski']['V'] + [dxo, 0, 0]
    changes.append(f"Odblaski boczne (pomarańczowe) przesunięte do X={ODBLASK_X0:.0f}-{ODBLASK_X0 + 70:.0f} mm - w v5 "
                   "nachodziły na łby śrub W5-5.")

    # -------------------------------------------------- 5. rampa: kinematyka składania i podnoszenia
    a1 = float(np.degrees(np.arctan2(TF[1][0][1, 0], TF[1][0][0, 0])))   # kąt podnoszenia (~101.7 st.)

    def fold_clash(movers, fixed, step=3.0):
        """Segment 2 składany pod segment 1: obrót 0..-180 st. wokół zawiasu środkowego."""
        hits = []
        fb = {f: occ.bbox(S[f]) for f in fixed}
        for ang in np.arange(-step, -180.0 - 1e-6, -step):
            for mv in movers:
                m = occ.rotate_z(S[mv], *HINGE_MID, ang)
                bm = occ.bbox(m)
                for f in fixed:
                    if all(bm[i] <= fb[f][i + 3] and fb[f][i] <= bm[i + 3] for i in range(3)):
                        if occ.common_volume(m, S[f]) > 1.0:
                            hits.append((float(ang), mv, f))
        return hits

    # 5a. szczeble przy zawiasie środkowym przechodzą przez płaszczyzny blach zawiasu (Z 100..112) -> przy składaniu
    #     zahaczają o T3/T4. Szczebel dzielimy na 3 odcinki (szczelina w strefie blach), śruby i otwory bez zmian.
    split = []
    for rung in ('TRAP_zal_T2#13', 'TRAP_zal_T2#21'):
        v0 = occ.volume(S[rung])[0]
        for z0, z1 in ((100.0 - LUZ_ZAWIAS, 112.0 + LUZ_ZAWIAS), (-112.0 - LUZ_ZAWIAS, -100.0 + LUZ_ZAWIAS)):
            S[rung] = occ.cut(S[rung], occ.box(3000, -100, z0, 5200, 500, z1))
        split.append(rung)
        changes.append(f"{rung}: szczebel przy zawiasie środkowym podzielony na 3 odcinki (szczeliny Z +/-{100 - LUZ_ZAWIAS:.0f}"
                       f"..{112 + LUZ_ZAWIAS:.0f}, usunięto {v0 - occ.volume(S[rung])[0]:.0f} mm3) - w v5 przy składaniu "
                       "rampy zahaczał o blachy zawiasu T3/T4, a w położeniu transportowym przenikał się z nimi.")
    hits = fold_clash([n for n in seg2 if n in S and occ.bbox(S[n])[0] < 4450],
                      [n for n in seg1 if n in S and occ.bbox(S[n])[3] > 3950])
    assert not [h for h in hits if 'T4P' not in h[1]], hits[:5]

    # 5b. wycięcia w blachach tylko tam, gdzie szczebel nadal przenika blachę
    notch = []
    for plate in ['TRAP_zal_T6#11', 'TRAP_zal_T6#12', 'TRAP_zal_T3#11', 'TRAP_zal_T3#12', 'TRAP_zal_T4#21', 'TRAP_zal_T4#22']:
        for rung in [n for n in S if '_T2#' in n]:
            v = occ.common_volume(S[plate], S[rung])
            if v > 1.0:
                S[plate] = occ.cut(S[plate], S[rung])
                notch.append(plate)
                changes.append(f"{plate}: wycięcie pod szczebel {rung} (było przenikanie {v:.0f} mm3).")

    # 5c. przekładka T4P leży w płaszczyźnie blachy zawiasu T3 -> wytnij obwiednię ruchu T3 (składanie 180 st.)
    for t4p, t3 in [('TRAP_zal_T4P#21', 'TRAP_zal_T3#11'), ('TRAP_zal_T4P#22', 'TRAP_zal_T3#12')]:
        tool = S[t3]
        for dx, dy in [(LUZ_ZAWIAS, 0), (-LUZ_ZAWIAS, 0), (0, LUZ_ZAWIAS), (0, -LUZ_ZAWIAS)]:
            tool = occ.fuse(tool, occ.translate(S[t3], dx, dy))
        v0 = occ.volume(S[t4p])[0]
        # T3 obraca się względem segmentu 2 o 0..+180 st. wokół zawiasu środkowego
        for ang in np.arange(0.0, 180.1, 3.0):
            S[t4p] = occ.cut(S[t4p], occ.rotate_z(tool, *HINGE_MID, ang))
        changes.append(f"{t4p}: przekładka leżała w płaszczyźnie blachy {t3} - wycięta strefa ruchu T3 przy składaniu "
                       f"(usunięto {v0 - occ.volume(S[t4p])[0]:.0f} mm3, luz {LUZ_ZAWIAS:.0f} mm).")

    # 5d. płyta najazdowa T7 wchodzi w podłogę P1 i poprzeczkę R3 przy podnoszeniu rampy -> przycięcie po obwiedni
    c = LUZ_ZAWIAS + 1.0
    frame_tool = occ.fuse(occ.box(3100, 332 - c, -505, 3300 + c, 350 + c, 505),
                          occ.box(3250 - c, 212 - c, -450, 3300 + c, 332 + c, 450))
    v0 = occ.volume(S['TRAP_zal_T7#11'])[0]
    for ang in list(np.arange(0.0, a1, 2.0)) + [a1]:
        S['TRAP_zal_T7#11'] = occ.cut(S['TRAP_zal_T7#11'], occ.rotate_z(frame_tool, *PIN, -ang))
    b7 = occ.bbox(S['TRAP_zal_T7#11'])
    changes.append(f"TRAP_zal_T7#11 (płyta najazdowa): przycięta po obwiedni ruchu - w v5 przy podnoszeniu rampy "
                   f"(18-96 st.) wchodziła w podłogę P1 i poprzeczkę R3, czyli rampy nie dało się złożyć. "
                   f"Usunięto {v0 - occ.volume(S['TRAP_zal_T7#11'])[0]:.0f} mm3, przód płyty teraz X={b7[0]:.0f}.")

    # tuleje dystansowe na sworzniu zawiasu: między T6 (Z 100..106) a T5 (Z 149..229)
    S['T8-P'] = occ.tube_z(*PIN, 106.0, 149.0, 15.0, 10.5)
    S['T8-L'] = occ.tube_z(*PIN, -149.0, -106.0, 15.0, 10.5)
    changes.append("Dodane tuleje dystansowe T8-P/T8-L (fi30/fi21 x 43) na sworzniu zawiasu rampy - w v5 rampa "
                   "mogła się przesuwać na sworzniu o 43 mm na boki.")

    # -------------------------------------------------- 6. STEP v6 (nazwany, z kolorami)
    mat_of = {n: (G[n]['mat'] if n in G else 'rama_czarna') for n in S}
    mat_of.update({'T8-P': 'ocynk', 'T8-L': 'ocynk'})
    order = sorted(S, key=lambda n: (n.startswith('TRAP'), n))
    step_parts = [(n.replace('TRAP_zal_', 'RAMPA_'), S[n], COL.get(mat_of[n], COL['rama_czarna'])) for n in order]
    occ.write_step_named(step_parts, os.path.join(out, 'przyczepa_v6_zlozenie.step'))
    log("zapisano STEP")

    # -------------------------------------------------- 7. siatki zmienionych brył + rampa w transporcie
    def mesh_of(n):
        V, F = occ.tessellate(S[n])
        return V, F
    modified = (['D1#1'] + [f'B1#{i}' for i in range(1, 5)] + notch + ['TRAP_zal_T4P#21', 'TRAP_zal_T4P#22', 'TRAP_zal_T7#11']
                + split)
    raw_modified = ['TRAP_zal_SIATKA#1']
    for n in modified:
        V, F = mesh_of(n)
        G[n].update(V=V, F=F)
    # siatka segmentu 1 nachodziła na płytę T7 -> wycięcie (operacja na siatkach, siatki nie ma w STEP)
    sm = trimesh.Trimesh(G['TRAP_zal_SIATKA#1']['V'], G['TRAP_zal_SIATKA#1']['F'])
    t7 = trimesh.Trimesh(G['TRAP_zal_T7#11']['V'], G['TRAP_zal_T7#11']['F'])
    v0 = sm.volume
    sm = trimesh.boolean.difference([sm, t7], engine='manifold')
    G['TRAP_zal_SIATKA#1'].update(V=np.asarray(sm.vertices), F=np.asarray(sm.faces))
    changes.append(f"TRAP_zal_SIATKA#1: siatka przycięta pod płytą T7 (przenikanie {v0 - sm.volume:.0f} mm3 w v5).")
    for n in ['T8-P', 'T8-L']:
        V, F = mesh_of(n)
        G[n] = dict(V=V, F=F, mat='ocynk')

    def seg_tf(V, seg):
        R, t = TF[seg]
        return V @ R.T + t
    for n in seg1 + seg2:
        t = n.replace('_zal_', '_tr_')
        Vt = seg_tf(G[n]['V'], 1 if n in seg1 else 2)
        if n not in modified and n not in raw_modified and t in G:
            err = np.abs(Vt - G[t]['V']).max()
            assert err < 0.05, (n, err)   # kontrola: kinematyka zgodna z v5
        G[t] = dict(V=Vt, F=G[n]['F'], mat=G[n]['mat'])

    # -------------------------------------------------- 8. eksport GLB/STL
    def material(name):
        m = gmats.get(name, gmats['rama_czarna'])
        pbr = m.get('pbrMetallicRoughness', {})
        return trimesh.visual.material.PBRMaterial(
            name=name, baseColorFactor=[int(round(255 * c)) for c in pbr.get('baseColorFactor', [1, 1, 1, 1])],
            metallicFactor=pbr.get('metallicFactor', 0.5), roughnessFactor=pbr.get('roughnessFactor', 0.5),
            alphaMode=m.get('alphaMode', 'OPAQUE'), doubleSided=m.get('doubleSided', False))

    def scene(filter_fn):
        sc = trimesh.Scene()
        for n, d in G.items():
            if not filter_fn(n):
                continue
            tm = trimesh.Trimesh(d['V'] / 1000.0, d['F'], process=False)
            tm.visual = trimesh.visual.TextureVisuals(material=material(d['mat']))
            sc.add_geometry(tm, node_name=n, geom_name=n)
        return sc
    transport = lambda n: not n.startswith('TRAP_zal')
    zaladunek = lambda n: not n.startswith('TRAP_tr') and n != 'MOTOCYKL'
    scene(transport).export(os.path.join(out, 'przyczepa_v6_transport.glb'))
    scene(zaladunek).export(os.path.join(out, 'przyczepa_v6_zaladunek.glb'))
    stl = trimesh.util.concatenate([trimesh.Trimesh(d['V'], d['F'], process=False)
                                    for n, d in G.items() if transport(n) and n != 'MOTOCYKL'])
    stl.export(os.path.join(out, 'przyczepa_v6.stl'))
    log("zapisano GLB/STL")

    with open(os.path.join(out, 'zmiany_v6.json'), 'w', encoding='utf-8') as f:
        json.dump(changes, f, ensure_ascii=False, indent=1)
    for c in changes:
        log(" -", c)


if __name__ == '__main__':
    main(*sys.argv[1:4])
