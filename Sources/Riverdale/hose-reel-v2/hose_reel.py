"""Riverdale's fire hose reel cabinet v2: a red steel cabinet with a glazed door, and behind the glass a reel of red hose, its nozzle in a clip and the valve that feeds it.
Builds the mesh, paints the maps and writes the model with numpy and PIL, as Sources/Riverdale/notice-board-v2/board.py does.

python hose_reel.py <project root>

Engine X comes out of the wall, Y is the viewer's right, Z is up. The origin is on the wall at the cabinet's bottom centre, where the old box's bottom edge was (z 28.5 in
the hall). Same face as the old box, 33 x 35 in, but 5 in deep where the old one was 1.4. The paint's mottle and roughness come from forestbase/scans/metal_plate_02.
"""
import ctypes
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except AttributeError:
    pass

ROOT = sys.argv[1]
MODEL = "models/maps/riverdale/hose_reel_v2"
MATS = "materials/riverdale/hose_reel_v2"
OUT = os.path.join(ROOT, "Assets", *MODEL.split("/"))
MAT_OUT = os.path.join(ROOT, "Assets", *MATS.split("/"))
REVIEW = os.path.join(ROOT, "output", "asset-improvement-20261030", "hose-reel")
SCAN = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")
for folder in (OUT, MAT_OUT, REVIEW):
    os.makedirs(folder, exist_ok=True)

W, H, D = 33.0, 35.0, 4.6  # The body; the door stands proud of it to 4.95.
DOOR_X = 4.95
STILE, BAND, RAIL = 1.6, 7.0, 3.0
WIN_Y0, WIN_Y1, WIN_Z0, WIN_Z1 = -W / 2 + STILE, W / 2 - STILE, RAIL, H - BAND
ATLAS = 2048
PPI_FRONT = 28
REEL = np.array((1.0, -1.0, 15.6))  # The reel's back disc, on its axis.
BACK_X = 0.4  # The cabinet's back, in front of the hall's dado (0.3 in off the wall).
RED = np.array((0.62, 0.075, 0.065), np.float32)
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT = r"C:\Windows\Fonts\arial.ttf"


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def blobs(shape, sigma, seed):
    r = np.random.default_rng(seed).normal(size=(max(4, shape[0] // 4), max(4, shape[1] // 4)))
    r = ndi.gaussian_filter(r, sigma / 4, mode="wrap")
    r = ndi.zoom(r, (shape[0] / r.shape[0], shape[1] / r.shape[1]), order=1)[: shape[0], : shape[1]]
    return r / (r.std() * 2.5 + 1e-6)


def to_normal(height, ppi):
    dr, dc = np.gradient(height)
    n = np.stack((-dc * ppi, dr * ppi, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


_CLEAN = {}


def scan(name, shape, inches):
    """A forestbase scan at about true scale (metal_plate_02 covers about 40 in) on a canvas `inches` wide.
    The scan is a wall of riveted plates, so its seams are closed and opened away first: that leaves the stains, blotches and wear without the grid."""
    if name not in _CLEAN:
        g = np.asarray(Image.open(os.path.join(SCAN, name)).convert("L"), np.float32) / 255
        for size in ((1, 17), (17, 1)):
            g = ndi.grey_closing(g, size=size)
        for size in ((1, 11), (11, 1)):
            g = ndi.grey_opening(g, size=size)
        # Each plate had its own tone, and the square filters leave blocks: keep only what's smaller than a plate, softened.
        g = ndi.gaussian_filter(g, 2.5) - ndi.gaussian_filter(g, 40) + g.mean()
        _CLEAN[name] = Image.fromarray(np.clip(g * 255, 0, 255).astype(np.uint8))
    px = max(8, round(shape[1] * 40.0 / inches))
    tile = np.asarray(_CLEAN[name].resize((px, px), Image.LANCZOS), np.float32) / 255
    return np.tile(tile, (shape[0] // px + 1, shape[1] // px + 1))[: shape[0], : shape[1]]


# ---------------------------------------------------------------------------------------------------------------------
# Atlas: the front (unique, so its wear and label sit where they belong), a shared paint field for the other faces, the cabinet's back inside, the hose, swatches
# ---------------------------------------------------------------------------------------------------------------------

GUTTER = 6
rects = {"front": (round(W * PPI_FRONT), round(H * PPI_FRONT)), "paint": (480, 480), "back": (round((W - 1) * 16), round((H - 1) * 16)), "hose": (512, 64), "swatch": (320, 32)}
place = {}
_x, _y, _shelf = 0, 0, 0
for name, (rw, rh) in sorted(rects.items(), key=lambda kv: -kv[1][1]):
    if _x + rw + GUTTER > ATLAS:
        _x, _y, _shelf = 0, _y + _shelf + GUTTER, 0
    place[name] = (_x, _y, rw, rh)
    _x += rw + GUTTER
    _shelf = max(_shelf, rh)
assert _y + _shelf <= ATLAS, "atlas full"
COLOUR = np.zeros((ATLAS, ATLAS, 3), np.float32)
NORMAL = np.zeros((ATLAS, ATLAS, 3), np.float32)
NORMAL[..., 2] = 1
ROUGH = np.full((ATLAS, ATLAS), 0.5, np.float32)
METAL = np.zeros((ATLAS, ATLAS), np.float32)
AO = np.ones((ATLAS, ATLAS), np.float32)
COVER = np.zeros((ATLAS, ATLAS), bool)


def put(name, colour, normal=None, rough=None, metal=None, ao=None):
    x, y, w, h = place[name]
    for arr, value in ((COLOUR, colour), (NORMAL, normal), (ROUGH, rough), (METAL, metal), (AO, ao)):
        if value is not None:
            arr[y : y + h, x : x + w] = value
    COVER[y : y + h, x : x + w] = True


def paint_field(h, w, ppi, seed, inches):
    """Red powder coat: the scan's mottle and roughness at true scale, a fine orange peel, and broad handling."""
    mottle = scan("metal_plate_02_diff.jpg", (h, w), inches)
    mottle = (mottle - mottle.mean()) / (mottle.std() + 1e-6)
    sr = scan("metal_plate_02_rough.jpg", (h, w), inches)
    colour = RED[None, None, :] * (1 + 0.03 * np.clip(mottle, -2.5, 2.5) + 0.04 * blobs((h, w), 60, seed))[..., None]
    rough = 0.42 + 0.16 * (sr - sr.mean())
    peel = blobs((h, w), 1.2, seed + 1)
    return colour, rough, 0.0015 * peel + 0.002 * np.clip(mottle, -2, 2) * 0.2


def paint_front():
    x, y, w, h = place["front"]
    colour, rough, height = paint_field(h, w, PPI_FRONT, 11, W)
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    yy = cols / PPI_FRONT - W / 2
    zz = (h - rows) / PPI_FRONT
    # The label band: white print on the red, with the reel pictogram.
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_BOLD, round(2.1 * PPI_FRONT))
    d.text((round((W / 2 + 2.2) * PPI_FRONT), round(BAND / 2 * PPI_FRONT)), "FIRE HOSE REEL", font=f, fill=255, anchor="mm")
    # The pictogram: a reel of coils, the hose run off its bottom to a nozzle.
    P = PPI_FRONT
    cx, cy, r = 4.0 * P, BAND / 2 * P - 0.3 * P, 2.2 * P
    line = round(0.24 * P)
    for k, rr in enumerate((r, r * 0.72, r * 0.46)):
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=255, width=line if k else round(0.3 * P))
    d.ellipse((cx - 0.3 * P, cy - 0.3 * P, cx + 0.3 * P, cy + 0.3 * P), fill=255)
    hose_y = cy + r - 0.15 * P
    d.line((cx, hose_y, cx + r + 1.3 * P, hose_y), fill=255, width=round(0.3 * P))
    x0 = cx + r + 1.3 * P
    d.polygon([(x0, hose_y - 0.28 * P), (x0 + 0.9 * P, hose_y - 0.12 * P), (x0 + 0.9 * P, hose_y + 0.12 * P), (x0, hose_y + 0.28 * P)], fill=255)
    small = ImageFont.truetype(FONT, round(0.62 * PPI_FRONT))
    d.text((round((W / 2 + 2.2) * PPI_FRONT), round((BAND / 2 + 1.75) * PPI_FRONT)), "Open door - open valve - run out hose", font=small, fill=230, anchor="mm")
    # Small print on the bottom rail.
    d.text((round(2.2 * PPI_FRONT), round((H - RAIL / 2) * PPI_FRONT)), "Inspected  03 / 26   RD-FHR-07", font=small, fill=210, anchor="lm")
    ink = ndi.gaussian_filter(np.asarray(img, np.float32) / 255, 0.6)
    white = np.array((0.88, 0.88, 0.85), np.float32)
    colour = colour * (1 - ink[..., None]) + white * ink[..., None]
    rough = rough * (1 - ink) + 0.5 * ink
    # Wear: soft, where hands and knocks go: round the handle, the door's lower edge, the corners.
    hand = np.exp(-(((yy - (W / 2 - 2.0)) / 2.4) ** 2 + ((zz - 15.0) / 4.0) ** 2))
    low = smooth(4.0, 0.0, zz)
    corners = np.exp(-(np.minimum(np.abs(yy - W / 2), np.abs(yy + W / 2)) ** 2 + np.minimum(zz, np.abs(zz - H)) ** 2) / 3.0)
    wear = np.clip(blobs((h, w), 10, 12) * 0.5 + 0.5, 0, 1) * np.clip(0.55 * hand + 0.5 * low + 0.6 * corners, 0, 1)
    chips = smooth(0.62, 0.8, wear)
    steel = np.array((0.36, 0.36, 0.37), np.float32)
    colour = colour * (1 - 0.22 * wear[..., None]) * (1 - chips[..., None]) + steel * chips[..., None]
    rough = rough + 0.12 * wear + 0.1 * chips
    metal = 0.6 * chips
    height = height - 0.004 * chips
    # Dust on the band's top and grime low down.
    grime = smooth(3.0, 0.0, zz) * np.clip(blobs((h, w), 30, 13) + 0.6, 0, 1)
    colour = colour * (1 - 0.18 * grime[..., None])
    # The door's seam and the glass's rubber bead are geometry; the window area here is never seen, so it's plain.
    put("front", np.clip(colour, 0, 1), to_normal(height, PPI_FRONT), np.clip(rough, 0.1, 1), metal, 1.0)


def paint_shared():
    x, y, w, h = place["paint"]
    colour, rough, height = paint_field(h, w, 12, 21, 40.0)
    put("paint", np.clip(colour, 0, 1), to_normal(height, 12), np.clip(rough, 0.1, 1), 0.0, 1.0)
    # The back, inside: the reel's shadow on it, and the cabinet's corners darker.
    x, y, w, h = place["back"]
    colour, rough, height = paint_field(h, w, 16, 22, W)
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    yy, zz = cols / 16 - (W - 1) / 2, (h - rows) / 16 + 0.5
    rr = np.hypot(yy - REEL[1], zz - REEL[2])
    shade = 1 - 0.55 * smooth(11.5, 8.5, rr) - 0.25 * smooth(4.0, 0.0, np.minimum.reduce((yy + (W - 1) / 2, (W - 1) / 2 - yy, zz - 0.5, H - 0.5 - zz)))
    put("back", np.clip(colour * 0.8 * shade[..., None], 0, 1), to_normal(height, 16), np.clip(rough, 0.1, 1), 0.0, np.clip(shade, 0, 1))
    # The hose: a woven jacket, red, a little dusty along its top.
    x, y, w, h = place["hose"]
    rows, cols = np.mgrid[0:h, 0:w].astype(np.float32)
    weave = 0.5 + 0.5 * np.sin(cols * 2 * np.pi / 6) * np.sin(rows * 2 * np.pi / 6)
    colour = np.array((0.7, 0.09, 0.07), np.float32)[None, None, :] * (0.86 + 0.14 * weave)[..., None] * (1 + 0.06 * blobs((h, w), 20, 23))[..., None]
    put("hose", np.clip(colour, 0, 1), to_normal(0.004 * weave, 64), 0.72 - 0.1 * weave, 0.0, 1.0)


SWATCH = {"red": tuple(RED), "dark": (0.06, 0.06, 0.065), "brass": (0.72, 0.52, 0.22), "chrome": (0.7, 0.7, 0.72), "grey": (0.34, 0.35, 0.36), "white": (0.86, 0.86, 0.84), "rubber": (0.03, 0.03, 0.03), "nozzle_red": (0.7, 0.08, 0.06)}


def paint_swatches():
    x, y, w, h = place["swatch"]
    colour = np.zeros((h, w, 3), np.float32)
    rough = np.full((h, w), 0.4, np.float32)
    metal = np.zeros((h, w), np.float32)
    step = w / len(SWATCH)
    for k, (name, c) in enumerate(SWATCH.items()):
        c0, c1 = round(k * step), round((k + 1) * step)
        colour[:, c0:c1] = c
        if name in ("brass", "chrome"):
            metal[:, c0:c1], rough[:, c0:c1] = 0.85, 0.3
        if name == "rubber":
            rough[:, c0:c1] = 0.8
    put("swatch", colour, None, rough, metal, 1.0)


def swatch_uv(name):
    x, y, w, h = place["swatch"]
    k = list(SWATCH).index(name)
    return np.array((x + (k + 0.5) * w / len(SWATCH), y + h / 2), np.float32)


# ---------------------------------------------------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------------------------------------------------


class Mesh:
    def __init__(self):
        self.sections = {"hose_reel": ([], [], []), "hose_reel_glass": ([], [], [])}

    def tri(self, p, t, n, mat="hose_reel"):
        ps, ts, ns = self.sections[mat]
        ps.append(np.asarray(p, float))
        ts.append(np.asarray(t, float))
        ns.append(np.broadcast_to(np.asarray(n, float), (3, 3)) if np.ndim(n) == 1 else np.asarray(n, float))

    def quad(self, a, b, c, d, uvs, normal, mat="hose_reel"):
        a, b, c, d = (np.asarray(v_, float) for v_ in (a, b, c, d))
        n = np.asarray(normal, float)
        self.tri((a, b, c), (uvs[0], uvs[1], uvs[2]), n, mat)
        self.tri((a, c, d), (uvs[0], uvs[2], uvs[3]), n, mat)

    def box(self, lo, hi, uv_of, skip=()):
        """An axis box; uv_of(face, point) gives each corner's texel."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        faces = {
            "+x": ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0)),
            "-x": ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (-1, 0, 0)),
            "+y": ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (0, 1, 0)),
            "-y": ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)),
            "+z": ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)),
            "-z": ((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0), (0, 0, -1)),
        }
        for name, (a, b, c, d, n) in faces.items():
            if name in skip:
                continue
            self.quad(a, b, c, d, [uv_of(name, np.array(p)) for p in (a, b, c, d)], n)

    def lathe(self, start, axis, profile, uv, seg=12, cap=True):
        axis = np.asarray(axis, float) / np.linalg.norm(axis)
        ref = np.array((0.0, 0.0, 1.0)) if abs(axis[2]) < 0.9 else np.array((1.0, 0.0, 0.0))
        e1 = np.cross(axis, ref)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        ang = np.linspace(0, 2 * np.pi, seg + 1)
        rings = np.array([[np.asarray(start) + axis * h + (e1 * np.cos(a) + e2 * np.sin(a)) * r for a in ang] for r, h in profile])
        for j in range(len(profile) - 1):
            slope = (profile[j][0] - profile[j + 1][0]) / max(1e-6, abs(profile[j + 1][1] - profile[j][1]))
            for k in range(seg):
                na, nb = [(e1 * np.cos(a) + e2 * np.sin(a)) + axis * slope for a in (ang[k], ang[k + 1])]
                na, nb = na / np.linalg.norm(na), nb / np.linalg.norm(nb)
                a_, b_, c_, d_ = rings[j, k], rings[j, k + 1], rings[j + 1, k + 1], rings[j + 1, k]
                if np.linalg.norm(np.cross(b_ - a_, c_ - a_)) > 1e-9:
                    self.tri((a_, b_, c_), (uv, uv, uv), (na, nb, nb))
                if np.linalg.norm(np.cross(c_ - a_, d_ - a_)) > 1e-9:
                    self.tri((a_, c_, d_), (uv, uv, uv), (na, nb, na))
        if cap:
            for j, sign in ((0, -1), (len(profile) - 1, 1)):
                if profile[j][0] > 1e-6:
                    centre = np.asarray(start) + axis * profile[j][1]
                    for k in range(seg):
                        self.tri((centre, rings[j, k], rings[j, k + 1]), (uv, uv, uv), axis * sign)

    def torus(self, centre, axis, radius, tube, uv_box, seg=24, sides=6, turn=0.0):
        """A ring of hose round an axis. Its UVs run along the hose's texture."""
        axis = np.asarray(axis, float) / np.linalg.norm(axis)
        e1 = np.cross(axis, (0, 0, 1)) if abs(axis[2]) < 0.9 else np.array((1.0, 0, 0))
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        x, y, w, h = uv_box
        pts, nor, uvs = [], [], []
        for i in range(seg + 1):
            a = 2 * np.pi * i / seg + turn
            radial = e1 * np.cos(a) + e2 * np.sin(a)
            row_p, row_n, row_t = [], [], []
            for j in range(sides + 1):
                b = 2 * np.pi * j / sides
                n = radial * np.cos(b) + axis * np.sin(b)
                row_p.append(np.asarray(centre) + radial * radius + n * tube)
                row_n.append(n)
                row_t.append((x + w * (i / seg) * 0.98, y + h * j / sides))
            pts.append(row_p)
            nor.append(row_n)
            uvs.append(row_t)
        for i in range(seg):
            for j in range(sides):
                idx = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
                p = [pts[a][b] for a, b in idx]
                n = [nor[a][b] for a, b in idx]
                t = [uvs[a][b] for a, b in idx]
                self.tri((p[0], p[1], p[2]), (t[0], t[1], t[2]), (n[0], n[1], n[2]))
                self.tri((p[0], p[2], p[3]), (t[0], t[2], t[3]), (n[0], n[2], n[3]))

    def sweep(self, path, tube, uv_box, sides=6):
        """A tube along a path of points."""
        path = [np.asarray(p, float) for p in path]
        x, y, w, h = uv_box
        rings = []
        for k, p in enumerate(path):
            t = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)])
            t /= np.linalg.norm(t)
            e1 = np.cross(t, (1.0, 0, 0)) if abs(t[0]) < 0.9 else np.cross(t, (0, 0, 1.0))
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(t, e1)
            rings.append([(p + (e1 * np.cos(b) + e2 * np.sin(b)) * tube, e1 * np.cos(b) + e2 * np.sin(b)) for b in np.linspace(0, 2 * np.pi, sides + 1)])
        for k in range(len(path) - 1):
            for j in range(sides):
                (a, na), (b, nb) = rings[k][j], rings[k][j + 1]
                (c, nc), (d, nd) = rings[k + 1][j + 1], rings[k + 1][j]
                ta, tb = (x + w * k / len(path), y + h * j / sides), (x + w * k / len(path), y + h * (j + 1) / sides)
                tc, td = (x + w * (k + 1) / len(path), y + h * (j + 1) / sides), (x + w * (k + 1) / len(path), y + h * j / sides)
                self.tri((a, b, c), (ta, tb, tc), (na, nb, nc))
                self.tri((a, c, d), (ta, tc, td), (na, nc, nd))


def spot(name):
    """A swatch as a one-texel UV box, for the sweeps and tori."""
    u, v_ = swatch_uv(name)
    return (u, v_, 1, 1)


def smooth_path(points, per):
    """A Catmull-Rom curve through the points, `per` steps a span."""
    P = [np.asarray(p, float) for p in points]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def front_uv(face, p):
    x, y, w, h = place["front"]
    return (x + (p[1] + W / 2) * PPI_FRONT, y + (H - p[2]) * PPI_FRONT)


def paint_uv(face, p):
    """The shared paint field, by the face's plane, in inches."""
    x, y, w, h = place["paint"]
    if face in ("+x", "-x"):
        a, b = p[1] + W / 2, p[2]
    elif face in ("+y", "-y"):
        a, b = p[0] * 3, p[2]
    else:
        a, b = p[1] + W / 2, p[0] * 3
    return (x + (a % 40) * 12, y + h - (b % 40) * 12)


def build(lod):
    m = Mesh()
    # The body: a shell open at the front, its outside and its inside.
    t = 0.12
    m.box((0.0, -W / 2, 0.0), (D, W / 2, t), paint_uv, skip=("+x", "-x"))
    m.box((0.0, -W / 2, H - t), (D, W / 2, H), paint_uv, skip=("+x", "-x"))
    m.box((0.0, -W / 2, 0.0), (D, -W / 2 + t, H), paint_uv, skip=("+x", "-x"))
    m.box((0.0, W / 2 - t, 0.0), (D, W / 2, H), paint_uv, skip=("+x", "-x"))
    bx, by, bw, bh = place["back"]
    m.quad((BACK_X, -W / 2 + 0.5, 0.5), (BACK_X, W / 2 - 0.5, 0.5), (BACK_X, W / 2 - 0.5, H - 0.5), (BACK_X, -W / 2 + 0.5, H - 0.5), [(bx, by + bh), (bx + bw, by + bh), (bx + bw, by), (bx, by)], (1, 0, 0))
    # The door: band, rail and stiles standing proud, its edge bevelled, and the glass between.
    for lo, hi in (((D, -W / 2, H - BAND), (DOOR_X, W / 2, H)), ((D, -W / 2, 0.0), (DOOR_X, W / 2, RAIL)), ((D, -W / 2, RAIL), (DOOR_X, WIN_Y0, H - BAND)), ((D, WIN_Y1, RAIL), (DOOR_X, W / 2, H - BAND))):
        m.box(lo, hi, lambda f, p: front_uv(f, p) if f == "+x" else paint_uv(f, p), skip=("-x",))
    dark = swatch_uv("rubber")
    bead = 0.28
    for lo, hi in (((DOOR_X - 0.1, WIN_Y0, WIN_Z1 - bead), (DOOR_X + 0.06, WIN_Y1, WIN_Z1)), ((DOOR_X - 0.1, WIN_Y0, WIN_Z0), (DOOR_X + 0.06, WIN_Y1, WIN_Z0 + bead)),
                   ((DOOR_X - 0.1, WIN_Y0, WIN_Z0), (DOOR_X + 0.06, WIN_Y0 + bead, WIN_Z1)), ((DOOR_X - 0.1, WIN_Y1 - bead, WIN_Z0), (DOOR_X + 0.06, WIN_Y1, WIN_Z1))):
        m.box(lo, hi, lambda f, p: dark, skip=("-x",))
    gx = DOOR_X - 0.06
    g = swatch_uv("white")
    m.quad((gx, WIN_Y0, WIN_Z0), (gx, WIN_Y1, WIN_Z0), (gx, WIN_Y1, WIN_Z1), (gx, WIN_Y0, WIN_Z1), [g, g, g, g], (1, 0, 0), mat="hose_reel_glass")
    # Hinges on the left, the lock on the right.
    for z in (5.0, H - 5.0):
        m.lathe((DOOR_X + 0.15, -W / 2 - 0.05, z - 1.4), (0, 0, 1), [(0.0, 0.0), (0.22, 0.0), (0.22, 2.8), (0.0, 2.8)], swatch_uv("chrome"), seg=8)
    m.lathe((DOOR_X, W / 2 - 0.9, 16.0), (1, 0, 0), [(0.0, 0.0), (0.55, 0.0), (0.55, 0.18), (0.32, 0.22), (0.3, 0.6), (0.0, 0.62)], swatch_uv("chrome"), seg=10)
    m.box((DOOR_X + 0.55, W / 2 - 1.05, 14.6), (DOOR_X + 0.82, W / 2 - 0.75, 17.4), lambda f, p: swatch_uv("chrome"))
    if lod >= 2:
        return m
    # Inside: the reel standing off the back, its axis out of the wall.
    centre = REEL.copy()
    red = swatch_uv("red")
    m.lathe(centre, (1, 0, 0), [(0.0, 0.0), (10.6, 0.0), (10.6, 0.22), (0.0, 0.22)], red, seg=48)
    m.lathe(centre + (0.22, 0, 0), (1, 0, 0), [(3.1, 0.0), (3.1, 3.0)], red, seg=24, cap=False)
    m.lathe(centre + (3.1, 0, 0), (1, 0, 0), [(0.0, 0.0), (1.4, 0.0), (1.4, 0.3), (0.7, 0.42), (0.0, 0.42)], swatch_uv("grey"), seg=24)
    # Hose wound on it: rings across the drum's width, layer on layer; the outer layer's last turn is the hose running off.
    hose = place["hose"]
    if lod == 0:
        for layer, r in enumerate((3.55, 4.4, 5.25, 6.1, 6.95, 7.8, 8.65)):
            for k, x in enumerate((0.82, 1.62, 2.42, 3.2)):
                if layer == 6 and k == 3:
                    continue
                m.torus(centre + (x, 0, 0), (1, 0, 0), r, 0.42, hose, seg=30, sides=6, turn=layer * 0.4 + k)
    else:
        for r in (5.0, 7.6):
            m.torus(centre + (1.9, 0, 0), (1, 0, 0), r, 1.6, hose, seg=16, sides=5)
    # The front flange: an open rim on three spokes, so the hose shows.
    m.torus(centre + (3.5, 0, 0), (1, 0, 0), 10.35, 0.24, spot("red"), seg=72 if lod == 0 else 36, sides=5)
    for k in range(3):
        a = np.radians(90 + 120 * k)
        direction = np.array((0.0, np.cos(a), np.sin(a)))
        m.sweep([centre + (3.5, 0, 0) + direction * 1.2, centre + (3.5, 0, 0) + direction * 10.2], 0.22, spot("red"), sides=5)
    # The hose off the reel's top to the nozzle, hung in a clip on the right. Its cut end is buried in the turn beside it.
    tip = centre + np.array((2.4, 13.4, 0.5))
    path = [centre + (2.42, -3.0, 8.11), centre + (3.2, -0.5, 8.64), centre + (3.1, 2.5, 8.9), centre + (2.8, 7.5, 7.6), centre + (2.5, 11.4, 4.6), centre + (2.4, 13.2, 1.6), tip]
    m.sweep(smooth_path(path, 6 if lod == 0 else 2), 0.42, hose, sides=7 if lod == 0 else 5)
    m.lathe(tip, (0, 0, -1), [(0.42, 0.0), (0.6, 0.3), (0.62, 2.6), (0.5, 3.0), (0.5, 3.6), (0.34, 4.1), (0.0, 4.2)], swatch_uv("rubber"), seg=12)
    m.lathe(tip + (0, 0, -4.2), (0, 0, -1), [(0.34, 0.0), (0.4, 0.4), (0.3, 1.3), (0.0, 1.35)], swatch_uv("nozzle_red"), seg=12)
    clip_z = tip[2] - 3.2
    m.box((BACK_X, tip[1] - 0.35, clip_z - 0.3), (tip[0] - 0.55, tip[1] + 0.35, clip_z + 0.3), lambda f, p: swatch_uv("dark"))
    m.torus((tip[0], tip[1], clip_z), (0, 0, 1), 0.72, 0.12, spot("dark"), seg=14, sides=4)
    # The feed: down from the top through a brass valve with a red handwheel, then behind the reel to its hub.
    vx, vy, vz = 2.2, -13.0, 25.0
    brass = swatch_uv("brass")
    m.lathe((vx, vy, H), (0, 0, -1), [(0.6, 0.0), (0.6, H - vz - 1.0)], brass, seg=10, cap=False)
    m.lathe((vx, vy, vz + 1.2), (0, 0, -1), [(0.0, 0.0), (0.95, 0.0), (0.95, 0.3), (0.8, 0.45), (0.8, 1.95), (0.95, 2.1), (0.95, 2.4), (0.0, 2.4)], brass, seg=12)
    m.lathe((vx, vy, vz), (1, 0, 0), [(0.0, 0.0), (0.3, 0.0), (0.3, 1.7), (0.0, 1.7)], brass, seg=8)
    wheel = np.array((vx + 1.75, vy, vz))
    m.torus(wheel, (1, 0, 0), 1.55, 0.19, spot("red"), seg=20, sides=5)
    for k in range(3):
        a = np.radians(30 + 120 * k)
        m.sweep([wheel, wheel + np.array((0.0, np.cos(a), np.sin(a))) * 1.5], 0.13, spot("red"), sides=4)
    feed = [(vx, vy, vz - 1.2), (vx, vy, 21.5), (1.2, -13.2, 19.6), (0.5, -11.8, 18.2), (0.5, -6.0, 16.2), (0.5, REEL[1] - 1.0, REEL[2])]
    m.sweep(smooth_path(feed, 5 if lod == 0 else 2), 0.45, spot("red"), sides=8)
    return m


def fix_winding(p, t, n):
    face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    flip = (face * n.mean(1)).sum(-1) < 0
    p[flip], t[flip], n[flip] = p[flip][:, [0, 2, 1]], t[flip][:, [0, 2, 1]], n[flip][:, [0, 2, 1]]
    return int(flip.sum())


def write_obj(path, mesh):
    tables, lines, body, total = ({}, {}, {}), ([], [], []), [], 0

    def index(k, prefix, values):
        key = tuple(np.round(values, 5))
        got = tables[k].get(key)
        if got is None:
            got = len(tables[k]) + 1
            tables[k][key] = got
            lines[k].append(prefix + " ".join(f"{v_:.5f}" for v_ in key) + "\n")
        return got

    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for mat, (ps, ts, ns) in mesh.sections.items():
        if not ps:
            continue
        p, t, n = np.array(ps), np.array(ts), np.array(ns)
        fix_winding(p, t, n)
        uv = np.stack((t[..., 0] / ATLAS, 1 - t[..., 1] / ATLAS), -1)
        po, no = p[..., [1, 2, 0]], n[..., [1, 2, 0]]  # Engine X, Y, Z become OBJ Z, X, Y.
        body.append(f"usemtl {mat}\n")
        for k in range(len(po)):
            body.append("f " + " ".join("%d/%d/%d" % (index(0, "v ", po[k, c]), index(1, "vt ", uv[k, c]), index(2, "vn ", no[k, c])) for c in range(3)) + "\n")
        total += len(po)
        lo, hi = np.minimum(lo, p.reshape(-1, 3).min(0)), np.maximum(hi, p.reshape(-1, 3).max(0))
    with open(path, "w", newline="\n") as h:
        h.write("# Generated by Sources/Riverdale/hose-reel-v2/hose_reel.py\nmtllib hose_reel.mtl\n")
        for block in lines:
            h.writelines(block)
        h.writelines(body)
    print(os.path.basename(path), "triangles", total, "bounds", lo.round(2), hi.round(2), flush=True)
    return total


paint_front()
paint_shared()
paint_swatches()
fill = tuple(ndi.distance_transform_edt(~COVER, return_distances=False, return_indices=True))
COLOUR, NORMAL, ROUGH, METAL, AO = COLOUR[fill], NORMAL[fill], ROUGH[fill], METAL[fill], AO[fill]
Image.fromarray((np.clip(COLOUR, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, "hose_reel_color.png"))
Image.fromarray((np.clip(NORMAL * 0.5 + 0.5, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(MAT_OUT, "hose_reel_normal.png"))
for array, name in ((ROUGH, "rough"), (METAL, "metal"), (AO, "ao")):
    Image.fromarray((np.clip(array, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((1024, 1024), Image.BOX).save(os.path.join(MAT_OUT, f"hose_reel_{name}.png"))
counts = [write_obj(os.path.join(OUT, f"hose_reel_lod{k}.obj"), build(k)) for k in range(3)]
with open(os.path.join(OUT, "hose_reel.mtl"), "w", newline="\n") as h:
    h.write("newmtl hose_reel\nnewmtl hose_reel_glass\n")
tail = 'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] }'
meshes = "\n".join(f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{MODEL}/hose_reel_lod{k}.obj" {tail} }},' for k in range(3))
with open(os.path.join(OUT, "hose_reel.vmdl"), "w", newline="\n") as h:
    h.write(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Sources/Riverdale/hose-reel-v2/hose_reel.py
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
							{{ from = "hose_reel.vmat" to = "{MATS}/hose_reel.vmat" }},
							{{ from = "hose_reel_glass.vmat" to = "{MATS}/hose_reel_glass.vmat" }}
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
					{{ _class = "LODGroup" switch_threshold = 30.0 meshes = [ "lod1" ] }},
					{{ _class = "LODGroup" switch_threshold = 80.0 meshes = [ "lod2" ] }}
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
with open(os.path.join(MAT_OUT, "hose_reel.vmat"), "w", newline="\n") as h:
    h.write(f"""// Generated by Sources/Riverdale/hose-reel-v2/hose_reel.py

Layer0
{{
	shader "shaders/complex.shader"
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{MATS}/hose_reel_ao.png"
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{MATS}/hose_reel_color.png"
	g_bFogEnabled "1"
	TextureMetalness "{MATS}/hose_reel_metal.png"
	TextureNormal "{MATS}/hose_reel_normal.png"
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{MATS}/hose_reel_rough.png"
}}
""")
with open(os.path.join(MAT_OUT, "hose_reel_glass.vmat"), "w", newline="\n") as h:
    h.write("""// Generated by Sources/Riverdale/hose-reel-v2/hose_reel.py: the door's glass, as Tools/zombies_workbench.py's jars are made

Layer0
{
	shader "shaders/complex.shader"
	F_SPECULAR 1
	F_TRANSLUCENT 1
	TextureColor "[0.80 0.84 0.82 1.0]"
	TextureTranslucency "[0.16 0.16 0.16 1.0]"
	TextureRoughness "[0.05 0.05 0.05 1.0]"
	g_flMetalness "0.000"
	g_bFogEnabled "1"
}
""")
print("triangles", counts, flush=True)
