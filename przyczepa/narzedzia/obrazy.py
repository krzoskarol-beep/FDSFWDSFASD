#!/usr/bin/env python3
"""Generuje obrazy do raportu:  python3 obrazy.py <v5.glb> <katalog_v6> <katalog_obrazów>"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glbio import load  # noqa: E402
from render import render  # noqa: E402

ZMIENIONE = ('R4#', 'W6#', 'B1#', 'D1#', 'K2-P#5', 'K2-L#5', 'KUPNE_blotniki', 'KUPNE_odblaski', 'T8-',
             'KUPNE_opony', 'KUPNE_felgi', 'KUPNE_polosie', 'K-POL',
             'TRAP_tr_T7', 'TRAP_tr_T4P', 'TRAP_tr_T2#13', 'TRAP_tr_T2#21', 'TRAP_tr_T6',
             'TRAP_zal_T7', 'TRAP_zal_T4P', 'TRAP_zal_T2#13', 'TRAP_zal_T2#21', 'TRAP_zal_T6')
PIN = np.array([3345.0, 318.0])


def ramp_sequence(glb, png, title):
    """Przekrój boczny okolic zawiasu rampy przy podnoszeniu (obrót segmentu 1 wokół sworznia)."""
    _, P = load(glb)
    d = {p['name']: p for p in P}
    frame = ['P1#1', 'R3#1', 'T5-P#1', 'S1#1', 'R2-P#1']
    seg = [n for n in d if n.startswith('TRAP_zal') and n.split('#')[-1].startswith('1') and 'SRUBY' not in n
           and 'SIATKA' not in n and ('T1-N' in n or 'T7' in n or 'T6' in n)]
    fig, axs = plt.subplots(1, 4, figsize=(16, 4.6), dpi=110)
    for ax, ang in zip(axs, (0, 30, 60, 101.67)):
        a = np.radians(ang)
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        for n in frame:
            V = d[n]['V'][:, :2] * 1000
            ax.add_collection(PolyCollection(V[d[n]['F']], facecolors='#9aa0a6', edgecolors='#9aa0a6', linewidths=0.2))
        for n in seg:
            V = (d[n]['V'][:, :2] * 1000 - PIN) @ R.T + PIN
            col = '#d9480f' if 'T7' in n else '#1f2933'
            ax.add_collection(PolyCollection(V[d[n]['F']], facecolors=col, edgecolors=col, linewidths=0.2, alpha=0.9))
        ax.plot(*PIN, 'o', color='#2b8a3e', ms=5)
        ax.set_xlim(3150, 3560)
        ax.set_ylim(150, 620)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"obrót rampy {ang:.0f}°", fontsize=11)
    fig.suptitle(title, fontsize=13)
    fig.text(0.5, 0.02, "szary: podłoga P1, poprzeczka R3, wspornik T5   ·   czerwony: płyta najazdowa T7   ·   "
             "zielony punkt: sworzeń zawiasu", ha='center', fontsize=10)
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(png, facecolor='white')
    plt.close(fig)


def main(v5, v6dir, out):
    os.makedirs(out, exist_ok=True)
    t6 = os.path.join(v6dir, 'przyczepa_v6_transport.glb')
    z6 = os.path.join(v6dir, 'przyczepa_v6_zaladunek.glb')
    render(v5, f'{out}/v5_iso.png', 'iso', 'v5 – stan wejściowy (w GLB obie pozycje rampy naraz)')
    render(t6, f'{out}/v6_iso.png', 'iso', 'v6 – transport (na pomarańczowo części zmienione)', highlight=ZMIENIONE)
    render(z6, f'{out}/v6_zaladunek_iso.png', 'iso', 'v6 – rampa w pozycji do załadunku', highlight=ZMIENIONE)
    render(v5, f'{out}/v5_bok.png', 'bok', 'v5 – widok z boku (oś X = 2400 mm)', skip=('MOTOCYKL',))
    render(t6, f'{out}/v6_bok.png', 'bok', 'v6 – widok z boku (oś X = 2250 mm, błotnik +60 mm)', highlight=ZMIENIONE,
           skip=('MOTOCYKL',))
    render(t6, f'{out}/v6_spod.png', 'gora', 'v6 – widok z dołu: dyszel D1 doprowadzony do poprzeczki osi R4',
           highlight=ZMIENIONE, skip=('MOTOCYKL', 'P1#1', 'SRUBY_W14', 'KL1#1', 'KL1#2', 'KL2#1'))
    ramp_sequence(v5, f'{out}/v5_rampa_podnoszenie.png', 'v5 – płyta T7 wchodzi w podłogę i poprzeczkę R3 (rampy nie da się podnieść)')
    ramp_sequence(z6, f'{out}/v6_rampa_podnoszenie.png', 'v6 – płyta T7 przycięta po obwiedni ruchu: brak kolizji')


if __name__ == '__main__':
    main(*sys.argv[1:4])
