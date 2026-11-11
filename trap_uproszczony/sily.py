# -*- coding: utf-8 -*-
"""
Drogi sił w pokładzie trapu – model rusztu (grillage).

Każda rura podłużna i każda poprzeczka to belka w planie; węzeł ma 3 stopnie swobody:
w (ugięcie w pionie), obrót wokół osi s (wzdłuż trapu) i obrót wokół osi x (w poprzek).
Skrzyżowanie rura–poprzeczka = jedna śruba M8 z tuleją: przenosi tylko siłę pionową
(docisk, gdy rura naciska na poprzeczkę; rozciąganie śruby, gdy poprzeczka „wisi” na rurze).
Podpory: sworznie zawiasu przy przyczepie (tylko rury L1, ±125), ziemia pod końcami rur B
(tylko docisk – podpora odrywa się, gdy ciągnie), opcjonalnie oparcie chodnika przy przyczepie.
Zawias środkowy łączy A i B tylko tam, gdzie są płyty Z ze sworzniem (przenosi siłę i moment).

Wynik: siły w każdym skrzyżowaniu, reakcje podpór, ugięcia, skok na styku sekcji.
Obciążenia obliczeniowe jak w obliczeniach ręcznych: koło 273 kg ×1,5 ×1,5, stopa 105 kg ×1,5 ×1,5,
ciężar własny ×1,35.
"""
import numpy as np

E, G_MOD = 210000.0, 81000.0


def rhs_IJ(b, h, t):
    """b – szerokość, h – wysokość (oś zginania pozioma), t – ścianka; J dla przekroju zamkniętego (Bredt)"""
    I = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12
    Am = (b - t) * (h - t)
    return I, 4 * Am * Am * t / (2 * ((b - t) + (h - t)))


class Ruszt:
    def __init__(self, xs, x0, x1, L, lane_IJ, walk_IJ, cross_IJ, crossA, crossB, tie=None, tie_IJ=None,
                 hinges=(-125.0, 125.0), pins=(-125.0, 125.0), walk_rest=(), lane_x=200.0):
        self.xs, self.x0, self.x1, self.L = list(xs), x0, x1, L
        self.nodes, self.elems, self.links, self.sup, self.joints = {}, [], [], [], []
        for sec in "AB":
            cr = crossA if sec == "A" else crossB
            for x in self.xs:
                st = sorted(set([0.0, L] + list(cr) + list(np.arange(0, L + 1, 50.0)) + ([tie] if (sec == "B" and tie) else [])))
                prof = lane_IJ if abs(x) < lane_x else walk_IJ
                ids = [self._n((sec, "t", x, s), s, x) for s in st]
                for a, b, sa, sb in zip(ids, ids[1:], st, st[1:]):
                    self.elems.append((a, b, "s", sb - sa, prof))
            for s in cr:
                xx = sorted(set([x0, x1] + self.xs))
                ids = [self._n((sec, "c", s, x), s, x) for x in xx]
                for a, b, xa, xb in zip(ids, ids[1:], xx, xx[1:]):
                    self.elems.append((a, b, "x", xb - xa, cross_IJ))
                for x in self.xs:
                    self.links.append((self.nodes[(sec, "t", x, s)][0], self.nodes[(sec, "c", s, x)][0], ("skrzyżowanie", sec, s, x)))
            if sec == "B" and tie:
                xx = sorted(set([x0, x1] + self.xs))
                ids = [self._n(("B", "T", tie, x), tie, x) for x in xx]
                for a, b, xa, xb in zip(ids, ids[1:], xx, xx[1:]):
                    self.elems.append((a, b, "x", xb - xa, tie_IJ))
                for x in self.xs:
                    self.links.append((self.nodes[("B", "t", x, tie)][0], self.nodes[("B", "T", tie, x)][0], ("nity listwy T", "B", tie, x)))
        for x in pins:
            self.sup.append((self.nodes[("A", "t", x, 0.0)][0], ("sworzeń przy przyczepie", x), False))
        for x in self.xs:
            self.sup.append((self.nodes[("B", "t", x, L)][0], ("ziemia", x), True))
        for x in walk_rest:
            self.sup.append((self.nodes[("A", "t", x, 0.0)][0], ("oparcie chodnika", x), True))
        for x in self.xs:
            if x in hinges:
                self.joints.append((self.nodes[("A", "t", x, L)][0], self.nodes[("B", "t", x, 0.0)][0], ("zawias", x)))
        self.K = self._stiffness()

    def _n(self, key, s, x):
        if key not in self.nodes:
            self.nodes[key] = (len(self.nodes), s, x)
        return self.nodes[key][0]

    def _stiffness(self):
        N = 3 * len(self.nodes)
        K = np.zeros((N, N))
        for (a, b, d, Lb, (I, J)) in self.elems:
            EI, GJ = E * I, G_MOD * J
            kb = EI / Lb ** 3 * np.array([[12, 6 * Lb, -12, 6 * Lb], [6 * Lb, 4 * Lb * Lb, -6 * Lb, 2 * Lb * Lb],
                                          [-12, -6 * Lb, 12, -6 * Lb], [6 * Lb, 2 * Lb * Lb, -6 * Lb, 4 * Lb * Lb]])
            bend, tors = (2, 1) if d == "s" else (1, 2)
            sg = -1.0 if d == "s" else 1.0
            T = np.diag([1, sg, 1, sg])
            ib = [3 * a, 3 * a + bend, 3 * b, 3 * b + bend]
            K[np.ix_(ib, ib)] += T @ kb @ T
            it = [3 * a + tors, 3 * b + tors]
            K[np.ix_(it, it)] += GJ / Lb * np.array([[1, -1], [-1, 1]])
        return K

    def solve(self, loads):
        """loads: [(klucz węzła rury (sekcja, 't', x, s), siła w dół [N])]"""
        k = 1e6
        K = self.K.copy()
        for (a, b, tag) in self.links:
            K[np.ix_([3 * a, 3 * b], [3 * a, 3 * b])] += k * np.array([[1, -1], [-1, 1]])
        for (a, b, tag) in self.joints:
            for d, kk in ((0, k), (1, k * 1e3), (2, k * 1e3)):
                K[np.ix_([3 * a + d, 3 * b + d], [3 * a + d, 3 * b + d])] += kk * np.array([[1, -1], [-1, 1]])
        K += np.eye(len(K)) * 1e-3
        F = np.zeros(len(K))
        for key, P in loads:
            F[3 * self.nodes[key][0]] -= P
        active = list(self.sup)
        for _ in range(30):
            Kt = K.copy()
            for (a, tag, co) in active:
                Kt[3 * a, 3 * a] += 10 * k
            u = np.linalg.solve(Kt, F)
            R = {tag: -10 * k * u[3 * a] for (a, tag, co) in active}
            lift = [q for q in active if q[2] and R[q[1]] < -1.0]
            pen = [q for q in self.sup if q not in active and u[3 * q[0]] < -0.01]
            if not lift and not pen:
                break
            active = [q for q in active if q not in lift] + pen
        # siła w skrzyżowaniu: + rozciąganie śruby (poprzeczka wisi na rurze), − docisk
        link = {tag: k * (u[3 * a] - u[3 * b]) for (a, b, tag) in self.links}
        W = {key: u[3 * v[0]] for key, v in self.nodes.items()}
        reac = {q[1]: R.get(q[1], 0.0) for q in self.sup}
        return dict(link=link, R=reac, W=W)

    def self_weight(self, mA, mB, g=9.81, gamma=1.35):
        out = []
        for sec, m in (("A", mA), ("B", mB)):
            ks = [k for k in self.nodes if k[0] == sec and k[1] == "t"]
            out += [(k, m * g * gamma / len(ks)) for k in ks]
        return out


def cases(xs, L, P_wheel, P_foot, lane_x=200.0):
    """typowe położenia koła (rury jezdne) i stopy (chodnik): przy przyczepie, w środku, przy zawiasie, przy ziemi"""
    out = []
    for x in xs:
        P, nm = (P_wheel, "koło") if abs(x) < lane_x else (P_foot, "stopa")
        if x < 0 and abs(x) < lane_x and -x in xs:
            continue                                      # symetria pasa koła
        for sec, s, where in (("A", 0.0, "przy przyczepie"), ("A", 600.0, "środek A"), ("A", L, "przy zawiasie (A)"),
                              ("B", 0.0, "przy zawiasie (B)"), ("B", 600.0, "środek B"), ("B", L - 100.0, "przy ziemi")):
            out.append((f"{nm} x={x:+.0f}, {where}", [((sec, "t", x, s), P)], (sec, x, s)))
    return out


def analyse(r, mA, mB, P_wheel, P_foot):
    sw = r.self_weight(mA, mB)
    rows, worst = [], {}
    for nm, ld, (sec, x, s) in cases(r.xs, r.L, P_wheel, P_foot):
        res = r.solve(ld + sw)
        W = res["W"]
        defl = W[(sec, "t", x, s)]
        step = W[("A", "t", x, r.L)] - W[("B", "t", x, 0.0)]
        for tag, v in res["link"].items():
            if v > worst.get(tag, (0.0, ""))[0]:
                worst[tag] = (v, nm)
        rows.append(dict(przypadek=nm, ugiecie=defl, skok=step, R=res["R"],
                         max_rozc=max(res["link"].items(), key=lambda kv: kv[1])))
    return rows, worst
