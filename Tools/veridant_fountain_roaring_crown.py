"""Assemble the Veridant forecourt fountain's roaring-lion crown.

Two mirrored bronze lions from "Lion Statue" by beachmouse (CC BY 4.0), prepared and baked by
Tools/veridant_roaring_lion_blender.py, a carved limestone pier (round moulded cap, flaring shaft with
a framed acanthus panel on each open face and fluted corners, square plinth) and a cast bronze base
fitted to the lions' footprint. Writes three LOD OBJs, the vmdl, the lion and base texture sets and
their vmats.

python -I Tools/veridant_fountain_roaring_crown.py <lion work dir> [assets dir for a trial copy]
(Python with numpy, scipy, scikit-image and Pillow.)

Local axes: X along the lions (FORWARD in the scene), Y across them (LEFT), Z up, in the fountain
bowl object's space. Each lion's rump faces the pier and its head looks outward.
"""
import json
import shutil
import sys
from math import pi
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage import measure

ROOT = Path(__file__).resolve().parents[1]
# An optional second argument writes a trial copy of the Assets tree somewhere else.
ASSETS = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "Assets"
NAME = "veridant_fountain_roaring_crown"
FOLDER = ASSETS / "models/props/shared" / NAME
TEXTURES = ASSETS / "materials/veridant/fountain_roaring"
TEXTURE_PATH = "materials/veridant/fountain_roaring"
FORWARD = np.array((.6, -.8, 0.))
LEFT = np.array((.8, .6, 0.))
BASIS = np.column_stack((FORWARD, LEFT, (0., 0., 1.)))
LION_SHIFT = -2.0          # the baked lion's rump starts at x = 5.4; bring its haunch against the pier
LION_SCALE = 1.06          # scaled about the rump's base so the heads reach the prototype's height
LION_PIVOT = np.array((5.4, 0., 49.25))
BASE_TOP = 49.6
UV_TILE = 24.0
LION_MATERIAL, BASE_MATERIAL, STONE_MATERIAL = "roaring_lion_bronze", "roaring_base_bronze", "roaring_limestone"


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------- mesh
class Part:
    """Positions (V, 3), triangles (T, 3), per-corner UVs (T, 3, 2) and normals (T, 3, 3)."""

    def __init__(self, name, material, positions, triangles, uvs, normals):
        self.name, self.material = name, material
        self.positions, self.triangles = np.asarray(positions, float), np.asarray(triangles, int)
        self.uvs, self.normals = np.asarray(uvs, float), np.asarray(normals, float)

    @classmethod
    def per_vertex(cls, name, material, positions, triangles, uvs, normals):
        t = np.asarray(triangles, int)
        return cls(name, material, positions, t, np.asarray(uvs)[t], np.asarray(normals)[t])

    def mirrored(self, name):
        flip = np.array((-1., 1., 1.))
        order = [0, 2, 1]
        return Part(name, self.material, self.positions * flip, self.triangles[:, order],
                    self.uvs[:, order], (self.normals * flip)[:, order])


def face_normals(p, t):
    return np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])


def vertex_normals(p, t, seams=()):
    """Area-weighted vertex normals; each seam is a pair of index arrays that share their normals."""
    n = np.zeros_like(p)
    fn = face_normals(p, t)
    for k in range(3):
        np.add.at(n, t[:, k], fn)
    for a, b in seams:
        s = n[a] + n[b]
        n[a] = s
        n[b] = s
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def drop_degenerate(t, p):
    area = np.linalg.norm(face_normals(p, t), axis=1)
    return t[area > 1e-9]


def grid_triangles(rows, cols, keep=None):
    """Quads between rows (bottom to top) and columns (counter-clockwise seen from above)."""
    r, c = np.meshgrid(np.arange(rows - 1), np.arange(cols - 1), indexing="ij")
    a = (r * cols + c).ravel()
    b, d = a + 1, a + cols
    e = d + 1
    if keep is not None:
        k = keep.ravel()
        a, b, d, e = a[k], b[k], d[k], e[k]
    return np.concatenate([np.column_stack((a, b, e)), np.column_stack((a, e, d))])


# ---------------------------------------------------------------------------------------------- pier
N_SHAFT = 3.4
PANEL_X = 0.74                                    # the panel patch spans |x| < PANEL_X * rx
FIELD_Z = (52.6, 66.4)                            # recessed acanthus field
PATCH_Z = (52.0, 67.0)                            # patch rows, also shaft rows
SHAFT_Z = (51.5, 67.5)
FLUTE_W, FLUTE_DEPTH = 0.42, 0.22


def shaft_size(z):
    t = np.clip((np.asarray(z, float) - SHAFT_Z[0]) / (SHAFT_Z[1] - SHAFT_Z[0]), 0, 1) ** 2.2
    return 4.8 + 3.1 * t, 6.2 + 2.4 * t


def superellipse(rx, ry, n, theta):
    c, s = np.cos(theta), np.sin(theta)
    return rx * np.sign(c) * np.abs(c) ** (2 / n), ry * np.sign(s) * np.abs(s) ** (2 / n)


def outward(rx, ry, n, theta):
    c, s = np.cos(theta), np.sin(theta)
    gx = np.sign(c) * np.abs(c) ** (2 * (n - 1) / n) / rx
    gy = np.sign(s) * np.abs(s) ** (2 * (n - 1) / n) / ry
    g = np.stack((gx, gy), -1)
    return g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-12)


def ring_length(points):
    """Cumulative arc length along a ring's columns (the last column repeats the first)."""
    step = np.linalg.norm(np.diff(points, axis=-2), axis=-1)
    return np.concatenate([np.zeros(step.shape[:-1] + (1,)), np.cumsum(step, axis=-1)], -1)


def columns(detail):
    """Angles for the pier's columns: even spacing in x across the panels, dense at the corner flutes."""
    panel_count = {2: 104, 1: 52, 0: 0}[detail]
    rx, ry = shaft_size(SHAFT_Z[1])
    fine = np.linspace(0, 2 * pi, 8193)
    x, y = superellipse(rx, ry, N_SHAFT, fine)
    s = ring_length(np.stack((x, y), -1)[None])[0]
    spacing = {2: 0.42, 1: 0.7, 0: 1.4}[detail]
    angles = list(np.interp(np.arange(0, s[-1], spacing), s, fine))
    if detail:
        for corner in (pi / 4, 3 * pi / 4, 5 * pi / 4, 7 * pi / 4):
            sc = np.interp(corner, fine, s)
            offsets = np.linspace(-FLUTE_W - .25, FLUTE_W + .25, 15 if detail == 2 else 9)
            angles += list(np.interp(sc + offsets, s, fine))
    panel = []
    if panel_count:
        xn = np.linspace(PANEL_X, -PANEL_X, panel_count + 1)
        for side in (1, -1):
            theta = np.arccos(np.sign(xn) * np.abs(xn) ** (N_SHAFT / 2))
            panel.append(theta if side > 0 else 2 * pi - theta[::-1])
        lo1, hi1 = panel[0][0], panel[0][-1]
        lo2, hi2 = panel[1][0], panel[1][-1]
        angles = [a for a in angles if not (lo1 - 1e-4 <= a <= hi1 + 1e-4 or lo2 - 1e-4 <= a <= hi2 + 1e-4)]
        angles += list(panel[0]) + list(panel[1])
    angles = np.unique(np.round(np.mod(angles, 2 * pi), 7))
    keep = np.concatenate([[True], np.diff(angles) > 1e-4])
    angles = angles[keep]
    angles = np.append(angles, angles[0] + 2 * pi)   # seam column for continuous UVs
    spans = []
    for p in panel:
        spans.append((int(np.argmin(np.abs(angles - p[0]))), int(np.argmin(np.abs(angles - p[-1])))))
    return angles, spans


def pier_profile():
    """(z, rx, ry, n, shaft) rings from the plinth to the cap. Repeated rings make sharp creases."""
    rows = [
        (48.10, 5.00, 6.40, 9.0), (50.35, 5.00, 6.40, 9.0), (50.35, 5.00, 6.40, 9.0),
        (50.45, 4.93, 6.33, 8.0), (50.56, 4.78, 6.18, 7.0), (50.68, 4.68, 6.08, 6.0),
        (50.80, 4.64, 6.04, 5.0), (50.80, 4.64, 6.04, 5.0),
        (50.80, 4.90, 6.30, 4.0), (50.92, 5.07, 6.47, 3.8), (51.06, 5.16, 6.56, 3.6),
        (51.21, 5.13, 6.53, 3.5), (51.36, 4.97, 6.37, 3.4),
    ]
    shaft = sorted(set(np.round(np.concatenate([
        np.arange(SHAFT_Z[0], SHAFT_Z[1] + 1e-6, 0.5),
        [FIELD_Z[0] - .25, FIELD_Z[0] + .25, FIELD_Z[1] - .25, FIELD_Z[1] + .25]]), 4)))
    rows += [(z, *shaft_size(z), N_SHAFT, True) for z in shaft]
    rx, ry = shaft_size(SHAFT_Z[1])
    rows += [
        (67.5, rx, ry, N_SHAFT), (67.62, rx + .18, ry + .18, 3.2), (67.80, rx + .40, ry + .40, 3.0),
        (68.00, rx + .46, ry + .46, 2.9), (68.18, rx + .36, ry + .36, 2.8), (68.30, rx + .14, ry + .14, 2.7),
        (68.30, rx + .14, ry + .14, 2.7),
        (68.30, 9.95, 9.95, 2.2), (69.35, 9.95, 9.95, 2.1), (69.35, 9.95, 9.95, 2.1),
        (69.35, 10.45, 10.45, 2.0), (69.70, 10.45, 10.45, 2.0), (69.70, 10.45, 10.45, 2.0),
        (69.95, 10.52, 10.52, 2.0), (70.25, 10.68, 10.68, 2.0), (70.55, 10.96, 10.96, 2.0),
        (70.80, 11.35, 11.35, 2.0), (70.98, 11.80, 11.80, 2.0), (70.98, 11.80, 11.80, 2.0),
        (71.28, 11.80, 11.80, 2.0), (71.28, 11.80, 11.80, 2.0),
        (71.45, 12.02, 12.02, 2.0), (71.70, 12.17, 12.17, 2.0), (72.00, 12.22, 12.22, 2.0),
        (72.30, 12.15, 12.15, 2.0), (72.55, 11.96, 11.96, 2.0), (72.74, 11.72, 11.72, 2.0),
        (72.85, 11.42, 11.42, 2.0), (72.85, 11.42, 11.42, 2.0),
        (72.85, 10.90, 10.90, 2.0), (72.85, 10.90, 10.90, 2.0), (72.70, 10.40, 10.40, 2.0),
    ]
    return [r if len(r) == 5 else (*r, False) for r in rows]


def flute_depth(arc_offset, z):
    """Rounded vertical grooves on the pier's corners."""
    za, zb = FIELD_Z
    dz = np.maximum(0, np.maximum(za - z, z - zb))
    d = np.sqrt(arc_offset ** 2 + dz ** 2)
    return FLUTE_DEPTH * np.sqrt(np.clip(1 - (d / FLUTE_W) ** 2, 0, 1))


def acanthus_spine(points, samples=180):
    """Catmull-Rom curve through panel points (u across the field, v up it)."""
    p = np.asarray(points, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        t = np.linspace(0, 1, samples // (len(p) - 3), endpoint=False)[:, None]
        a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
        out.append(.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t ** 2 + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(p[-2][None])
    return np.vstack(out)


# Each leaf: spine through (u across the field, v up it), blade half-width, height, lobes.
LEAVES = [
    ([(-.30, .02), (-.62, .10), (-.88, .07)], 1.05, .50, 3),
    ([(-.24, .13), (.10, .22), (.48, .19), (.62, .14)], 1.00, .50, 3),
    ([(-.16, .26), (-.55, .37), (-.86, .34), (-.95, .28)], 1.35, .60, 4),
    ([(-.06, .40), (.34, .49), (.70, .47), (.84, .41)], 1.30, .60, 4),
    ([(.03, .53), (-.42, .64), (-.80, .62), (-.92, .55)], 1.55, .66, 4),
    ([(.12, .65), (.48, .74), (.78, .71), (.88, .65)], 1.30, .62, 4),
    ([(.17, .80), (-.12, .89), (-.46, .91), (-.62, .86)], 1.20, .58, 3),
    ([(.19, .74), (.25, .87), (.40, .97), (.60, .97), (.70, .90)], 1.60, .70, 4),
]
STEM = [(-.30, -.02), (-.20, .20), (-.05, .44), (.10, .65), (.18, .78)]


def acanthus(x, z):
    """Relief height above the recessed field (game units) at real face coordinates x, z.

    Each leaf is a continuous blade around a curved midrib: a scalloped outline of rounded lobes,
    each lobe with three shallow points, a soft domed section, a raised midrib, veins running into
    the lobes, drilled eyes where the lobes meet and a tip that turns over towards the viewer.
    """
    zf0, zf1 = FIELD_Z
    rx, _ = shaft_size(z)
    half = 0.585 * rx
    pts = np.column_stack((x, z))
    height = np.zeros(len(pts))

    def to_real(uv):
        zz = zf0 + uv[:, 1] * (zf1 - zf0)
        return np.column_stack((uv[:, 0] * 0.585 * shaft_size(zz)[0], zz))

    def project(spine):
        """Distance to the spine, the arc parameter t of the closest point and the side."""
        a, b = spine[:-1], spine[1:]
        ab = b - a
        seg_len = np.linalg.norm(ab, axis=1)
        s0 = np.concatenate([[0], np.cumsum(seg_len)])[:-1]
        total = seg_len.sum()
        best = np.full(len(pts), np.inf)
        t_best = np.zeros(len(pts))
        side = np.zeros(len(pts))
        for k in range(0, len(a), 40):
            aa, abk, ll, ss = a[k:k + 40], ab[k:k + 40], seg_len[k:k + 40], s0[k:k + 40]
            ap = pts[:, None, :] - aa[None]
            f = np.clip((ap * abk[None]).sum(-1) / np.maximum(ll ** 2, 1e-12), 0, 1)
            closest = aa[None] + f[..., None] * abk[None]
            d = np.linalg.norm(pts[:, None, :] - closest, axis=-1)
            j = d.argmin(1)
            dj = d[np.arange(len(pts)), j]
            better = dj < best
            best[better] = dj[better]
            t_best[better] = ((ss[j] + f[np.arange(len(pts)), j] * ll[j]) / total)[better]
            cross = abk[j, 0] * ap[np.arange(len(pts)), j, 1] - abk[j, 1] * ap[np.arange(len(pts)), j, 0]
            side[better] = np.sign(cross[better])
        return best, t_best, side

    stem = to_real(acanthus_spine(STEM, 200))
    d, t, _ = project(stem)
    w = .34 - .10 * t
    np.maximum(height, .46 * np.clip(1 - (d / w) ** 2, 0, 1) ** 1.2, out=height)
    for points, width, peak, lobes in LEAVES:
        spine = to_real(acanthus_spine(points, 200))
        d, t, side = project(spine)
        envelope = np.sin(pi * np.clip(t, 0, 1) ** .75) ** .65
        phase = lobes * np.clip(t, 0, 1) + .5
        scallop = .70 + .30 * np.cos(2 * pi * phase) ** 2
        points3 = 1 - .07 * (.5 - .5 * np.cos(2 * pi * 3 * phase))
        reach = width * envelope * scallop * points3
        q = d / np.maximum(reach, 1e-6)
        crest = peak * (.55 + .45 * np.sin(pi * np.clip(t, 0, 1)) ** .5)
        # A cupped blade: the lobes' rims stand proud of the hollow beside the midrib.
        cup = .62 + .38 * smoothstep(.15, .72, q)
        blade = crest * cup * smoothstep(1.0, .66, q) * (.82 + .18 * np.cos(2 * pi * phase) ** 2)
        midrib = .22 * crest * np.exp(-(d / (.10 * width + .05)) ** 2) * (t < .94)
        blade = blade + midrib
        # Drilled eyes where neighbouring lobes meet, a little out from the midrib.
        junction = np.clip(1 - np.abs(np.sin(pi * phase)) / .2, 0, 1)
        eye = np.exp(-((q - .45) / .12) ** 2) * junction
        blade -= .60 * crest * eye * (t > .12) * (t < .9)
        np.maximum(height, np.where(q < 1, blade, 0), out=height)
    height = np.clip(height, 0, None)
    inside = (np.abs(x) < half - .1) & (z > zf0 + .1) & (z < zf1 - .1)
    return np.where(inside, height, 0)


def preview_acanthus(path, res=.03):
    """Shaded 2D preview of one panel's relief (internal check)."""
    z = np.arange(PATCH_Z[0], PATCH_Z[1], res)
    xs = np.arange(-PANEL_X * shaft_size(PATCH_Z[1])[0], PANEL_X * shaft_size(PATCH_Z[1])[0], res)
    X, Z = np.meshgrid(xs, z)
    rx = shaft_size(Z)[0]
    xn = X / rx
    H = panel_relief(xn.ravel(), Z.ravel()) + acanthus(X.ravel(), Z.ravel())
    H = np.where(np.abs(xn.ravel()) > PANEL_X, np.nan, H).reshape(X.shape)
    gz, gx = np.gradient(np.nan_to_num(H), res)
    n = np.dstack((-gx, -gz, np.ones_like(gx)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    light = np.array((-.45, .55, .70)) / np.linalg.norm((-.45, .55, .70))
    shade = np.clip(n @ light, 0, 1) * .85 + .15
    shade[np.isnan(H)] = 0
    Image.fromarray((shade[::-1] * 255).astype(np.uint8)).save(path)


def panel_relief(xn, z):
    """Height above the shaft face across a panel patch (xn = x / rx)."""
    zf0, zf1 = FIELD_Z
    a = np.abs(xn)
    rail_v = .16 * smoothstep(.598, .612, a) * (1 - smoothstep(.688, .702, a)) * (z > zf0 - .45) * (z < zf1 + .45)
    rail_h = .16 * (1 - smoothstep(.688, .702, a)) * (
        smoothstep(zf0 - .47, zf0 - .43, z) * (1 - smoothstep(zf0 - .05, zf0 - .01, z)) +
        smoothstep(zf1 + .01, zf1 + .05, z) * (1 - smoothstep(zf1 + .43, zf1 + .47, z)))
    field = -.30 * (1 - smoothstep(.570, .590, a)) * smoothstep(zf0 - .02, zf0 + .03, z) * (1 - smoothstep(zf1 - .03, zf1 + .02, z))
    return np.maximum(rail_v, rail_h) + field


def pier(detail):
    angles, spans = columns(detail)
    profile = pier_profile()
    cols = len(angles)
    z = np.array([r[0] for r in profile])
    rings = []
    for zz, rx, ry, n, shaft in profile:
        x, y = superellipse(rx, ry, n, angles)
        rings.append(np.column_stack((x, y, np.full(cols, zz))))
    p = np.array(rings)                                         # (rows, cols, 3)
    # Profile length for V, ring length for U.
    radial = np.linalg.norm(p[:, 0, :2], axis=1)
    step = np.hypot(np.diff(z), np.diff(radial))
    v_rows = np.concatenate([[0], np.cumsum(step)]) / UV_TILE
    u = ring_length(p[:, :, :2]) / UV_TILE
    shaft_rows = np.array([r[4] for r in profile])
    if detail:
        # Flutes on the corners.
        rx_top, ry_top = shaft_size(SHAFT_Z[1])
        ref = np.stack(superellipse(rx_top, ry_top, N_SHAFT, angles), -1)
        s_ref = ring_length(ref[None])[0]
        for row in np.where(shaft_rows)[0]:
            zz = z[row]
            rx, ry = shaft_size(zz)
            scale = ring_length(p[row:row + 1, :, :2])[0][-1] / s_ref[-1]
            depth = np.zeros(cols)
            for corner in (pi / 4, 3 * pi / 4, 5 * pi / 4, 7 * pi / 4):
                sc = np.interp(corner, angles, s_ref)
                depth = np.maximum(depth, flute_depth((s_ref - sc) * scale, zz))
            nrm = outward(rx, ry, N_SHAFT, angles)
            p[row, :, :2] -= nrm * depth[:, None]
    keep = np.ones((len(z) - 1, cols - 1), bool)
    pos, uv = p.reshape(-1, 3), np.column_stack((u.ravel(), np.repeat(v_rows, cols)))
    patches = []
    if detail:
        r0, r1 = int(np.argmin(np.abs(z - PATCH_Z[0]))), int(np.argmin(np.abs(z - PATCH_Z[1])))
        assert shaft_rows[r0] and shaft_rows[r1]
        for c0, c1 in spans:
            keep[r0:r1, c0:c1] = False
            patches.append(panel_patch(angles[c0:c1 + 1], detail, z, v_rows, profile))
    tris = drop_degenerate(grid_triangles(len(z), cols, keep), pos)
    seam = (np.arange(len(z)) * cols, np.arange(len(z)) * cols + cols - 1)
    normals = vertex_normals(pos, tris, [seam])
    parts = [Part.per_vertex("pier", STONE_MATERIAL, pos, tris, uv, normals)]
    # Shallow dish closing the cap.
    top = p[-1]
    centre = np.array([0, 0, 72.62])
    cap_pos = np.vstack([top[:-1], centre])
    k = cols - 1
    cap_tris = np.column_stack((np.full(k, k), np.arange(k), (np.arange(k) + 1) % k))
    cap_n = vertex_normals(cap_pos, cap_tris)
    parts.append(Part.per_vertex("pier_top", STONE_MATERIAL, cap_pos, cap_tris, cap_pos[:, :2] / UV_TILE, cap_n))
    for i, (pp, tt, uu, nn) in enumerate(patches):
        parts.append(Part.per_vertex(f"panel_{i}", STONE_MATERIAL, pp, tt, uu, nn))
    return parts


def relief_triangles(heights):
    """Grid triangles whose quad diagonals follow the relief (the pair of corners closer in height)."""
    rows, cols = heights.shape
    r, c = np.meshgrid(np.arange(rows - 1), np.arange(cols - 1), indexing="ij")
    a = (r * cols + c).ravel()
    b, d = a + 1, a + cols
    e = d + 1
    h = heights.ravel()
    main = np.abs(h[a] - h[e]) <= np.abs(h[b] - h[d])
    first = np.where(main[:, None], np.column_stack((a, b, e)), np.column_stack((a, b, d)))
    second = np.where(main[:, None], np.column_stack((a, e, d)), np.column_stack((b, e, d)))
    return np.concatenate([first, second])


def panel_patch(angles, detail, z_rows, v_rows, profile):
    rows = np.linspace(PATCH_Z[0], PATCH_Z[1], {2: 151, 1: 76}[detail])
    cols = len(angles)
    full_angles, _ = columns(detail)
    zz = np.repeat(rows, cols)
    th = np.tile(angles, len(rows))
    rx, ry = shaft_size(zz)
    x, y = superellipse(rx, ry, N_SHAFT, th)
    nrm = outward(rx, ry, N_SHAFT, th)
    xn = x / rx
    h = (panel_relief(xn, zz) + acanthus(x, zz)).reshape(len(rows), cols)
    # A light binomial blur keeps carved edges from stepping along the grid; the patch's border
    # stays exactly on the shaft surface so it meets the shaft's own vertices.
    for axis in (0, 1):
        h = .25 * np.roll(h, 1, axis) + .5 * h + .25 * np.roll(h, -1, axis)
    h[[0, -1], :] = 0
    h[:, [0, -1]] = 0
    heights = h
    h = h.ravel()
    pos = np.column_stack((x + nrm[:, 0] * h, y + nrm[:, 1] * h, zz))
    # U continues the shaft's ring lengths; V interpolates the profile length.
    u = np.empty(len(zz))
    for r, zr in enumerate(rows):
        rxr, ryr = shaft_size(zr)
        ring = np.stack(superellipse(rxr, ryr, N_SHAFT, full_angles), -1)
        s = ring_length(ring[None])[0] / UV_TILE
        u[r * cols:(r + 1) * cols] = np.interp(angles, full_angles, s)
    v = np.interp(zz, z_rows[[i for i, r in enumerate(profile) if r[4]]], v_rows[[i for i, r in enumerate(profile) if r[4]]])
    tris = relief_triangles(heights)
    normals = vertex_normals(pos, tris)
    return pos, tris, np.column_stack((u, v)), normals


# ---------------------------------------------------------------------------------------------- base
def footprint_outline(points, spacing):
    """Smoothed outline (counter-clockwise, metres... game units) around both lions and the plinth."""
    res = .1
    x0, y0 = -42., -14.
    w, h = int(84 / res), int(30 / res)
    occ = np.zeros((h, w), bool)
    low = points[points[:, 2] < BASE_TOP + 1.3]
    for sign in (1, -1):
        ix = ((sign * low[:, 0] - x0) / res).astype(int)
        iy = ((low[:, 1] - y0) / res).astype(int)
        occ[np.clip(iy, 0, h - 1), np.clip(ix, 0, w - 1)] = True
    occ = ndimage.binary_closing(occ, iterations=4)
    yy, xx = np.mgrid[0:h, 0:w]
    px, py = x0 + xx * res, y0 + yy * res
    occ |= (np.abs(px) < 6.4) & (np.abs(py) < 7.4)
    occ = ndimage.binary_fill_holes(occ)
    disk = (np.hypot(*np.mgrid[-12:13, -12:13]) <= 11.5)
    occ = ndimage.binary_dilation(occ, structure=disk)
    occ = ndimage.binary_fill_holes(occ)
    smooth = ndimage.gaussian_filter(occ.astype(float), 9)
    contour = max(measure.find_contours(smooth, .5), key=len)
    poly = np.column_stack((x0 + contour[:, 1] * res, y0 + contour[:, 0] * res))
    if np.allclose(poly[0], poly[-1]):
        poly = poly[:-1]
    area = .5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1])
    if area < 0:
        poly = poly[::-1]
    seg = np.linalg.norm(np.diff(np.vstack([poly, poly[:1]]), axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    samples = np.arange(0, s[-1], spacing)
    closed = np.vstack([poly, poly[:1]])
    return np.column_stack((np.interp(samples, s, closed[:, 0]), np.interp(samples, s, closed[:, 1])))


def ear_clip(poly):
    """Triangulate a simple counter-clockwise polygon."""
    idx = list(range(len(poly)))
    tris = []
    p = poly

    def convex(a, b, c):
        return (p[b, 0] - p[a, 0]) * (p[c, 1] - p[a, 1]) - (p[b, 1] - p[a, 1]) * (p[c, 0] - p[a, 0]) > 1e-12

    guard = 0
    while len(idx) > 3 and guard < 200000:
        guard += 1
        n = len(idx)
        clipped = False
        arr = np.array(idx)
        for k in range(n):
            a, b, c = idx[k - 1], idx[k], idx[(k + 1) % n]
            if not convex(a, b, c):
                continue
            others = arr[(arr != a) & (arr != b) & (arr != c)]
            q = p[others]
            d1 = (p[b, 0] - p[a, 0]) * (q[:, 1] - p[a, 1]) - (p[b, 1] - p[a, 1]) * (q[:, 0] - p[a, 0])
            d2 = (p[c, 0] - p[b, 0]) * (q[:, 1] - p[b, 1]) - (p[c, 1] - p[b, 1]) * (q[:, 0] - p[b, 0])
            d3 = (p[a, 0] - p[c, 0]) * (q[:, 1] - p[c, 1]) - (p[a, 1] - p[c, 1]) * (q[:, 0] - p[c, 0])
            if np.any((d1 >= 0) & (d2 >= 0) & (d3 >= 0)):
                continue
            tris.append((a, b, c))
            idx.pop(k)
            clipped = True
            break
        if not clipped:
            raise RuntimeError("ear clipping stalled")
    tris.append(tuple(idx))
    return np.array(tris)


BASE_PROFILE = [(0., 48.0), (0., 48.78), (0., 48.78), (.04, 48.98), (.12, 49.17), (.25, 49.34),
                (.42, 49.48), (.61, 49.57), (.8, BASE_TOP), (.8, BASE_TOP)]


def base(points, spacing):
    outline = footprint_outline(points, spacing)
    n = len(outline)
    closed = np.vstack([outline, outline[:1]])
    tangent = np.roll(outline, -1, 0) - np.roll(outline, 1, 0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    inward = np.column_stack((-tangent[:, 1], tangent[:, 0]))       # left of a counter-clockwise path
    rings = []
    for inset, zz in BASE_PROFILE:
        ring = outline + inward * inset
        ring = np.vstack([ring, ring[:1]])
        rings.append(np.column_stack((ring, np.full(n + 1, zz))))
    p = np.array(rings)
    radial_step = np.array([0] + [np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(BASE_PROFILE, BASE_PROFILE[1:])])
    v = np.cumsum(radial_step) / UV_TILE
    u = ring_length(closed[None])[0] / UV_TILE
    pos = p.reshape(-1, 3)
    uv = np.column_stack((np.tile(u, len(rings)), np.repeat(v, n + 1)))
    # Counter-clockwise columns rising up the profile face outward (and upward on the moulding).
    tris = drop_degenerate(grid_triangles(len(rings), n + 1), pos)
    seam = (np.arange(len(rings)) * (n + 1), np.arange(len(rings)) * (n + 1) + n)
    normals = vertex_normals(pos, tris, [seam])
    side = Part.per_vertex("base_edge", BASE_MATERIAL, pos, tris, uv, normals)
    top_ring = rings[-1][:-1]
    top_tris = ear_clip(top_ring[:, :2])
    top = Part.per_vertex("base_top", BASE_MATERIAL, top_ring, top_tris, top_ring[:, :2] / UV_TILE,
                          np.tile((0., 0., 1.), (n, 1)))
    return [side, top]


# ---------------------------------------------------------------------------------------------- lions
def place_lion(points):
    return (points - LION_PIVOT) * LION_SCALE + LION_PIVOT + (LION_SHIFT, 0, 0)


def lions(work, lod):
    data = np.load(work / f"lod{lod}.npz")
    positions = place_lion(data["positions"].astype(float))
    lion = Part("lion_a", LION_MATERIAL, positions, data["triangles"], data["uvs"], data["normals"])
    return [lion, lion.mirrored("lion_b")]


# ---------------------------------------------------------------------------------------------- output
def write_obj(path, parts):
    with path.open("w", encoding="utf-8", newline="\n") as obj:
        obj.write(f"# Generated by Tools/veridant_fountain_roaring_crown.py\nmtllib crown.mtl\n")
        v_off = vt_off = vn_off = 1
        for part in parts:
            world = part.positions @ BASIS.T
            normals = part.normals.reshape(-1, 3) @ BASIS.T
            normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
            uv_keys, uv_index = np.unique(np.round(part.uvs.reshape(-1, 2), 6), axis=0, return_inverse=True)
            n_keys, n_index = np.unique(np.round(normals, 5), axis=0, return_inverse=True)
            uv_index, n_index = uv_index.reshape(-1), n_index.reshape(-1)
            obj.write(f"o {part.name}\nusemtl {part.material}\n")
            obj.write("".join(f"v {y:.5f} {z:.5f} {x:.5f}\n" for x, y, z in world))
            obj.write("".join(f"vt {a:.6f} {b:.6f}\n" for a, b in uv_keys))
            obj.write("".join(f"vn {y:.5f} {z:.5f} {x:.5f}\n" for x, y, z in n_keys))
            tri = part.triangles + v_off
            ti = uv_index.reshape(-1, 3) + vt_off
            ni = n_index.reshape(-1, 3) + vn_off
            obj.write("".join(
                f"f {a}/{b}/{c} {d}/{e}/{f} {g}/{h}/{i}\n"
                for (a, d, g), (b, e, h), (c, f, i) in zip(tri, ti, ni)))
            v_off += len(world)
            vt_off += len(uv_keys)
            vn_off += len(n_keys)
    return sum(len(p.triangles) for p in parts)


def srgb(linear):
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= .0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - .055)


def linear(rgb255):
    c = np.asarray(rgb255, float) / 255
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)


def lion_textures(work):
    a = np.asarray(Image.open(work / "lion_ingredients_a.png").convert("RGB"), np.float32) / 255
    b = np.asarray(Image.open(work / "lion_ingredients_b.png").convert("RGB"), np.float32) / 255
    ao_small, ao_large, convex = a[..., 0], a[..., 1], a[..., 2]
    used = a.sum(-1) > 0        # texels inside the UV charts (or their bleed margins)

    def norm(ch):
        lo, hi = np.percentile(ch[used], (2, 98))
        return np.clip((ch - lo) / max(hi - lo, 1e-6), 0, 1)
    mottle, fine, streak = norm(b[..., 0]), norm(b[..., 1]), norm(b[..., 2])
    # Measured on this bake: tight occlusion is ~0.98 on open bronze and ~0.7 in the deepest 5%.
    cavity = smoothstep(.02, .25, 1 - ao_small)
    sheltered = smoothstep(.86, .55, ao_large)
    ridge = smoothstep(.53, .70, convex) * smoothstep(.85, .99, ao_small)
    # Verdigris gathers in the carving and under the mane; elsewhere it is a thin, broken film.
    film = smoothstep(.56, .82, mottle * .55 + fine * .30 + streak * .35 - .1)
    patina = np.maximum.reduce([smoothstep(.05, .6, cavity) * .9, sheltered * .6, film * .42])
    patina = np.clip(patina * (1 - .8 * ridge), 0, 1)
    dark, mid, high = linear((86, 61, 39)), linear((124, 90, 57)), linear((170, 130, 86))
    verd_dark, verd_mid, verd_light = linear((60, 80, 66)), linear((86, 110, 92)), linear((124, 146, 124))
    crevice = linear((30, 31, 25))
    t = np.clip(.40 + .5 * (fine - .5) + .35 * (ao_large - .6), 0, 1)[..., None]
    bronze = dark * (1 - t) + mid * t
    bronze = bronze * (1 - ridge[..., None] * .8) + high * ridge[..., None] * .8
    pt = fine[..., None]
    verd = verd_dark * (1 - pt) + verd_mid * pt
    chalk = (smoothstep(.65, .88, fine) * (1 - cavity) * .45)[..., None]
    verd = verd * (1 - chalk) + verd_light * chalk
    colour = bronze * (1 - patina[..., None]) + verd * patina[..., None]
    deep = (smoothstep(.55, 1., cavity) * .65)[..., None]
    colour = colour * (1 - deep) + crevice * deep
    colour *= (.74 + .26 * ao_large)[..., None]
    # Weathered statuary bronze: a soft sheen on the cast surface, polished on the ridges,
    # matte where the patina has formed.
    rough = .52 * (1 - patina) + .82 * patina
    rough = rough * (1 - ridge * .5) + .34 * ridge * .5
    rough = np.clip(rough + .08 * deep[..., 0] + (fine - .5) * .08, .25, .95)
    metal = np.clip((.34 + .26 * ridge) * (1 - patina) * (1 - deep[..., 0]), 0, 1)
    ao = np.clip(ao_large ** .8 * (.55 + .45 * ao_small), 0, 1)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    Image.fromarray((srgb(colour) * 255 + .5).astype(np.uint8)).save(TEXTURES / "lion_color.png", optimize=True)
    half = (a.shape[1] // 2, a.shape[0] // 2)
    for name, data in (("lion_rough", rough), ("lion_metal", metal), ("lion_ao", ao)):
        Image.fromarray((data * 255 + .5).astype(np.uint8)).resize(half, Image.Resampling.LANCZOS).save(
            TEXTURES / f"{name}.png", optimize=True)
    shutil.copyfile(work / "lion_normal.png", TEXTURES / "lion_normal.png")


def periodic_noise(size, scale, seed):
    """Tileable fractal noise in [0, 1]: white noise filtered by a power law in frequency."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(size)
    r = np.hypot(*np.meshgrid(f, f, indexing="ij"))
    spectrum = np.fft.fft2(rng.standard_normal((size, size))) * np.exp(-(r * size / scale) ** 2) / np.maximum(r, 1 / size) ** 1.1
    field = np.real(np.fft.ifft2(spectrum))
    lo, hi = np.percentile(field, (1, 99))
    return np.clip((field - lo) / (hi - lo), 0, 1)


def base_textures():
    size = 1024
    mottle = periodic_noise(size, 24, 3)
    fine = periodic_noise(size, 260, 5)
    pits = periodic_noise(size, 420, 9)
    patina = smoothstep(.52, .80, mottle * .80 + fine * .30 - .05) * .55
    dark, mid = linear((80, 57, 37)), linear((116, 84, 54))
    verd_dark, verd_mid = linear((60, 80, 66)), linear((86, 110, 92))
    t = fine[..., None]
    bronze = dark * (1 - t) + mid * t
    verd = verd_dark * (1 - t) + verd_mid * t
    colour = bronze * (1 - patina[..., None]) + verd * patina[..., None]
    colour *= (.86 + .14 * pits)[..., None]
    rough = np.clip(.54 * (1 - patina) + .82 * patina + (fine - .5) * .08, .25, .95)
    metal = np.clip(.34 * (1 - patina), 0, 1)
    height = ndimage.gaussian_filter(pits, 1.2, mode="wrap") * .6 + fine * .4
    gy, gx = np.gradient(height)
    normal = np.dstack((-gx * 6, -gy * 6, np.ones_like(gx)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    Image.fromarray((srgb(colour) * 255 + .5).astype(np.uint8)).save(TEXTURES / "base_color.png", optimize=True)
    Image.fromarray((rough * 255 + .5).astype(np.uint8)).save(TEXTURES / "base_rough.png", optimize=True)
    Image.fromarray((metal * 255 + .5).astype(np.uint8)).save(TEXTURES / "base_metal.png", optimize=True)
    Image.fromarray(((normal * .5 + .5) * 255 + .5).astype(np.uint8)).save(TEXTURES / "base_normal.png", optimize=True)


def vmat(name, prefix):
    (ASSETS / "materials/veridant" / f"fountain_roaring_{name}.vmat").write_text(f"""// Generated by Tools/veridant_fountain_roaring_crown.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.300"
	g_flAmbientOcclusionDirectSpecular "0.500"
	TextureAmbientOcclusion "{TEXTURE_PATH}/{prefix}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{TEXTURE_PATH}/{prefix}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{TEXTURE_PATH}/{prefix}_metal.png"

	//---- Normal ----
	TextureNormal "{TEXTURE_PATH}/{prefix}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{TEXTURE_PATH}/{prefix}_rough.png"
}}
""", encoding="utf-8")


def vmdl():
    meshes = "\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "models/props/shared/{NAME}/crown_lod{i}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        'import_filter = { exclude_by_default = false exception_list = [ ] } },' for i in range(3))
    (FOLDER / "crown.vmdl").write_text(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Tools/veridant_fountain_roaring_crown.py
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
							{{ from = "{LION_MATERIAL}.vmat" to = "materials/veridant/fountain_roaring_lion_bronze.vmat" }},
							{{ from = "{BASE_MATERIAL}.vmat" to = "materials/veridant/fountain_roaring_base_bronze.vmat" }},
							{{ from = "{STONE_MATERIAL}.vmat" to = "materials/veridant/fountain_carved_limestone.vmat" }}
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
					{{ _class = "LODGroup" switch_threshold = 36.0 meshes = [ "lod1" ] }},
					{{ _class = "LODGroup" switch_threshold = 90.0 meshes = [ "lod2" ] }}
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""", encoding="utf-8")


ATTRIBUTION = """Bronze lions: "Lion Statue" by beachmouse, a scan of a lion statue outside a library in
Burlingame, California. https://sketchfab.com/3d-models/lion-statue-9abb1020ee34465cab478616ece693ac
Licensed under Creative Commons Attribution 4.0 International. https://creativecommons.org/licenses/by/4.0/
Adapted for HC1: scanned slab removed, rescaled, mirrored into a pair, decimated into LODs, unwrapped and
given a baked verdigris bronze finish. Pier and base are original to HC1.
"""


def main(work):
    FOLDER.mkdir(parents=True, exist_ok=True)
    points = place_lion(np.load(work / "high_points.npy").astype(float))
    report = {}
    for lod, (detail, spacing) in enumerate(((2, .3), (1, .6), (0, 1.2))):
        parts = lions(work, lod) + pier(detail) + base(points, spacing)
        report[f"lod{lod}"] = {p.name: len(p.triangles) for p in parts}
        report[f"lod{lod}"]["total"] = write_obj(FOLDER / f"crown_lod{lod}.obj", parts)
    (FOLDER / "crown.mtl").write_text("".join(f"newmtl {m}\n" for m in (LION_MATERIAL, BASE_MATERIAL, STONE_MATERIAL)))
    lion_textures(work)
    base_textures()
    vmat("lion_bronze", "lion")
    vmat("base_bronze", "base")
    (TEXTURES / "base_ao.png").exists() or Image.new("L", (64, 64), 255).save(TEXTURES / "base_ao.png")
    vmdl()
    (FOLDER / "ATTRIBUTION.txt").write_text(ATTRIBUTION, encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
