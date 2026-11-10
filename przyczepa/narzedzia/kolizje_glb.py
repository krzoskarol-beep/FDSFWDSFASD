#!/usr/bin/env python3
"""Kolizje między wszystkimi siatkami GLB (także części kupne i śruby).  python3 kolizje_glb.py plik.glb [prog_mm3]"""
import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glbio import load  # noqa: E402


def main(path, thr=50.0):
    _, P = load(path)
    M = {p['name']: trimesh.Trimesh(p['V'] * 1000, p['F']) for p in P}
    cm = trimesh.collision.CollisionManager()
    for k, m in M.items():
        cm.add_object(k, m)
    _, names = cm.in_collision_internal(return_names=True)
    out = []
    for a, b in sorted(names):
        try:
            v = trimesh.boolean.intersection([M[a], M[b]], engine='manifold').volume
        except Exception:
            v = float('nan')
        if v > thr:
            out.append((round(v), a, b))
    for v, a, b in sorted(out, reverse=True):
        print(f"{v:8d} mm3  {a} x {b}")
    return out


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 50.0)
