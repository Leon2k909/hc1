"""Riverside's lawn chairs v2: a folding aluminium chair with woven webbing, in the old ones' green and the porch's red.
Builds the mesh, paints the maps and writes the models with numpy and PIL, as Sources/Riverside/propane-v2/propane.py does.

python lawn_chair.py <project root>

Engine X is the way the chair faces, Y its left, Z up; the origin is on the ground under the middle of the seat, where the old chair's was.
The frame: a front U and a rear U of 1 in tube splayed into an A and standing on floor bars with plastic glides, the seat frame and the back frame inside
them, flat plastic armrests rounded over the front legs, bolts with washers and rivets.
The webbing: real straps of woven yarn, a thickness each, over and under one another, sagging where people sat, each wrapped round its tubes and tucked
under. One of the back's straps has snapped and hangs. Sun-bleached, grimy, mildewed and mud-splashed; the aluminium
dull, oxidised and caked with dried mud low down. Everything is made up; nothing copies a maker's pattern.
"""
import ctypes
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except AttributeError:
    pass

ROOT = sys.argv[1]
MODEL = "models/props/riverside/lawn_chair_v2"
MATS = "materials/riverside/lawn_chair_v2"
OUT = os.path.join(ROOT, "Assets", *MODEL.split("/"))
MAT_OUT = os.path.join(ROOT, "Assets", *MATS.split("/"))
SCAN = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")
for folder in (OUT, MAT_OUT):
    os.makedirs(folder, exist_ok=True)

AW, AH = 2048, 1024
PPI = 28
TUBE_R = 0.5
STRAP_W = 2.2
STRIP = (1008, 64)  # One strap's strip: 36 in long, its width across 64 px.
PALETTES = {
    "green": {"main": (0.10, 0.40, 0.28), "light": (0.86, 0.86, 0.80), "accent": (0.86, 0.70, 0.20)},
    "red": {"main": (0.60, 0.11, 0.09), "light": (0.86, 0.85, 0.80), "accent": (0.12, 0.16, 0.33)},
}


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def blobs(shape, sigma, seed, aspect=(1.0, 1.0)):
    r = np.random.default_rng(seed).normal(size=(max(4, shape[0] // 4), max(4, shape[1] // 4)))
    r = ndi.gaussian_filter(r, (max(0.3, sigma / 4 * aspect[0]), max(0.3, sigma / 4 * aspect[1])), mode="wrap")
    r = ndi.zoom(r, (shape[0] / r.shape[0], shape[1] / r.shape[1]), order=1)[: shape[0], : shape[1]]
    return r / (r.std() * 2.5 + 1e-6)


def to_normal(height, ppi):
    dr, dc = np.gradient(height)
    n = np.stack((-dc * ppi, dr * ppi, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def unit(x):
    x = np.asarray(x, float)
    return x / np.linalg.norm(x)


# ---------------------------------------------------------------------------------------------------------------------
# Atlas layout
# ---------------------------------------------------------------------------------------------------------------------

STRIPS = [((k % 2) * (STRIP[0] + 8), (k // 2) * (STRIP[1] + 4)) for k in range(16)]
TUBE_PPI = 24
TUBES = [(0, 548 + k * 68, 2016, 64) for k in range(4)]  # 84 in of tube at 24 px/in round its 3.14 in: clean, then three of mud, worse low down.
ARM = (0, 548 + 4 * 68 + 4, 528, 144)  # The armrests: 22 in at 24 px/in; the top in rows 0-48, the sides 52-66, the bottom 80-128.
SWATCH = (540, ARM[1], 192, 32)
SWATCHES = {"rivet": (0.62, 0.62, 0.6), "cap": (0.05, 0.05, 0.05), "glide": (0.07, 0.07, 0.07)}
STRAP_T = 0.025  # The webbing's thickness: under the weave's clearance at a crossing (0.65 of its depth), so crossing straps never touch.


def swatch_uv(name):
    k = list(SWATCHES).index(name)
    return (SWATCH[0] + (k + 0.5) * SWATCH[2] / len(SWATCHES), SWATCH[1] + SWATCH[3] / 2)


def mud_region(z):
    """Which tube picture a stretch of tube at height z takes: mud splashed up from the yard, worst at the floor bars."""
    return TUBES[3 if z < 2.0 else 2 if z < 4.5 else 1 if z < 8.0 else 0]


# ---------------------------------------------------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------------------------------------------------


class Mesh:
    def __init__(self):
        self.p, self.t, self.n = [], [], []

    def tri(self, p, t, n):
        self.p.append(np.asarray(p, float))
        self.t.append(np.asarray(t, float))
        self.n.append(np.broadcast_to(np.asarray(n, float), (3, 3)).copy() if np.ndim(n) == 1 else np.asarray(n, float))

    def quad(self, a, b, c, d, uv, n):
        n = np.asarray(n, float)
        if n.ndim == 1:
            n = np.array([n, n, n, n])
        self.tri((a, b, c), (uv[0], uv[1], uv[2]), (n[0], n[1], n[2]))
        self.tri((a, c, d), (uv[0], uv[2], uv[3]), (n[0], n[2], n[3]))

    def tube(self, path, r, sides, u0=0.0, caps=True):
        """A tube along a path, its UVs along a tube picture by length, the picture chosen by height so the low parts are muddy."""
        path = [np.asarray(p, float) for p in path]
        L = np.concatenate(([0.0], np.cumsum([np.linalg.norm(path[k + 1] - path[k]) for k in range(len(path) - 1)])))
        prev = None
        rings = []
        for k, p in enumerate(path):
            t = unit(path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)])
            if prev is None:
                ref = np.array((0, 0, 1.0)) if abs(t[2]) < 0.9 else np.array((1.0, 0, 0))
                e1 = unit(np.cross(t, ref))
            else:
                e1 = unit(prev - t * np.dot(prev, t))  # Carried along, so the tube doesn't twist.
            prev = e1
            e2 = np.cross(t, e1)
            rings.append([(e1 * np.cos(b) + e2 * np.sin(b)) for b in np.linspace(0, 2 * np.pi, sides + 1)])
        for k in range(len(path) - 1):
            x0, y0, w, h = mud_region((path[k][2] + path[k + 1][2]) / 2)
            ua = x0 + ((u0 + L[k]) * TUBE_PPI) % (w - 80)
            ub = ua + (L[k + 1] - L[k]) * TUBE_PPI
            for j in range(sides):
                na, nb, nc, nd = rings[k][j], rings[k][j + 1], rings[k + 1][j + 1], rings[k + 1][j]
                pa, pb, pc, pd = path[k] + na * r, path[k] + nb * r, path[k + 1] + nc * r, path[k + 1] + nd * r
                va, vb = y0 + h * j / sides, y0 + h * (j + 1) / sides
                self.quad(pa, pb, pc, pd, [(ua, va), (ua, vb), (ub, vb), (ub, va)], [na, nb, nc, nd])
        if caps:
            for end, k in ((path[0], 0), (path[-1], -1)):
                t = unit(path[1] - path[0]) if k == 0 else unit(path[-1] - path[-2])
                cap = swatch_uv("cap")
                ring = rings[k]
                for j in range(sides):
                    self.tri((end - t * 0.05 * (1 if k == 0 else -1), end + ring[j] * r, end + ring[j + 1] * r), (cap, cap, cap), -t if k == 0 else t)

    def ribbon(self, pts, width_dir, uv0, up_hint, lod=0):
        """A strap: a band of webbing STRAP_T thick down a path, its width across width_dir. UVs: along its strip by length from uv0, across the strip's height.
        Its underside is a thickness below its top, never on it, so the two never fight."""
        pts = [np.asarray(p, float) for p in pts]
        L = np.concatenate(([0.0], np.cumsum([np.linalg.norm(pts[k + 1] - pts[k]) for k in range(len(pts) - 1)])))
        x0, y0 = uv0
        wd = unit(width_dir)
        mid = len(pts) // 2
        sign = 1.0 if np.dot(np.cross(wd, unit(pts[mid + 1] - pts[mid - 1])), up_hint) >= 0 else -1.0
        normals = [unit(np.cross(wd, unit(pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]))) * sign for k in range(len(pts))]
        half = STRAP_W / 2
        for k in range(len(pts) - 1):
            na, nb = normals[k], normals[k + 1]
            a, b = pts[k] - wd * half, pts[k] + wd * half
            c, d = pts[k + 1] + wd * half, pts[k + 1] - wd * half
            u0, u1 = x0 + min(L[k] * PPI, STRIP[0] - 1), x0 + min(L[k + 1] * PPI, STRIP[0] - 1)
            uv = [(u0, y0 + 0.5), (u0, y0 + STRIP[1] - 0.5), (u1, y0 + STRIP[1] - 0.5), (u1, y0 + 0.5)]
            self.quad(a, b, c, d, uv, [na, na, nb, nb])
            ia, ib, ic, id_ = a - na * STRAP_T, b - na * STRAP_T, c - nb * STRAP_T, d - nb * STRAP_T
            self.quad(ia, id_, ic, ib, [uv[0], uv[3], uv[2], uv[1]], [-na, -nb, -nb, -na])
            if lod == 0:
                edge0 = [(u0, y0 + 1.0), (u0, y0 + 1.5), (u1, y0 + 1.5), (u1, y0 + 1.0)]
                self.quad(a, ia, id_, d, edge0, -wd)
                self.quad(b, c, ic, ib, edge0, wd)

    def dome(self, centre, axis, r, seg=8, washer=0.0):
        """A rivet head, on a washer if asked."""
        axis = unit(axis)
        e1 = unit(np.cross(axis, (0, 0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0, 0)))
        e2 = np.cross(axis, e1)
        uv = swatch_uv("rivet")
        base = np.asarray(centre, float)
        if washer:
            ring = [(washer, 0.0), (washer, 0.06), (r, 0.06)]
            for i in range(len(ring) - 1):
                for k in range(seg):
                    ps = []
                    for (rr, hh), q in ((ring[i], k), (ring[i], k + 1), (ring[i + 1], k + 1), (ring[i + 1], k)):
                        ang = 2 * np.pi * q / seg
                        ps.append(base + (e1 * np.cos(ang) + e2 * np.sin(ang)) * rr + axis * hh)
                    n = axis if i == 1 else unit(ps[0] - base - axis * 0.03)
                    self.quad(*ps, [uv] * 4, n)
            base = base + axis * 0.06
        rings = [(r * np.cos(a), r * 0.45 * np.sin(a)) for a in np.linspace(0, np.pi / 2, 4)]
        for i in range(len(rings) - 1):
            for k in range(seg):
                ps = []
                for (rr, hh), q in ((rings[i], k), (rings[i], k + 1), (rings[i + 1], k + 1), (rings[i + 1], k)):
                    ang = 2 * np.pi * q / seg
                    ps.append(base + (e1 * np.cos(ang) + e2 * np.sin(ang)) * rr + axis * hh)
                self.quad(*ps, [uv] * 4, [unit(p - base + axis * 0.2) for p in ps])

    def glide(self, centre, axis, r, length, seg=10):
        """A plastic glide clipped round a floor bar."""
        axis = unit(axis)
        e1 = unit(np.cross(axis, (0, 0, 1.0)))
        e2 = np.cross(axis, e1)
        uv = swatch_uv("glide")
        c = np.asarray(centre, float)
        prof = [(0.0, -length / 2), (r * 0.9, -length / 2), (r, -length / 2 + 0.12), (r, length / 2 - 0.12), (r * 0.9, length / 2), (0.0, length / 2)]
        for i in range(len(prof) - 1):
            (r0, h0), (r1, h1) = prof[i], prof[i + 1]
            for k in range(seg):
                ps, ns = [], []
                for rr, hh, q in ((r0, h0, k), (r0, h0, k + 1), (r1, h1, k + 1), (r1, h1, k)):
                    ang = 2 * np.pi * q / seg
                    radial = e1 * np.cos(ang) + e2 * np.sin(ang)
                    ps.append(c + radial * rr + axis * hh)
                    ns.append(unit(radial * (h1 - h0) - axis * (r1 - r0) + 1e-9 * radial))
                if np.linalg.norm(np.cross(ps[1] - ps[0], ps[2] - ps[0])) + np.linalg.norm(np.cross(ps[2] - ps[0], ps[3] - ps[0])) > 1e-9:
                    self.quad(*ps, [uv] * 4, ns)

    def armrest(self, y, lod):
        """A flat plastic arm: square at the back where it meets the back's upright, round at the front over the front leg, its top edges bevelled."""
        x_back, x_front, half, z0, z1, bev = ARM_BACK, FRONT_TOP[0], 1.0, ARM_Z - 0.55, ARM_Z, 0.12
        steps = (10, 6, 3)[lod]
        outline = [(x_back, y - half), (x_front, y - half)]
        outline += [(x_front + half * np.sin(a), y - half * np.cos(a)) for a in np.linspace(0, np.pi, steps + 2)[1:-1]]
        outline += [(x_front, y + half), (x_back, y + half)]
        P = np.array(outline)
        centre = P.mean(0)
        inset = centre + (P - centre) * np.array([1 - bev / (np.abs(P[:, 0] - centre[0]).max() + 1e-9), 1 - bev / half])[None, :] * 1.0
        inset = np.array([p - unit(p - centre) * 0 for p in inset])
        x0, y0, w, h = ARM

        def top_uv(p):
            return (x0 + (p[0] - x_back + 0.3) * 24, y0 + (p[1] - y + 1.0) * 24)

        def bottom_uv(p):
            return (x0 + (p[0] - x_back + 0.3) * 24, y0 + 80 + (p[1] - y + 1.0) * 24)

        n = len(P)
        cz = np.array((centre[0], centre[1], z1))
        for k in range(n):
            a, b = inset[k], inset[(k + 1) % n]
            self.tri((cz, (*a, z1), (*b, z1)), (top_uv(cz), top_uv(a), top_uv(b)), (0, 0, 1))
            a, b = P[k], P[(k + 1) % n]
            cb = np.array((centre[0], centre[1], z0))
            self.tri((cb, (*b, z0), (*a, z0)), (bottom_uv(cb), bottom_uv(b), bottom_uv(a)), (0, 0, -1))
            out = unit(np.array((*(b - a)[::-1] * np.array((1, -1)), 0.0)))
            if np.dot(out[:2], (a + b) / 2 - centre) < 0:
                out = -out
            ua, ub = x0 + (a[0] - x_back + 0.3) * 24, x0 + (b[0] - x_back + 0.3) * 24
            side = [(ua, y0 + 66), (ub, y0 + 66), (ub, y0 + 52), (ua, y0 + 52)]
            self.quad((*a, z0), (*b, z0), (*b, z1 - bev), (*a, z1 - bev), side, out)
            ia, ib = inset[k], inset[(k + 1) % n]
            slope = unit(out + np.array((0, 0, 1.0)))
            self.quad((*a, z1 - bev), (*b, z1 - bev), (*ib, z1), (*ia, z1), [(ua, y0 + 52), (ub, y0 + 52), (ub, y0 + 49), (ua, y0 + 49)], slope)


def fillet(points, radius, steps=6):
    """A polyline with each inner corner rounded to radius."""
    P = [np.asarray(p, float) for p in points]
    out = [P[0]]
    for k in range(1, len(P) - 1):
        a, b, c = P[k - 1], P[k], P[k + 1]
        d0, d1 = unit(a - b), unit(c - b)
        ang = np.arccos(np.clip(np.dot(d0, d1), -1, 1))
        if ang > np.pi - 1e-3:
            out.append(b)
            continue
        t = min(radius / np.tan(ang / 2), np.linalg.norm(a - b) * 0.45, np.linalg.norm(c - b) * 0.45)
        p0, p1 = b + d0 * t, b + d1 * t
        for s in np.linspace(0, 1, steps):
            q = (1 - s) ** 2 * p0 + 2 * (1 - s) * s * b + s ** 2 * p1  # A quadratic through the corner: close enough to an arc at these sizes.
            out.append(q)
    out.append(P[-1])
    return out


def densify(points, step):
    out = [np.asarray(points[0], float)]
    for a, b in zip(points[:-1], points[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        out += [a + (b - a) * (k / n) for k in range(1, n + 1)]
    return out


# ---------------------------------------------------------------------------------------------------------------------
# The chair
# ---------------------------------------------------------------------------------------------------------------------

YO, YI = 11.1, 10.0  # The legs' and the seat and back frames' sides.
ARM_Z = 22.9
BAR_Z = 0.62  # The floor bars' centres, up on their glides.
FRONT_TOP, FRONT_FOOT = np.array((9.0, 0.0, ARM_Z - 0.55)), np.array((11.8, 0.0, BAR_Z))
REAR_TOP, REAR_FOOT = np.array((-8.6, 0.0, ARM_Z - 0.55)), np.array((-13.6, 0.0, BAR_Z))


def leg_x(top, foot, z):
    return float(top[0] + (foot[0] - top[0]) * (top[2] - z) / (top[2] - foot[2]))


SEAT_FRONT = np.array((leg_x(FRONT_TOP, FRONT_FOOT, 14.8) - 0.35, 0.0, 14.8))
SEAT_BACK = np.array((leg_x(REAR_TOP, REAR_FOOT, 13.0) + 0.35, 0.0, 13.0))
UP_BACK = unit((-4.4, 0.0, 21.1))
BACK_FOOT = np.array((SEAT_BACK[0] - 0.2, 0.0, 12.4))
BACK_LOW = BACK_FOOT + UP_BACK * 3.6
BACK_TOP = BACK_FOOT + UP_BACK * 21.55
ARM_BACK = float(BACK_FOOT[0] + UP_BACK[0] * ((ARM_Z - 0.55 - BACK_FOOT[2]) / UP_BACK[2])) - 0.25


class Panel:
    """Webbing over a frame: p(a, b, w) = origin + A a + B b + N w, the tubes it wraps at a = 0, a = La (along B) and b = +-YI (along A)."""

    def __init__(self, origin, A, B, La, sag):
        self.o, self.A, self.B = np.asarray(origin, float), unit(A), unit(B)
        self.N = unit(np.cross(self.A, self.B))
        self.La, self.sag = La, sag

    def p(self, a, b, w):
        return self.o + self.A * a + self.B * b + self.N * w

    def dip(self, a, b):
        return -self.sag * (1 - (2 * a / self.La - 1) ** 2) * (1 - (b / YI) ** 2)


def strap_path(lo, hi, run, R, step, tuck=1.6):
    """A strap's 2D path (u, w) over a span from tube lo to tube hi: round lo from underneath, along the top by run(u), round hi and tucked under."""
    pts = []
    for th in np.linspace(np.radians(-125), np.radians(90), 9):  # Round lo: tucked under, out round the side, over the top.
        pts.append((lo - R * np.cos(th), R * np.sin(th)))
    pts.insert(0, (lo + tuck, -R))
    n = max(2, int(np.ceil((hi - lo) / step)))
    for u in np.linspace(lo, hi, n + 1)[1:-1]:
        pts.append((u, run(u)))
    for th in np.linspace(np.radians(90), np.radians(-125), 9):
        pts.append((hi + R * np.cos(th), R * np.sin(th)))
    pts.append((hi - tuck, -R))
    return pts


def webbing(m, panel, na, nb, rng, lod, broken=None, back=False, slack=()):
    """na straps running along a (wrapping the bars at a = 0 and La), nb straps running along b (wrapping the sides at b = +-YI), woven.
    Straps in slack have stretched and sag lower than the rest; the over-and-under is deep enough that they still clear the straps they cross."""
    R = TUBE_R + 0.04
    weave = (0.06, 0.06, 0.0)[lod]
    step = (0.25, 0.9, 3.0)[lod]
    a_pos = np.linspace(0.9 + STRAP_W / 2 - 0.4, panel.La - 0.9 - STRAP_W / 2 + 0.4, nb)  # Where the b-straps lie along a.
    b_pos = np.linspace(-YI + 0.5 + STRAP_W / 2, YI - 0.5 - STRAP_W / 2, na)  # Where the a-straps lie across b.
    pa, pb = a_pos[1] - a_pos[0], b_pos[1] - b_pos[0]

    def taper(u, lo, hi):
        return smooth(lo, lo + 1.2, u) * smooth(hi, hi - 1.2, u)

    k = 0
    for i, a in enumerate(a_pos):
        sign = (-1) ** i
        extra = 0.045 if ("b", i) in slack else 0.0

        def run(b, a=a, sign=sign, extra=extra):
            return R + panel.dip(a, b) * (1 + extra * 8) + weave * sign * np.cos(np.pi * (b - b_pos[0]) / pb) * taper(b, -YI, YI)

        path = strap_path(-YI, YI, run, R, step)
        if broken is not None and i == broken:
            # Snapped a third of the way in from each side: each end runs from its tube to the break, then hangs, curling off the webbing below.
            for side in (-1, 1):
                ordered = path if side < 0 else path[::-1]
                stub = []
                for u, w in ordered:
                    if u * side < 6.5 and w >= R - 0.01:
                        break
                    stub.append((u, w))
                edge = stub[-1][0]
                pts3 = [panel.p(a, u, w) for u, w in stub]
                for t in np.linspace(0.12, 1.0, 7):
                    pts3.append(panel.p(a - 3.2 * t * t, edge - side * 0.5 * t, R + 0.16 + 0.35 * t))
                m.ribbon(pts3, panel.A, STRIPS[(k + 5) % 8], panel.N, lod)
            k += 1
            continue
        m.ribbon([panel.p(a, u, w) for u, w in path], panel.A, STRIPS[(k + int(rng.integers(0, 8))) % 8], panel.N, lod)
        k += 1
    for j, b in enumerate(b_pos):
        sign = -((-1) ** j)
        extra = 0.045 if ("a", j) in slack else 0.0

        def run(a, b=b, sign=sign, extra=extra):
            return R + panel.dip(a, b) * (1 + extra * 8) + weave * sign * np.cos(np.pi * (a - a_pos[0]) / pa) * taper(a, 0, panel.La)

        path = strap_path(0.0, panel.La, run, R + 0.04, step)
        m.ribbon([panel.p(u, b, w) for u, w in path], panel.B, STRIPS[8 + (j + int(rng.integers(0, 8))) % 8], panel.N, lod)


def build(lod):
    m = Mesh()
    rng = np.random.default_rng(7)
    sides = (10, 6, 4)[lod]
    bend = (6, 4, 2)[lod]
    # Front U: from under each armrest's front down and forward to the floor bar. Rear U: down and back. The stance is an A, side on.
    for top, foot, u0 in ((FRONT_TOP, FRONT_FOOT, 0.0), (REAR_TOP, REAR_FOOT, 13.0)):
        path = fillet([top + (0, YO, 0), foot + (0, YO, 0), foot + (0, -YO, 0), top + (0, -YO, 0)], 1.3, bend)
        m.tube(densify(path, 1.6), TUBE_R, sides, u0)
    # The seat frame: a loop of tube inside the legs.
    fl, fr = SEAT_FRONT + (0, YI, 0), SEAT_FRONT + (0, -YI, 0)
    bl, br = SEAT_BACK + (0, YI, 0), SEAT_BACK + (0, -YI, 0)
    seat = fillet([fl + (0.3, -0.6, 0.03), fl, bl, br, fr, fl, fl + (-0.6, 0, -0.06)], 0.9, bend)
    m.tube(densify(seat, 2.0), TUBE_R, sides, 31.0)
    # The back frame: an upturned U on its pivots, and a bar low across it.
    back = fillet([BACK_FOOT + (0, YI, 0), BACK_TOP + (0, YI, 0), BACK_TOP + (0, -YI, 0), BACK_FOOT + (0, -YI, 0)], 1.6, bend)
    m.tube(densify(back, 2.0), TUBE_R, sides, 50.0)
    m.tube([BACK_LOW + (0, YI, 0), BACK_LOW + (0, -YI, 0)], TUBE_R * 0.9, sides, 70.0)
    for sy in (-1, 1):
        m.armrest(sy * YO, lod)
    if lod < 2:
        for sy in (-1, 1):
            # Bolts through the legs into the seat frame, and the back's pivots inside; rivets down through the arms into the legs.
            for at in ((leg_x(FRONT_TOP, FRONT_FOOT, 14.8), 14.8), (leg_x(REAR_TOP, REAR_FOOT, 13.0), 13.0)):
                m.dome((at[0], sy * (YO + TUBE_R + 0.01), at[1]), (0, sy, 0), 0.3, washer=0.42)
            pivot = BACK_FOOT + UP_BACK * 0.9
            m.dome((pivot[0], sy * (YI - TUBE_R - 0.01), pivot[2]), (0, -sy, 0), 0.28, washer=0.4)
            arm = BACK_FOOT + UP_BACK * ((ARM_Z - 1.0 - BACK_FOOT[2]) / UP_BACK[2])
            m.dome((arm[0], sy * (YI - TUBE_R - 0.01), arm[2]), (0, -sy, 0), 0.26)
            for x in (FRONT_TOP[0], REAR_TOP[0]):
                m.dome((x, sy * YO, ARM_Z + 0.005), (0, 0, 1), 0.28)
            for foot in (FRONT_FOOT, REAR_FOOT):
                m.glide((foot[0], sy * (YO - 2.6), BAR_Z), (0, 1, 0), 0.66, 1.7)
    # The webbing: the seat sags where people sat; one of the back's straps has snapped.
    seat_panel = Panel(SEAT_BACK, SEAT_FRONT - SEAT_BACK, (0, 1, 0), float(np.linalg.norm(SEAT_FRONT - SEAT_BACK)), 0.95)
    back_panel = Panel(BACK_LOW, UP_BACK, (0, -1, 0), float(np.linalg.norm(BACK_TOP - BACK_LOW)), 0.6)
    if lod < 2:
        webbing(m, seat_panel, 7, 7, rng, lod)
        webbing(m, back_panel, 7, 7, rng, lod, broken=4, back=True)
    else:
        for panel in (seat_panel, back_panel):
            pts = [panel.p(u, 0.0, TUBE_R + 0.04 + panel.dip(u, 0.0) * 0.6) for u in np.linspace(0, panel.La, 5)]
            x0, y0 = STRIPS[3]
            for k in range(len(pts) - 1):
                p0, p1 = pts[k], pts[k + 1]
                uv = [(x0 + k * 200, y0 + 1), (x0 + k * 200, y0 + 63), (x0 + (k + 1) * 200, y0 + 63), (x0 + (k + 1) * 200, y0 + 1)]
                q = [p0 - panel.B * YI, p0 + panel.B * YI, p1 + panel.B * YI, p1 - panel.B * YI]
                m.quad(*q, uv, panel.N)
                m.quad(*(x - panel.N * STRAP_T for x in (q[0], q[3], q[2], q[1])), [uv[0], uv[3], uv[2], uv[1]], -panel.N)
    return m


# ---------------------------------------------------------------------------------------------------------------------
# Paint
# ---------------------------------------------------------------------------------------------------------------------


def paint():
    """The webbing as woven polypropylene: coloured warp yarns make the stripes, the weft makes fine ribs across. Sun has bleached it unevenly and yellowed the
    white, grime has settled in the weave and the edges, there's mildew in specks and mud splashed up the low straps. The aluminium is dull and spotted with
    oxide, scratched along its length, caked with dried mud low down. The arms are chalky plastic."""
    rng = np.random.default_rng(11)
    YARN = np.zeros((AH, AW), np.int8)  # 0 main, 1 light, 2 accent.
    TINT = np.ones((AH, AW), np.float32)
    HEIGHT = np.zeros((AH, AW), np.float32)
    ROUGH = np.full((AH, AW), 0.6, np.float32)
    METAL = np.zeros((AH, AW), np.float32)
    AO = np.ones((AH, AW), np.float32)
    FADE = np.zeros((AH, AW), np.float32)
    DIRT = np.zeros((AH, AW), np.float32)
    MUD = np.zeros((AH, AW), np.float32)
    COVER = np.zeros((AH, AW), bool)
    BASE = np.zeros((AH, AW, 3), np.float32)
    w, h = STRIP
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp = np.floor(yy / 2.0)  # Two pixels a warp yarn, about 14 to the inch.
    centre = (warp * 2.0 + 1.0) / h  # Each yarn's place across the strap, 0..1, so stripes break on yarns.
    off = np.abs(centre - 0.5)
    stripe_a = np.select([off < 0.045, (off > 0.11) & (off < 0.2)], [2, 1], 0)  # Mostly main, a light band each side of an accent line.
    stripe_b = np.select([(off > 0.16) & (off < 0.27), off > 0.43], [0, 0], 1)  # Mostly light, two main bands and main edges.
    for k, (x0, y0) in enumerate(STRIPS):
        r = np.random.default_rng(300 + k)
        sl = (slice(y0, y0 + h), slice(x0, x0 + w))
        YARN[sl] = stripe_a if k < 8 else stripe_b
        yarn_tone = r.normal(1.0, 0.035, h // 2 + 1)[warp.astype(int)]  # Each warp yarn a touch different.
        slub = 1 + 0.03 * blobs((h, w), 6, 310 + k, aspect=(0.15, 4.0))
        TINT[sl] = yarn_tone * slub
        # Plain weave: the weft passes over and under alternate warp yarns, so bumps sit in a checker.
        weft = np.sin(2 * np.pi * (xx / 3.0 + 0.15 * blobs((h, w), 8, 320 + k)))
        over = np.where(warp % 2 == 0, 1.0, -1.0)
        bump = 0.5 + 0.5 * weft * over
        edge = smooth(0.07, 0.0, np.minimum(yy, h - 1 - yy) / h)
        fray = smooth(0.62, 0.8, blobs((h, w), 2.5, 330 + k, aspect=(0.5, 1.5)) * 0.5 + 0.5) * edge
        HEIGHT[sl] = 0.006 * bump + 0.002 * np.sin(np.pi * (yy % 2.0) / 2.0) - 0.012 * edge
        ROUGH[sl] = 0.58 + 0.16 * bump + 0.15 * fray
        AO[sl] = 0.85 + 0.15 * bump - 0.3 * edge - 0.25 * fray
        along = np.minimum(xx, w - xx) / w  # Near 0.5 is the middle of the strap's length: the seat's middle, where people sat.
        fade = r.uniform(0.3, 0.62) * (0.75 + 0.35 * (blobs((h, w), 60, 340 + k) * 0.5 + 0.5)) * (0.8 + 0.2 * smooth(0.05, 0.3, along))
        FADE[sl] = np.clip(fade, 0, 0.85)
        film = 0.18 + 0.12 * blobs((h, w), 30, 350 + k)
        sat = 0.35 * smooth(0.2, 0.48, along) * np.clip(blobs((h, w), 25, 360 + k) + 0.6, 0, 1)
        weave_dirt = 0.25 * (1 - bump) + 0.45 * edge
        mildew = 0.7 * smooth(0.84, 0.93, blobs((h, w), 0.9, 370 + k) * 0.5 + 0.5) * smooth(0.72, 0.86, blobs((h, w), 40, 380 + k) * 0.5 + 0.5)
        stain = smooth(0.55, 0.75, blobs((h, w), 22, 390 + k, aspect=(0.6, 2.0)) * 0.5 + 0.5) * 0.35
        DIRT[sl] = np.clip(film + sat + weave_dirt * 0.6 + 1.2 * mildew + stain, 0, 1)
        MUD[sl] = 0.6 * smooth(0.88, 0.95, blobs((h, w), 0.5, 395 + k) * 0.5 + 0.5) * (r.random() < 0.3) * smooth(0.35, 0.1, along)
        COVER[sl] = True
    # The tube: four pictures with the same aluminium, and more dried mud in each.
    tw, th = TUBES[0][2], TUBES[0][3]
    alu = np.array((0.62, 0.63, 0.62), np.float32)
    brushed = blobs((th, tw), 1.5, 400, aspect=(0.08, 8.0))
    oxide = np.clip(blobs((th, tw), 5, 401) * 0.5 + 0.5, 0, 1)
    chalk = smooth(0.74, 0.86, blobs((th, tw), 2.5, 402) * 0.5 + 0.5)
    pits = smooth(0.82, 0.9, blobs((th, tw), 0.8, 403) * 0.5 + 0.5)
    scratch = smooth(0.82, 0.92, blobs((th, tw), 1.2, 404, aspect=(0.12, 7.0)) * 0.5 + 0.5)
    grime = np.clip(blobs((th, tw), 25, 405) * 0.5 + 0.45, 0, 1)
    base = alu[None, None, :] * (0.9 + 0.06 * brushed + 0.08 * oxide)[..., None]
    chalk = smooth(0.84, 0.94, blobs((th, tw), 2.5, 402) * 0.5 + 0.5) * 0.5
    pits = smooth(0.88, 0.95, blobs((th, tw), 0.8, 403) * 0.5 + 0.5)
    base = base * (1 - 0.3 * pits[..., None]) * (1 - chalk[..., None]) + np.array((0.7, 0.7, 0.67), np.float32) * chalk[..., None] + 0.08 * scratch[..., None]
    base = base * (1 - 0.35 * grime[..., None])
    rough = 0.35 + 0.2 * oxide + 0.35 * chalk + 0.2 * pits - 0.15 * scratch + 0.2 * grime
    metal = 0.9 - 0.6 * chalk - 0.4 * pits - 0.3 * grime
    mud_noise = blobs((th, tw), 3, 406) * 0.5 + 0.5
    drip = blobs((th, tw), 1.2, 407, aspect=(0.3, 3.0)) * 0.5 + 0.5
    for k, (x0, y0, _, _) in enumerate(TUBES):
        amount = (0.0, 0.3, 0.6, 0.95)[k]
        mud = smooth(1 - amount, 1 - amount + 0.12, 0.65 * mud_noise + 0.35 * drip) if amount else np.zeros((th, tw), np.float32)
        dried = np.clip(blobs((th, tw), 4, 408 + k) * 0.5 + 0.5, 0, 1)
        mudc = np.array((0.24, 0.19, 0.13), np.float32) * (1 - dried[..., None]) + np.array((0.43, 0.37, 0.29), np.float32) * dried[..., None]
        sl = (slice(y0, y0 + th), slice(x0, x0 + tw))
        BASE[sl] = np.clip(base * (1 - mud[..., None]) + mudc * mud[..., None], 0, 1)
        ROUGH[sl] = np.clip(rough * (1 - mud) + 0.92 * mud, 0.05, 1)
        METAL[sl] = np.clip(metal * (1 - mud), 0, 1)
        HEIGHT[sl] = -0.002 * scratch - 0.003 * pits + 0.012 * mud * dried
        COVER[sl] = True
    # The armrests: off-white plastic gone chalky in the sun, greyer where hands rest, scuffed along the edges.
    x0, y0, aw, ah = ARM
    plastic = np.array((0.76, 0.74, 0.66), np.float32)
    uu = np.arange(aw, dtype=np.float32)[None, :] / 24
    hands = np.exp(-((uu - 15.0) / 5.0) ** 2) * np.clip(blobs((ah, aw), 12, 410) + 0.6, 0, 1)
    chalky = np.clip(blobs((ah, aw), 10, 411) * 0.5 + 0.5, 0, 1)
    scuff = 0.5 * smooth(0.88, 0.95, blobs((ah, aw), 1.2, 412, aspect=(0.2, 5.0)) * 0.5 + 0.5)
    col = plastic[None, None, :] * (1 + 0.06 * chalky)[..., None] * (1 - 0.32 * hands[..., None]) * (1 - 0.25 * scuff[..., None])
    col = col * (1 - 0.3 * np.clip(blobs((ah, aw), 25, 413) + 0.2, 0, 1)[..., None])
    sl = (slice(y0, y0 + ah), slice(x0, x0 + aw))
    BASE[sl] = np.clip(col, 0, 1)
    ROUGH[sl] = 0.72 + 0.15 * chalky - 0.2 * hands
    HEIGHT[sl] = 0.003 * blobs((ah, aw), 1.5, 414) - 0.003 * scuff
    COVER[sl] = True
    x0, y0, sw, sh = SWATCH
    for k, (name, c) in enumerate(SWATCHES.items()):
        c0, c1 = x0 + round(k * sw / len(SWATCHES)), x0 + round((k + 1) * sw / len(SWATCHES))
        BASE[y0:y0 + sh, c0:c1] = c
        METAL[y0:y0 + sh, c0:c1] = 0.8 if name == "rivet" else 0.0
        ROUGH[y0:y0 + sh, c0:c1] = 0.45 if name == "rivet" else 0.75
    COVER[y0:y0 + sh, x0:x0 + sw] = True
    webbing_mask = np.zeros((AH, AW), bool)
    for x0, y0 in STRIPS:
        webbing_mask[y0:y0 + h, x0:x0 + w] = True
    fill = tuple(ndi.distance_transform_edt(~COVER, return_distances=False, return_indices=True))
    maps = {}
    for name, pal in PALETTES.items():
        colours = np.array([pal["main"], pal["light"], pal["accent"]], np.float32)
        col = colours[np.clip(YARN, 0, 2)] * TINT[..., None]
        grey = col.mean(-1, keepdims=True)
        bleached = grey * 0.55 + np.array((0.5, 0.48, 0.42), np.float32) * 0.6  # Sun-bleached: greyed, and the white yellowed.
        col = col * (1 - FADE[..., None]) + bleached * FADE[..., None]
        dirtc = np.array((0.2, 0.18, 0.14), np.float32)
        col = col * (1 - 0.6 * DIRT[..., None]) + dirtc * 0.6 * DIRT[..., None]
        mudc = np.array((0.33, 0.27, 0.2), np.float32)
        col = col * (1 - 0.8 * MUD[..., None]) + mudc * 0.8 * MUD[..., None]
        maps[name] = np.where(webbing_mask[..., None], col, BASE)[fill]
    return maps, to_normal(HEIGHT[fill], PPI), ROUGH[fill], METAL[fill], AO[fill]


def twill_full(h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return 0.5 + 0.5 * np.sin((xx + yy) * 2 * np.pi / 5.0)


def fix_winding(p, t, n):
    face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    flip = (face * n.mean(1)).sum(-1) < 0
    p[flip], t[flip], n[flip] = p[flip][:, [0, 2, 1]], t[flip][:, [0, 2, 1]], n[flip][:, [0, 2, 1]]


def write_obj(path, mesh):
    p, t, n = np.array(mesh.p), np.array(mesh.t), np.array(mesh.n)
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
    keep = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1) > 1e-9
    p, t, n = p[keep], t[keep], n[keep]
    fix_winding(p, t, n)
    uv = np.stack((t[..., 0] / AW, 1 - t[..., 1] / AH), -1)
    po, no = p[..., [1, 2, 0]], n[..., [1, 2, 0]]  # Engine X, Y, Z become OBJ Z, X, Y.
    tables, lines, body = ({}, {}, {}), ([], [], []), []

    def index(k, prefix, values):
        key = tuple(np.round(values, 5))
        got = tables[k].get(key)
        if got is None:
            got = len(tables[k]) + 1
            tables[k][key] = got
            lines[k].append(prefix + " ".join(f"{v_:.5f}" for v_ in key) + "\n")
        return got

    for k in range(len(po)):
        body.append("f " + " ".join("%d/%d/%d" % (index(0, "v ", po[k, c]), index(1, "vt ", uv[k, c]), index(2, "vn ", no[k, c])) for c in range(3)) + "\n")
    with open(path, "w", newline="\n") as h:
        h.write("# Generated by Sources/Riverside/lawn-chair-v2/lawn_chair.py\nmtllib lawn_chair.mtl\n")
        for block in lines:
            h.writelines(block)
        h.write("usemtl lawn_chair\n")
        h.writelines(body)
    print(os.path.basename(path), "triangles", len(po), "bounds", p.reshape(-1, 3).min(0).round(2), p.reshape(-1, 3).max(0).round(2), flush=True)
    return len(po)


maps, NORMAL, ROUGH, METAL, AO = paint()
for name, colour in maps.items():
    Image.fromarray((np.clip(colour, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, f"lawn_chair_{name}_color.png"))
Image.fromarray((np.clip(NORMAL * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, "lawn_chair_normal.png"))
for array, kind in ((ROUGH, "rough"), (METAL, "metal"), (AO, "ao")):
    Image.fromarray((np.clip(array, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((AW // 2, AH // 2), Image.BOX).save(os.path.join(MAT_OUT, f"lawn_chair_{kind}.png"))
counts = [write_obj(os.path.join(OUT, f"lawn_chair_lod{k}.obj"), build(k)) for k in range(3)]
with open(os.path.join(OUT, "lawn_chair.mtl"), "w", newline="\n") as h:
    h.write("newmtl lawn_chair\n")
tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
meshes = "\n".join(f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{MODEL}/lawn_chair_lod{k}.obj" {tail} }},' for k in range(3))
for name in PALETTES:
    with open(os.path.join(OUT, f"lawn_chair_{name}.vmdl"), "w", newline="\n") as h:
        h.write(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Riverside/lawn-chair-v2/lawn_chair.py: {counts}
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "lawn_chair.vmat" to = "{MATS}/lawn_chair_{name}.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
{meshes}
				]
			}},
			{{
				_class = "LODGroupList"
				children =
				[
					{{ _class = "LODGroup" switch_threshold = 0.0 meshes = [ "lod0" ] }},
					{{ _class = "LODGroup" switch_threshold = 24.0 meshes = [ "lod1" ] }},
					{{ _class = "LODGroup" switch_threshold = 70.0 meshes = [ "lod2" ] }}
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""")
    with open(os.path.join(MAT_OUT, f"lawn_chair_{name}.vmat"), "w", newline="\n") as h:
        h.write(f"""// Generated by Sources/Riverside/lawn-chair-v2/lawn_chair.py

Layer0
{{
	shader "shaders/complex.shader"
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/lawn_chair_ao.png"
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/lawn_chair_{name}_color.png"
	g_bFogEnabled "1"
	TextureMetalness "{MATS}/lawn_chair_metal.png"
	TextureNormal "{MATS}/lawn_chair_normal.png"
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/lawn_chair_rough.png"
}}
""")
print("triangles", counts, flush=True)
