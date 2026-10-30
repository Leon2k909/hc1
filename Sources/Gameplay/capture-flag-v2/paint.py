"""Paint the capture flag's PBR maps from the bakes, with numpy. Every map is authored here; nothing is downloaded.

python paint.py <work dir> <materials dir> [hw] [soft] [flag] [rope]

Wear is worked out in 3D, from the baked position and normal of each texel, so it runs across UV seams:
paint over primer over steel, chipped on real edges; rust where the chips are and running downhill from them; dust on
what faces up and mud low down. Maps are OpenGL normals (as s&box reads them), rows flipped to image order on save.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

WORK, OUT = sys.argv[1], sys.argv[2]
JOBS = set(sys.argv[3:]) or {"hw", "soft", "flag", "rope"}
os.makedirs(OUT, exist_ok=True)

PAINT, GALV, OXIDE, ZINC, BRASS, RUBBER, WELD, PLATE, RUST = range(9)
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"


def srgb_to_linear(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    if a.ndim == 3 and getattr(t, "ndim", 0) == 2:
        t = t[..., None]
    return a + (b - a) * t


def fill_from(cover, *arrays):
    """Extend every array from the covered texels to the rest, so filters and mips see no holes."""
    index = ndi.distance_transform_edt(~cover, return_distances=False, return_indices=True)
    return [a[tuple(index)] for a in arrays]


def load(name):
    return np.load(os.path.join(WORK, name + ".npy"))


_lattices = {}


def noise(p, freq, seed=0, octaves=1, gain=0.5):
    """Value noise over points p (N, 3), about 0..1, wrapped on a 64-cell lattice and smoothed so it has no grid look."""
    total = np.zeros(p.shape[0], np.float32)
    amp = 1.0
    norm = 0.0
    for o in range(octaves):
        key = seed * 37 + o
        if key not in _lattices:
            lat = np.random.default_rng(key + 11).random((64, 64, 64), np.float32)
            _lattices[key] = ndi.gaussian_filter(lat, 0.8, mode="wrap")
            _lattices[key] = (_lattices[key] - _lattices[key].mean()) / (_lattices[key].std() * 4.0) + 0.5
        f = freq * 2.0 ** o
        total += amp * ndi.map_coordinates(_lattices[key], (p * f).T, order=1, mode="grid-wrap")
        norm += amp
        amp *= gain
    return total / norm


def to_normal(height, px_per_in, strength=1.0, px_per_in_v=None):
    """Tangent-space normal of a height in inches, rows bottom-up as Blender stores images."""
    dv, du = np.gradient(height)
    n = np.stack((-du * px_per_in * strength, -dv * (px_per_in_v or px_per_in) * strength, np.ones_like(height)), -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def blend_normals(base, detail):
    """Reoriented normal mapping: detail laid over base."""
    t = base + np.array((0, 0, 1), np.float32)
    u = detail * np.array((-1, -1, 1), np.float32)
    r = t * (t * u).sum(-1, keepdims=True) / t[..., 2:3] - u
    return r / np.linalg.norm(r, axis=-1, keepdims=True)


def save_rgb(path, linear=None, data=None):
    a = linear_to_srgb(linear) if linear is not None else data
    Image.fromarray((np.clip(a, 0, 1)[::-1] * 255 + 0.5).astype(np.uint8)).save(path, optimize=False, compress_level=6)


def save_gray(path, a):
    Image.fromarray((np.clip(a, 0, 1)[::-1] * 255 + 0.5).astype(np.uint8), "L").save(path, compress_level=6)


def save_normal(path, n):
    save_rgb(path, data=n * 0.5 + 0.5)


def stencil_image(lines, size, bridge=True, align="center"):
    """White lettering on black, cut with stencil bridges."""
    w, h = size
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    rows = len(lines)
    tall = int(h / rows * 0.86)
    y = int((h - rows * h / rows) / 2)
    for k, line in enumerate(lines):
        font = ImageFont.truetype(FONT, tall)
        try:
            font.set_variation_by_name("Bold Condensed")
        except Exception:
            pass
        bb = d.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        if tw > w * 0.97:
            font = ImageFont.truetype(FONT, int(tall * w * 0.97 / tw))
            try:
                font.set_variation_by_name("Bold Condensed")
            except Exception:
                pass
            bb = d.textbbox((0, 0), line, font=font)
            tw = bb[2] - bb[0]
        x = (w - tw) // 2 if align == "center" else 0
        top = y + int(k * h / rows) + (int(h / rows) - (bb[3] - bb[1])) // 2 - bb[1]
        d.text((x, top), line, 255, font=font)
        if bridge:
            band = int(h / rows)
            yb = y + int(k * h / rows)
            d.rectangle((0, yb + band // 2 - max(1, band // 26), w, yb + band // 2 + max(1, band // 26)), fill=0)
    return np.asarray(img, np.float32) / 255.0


def sample_image(image, uu, vv):
    """Sample a top-down image with uu, vv in 0..1 (vv up). Outside is zero."""
    h, w = image.shape
    rows = (1 - vv) * (h - 1)
    cols = uu * (w - 1)
    out = ndi.map_coordinates(image, (rows, cols), order=1, mode="constant", cval=0.0)
    return np.where((uu >= 0) & (uu <= 1) & (vv >= 0) & (vv <= 1), out, 0)


def paint_hardware():
    pos4 = load("bake_hw_pos")
    nor4 = load("bake_hw_nor")
    facts4 = load("bake_hw_facts")
    ao4 = load("bake_hw_ao")
    H, W = pos4.shape[:2]
    # Positions are stored around 0.5, so only an unbaked texel is black. Bakes leave alpha at 1 everywhere.
    cover = pos4[..., :3].max(-1) > 1e-3
    print("hardware coverage %.2f" % cover.mean(), flush=True)
    meta = json.load(open(os.path.join(WORK, "atlas.json")))
    density = meta["hw_px_per_in"]

    pos = (pos4[..., :3] - 0.5) * 400.0
    nor = pos4[..., :3] * 0
    nor = nor4[..., :3] * 2 - 1
    finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
    part = facts4[..., 1]
    pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)

    aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
    ao = fill_from(aoc, ao4[..., 0])[0]
    ao = ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1)
    ao = np.clip(ao, 0, 1)
    del pos4, nor4, facts4, ao4

    # Curvature from how the smooth normal turns over the surface; real bevels light up, flats stay quiet.
    def curvature():
        out = np.zeros((H, W), np.float32)
        for axis in (0, 1):
            dn = np.gradient(nor, axis=axis)
            dp = np.gradient(pos, axis=axis)
            out += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
        return out

    curve = curvature()
    # The filled gutters make false gradients at island borders; without this every UV seam reads as a worn edge.
    curve[~ndi.binary_erosion(cover, iterations=2)] = 0
    # Curvature is one over the radius. A mast or a stay is curved all over and isn't an edge: only tighter than about
    # 3/8 inch counts, which keeps the wear on real bevels and rims.
    convex = np.clip((curve - 2.6) * 0.38, 0, 1)
    concave = np.clip((-curve - 2.6) * 0.34, 0, 1)
    edge = np.clip(ndi.gaussian_filter(convex, 2.2) * 2.4 + ndi.gaussian_filter(convex, 6.0) * 3.0, 0, 1)
    del curve

    pts = pos[cover]
    N = pts.shape[0]
    z_up = nor[..., 2][cover]
    z = pts[:, 2]

    def field(values, default=0.0):
        out = np.full((H, W), default, np.float32)
        out[cover] = values
        return out

    big = field(noise(pts, 0.11, 1, 3))
    mid = field(noise(pts, 0.55, 2, 4))
    fine = field(noise(pts, 2.7, 3, 3))
    micro = field(noise(pts, 11.0, 4, 2))
    print("noise done", flush=True)

    # Layers of the painted finish: topcoat, primer, steel.
    # Edges wear in patches, never as a continuous line.
    edge_patchy = edge * smooth(0.34, 0.66, mid * 0.65 + fine * 0.35)
    chip = edge_patchy * 1.12 + (mid - 0.5) * 0.62 + (big - 0.5) * 0.42 + (fine - 0.5) * 0.85 + (micro - 0.5) * 0.3 + concave * -0.1
    bare = smooth(0.735, 0.75, chip)
    primer = smooth(0.69, 0.705, chip)
    # Now and then a stone or a boot takes paint off a flat.
    ding_seed = field(noise(pts, 3.1, 5, 3))
    ding = smooth(0.84, 0.85, ding_seed + (fine - 0.5) * 0.3)
    primer = np.maximum(primer, smooth(0.825, 0.835, ding_seed + (fine - 0.5) * 0.3))
    bare = np.maximum(bare, ding)

    # Long scratches, drawn in UV so they stay sharp.
    scratch_img = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(scratch_img)
    rs = np.random.default_rng(7)
    for _ in range(1500):
        x, y = rs.uniform(0, W), rs.uniform(0, H)
        a = rs.uniform(0, 2 * math.pi)
        n = rs.integers(12, 90)
        bend = rs.normal(0, 0.012)
        line = []
        for s in np.linspace(0, n, 6):
            line.append((x + math.cos(a) * s, y + math.sin(a) * s))
            a += bend * 6
        draw.line(line, fill=int(rs.uniform(70, 235)), width=1)
    scratch = np.asarray(scratch_img, np.float32)[::-1] / 255.0
    scratch = scratch * smooth(0.42, 0.62, big + (mid - 0.5) * 0.5)

    # Rust: in the chips, and running down from them and from under the fittings.
    streak_p = pts * np.array((4.2, 4.2, 0.13), np.float32)
    streak = field(noise(streak_p, 0.26, 6, 4))
    crevice = np.clip((1 - ao) * 1.3, 0, 1)
    rust_run = smooth(0.54, 0.76, streak + crevice * 0.26) * smooth(0.25, 0.6, mid + crevice * 0.55)
    rust_in_chip = bare * smooth(0.46, 0.72, field(noise(pts, 1.7, 7, 3)) + crevice * 0.4) * 0.9

    # Colours, linear.
    od = srgb_to_linear((86, 92, 60))
    od_faded = srgb_to_linear((112, 113, 84))
    od_dark = srgb_to_linear((58, 64, 42))
    primer_c = srgb_to_linear((112, 110, 94))
    steel = srgb_to_linear((168, 168, 165))
    rust_dark = srgb_to_linear((58, 30, 18))
    rust_mid = srgb_to_linear((84, 50, 30))
    rust_bright = srgb_to_linear((120, 72, 42))

    color = np.zeros((H, W, 3), np.float32)
    rough = np.zeros((H, W), np.float32)
    metal = np.zeros((H, W), np.float32)
    height = np.zeros((H, W), np.float32)

    def rust_color(t):
        out = mix(np.broadcast_to(rust_dark, (H, W, 3)), np.broadcast_to(rust_mid, (H, W, 3)), smooth(0.25, 0.6, t))
        return mix(out, np.broadcast_to(rust_bright, (H, W, 3)), smooth(0.78, 0.98, t))

    rust_tone = field(noise(pts, 3.1, 8, 3))
    rust_c = rust_color(rust_tone)

    # Painted steel, and welds that were painted with it.
    painted = (finish == PAINT) | (finish == WELD)
    fade = smooth(0.3, 0.75, big + 0.12 * np.broadcast_to(np.clip(nor[..., 2], 0, 1), (H, W)))
    top = mix(np.broadcast_to(od_dark, (H, W, 3)), np.broadcast_to(od, (H, W, 3)), smooth(0.2, 0.6, mid * 0.5 + big * 0.5))
    top = mix(top, np.broadcast_to(od_faded, (H, W, 3)), fade * 0.24)
    # Years of rain have left long faint runs down whatever stands upright.
    upright = 1 - np.abs(nor[..., 2])
    top = top * (1 + upright[..., None] * (streak[..., None] - 0.5) * 0.42)
    # Each welded-up part was touched up at its own time.
    top = top * (0.93 + 0.14 * part[..., None])
    p_color = top.copy()
    p_rough = 0.5 + 0.2 * mid + 0.12 * fine
    p_metal = np.zeros((H, W), np.float32)
    p_height = 0.006 * (micro - 0.5) + 0.0024 * (fine - 0.5)

    # Weld ripple is a real, lumpy surface under the paint.
    weld = finish == WELD
    w_detail = field(noise(pts, 4.2, 9, 3))
    p_height = p_height + weld * (0.05 * (w_detail - 0.5) + 0.02 * (micro - 0.5))

    # The band of hazard paint on the socket collar and foot-plate lips.
    radial = np.hypot(pos[..., 0], pos[..., 1])
    theta = np.arctan2(pos[..., 1], pos[..., 0])
    collar = (pos[..., 2] > 10.45) & (pos[..., 2] < 12.2) & (radial > 2.5) & (radial < 2.95) & (finish == PAINT)
    stripes = np.mod((theta * 2.78 + pos[..., 2]) / 2.2, 1.0) < 0.5
    hazard = np.where(stripes[..., None], srgb_to_linear((196, 150, 26)), srgb_to_linear((26, 26, 24)))
    p_color = np.where(collar[..., None], hazard * (0.82 + 0.3 * mid[..., None]), p_color)

    # Stencilled lettering, sprayed on and worn with the coat.
    lettering = np.zeros((H, W), np.float32)
    mast_low = (finish == PAINT) & (radial < 1.72) & (pos[..., 2] > 13) & (pos[..., 2] < 43)
    art = stencil_image(["MAST ASSY", "LOAD 40 KG MAX"], (1000, 170))
    for centre in (math.radians(285), math.radians(105)):
        a = np.angle(np.exp(1j * (theta - centre)))
        uu = (pos[..., 2] - 17.0) / 19.0
        vv = 0.5 - a * 1.6 / 3.0
        hit = sample_image(art, np.clip(uu, -1, 2), np.clip(vv, -1, 2))
        lettering = np.maximum(lettering, hit * mast_low * (np.abs(a) < 1.2))
    plate_top = (finish == PAINT) & (pos[..., 2] > 0.55) & (pos[..., 2] < 0.7) & (radial < 11.5)
    art2 = stencil_image(["KEEP CLEAR"], (600, 90))
    uu = (4.2 - pos[..., 1]) / 8.4
    vv = (pos[..., 0] + 7.7) / 1.25
    lettering = np.maximum(lettering, sample_image(art2, np.clip(uu, -1, 2), np.clip(vv, -1, 2)) * plate_top)
    lettering = lettering * smooth(0.12, 0.32, field(noise(pts, 3.3, 10, 3)) + big * 0.15)
    p_color = mix(p_color, np.broadcast_to(srgb_to_linear((192, 188, 168)), (H, W, 3)), lettering * 0.93)

    # Through the coats.
    p_color = mix(p_color, np.broadcast_to(primer_c, (H, W, 3)) * (0.86 + 0.28 * fine[..., None]), primer)
    p_rough = p_rough * (1 - primer) + (0.8 + 0.1 * fine) * primer
    p_color = mix(p_color, np.broadcast_to(steel, (H, W, 3)) * (0.72 + 0.4 * fine[..., None]), bare)
    p_rough = p_rough * (1 - bare) + (0.36 + 0.26 * fine) * bare
    p_metal = np.maximum(p_metal, bare)
    p_height = p_height + (1 - primer) * 0.009 + (1 - bare) * 0.008
    p_color = mix(p_color, np.broadcast_to(steel, (H, W, 3)) * 0.82, scratch * 0.55)
    p_metal = np.maximum(p_metal, scratch * 0.6)
    p_rough = p_rough * (1 - scratch * 0.3) + 0.42 * scratch * 0.3
    p_height = p_height - scratch * 0.004
    rusted = np.maximum(rust_in_chip, 0)
    p_color = mix(p_color, rust_c, rusted)
    p_rough = p_rough * (1 - rusted) + (0.82 + 0.14 * fine) * rusted
    p_metal = p_metal * (1 - rusted)
    p_height = p_height + rusted * 0.006 * (rust_tone - 0.2)
    run = rust_run * 0.5
    p_color = mix(p_color, p_color * rust_c * 3.2, run)
    p_rough = p_rough + run * 0.14

    # Welds were laid before the coat and hold grime in their ripples.
    p_color = np.where(weld[..., None], p_color * 0.72, p_color)
    color = np.where(painted[..., None], p_color, color)
    rough = np.where(painted, p_rough, rough)
    metal = np.where(painted, p_metal, metal)
    height = np.where(painted, p_height, height)

    # Hot-dip zinc: visible crystals, dull and streaky.
    galv = finish == GALV
    if galv.any():
        tree_points = np.random.default_rng(3).uniform((-8, -8, 30), (8, 8, 104), (70000, 3))
        crystal_values = np.random.default_rng(4).random(70000).astype(np.float32)
        g_pts = pos[galv]
        _, near = cKDTree(tree_points).query(g_pts, k=1, workers=1)
        spangle = np.zeros((H, W), np.float32)
        spangle[galv] = crystal_values[near]
        z_col = srgb_to_linear((162, 165, 162))
        g_color = np.broadcast_to(z_col, (H, W, 3)) * (0.66 + 0.3 * spangle[..., None] + 0.28 * (big[..., None] - 0.5))
        g_rough = 0.33 + 0.26 * spangle + 0.16 * mid
        g_white = smooth(0.58, 0.78, streak + (1 - ao) * 0.22)
        g_color = mix(g_color, np.broadcast_to(srgb_to_linear((188, 186, 176)), (H, W, 3)) * 0.8, g_white * 0.6)
        g_rough = g_rough + g_white * 0.28
        g_metal = 1.0 - g_white * 0.65
        g_color = mix(g_color, np.broadcast_to(steel, (H, W, 3)), scratch * 0.7)
        g_rough = g_rough * (1 - scratch * 0.5) + 0.3 * scratch * 0.5
        g_height = 0.0022 * (spangle - 0.5) + 0.0012 * (micro - 0.5) - scratch * 0.003
        g_edge_dark = smooth(0.1, 0.8, 1 - ao) * 0.5
        g_color = g_color * (1 - g_edge_dark[..., None])
        # The index holes up the mast.
        for hole_z in (66, 72, 78, 84, 90):
            d = np.hypot((np.angle(np.exp(1j * (theta + math.pi / 2)))) * 1.2, pos[..., 2] - hole_z)
            hole = (d < 0.2) & galv & (radial < 1.3)
            lip = (d < 0.27) & galv & (radial < 1.3)
            g_color = np.where(hole[..., None], np.array((0.006, 0.006, 0.006), np.float32), g_color)
            g_rough = np.where(hole, 0.9, g_rough)
            g_height = g_height - hole * 0.05 + (lip & ~hole) * 0.012
        color = np.where(galv[..., None], g_color, color)
        rough = np.where(galv, g_rough, rough)
        metal = np.where(galv, g_metal, metal)
        height = np.where(galv, g_height, height)

    # Black oxide: rubs back to steel on edges and rusts in small spots.
    oxide = finish == OXIDE
    o_wear = smooth(0.44, 0.62, edge * 0.95 + (fine - 0.5) * 0.7 + (mid - 0.5) * 0.3)
    o_color = np.broadcast_to(srgb_to_linear((42, 42, 44)), (H, W, 3)) * (0.75 + 0.5 * mid[..., None])
    o_color = mix(o_color, np.broadcast_to(steel, (H, W, 3)) * 0.8, o_wear * 0.9)
    o_rust = smooth(0.8, 0.9, field(noise(pts, 3.6, 11, 3)) + crevice * 0.06)
    o_color = mix(o_color, rust_c, o_rust * 0.7)
    o_rough = 0.4 + 0.2 * fine - 0.1 * o_wear + 0.35 * o_rust
    o_metal = (1 - o_rust) * 0.92
    o_height = 0.0016 * (micro - 0.5) + o_rust * 0.006 * (rust_tone - 0.3) - o_wear * 0.002
    color = np.where(oxide[..., None], o_color, color)
    rough = np.where(oxide, o_rough, rough)
    metal = np.where(oxide, o_metal, metal)
    height = np.where(oxide, o_height, height)

    # Plated fasteners, some clear zinc and some the yellow passivate fasteners often come in.
    zinc = finish == ZINC
    yellow = np.mod(part * 7.0, 1.0) > 0.68
    z_base = np.where(yellow[..., None], srgb_to_linear((176, 158, 112)), srgb_to_linear((186, 188, 186)))
    z_color = z_base * (0.52 + 0.3 * mid[..., None])
    z_white = smooth(0.48, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.5)
    z_color = mix(z_color, np.broadcast_to(rust_mid, (H, W, 3)), z_white * 0.55)
    z_color = mix(z_color, np.broadcast_to(steel, (H, W, 3)), smooth(0.5, 0.8, edge) * 0.5)
    z_rough = 0.3 + 0.2 * fine + 0.4 * z_white
    color = np.where(zinc[..., None], z_color, color)
    rough = np.where(zinc, z_rough, rough)
    metal = np.where(zinc, 1 - z_white * 0.75, metal)
    height = np.where(zinc, 0.0012 * (micro - 0.5), height)

    # Brass: tarnished brown in the hollows, bright where a hand or a rope rubs it.
    brass = finish == BRASS
    b_tarnish = smooth(0.32, 0.72, mid * 0.5 + big * 0.2 + crevice * 0.7 - edge * 0.45)
    b_color = mix(np.broadcast_to(srgb_to_linear((214, 170, 92)), (H, W, 3)), np.broadcast_to(srgb_to_linear((92, 66, 34)), (H, W, 3)), b_tarnish)
    b_green = smooth(0.66, 0.84, field(noise(pts, 2.1, 12, 3)) + crevice * 0.26)
    b_color = mix(b_color, np.broadcast_to(srgb_to_linear((86, 112, 86)), (H, W, 3)), b_green * 0.55)
    b_rough = 0.24 + 0.34 * b_tarnish + 0.1 * fine + 0.2 * b_green
    color = np.where(brass[..., None], b_color, color)
    rough = np.where(brass, b_rough, rough)
    metal = np.where(brass, 1 - b_green * 0.7, metal)
    height = np.where(brass, 0.0012 * (micro - 0.5), height)

    # The lever's rubber sleeve, ribbed and worn smooth where it is gripped.
    rubber = finish == RUBBER
    ribs = 0.5 + 0.5 * np.sin(pos[..., 2] * 2 * math.pi / 0.32)
    grip_wear = smooth(0.4, 0.8, big + (mid - 0.5))
    color = np.where(rubber[..., None], np.broadcast_to(srgb_to_linear((30, 30, 30)), (H, W, 3)) * (0.75 + 0.5 * fine[..., None]), color)
    rough = np.where(rubber, 0.72 + 0.16 * fine - grip_wear * 0.18, rough)
    metal = np.where(rubber, 0.0, metal)
    height = np.where(rubber, 0.012 * ribs * (1 - grip_wear * 0.7) + 0.002 * micro, height)

    # The aluminium data plate, stamped.
    plate = finish == PLATE
    art3 = stencil_image(["FIELD MAST", "FM-92  04417"], (680, 380), bridge=False)
    a = np.angle(np.exp(1j * (theta - math.pi)))
    uu = a * 2.31 / 3.39 + 0.5
    vv = (pos[..., 2] - 3.1) / 1.9
    stamp = sample_image(art3, np.clip(uu, -1, 2), np.clip(vv, -1, 2))
    pc = np.broadcast_to(srgb_to_linear((176, 176, 170)), (H, W, 3)) * (0.82 + 0.3 * mid[..., None])
    pc = mix(pc, np.broadcast_to(np.array((0.015, 0.015, 0.016), np.float32), (H, W, 3)), stamp * 0.85)
    pc = mix(pc, pc * 0.45, smooth(0.45, 0.8, crevice + (mid - 0.5)))
    color = np.where(plate[..., None], pc, color)
    rough = np.where(plate, 0.42 + 0.22 * fine + stamp * 0.3, rough)
    metal = np.where(plate, 1 - stamp * 0.85, metal)
    height = np.where(plate, stamp * 0.012 + 0.001 * (micro - 0.5), height)

    # Rebar stakes: all rust, bright where the hammer lands.
    stake = finish == RUST
    s_struck = (nor[..., 2] > 0.55) & smooth(0.3, 0.55, mid + 0.2).astype(bool)
    s_color = rust_c * (0.72 + 0.5 * fine[..., None])
    s_color = np.where(s_struck[..., None], np.broadcast_to(steel, (H, W, 3)) * 0.46, s_color)
    color = np.where(stake[..., None], s_color, color)
    rough = np.where(stake, np.where(s_struck, 0.5, 0.86 + 0.1 * fine), rough)
    metal = np.where(stake, np.where(s_struck, 0.9, 0.0), metal)
    height = np.where(stake, 0.024 * (fine - 0.5) + 0.012 * (micro - 0.5), height)

    # Field dirt over everything: settles on what faces up, in the corners, and climbs from the ground.
    upward = np.clip(nor[..., 2], 0, 1)
    low = np.clip(1 - pos[..., 2] / 15.0, 0, 1) ** 1.5
    settled = smooth(0.38, 0.88, upward * 0.82 + (big - 0.5) * 0.34 + crevice * 0.2)
    splash = low * smooth(0.48, 0.66, field(noise(pts * np.array((1.3, 1.3, 0.55), np.float32), 1.2, 13, 4)) + low * 0.14)
    speckle = low * smooth(0.64, 0.72, field(noise(pts, 7.5, 14, 2)))
    dirt = np.clip(settled * 0.5 + splash * 0.72 + speckle * 0.62, 0, 0.92)
    dirt_c = np.broadcast_to(srgb_to_linear((102, 88, 68)), (H, W, 3)) * (0.75 + 0.5 * fine[..., None])
    color = mix(color, dirt_c, dirt)
    rough = rough * (1 - dirt) + 0.93 * dirt
    metal = metal * (1 - dirt)
    height = height + dirt * 0.004 * (fine - 0.35)

    # A little occlusion stays in the colour, so the shapes hold up under engine lighting.
    color = color * (0.72 + 0.28 * ao[..., None])
    rough = np.clip(rough, 0.1, 1)
    metal = np.clip(metal, 0, 1)

    # The noises only exist on covered texels. Fill the gutters from the islands or texture filtering draws every seam.
    solid = ndi.binary_erosion(cover, iterations=1)
    height = fill_from(solid, height)[0]
    normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
    color, rough, metal, normal = fill_from(solid, color, rough, metal, normal)
    save_rgb(os.path.join(OUT, "cf_hardware_color.png"), color)
    save_gray(os.path.join(OUT, "cf_hardware_rough.png"), rough)
    save_gray(os.path.join(OUT, "cf_hardware_metal.png"), metal)
    save_gray(os.path.join(OUT, "cf_hardware_ao.png"), np.clip(ao * 1.03, 0, 1))
    save_normal(os.path.join(OUT, "cf_hardware_normal.png"), normal)
    print("hardware painted", flush=True)


def grid_normals(p, flip=False):
    """Unit normals, tangents and bitangents of a grid of points (rows, cols, 3)."""
    dv = np.gradient(p, axis=0)
    du = np.gradient(p, axis=1)
    n = np.cross(du, dv)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
    if flip:
        n = -n
    return n, du, dv


def resample(field_, rows, cols):
    """Bicubic resample of a grid to rows x cols, keeping corners on corners."""
    h, w = field_.shape[:2]
    jj = np.linspace(0, h - 1, rows)
    ii = np.linspace(0, w - 1, cols)
    J, I = np.meshgrid(jj, ii, indexing="ij")
    if field_.ndim == 2:
        return ndi.map_coordinates(field_, (J, I), order=3, mode="nearest")
    return np.stack([ndi.map_coordinates(field_[..., c], (J, I), order=3, mode="nearest") for c in range(field_.shape[-1])], -1)


def tangent_bake(high, low, rows, cols, flip=False):
    """The high grid's normals in the tangent frame of the low grid, over a rows x cols texture region."""
    hn, _, _ = grid_normals(high, flip)
    ln, ldu, ldv = grid_normals(low, flip)
    hn = resample(hn.astype(np.float32), rows, cols)
    hn /= np.linalg.norm(hn, axis=-1, keepdims=True) + 1e-9
    N = resample(ln.astype(np.float32), rows, cols)
    N /= np.linalg.norm(N, axis=-1, keepdims=True) + 1e-9
    T = resample(ldu.astype(np.float32), rows, cols)
    B = resample(ldv.astype(np.float32), rows, cols)
    T -= N * (T * N).sum(-1, keepdims=True)
    T /= np.linalg.norm(T, axis=-1, keepdims=True) + 1e-9
    B -= N * (B * N).sum(-1, keepdims=True)
    B /= np.linalg.norm(B, axis=-1, keepdims=True) + 1e-9
    out = np.stack(((hn * T).sum(-1), (hn * B).sum(-1), (hn * N).sum(-1)), -1)
    out[..., 2] = np.maximum(out[..., 2], 0.02)
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def weave(rows, cols, px_per_in_u, px_per_in_v, period, seed, slub=0.3):
    """Plain weave height 0..1, with thread-to-thread variation."""
    v, u = np.meshgrid(np.arange(rows) / px_per_in_v, np.arange(cols) / px_per_in_u, indexing="ij")
    period_u = max(4, round(period * px_per_in_u)) / px_per_in_u
    period_v = max(4, round(period * px_per_in_v)) / px_per_in_v
    r = np.random.default_rng(seed)
    warp_var = ndi.gaussian_filter1d(r.standard_normal(cols + 64), 2.0)[: cols]
    weft_var = ndi.gaussian_filter1d(r.standard_normal(rows + 64), 2.0)[: rows]
    wu = 2 * np.pi * u / period_u + warp_var[None, :] * slub
    wv = 2 * np.pi * v / period_v + weft_var[:, None] * slub
    over = np.sin(wu) * np.sin(wv)
    warp = (0.5 + 0.5 * np.cos(wu)) * (0.5 + 0.5 * over)
    weft = (0.5 + 0.5 * np.cos(wv)) * (0.5 - 0.5 * over)
    return np.maximum(warp, weft) + 0.022 * warp_var[None, :] + 0.022 * weft_var[:, None]


def paint_soft():
    meta = json.load(open(os.path.join(WORK, "atlas.json")))
    rects, sizes = meta["rects"], meta["sizes"]
    grids = np.load(os.path.join(WORK, "soft_grids.npz"))
    S = 2048
    pos4 = load("bake_soft_pos")
    nor4 = load("bake_soft_nor")
    ao4 = load("bake_soft_ao")
    cover = pos4[..., :3].max(-1) > 1e-3
    pos = (pos4[..., :3] - 0.5) * 400.0
    nor = nor4[..., :3] * 2 - 1
    pos, nor = fill_from(cover, pos, nor)
    aoc = cover[:: S // ao4.shape[0], :: S // ao4.shape[1]]
    ao = fill_from(aoc, ao4[..., 0])[0]
    ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.8), S / ao.shape[1], order=1), 0, 1)
    pts = pos[cover]

    def field(values):
        out = np.zeros((S, S), np.float32)
        out[cover] = values
        return out

    big = field(noise(pts, 0.09, 21, 3))
    mid = field(noise(pts, 0.42, 22, 4))
    fine = field(noise(pts, 2.2, 23, 3))
    speck = field(noise(pts, 8.0, 24, 2))

    density = 2048 * rects["strip"][2]
    normal = np.zeros((S, S, 3), np.float32)
    normal[..., 2] = 1
    height = np.zeros((S, S), np.float32)
    tone = np.ones((S, S, 3), np.float32)
    seam_mask = np.zeros((S, S), np.float32)
    is_strip = np.zeros((S, S), bool)
    thread = np.zeros((S, S), np.float32)

    r = np.random.default_rng(55)
    for key, (u0, v0, scale) in rects.items():
        w_in, h_in = sizes[key]
        x0, y0 = int(round(u0 * S)), int(round(v0 * S))
        cols, rows = int(round(w_in * scale * S)), int(round(h_in * scale * S))
        pad = 5
        ax0, ay0 = max(0, x0 - pad), max(0, y0 - pad)
        V, U = np.mgrid[0 : rows, 0 : cols]
        uu = U / max(cols - 1, 1)
        vv = V / max(rows - 1, 1)
        px_u = cols / w_in
        px_v = rows / h_in
        if key == "strip":
            is_strip[y0 : y0 + rows, x0 : x0 + cols] = True
            wv = weave(rows, cols, px_u, px_v, 0.2, 77, slub=0.2)
            h = 0.0035 * wv
            edge_u = np.minimum(vv, 1 - vv) * h_in
            stitch = (np.minimum(np.abs(edge_u - 0.22), 9) < 0.035) * (np.mod(uu * w_in, 0.2) < 0.13)
            h += stitch * 0.012
            height[y0 : y0 + rows, x0 : x0 + cols] = h
            thread[y0 : y0 + rows, x0 : x0 + cols] = stitch
            continue
        bag = key[:-1]
        side = key[-1]
        grid = grids[bag + ("_top" if side == "t" else "_bottom")].astype(np.float64)
        jj = np.round(np.linspace(0, grid.shape[0] - 1, 10)).astype(int)
        ii = np.round(np.linspace(0, grid.shape[1] - 1, 15)).astype(int)
        low = grid[np.ix_(jj, ii)]
        n = tangent_bake(grid, low, rows, cols, flip=side == "b")
        normal[y0 : y0 + rows, x0 : x0 + cols] = n

        full_w = 19.0
        full_h = 11.0
        px_u_real = cols / full_w
        px_v_real = rows / full_h
        wv = weave(rows, cols, px_u_real, px_v_real, 0.16, int(r.integers(1, 9999)), slub=0.34)

        # Crinkle: long soft wrinkles running in from the corners and the sewn edges, as a filled sack has them.
        seed = int(r.integers(1, 1 << 30))
        rg = np.random.default_rng(seed)
        crinkle = ndi.gaussian_filter(rg.standard_normal((rows, cols)), (6 * px_v_real / 37.8, 22 * px_u_real / 37.8))
        crinkle /= crinkle.std() + 1e-6
        cross = ndi.gaussian_filter(rg.standard_normal((rows, cols)), (22 * px_v_real / 37.8, 5 * px_u_real / 37.8))
        cross /= cross.std() + 1e-6
        small = ndi.gaussian_filter(rg.standard_normal((rows, cols)), 2.2 * px_u_real / 37.8)
        small /= small.std() + 1e-6
        along_edge = np.minimum(np.minimum(vv, 1 - vv) * full_h, np.minimum(uu, 1 - uu) * full_w)
        edge_weight = np.exp(-along_edge / 1.9)
        creases = np.abs(crinkle) ** 0.9 * 0.06 * (0.25 + edge_weight) + np.abs(cross) ** 0.9 * 0.05 * (0.2 + 1.2 * edge_weight * (np.minimum(uu, 1 - uu) < 0.2))
        h = 0.0085 * wv + (0.03 - creases) + 0.0028 * small

        # The sewn seam round the edge: a raised flange, two lines of chain stitch.
        flange = smooth(0.42, 0.26, along_edge)
        h = h + flange * 0.045
        stitch_line = (np.abs(along_edge - 0.4) < 0.022)
        along = np.where(np.minimum(uu, 1 - uu) * full_w < np.minimum(vv, 1 - vv) * full_h, vv * full_h, uu * full_w)
        stitches = stitch_line * (np.mod(along, 0.22) < 0.15)
        h = h + stitches * 0.012 - stitch_line * 0.012
        height[y0 : y0 + rows, x0 : x0 + cols] = h
        seam_mask[y0 : y0 + rows, x0 : x0 + cols] = flange
        thread[y0 : y0 + rows, x0 : x0 + cols] = stitches

        # Each bag came out of a different batch and has lain out differently.
        tint = np.array((1.0 + r.normal(0, 0.05), 1.0 + r.normal(0, 0.04), 1.0 + r.normal(0, 0.05)), np.float32) * r.uniform(0.86, 1.08)
        tone[y0 : y0 + rows, x0 : x0 + cols] = tint
        # Weave shows in the colour too: thread tops are lighter.
        tone[y0 : y0 + rows, x0 : x0 + cols] *= (0.84 + 0.3 * np.clip(wv, 0, 1))[..., None]
        creased = np.clip(creases * 9, 0, 1)
        tone[y0 : y0 + rows, x0 : x0 + cols] *= (1 - creased * 0.22)[..., None]

    hessian = np.broadcast_to(srgb_to_linear((158, 128, 82)), (S, S, 3))
    hessian_dark = np.broadcast_to(srgb_to_linear((112, 86, 52)), (S, S, 3))
    color = mix(hessian, hessian_dark, smooth(0.3, 0.75, mid * 0.7 + big * 0.3))
    color = color * tone
    color = np.where(is_strip[..., None], srgb_to_linear((176, 172, 158)) * (0.85 + 0.25 * fine[..., None]), color)

    # Damp from the ground, dust on top, grime in the folds.
    z = pos[..., 2]
    damp = smooth(0.3, 1.0, np.clip(1 - z / 7.5, 0, 1)) * smooth(0.3, 0.68, big + (mid - 0.5) * 0.8)
    color = color * (1 - damp[..., None] * 0.52)
    upward = np.clip(nor[..., 2], 0, 1)
    dust = smooth(0.5, 0.95, upward * 0.72 + (mid - 0.5) * 0.7 + (big - 0.5) * 0.4)
    color = mix(color, np.broadcast_to(srgb_to_linear((166, 146, 112)), (S, S, 3)) * (0.8 + 0.4 * speck[..., None]), dust * 0.28)
    mud = smooth(0.58, 0.74, field(noise(pts * np.array((1, 1, 0.6), np.float32), 1.1, 25, 4)) + np.clip(1 - z / 6, 0, 1) * 0.18)
    color = mix(color, np.broadcast_to(srgb_to_linear((66, 54, 42)), (S, S, 3)), mud * 0.68)
    color = mix(color, np.broadcast_to(srgb_to_linear((148, 132, 100)), (S, S, 3)), thread[..., None] * 0.6)
    color = color * (0.68 + 0.32 * ao[..., None])
    rough = np.clip(0.9 + 0.08 * fine - damp * 0.14 + mud * 0.04, 0.5, 1)

    detail = to_normal(ndi.gaussian_filter(height, 0.45), density, 1.0)
    final = blend_normals(normal, detail)

    color, rough, final = fill_from(cover, color, rough, final)
    save_rgb(os.path.join(OUT, "cf_soft_color.png"), color)
    save_gray(os.path.join(OUT, "cf_soft_rough.png"), rough)
    save_gray(os.path.join(OUT, "cf_soft_ao.png"), ao)
    save_normal(os.path.join(OUT, "cf_soft_normal.png"), final)
    print("soft painted", flush=True)


def paint_flag():
    W, H = 2048, 1024
    FLY, DROP = 40.0, 27.0
    grid = np.load(os.path.join(WORK, "soft_grids.npz"))["flag"].astype(np.float64)
    jj = np.round(np.linspace(0, grid.shape[0] - 1, 27)).astype(int)
    ii = np.round(np.linspace(0, grid.shape[1] - 1, 41)).astype(int)
    low = grid[np.ix_(jj, ii)]
    base_n = tangent_bake(grid, low, H, W)
    V, U = np.mgrid[0 : H, 0 : W]
    u = U / (W - 1)
    v = V / (H - 1)
    x = u * FLY
    y = v * DROP
    px_u, px_v = W / FLY, H / DROP
    r = np.random.default_rng(1944)

    def blur_noise(sy, sx, seed):
        f = ndi.gaussian_filter(np.random.default_rng(seed).standard_normal((H, W)), (sy, sx), mode="reflect")
        return f / (f.std() + 1e-7)

    # Small wrinkles the coarse folds leave behind: tension lines off the two hooks, puckers along the hems.
    a_top = np.arctan2(y - DROP, x + 0.5)
    a_low = np.arctan2(y, x + 0.5)
    fan = np.sin(a_top * 22 + 1.0 * blur_noise(130, 130, 3)) * np.exp(-np.hypot(x, y - DROP) / 8.5) + np.sin(a_low * 19 + 1.0 * blur_noise(130, 130, 4)) * np.exp(-np.hypot(x, y) / 8.0)
    pucker = blur_noise(40, 7, 5) * np.exp(-np.minimum(y, DROP - y) / 2.4) * 0.8 + blur_noise(9, 40, 8) * np.exp(-(FLY - x) / 2.4) * 0.8
    soft_w = blur_noise(26, 26, 6)
    fine_w = blur_noise(7, 7, 7)
    # Secondary folds follow the big ones' lean, too fine for the mesh, so they live in the normal map.
    def ridge(t, k):
        return 2.0 * (np.exp(k * (np.cos(t) - 1.0)) - np.exp(-2.0 * k)) / (1.0 - np.exp(-2.0 * k)) - 1.0

    lean = 0.34 * (v - 0.5) + 0.05 * blur_noise(120, 120, 51)
    build_up = 0.35 + 0.65 * np.clip(u / 0.5, 0, 1)
    patches = smooth(-0.35, 0.75, blur_noise(110, 150, 54))
    secondary = (
        0.13 * ridge(2 * np.pi * ((u - lean) * 5.6 + 0.2) + 0.7 * blur_noise(170, 170, 52), 1.9)
        + 0.016 * ridge(2 * np.pi * ((u - lean * 1.2) * 11.0) + 0.8 * blur_noise(130, 130, 53), 1.4)
    ) * build_up * patches
    wrinkle = 0.08 * fan + 0.026 * pucker + 0.016 * soft_w + 0.0028 * fine_w + secondary

    # Hem: top, bottom and fly turned over twice and sewn, two lines of stitching.
    edge_top, edge_low, edge_fly = DROP - y, y, FLY - x
    edge = np.minimum(np.minimum(edge_top, edge_low), edge_fly)
    hem = smooth(1.02, 0.96, edge)
    height = wrinkle + hem * 0.022
    stitch_lines = (np.abs(edge - 0.2) < 0.022) | (np.abs(edge - 0.88) < 0.022)
    along = np.where(edge_fly < np.minimum(edge_top, edge_low), y, x)
    stitches = stitch_lines & (np.mod(along, 0.14) < 0.095)
    height += stitches * 0.012 - stitch_lines * 0.009

    wv = weave(H, W, px_u, px_v, 0.11, 13, slub=0.22)
    height += 0.0018 * wv

    # Tears: the fly end frays and rips, and it has been shot through.
    fray_noise = 0.26 * blur_noise(10, 3, 21) + 0.14 * blur_noise(3, 2, 22) + 0.1 * blur_noise(30, 8, 23)
    cut = edge_fly + fray_noise * 0.9 - 0.12
    for centre, width, depth in ((5.5, 0.34, 5.4), (15.4, 0.22, 3.1), (22.6, 0.42, 7.2), (9.8, 0.13, 1.7)):
        lean = 0.12 * r.normal()
        offset = (y - centre) - lean * edge_fly + 0.3 * blur_noise(9, 18, int(r.integers(99, 9999))) * 0.5
        wedge = np.abs(offset) - width * np.clip(1 - edge_fly / depth, 0, 1)
        rip = (wedge < 0) & (edge_fly < depth)
        cut = np.where(rip, -1.0, cut)
    corner = np.hypot(edge_fly - 0.0, edge_low - 0.0)
    cut = np.where(corner + fray_noise * 0.6 < 1.3, -1.0, cut)
    alpha = np.zeros((H, W), np.float32)
    alpha[cut > 0] = 1.0

    # A burst across the fly end and two strays, not an even scatter.
    holes = [(29.3, 19.6, 0.21), (30.9, 18.1, 0.15), (28.2, 17.4, 0.18), (34.6, 7.4, 0.2), (17.1, 22.6, 0.11)]
    scorch = np.zeros((H, W), np.float32)
    rim = blur_noise(3, 3, 41)
    for hx, hy, hr in holes:
        d = np.hypot(x - hx, y - hy) + rim * 0.05
        alpha[d < hr] = 0
        scorch = np.maximum(scorch, np.exp(-np.maximum(d - hr, 0) / 0.16) * 0.7)
        height -= np.exp(-np.maximum(d - hr, 0) / 0.2) * 0.012 * (d >= hr)

    # Loose threads off the torn fly edge.
    thread_img = Image.new("L", (W, H), 0)
    td = ImageDraw.Draw(thread_img)
    for _ in range(520):
        ty = r.uniform(0.02, 0.98) * H
        tx = W - 1 - r.uniform(0, 30)
        length = r.uniform(8, 44)
        drift = r.normal(0, 0.28)
        points = [(tx - 14, ty)]
        for t in np.linspace(0.3, 1, 5):
            points.append((min(W - 1, tx + length * t), ty + drift * length * t * t + r.normal(0, 1.2)))
        td.line(points, fill=255, width=1)
    threads = np.asarray(thread_img, np.float32)[::-1] / 255.0
    alpha = np.maximum(alpha, threads * (edge_fly < 2.0))
    alpha = np.clip(ndi.gaussian_filter(alpha, 0.5) * 1.15, 0, 1)

    normal = blend_normals(base_n, to_normal(ndi.gaussian_filter(height, 0.5), px_u, 1.0, px_v))

    # The cloth stays pale, since the team colour is multiplied over it.
    base = np.array((0.86, 0.85, 0.82), np.float32)
    # Soot and rain work along the cloth, so the grime is streaked that way, not cloudy.
    grime_big = 0.5 + 0.25 * blur_noise(60, 300, 31)
    grime_mid = 0.5 + 0.25 * blur_noise(10, 90, 32)
    grime_fine = 0.5 + 0.25 * blur_noise(2.5, 9, 33)
    out_end = np.clip(x / FLY, 0, 1) ** 1.8
    low_end = np.clip(1 - y / DROP, 0, 1) ** 2
    trough = np.clip(-(grid[..., 1] * 0), 0, 1)
    grime = np.clip(0.2 * out_end + 0.14 * low_end + (grime_big - 0.5) * 0.2 + (grime_mid - 0.5) * 0.22 + (grime_fine - 0.5) * 0.14 + np.exp(-edge / 1.1) * 0.2, 0, 1)
    color = base * (1 - grime[..., None] * np.array((0.5, 0.52, 0.56), np.float32))
    color *= (0.93 + 0.1 * np.clip(wv, 0, 1))[..., None]
    color *= (1 - scorch[..., None] * np.array((0.74, 0.76, 0.8), np.float32))
    # Sewing thread takes the tint less, and hems hold grime.
    color *= (1 - hem[..., None] * 0.07)
    color = np.where(stitches[..., None], color * 1.1, color)
    # Fold shading from the bake keeps the flag's shapes at a distance, where the normal map fades.
    fold = np.clip(base_n[..., 2], 0, 1)
    color *= (0.82 + 0.18 * fold[..., None])
    color *= (1 + np.clip(secondary, -0.3, 0.3)[..., None] * 0.2)
    rough = np.clip(0.78 + 0.1 * grime - 0.03 * np.clip(wv, 0, 1), 0.4, 1)

    save_rgb(os.path.join(OUT, "cf_cloth_color.png"), color)
    save_gray(os.path.join(OUT, "cf_cloth_rough.png"), rough)
    save_gray(os.path.join(OUT, "cf_cloth_alpha.png"), alpha)
    save_normal(os.path.join(OUT, "cf_cloth_normal.png"), normal)
    print("flag painted; holes", int((alpha < 0.5).sum()), flush=True)


def paint_rope():
    """A 3-strand laid rope, tiling in both directions."""
    S = 512
    V, U = np.mgrid[0 : S, 0 : S]
    u, v = U / S, V / S
    strand = np.mod(3.0 * (u + v * 1.0), 1.0)
    profile = np.sqrt(np.clip(1 - (2 * strand - 1) ** 2, 0, 1))
    yarn = 0.5 + 0.5 * np.sin(2 * np.pi * (15 * u - 20 * v))
    fibre = np.random.default_rng(8).standard_normal((S, S))
    fibre = ndi.gaussian_filter(fibre, (6.0, 0.8), mode="wrap")
    fibre /= fibre.std() + 1e-7
    height = profile * 0.05 + yarn * 0.006 * profile + fibre * 0.0012
    normal = to_normal(height, S / 0.8)
    occl = 0.45 + 0.55 * profile
    color = srgb_to_linear((176, 164, 128)) * (occl * (0.88 + 0.12 * yarn) * (0.92 + 0.05 * fibre))[..., None]
    dirt = 0.5 + 0.25 * ndi.gaussian_filter(np.random.default_rng(9).standard_normal((S, S)), 22, mode="wrap") / max(
        1e-7, ndi.gaussian_filter(np.random.default_rng(9).standard_normal((S, S)), 22, mode="wrap").std()
    )
    color = color * (0.72 + 0.4 * dirt[..., None])
    rough = np.clip(0.86 + 0.08 * (1 - profile), 0, 1)
    save_rgb(os.path.join(OUT, "cf_rope_color.png"), color)
    save_gray(os.path.join(OUT, "cf_rope_rough.png"), rough)
    save_normal(os.path.join(OUT, "cf_rope_normal.png"), normal)
    print("rope painted", flush=True)


if __name__ == "__main__":
    if "rope" in JOBS:
        paint_rope()
    if "flag" in JOBS:
        paint_flag()
    if "soft" in JOBS:
        paint_soft()
    if "hw" in JOBS:
        paint_hardware()
