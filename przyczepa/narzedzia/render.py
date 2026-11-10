#!/usr/bin/env python3
"""Proste rendery (rzut prostokątny, cieniowanie płaskie) plików GLB do PNG - bez GPU.

    python3 render.py <plik.glb> <wyjście.png> [widok] [tytuł]
widok: iso | bok | gora | tyl | os (zbliżenie na koło)
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glbio import load  # noqa: E402

COL = {'rama_czarna': (0.16, 0.17, 0.19), 'ocynk': (0.78, 0.79, 0.80), 'polos': (0.55, 0.57, 0.58),
       'sklejka': (0.45, 0.33, 0.20), 'siatka': (0.35, 0.36, 0.38), 'opona': (0.08, 0.08, 0.08),
       'felga': (0.30, 0.30, 0.32), 'blotnik': (0.12, 0.12, 0.13), 'obrysowa': (0.95, 0.95, 0.93),
       'odblask': (0.97, 0.58, 0.06), 'lampa': (0.80, 0.06, 0.05), 'motocykl': (0.20, 0.45, 0.85)}
HL = (0.85, 0.25, 0.10)   # podświetlenie części zmienionych w v6


def view_matrix(kind):
    def rot(az, el):
        az, el = np.radians(az), np.radians(el)
        Ry = np.array([[np.cos(az), 0, np.sin(az)], [0, 1, 0], [-np.sin(az), 0, np.cos(az)]])
        Rx = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
        return Rx @ Ry
    return {'iso': rot(-35, 25), 'bok': rot(0, 0), 'gora': rot(0, 90), 'tyl': rot(-90, 0),
            'os': rot(-20, 15)}[kind]


def render(glb, png, kind='iso', title='', highlight=(), crop=None, skip=()):
    _, parts = load(glb)
    R = view_matrix(kind)
    light = np.array([0.3, 0.8, 0.5])
    light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    for p in parts:
        if p['name'] in skip:
            continue
        V = p['V'] * 1000.0 @ R.T
        T = V[p['F']]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ok = ln > 1e-9
        T, n = T[ok], n[ok] / ln[ok, None]
        if crop is not None:
            c = T.mean(1)
            sel = (c[:, 0] > crop[0]) & (c[:, 0] < crop[1]) & (c[:, 1] > crop[2]) & (c[:, 1] < crop[3])
            T, n = T[sel], n[sel]
        base = np.array(HL if any(p['name'].startswith(h) for h in highlight) else COL.get(p['mat'], (0.5, 0.5, 0.5)))
        shade = 0.35 + 0.65 * np.abs(n @ light)
        c = np.clip(base[None, :] * shade[:, None] + 0.04, 0, 1)
        alpha = 0.25 if p['mat'] == 'motocykl' else 1.0
        polys.append(T[:, :, :2])
        cols.append(np.c_[c, np.full(len(c), alpha)])
        depth.append(T[:, :, 2].mean(1))
    P = np.concatenate(polys)
    C = np.concatenate(cols)
    D = np.concatenate(depth)
    o = np.argsort(D)
    fig, ax = plt.subplots(figsize=(14, 7) if kind != 'os' else (10, 8), dpi=110)
    ax.add_collection(PolyCollection(P[o], facecolors=C[o], edgecolors=C[o], linewidths=0.15))
    xy = P.reshape(-1, 2)
    ax.set_xlim(xy[:, 0].min() - 50, xy[:, 0].max() + 50)
    ax.set_ylim(xy[:, 1].min() - 50, xy[:, 1].max() + 50)
    ax.set_aspect('equal')
    ax.axis('off')
    if title:
        ax.set_title(title, fontsize=13)
    fig.tight_layout()
    fig.savefig(png, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    a = sys.argv[1:]
    render(a[0], a[1], a[2] if len(a) > 2 else 'iso', a[3] if len(a) > 3 else '')
