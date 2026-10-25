"""Worn gate-tower corners, separate coping stones and eased battlements.

Only render geometry changes. The original body and merlon collision boxes stay
in place, and all surfaces use the existing masonry materials at world scale.
"""
import itertools
import math
import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection
import belltower_furniture as F


def seed_at(lo, extra=0):
    return (int(round(np.dot(lo, (37, 71, 19)))) + extra * 104729) & 0xffffffff


def triangle(model, paint, points, expected):
    exported = np.round(np.asarray(points, float), 3)
    normal = np.cross(exported[1] - exported[0], exported[2] - exported[0])
    if np.linalg.norm(normal) < 1e-8:
        return
    if np.dot(normal, expected) < 0:
        points = list(reversed(points))
        normal = -normal
    model.polygon(paint, points, normal / np.linalg.norm(normal))


def stone(model, lo, hi, paint, rng, cap=False):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    half, centre = (hi-lo)/2, (hi+lo)/2
    planes = []
    for axis in range(3):
        for sign in (-1, 1):
            n = np.eye(3)[axis] * sign
            planes.append((*n, -half[axis]))
    for a, b in itertools.combinations(range(3), 2):
        for sa, sb in itertools.product((-1, 1), repeat=2):
            n = np.zeros(3); n[a] = sa; n[b] = sb
            bevel = rng.uniform(.38, .78) if cap else rng.uniform(.33, .67)
            if b == 2 and sb > 0:
                bevel *= 1.35
            planes.append((*n, -(half[a] + half[b] - bevel)))
    for sx, sy in itertools.product((-1, 1), repeat=2):
        if rng.random() < .55:
            planes.append((sx, sy, 1, -(sum(half) - rng.uniform(1.35, 2.35))))
    vertices = HalfspaceIntersection(np.asarray(planes), np.zeros(3)).intersections
    hull = ConvexHull(vertices)
    for face, equation in zip(hull.simplices, hull.equations):
        triangle(model, paint, [centre + vertices[i] for i in face], equation[:3])


def shaft(model, lo, hi):
    """A continuous closed shaft with unequal, locally chipped corner arrises."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    rng = np.random.default_rng(seed_at(lo, 1))
    levels = np.linspace(lo[2], hi[2], math.ceil((hi[2]-lo[2])/25) + 1)
    rings = []
    for z in levels:
        cuts = rng.uniform(.95, 2.15, 4)
        cuts += (rng.random(4) < .18) * rng.uniform(.65, 1.7, 4)
        x0, y0 = lo[:2]; x1, y1 = hi[:2]
        rings.append(np.array(((x0+cuts[0], y0, z), (x1-cuts[1], y0, z),
            (x1, y0+cuts[1], z), (x1, y1-cuts[2], z),
            (x1-cuts[2], y1, z), (x0+cuts[3], y1, z),
            (x0, y1-cuts[3], z), (x0, y0+cuts[0], z))))
    for lower, upper in zip(rings, rings[1:]):
        for i in range(8):
            j = (i+1) % 8
            edge = lower[j] - lower[i]
            expected = (edge[1], -edge[0], 0)
            triangle(model, 'rubble', [lower[i], lower[j], upper[j]], expected)
            triangle(model, 'rubble', [lower[i], upper[j], upper[i]], expected)
    F.face(model, 'rubble', rings[0], (0, 0, -1))
    F.face(model, 'rubble', rings[-1], (0, 0, 1))


def coping(model, lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    rng = np.random.default_rng(seed_at(lo, 2))
    # A recessed continuous core closes the narrow joints behind the front stones.
    model.box(lo + (.85, .85, .12), hi - (.85, .85, .5), 'ashlar_grey')
    for axis in range(2):
        across = 1-axis
        length = hi[axis] - lo[axis]
        count = round(length/34)
        ends = np.linspace(lo[axis], hi[axis], count+1)
        ends[1:-1] += rng.uniform(-2.5, 2.5, count-1)
        for side in (-1, 1):
            for i, (a, b) in enumerate(zip(ends, ends[1:])):
                # The x-running sides own the corners; the other sides butt in.
                aa, bb = a+.10, b-.10
                if axis == 1:
                    aa = max(aa, lo[axis]+10.2)
                    bb = min(bb, hi[axis]-10.2)
                low, high = lo.copy(), hi.copy()
                low[axis], high[axis] = aa, bb
                if side < 0:
                    high[across] = lo[across]+10
                else:
                    low[across] = hi[across]-10
                high[2] -= rng.uniform(.03, .36)
                low[2] += rng.uniform(.02, .14)
                stone(model, low, high, 'ashlar_grey', rng, cap=True)


def merlon(model, lo, hi, surface=None, worn=True):
    if not worn:
        model.box(lo, hi, 'rubble', surface)
        return
    model.box(lo, hi, None, surface)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    rng = np.random.default_rng(seed_at(lo, 3))
    mid = (lo[2]+hi[2])/2 + rng.uniform(-.65, .65)
    for bottom, top in ((lo[2]-.45, mid-.095), (mid+.095, hi[2]-rng.uniform(.05, .55))):
        low = lo + (rng.uniform(0, .16), rng.uniform(0, .16), 0)
        high = hi - (rng.uniform(0, .16), rng.uniform(0, .16), 0)
        low[2], high[2] = bottom, top
        stone(model, low, high, 'rubble', rng)


def tower(model, n0, n1, surface=None, worn=True):
    lo, hi = (-2410, n0, -500), (-2280, n1, 330)
    if worn:
        model.box(lo, hi, None, surface)
        shaft(model, lo, hi)
        coping(model, (-2414, n0-4, 318), (-2276, n1+4, 330))
    else:
        model.box(lo, hi, {'default': 'rubble', '+z': 'ashlar_grey'}, surface)
        model.box((-2414, n0-4, 318), (-2276, n1+4, 330), 'ashlar_grey')
    for k in range(3):
        ce = -2410+20+k*45
        merlon(model, (ce-12, n0-4, 330), (ce+12, n0+12, 362), surface, worn)
        merlon(model, (ce-12, n1-12, 330), (ce+12, n1+4, 362), surface, worn)
    for nn in (n0+36, n1-36):
        merlon(model, (-2410, nn-12, 330), (-2398, nn+12, 362), surface, worn)
        merlon(model, (-2292, nn-12, 330), (-2280, nn+12, 362), surface, worn)


def targets(model, surface=None, worn=True):
    for n0, n1 in ((-230, -110), (110, 230)):
        tower(model, n0, n1, surface, worn)
    for n in np.arange(-1466+30, 1860, 70):
        if not -250 < n < 250:
            merlon(model, (-2380, n-20, 240), (-2366, n+20, 274), surface, worn)
    for e in np.arange(-2330, -1850-10, 70):
        merlon(model, (e-20, 1866, 240), (e+20, 1880, 274), surface, worn)
