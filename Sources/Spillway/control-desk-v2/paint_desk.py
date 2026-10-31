"""Paint the control desk's maps: python paint_desk.py <work dir> <materials dir> <body|panel|glow> ...

The body works from the bakes, so its wear runs across UV seams: enamel over primer over steel, chipped on real edges and
rubbed where hands and boots go, dust on what faces up. Wear masks stay soft, as hard cut-offs read as pixels at this density.
The panel and the screens are drawn flat, at their own density, so their lettering stays sharp.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
sys.path.insert(0, HERE)
JOBS = set(sys.argv[3:]) or {"body", "panel", "glow"}
sys.argv = sys.argv[:3] + ["none"]
import layout as L  # noqa: E402
from paint import OUT, WORK, fill_from, load, mix, noise, save_gray, save_normal, save_rgb, smooth, srgb_to_linear, to_normal  # noqa: E402

from scipy import ndimage as ndi  # noqa: E402

FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
NAVY, GREY, CHROME, BLACK, RUBBER, LAM, RED, YELLOW, PAPER, ENAMEL, KEY, PLATE, BOARD = range(13)


def font(size, condensed=True):
    f = ImageFont.truetype(FONT, int(size))
    try:
        f.set_variation_by_name("SemiBold Condensed" if condensed else "SemiBold")
    except Exception:
        pass
    return f


def text(d, xy, s, f, fill, anchor="mm"):
    d.text(xy, s, fill=fill, font=f, anchor=anchor)


def paint_body():
    facts = json.load(open(os.path.join(WORK, "desk.json")))
    density = facts["density"]
    pos4 = load("bake_desk_pos")
    nor4 = load("bake_desk_nor")
    facts4 = load("bake_desk_facts")
    ao4 = load("bake_desk_ao")
    H, W = pos4.shape[:2]
    cover = pos4[..., :3].max(-1) > 1e-3
    pos = (pos4[..., :3] - 0.5) * 400.0
    nor = nor4[..., :3] * 2 - 1
    finish = np.rint(facts4[..., 0] * 16).astype(np.int32)
    part = facts4[..., 1]
    del pos4, nor4, facts4
    pos, nor, finish, part = fill_from(cover, pos, nor, finish, part)
    aoc = cover[:: H // ao4.shape[0], :: W // ao4.shape[1]]
    ao = fill_from(aoc, ao4[..., 0])[0]
    ao = np.clip(ndi.zoom(ndi.gaussian_filter(ao, 0.7), W / ao.shape[1], order=1), 0, 1).astype(np.float32)
    del ao4

    curve = np.zeros((H, W), np.float32)
    for axis in (0, 1):
        dn = np.gradient(nor, axis=axis)
        dp = np.gradient(pos, axis=axis)
        curve += (dn * dp).sum(-1) / np.maximum((dp * dp).sum(-1), 1e-5)
    del dn, dp
    curve[~ndi.binary_erosion(cover, iterations=2)] = 0
    convex = np.clip((curve - 2.2) * 0.34, 0, 1)
    edge = np.clip(ndi.gaussian_filter(convex, 2.5) * 2.6 + ndi.gaussian_filter(convex, 7.0) * 3.2, 0, 1)
    del curve, convex
    pts = pos[cover]

    def field(values):
        out = np.zeros((H, W), np.float32)
        out[cover] = values
        return out

    big = field(noise(pts, 0.05, 1, 3))
    mid = field(noise(pts, 0.32, 2, 4))
    fine = field(noise(pts, 1.5, 3, 3))
    micro = field(noise(pts, 6.0, 4, 2))
    crevice = np.clip((1 - ao) * 1.3, 0, 1)
    X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
    up = np.clip(nor[..., 2], 0, 1)
    front = np.clip(nor[..., 0], 0, 1)
    full = lambda c: np.broadcast_to(srgb_to_linear(c), (H, W, 3))

    # Where people wear it: boots along the kick and in the kneehole, hands on drawers, the latch and the worktop's edge.
    kick = smooth(11.0, 2.0, Z) * front
    drawers = smooth(5.0, 1.0, np.abs(Z - 12.0) * 0.1 + np.abs(Y - 41.0) * 0.14) * (X > 30.0)
    latch = smooth(5.5, 1.0, np.hypot(Y + 28.6, Z - 21.0)) * (X > 30.0)
    high = smooth(40.0, 64.0, Z)

    # Blue enamel over grey primer over steel. Chips are big enough and soft enough not to read as pixels.
    chip = (
        edge * smooth(0.25, 0.7, mid * 0.6 + fine * 0.4) * 1.0
        + (mid - 0.5) * 0.46
        + (big - 0.5) * 0.3
        + (fine - 0.5) * 0.56
        + kick * 0.13
        + drawers * 0.1
        + latch * 0.12
    )
    to_primer = smooth(0.64, 0.72, chip)
    to_steel = smooth(0.74, 0.84, chip)
    primer = full((122, 118, 106)) * (0.85 + 0.3 * fine[..., None])
    bare = full((128, 126, 122)) * (0.7 + 0.45 * micro[..., None])
    rust = mix(full((62, 36, 22)), full((116, 68, 38)), smooth(0.35, 0.8, field(noise(pts, 1.4, 8, 3))))
    rusty = smooth(0.42, 0.75, field(noise(pts, 0.7, 9, 3)) + smooth(30.0, 0.0, Z) * 0.14)

    def enamel(colour, faded):
        fade = smooth(0.32, 0.72, big + (mid - 0.5) * 0.3) * 0.4 + up * 0.14
        base = mix(full(colour), full(faded), fade) * (0.86 + 0.26 * part[..., None])
        return base * (0.93 + 0.14 * mid[..., None])

    def layered(base):
        c = mix(base, primer, to_primer)
        c = mix(c, mix(bare, rust, rusty * 0.62), to_steel)
        return c

    color = np.zeros((H, W, 3), np.float32)
    rough = np.full((H, W), 0.6, np.float32)
    metal = np.zeros((H, W), np.float32)
    height = np.zeros((H, W), np.float32)

    def put(mask, c, r, m=0.0, h=0.0):
        nonlocal color, rough, metal, height
        color = np.where(mask[..., None], c, color)
        rough = np.where(mask, r, rough)
        metal = np.where(mask, m, metal)
        height = np.where(mask, h, height)

    peel = 0.0012 * (micro - 0.5)
    painted_rough = 0.36 + 0.16 * mid + 0.08 * fine
    painted_rough = painted_rough * (1 - to_primer) + (0.72 + 0.1 * fine) * to_primer
    painted_rough = painted_rough * (1 - to_steel) + (0.5 + 0.14 * fine + rusty * 0.3) * to_steel
    painted_metal = to_steel * (1 - rusty * 0.8) * 0.68
    painted_height = peel + (1 - to_primer) * 0.006 + (1 - to_steel) * 0.006
    # The worn gloss of hands, without taking the paint off.
    rubbed = np.clip(drawers * smooth(0.4, 0.7, mid) * 0.8 + latch * 0.8, 0, 1)
    painted_rough = painted_rough - rubbed * 0.12

    put(finish == NAVY, layered(enamel((42, 66, 124), (66, 88, 136))), painted_rough, painted_metal, painted_height)
    put(finish == GREY, layered(enamel((96, 102, 108), (118, 122, 124))), painted_rough, painted_metal, painted_height)
    put(finish == YELLOW, layered(enamel((226, 160, 8), (200, 150, 30))), painted_rough, painted_metal, painted_height)

    # Plated steel: dull, with its edges rubbed bright and a little rust in the corners.
    bright = smooth(0.35, 0.72, edge * 0.8 + (mid - 0.5) * 0.7 + (fine - 0.5) * 0.5)
    c = mix(full((128, 128, 124)), full((186, 186, 180)), bright)
    c = mix(c, rust, smooth(0.66, 0.84, field(noise(pts, 2.2, 13, 3)) + crevice * 0.24) * 0.6)
    put(finish == CHROME, c, 0.34 + 0.16 * fine - bright * 0.1, 0.68, 0.0012 * (micro - 0.5))

    # Black plastics and oxide: darker than looks right, or the engine reads them slate.
    scuff = smooth(0.45, 0.8, edge * 0.9 + (fine - 0.5) * 0.7)
    c = full((11, 11, 12)) * (0.8 + 0.4 * mid[..., None])
    c = mix(c, full((60, 60, 62)), scuff * 0.55)
    put(finish == BLACK, c, 0.42 + 0.14 * mid + scuff * 0.1, 0.0, 0.0008 * (micro - 0.5))
    put(finish == RUBBER, full((9, 9, 9)) * (0.85 + 0.3 * fine[..., None]), 0.8 + 0.1 * mid, 0.0, 0.0012 * (micro - 0.5))
    # The keys, shiny where the fingers go.
    c = full((16, 16, 17)) * (0.8 + 0.3 * part[..., None])
    put(finish == KEY, c, 0.3 + 0.2 * part, 0.0, 0.0)

    # The worktop: a pale laminate, polished by forearms, with scratches, pen and a mug's rings. Drawn from above, as a plan.
    scale = 16
    plan = Image.new("L", (int(120 * scale), int(44 * scale)), 0)
    rings = Image.new("L", plan.size, 0)
    d = ImageDraw.Draw(plan)
    r = np.random.default_rng(23)
    for _ in range(260):
        # Mostly short and along the operator's own reach.
        x0, y0 = r.uniform(0, plan.size[0]), r.uniform(0, plan.size[1])
        a = r.normal(0, 0.5) + (math.pi / 2 if r.random() < 0.25 else 0)
        n = r.uniform(10, 54)
        d.line((x0, y0, x0 + math.cos(a) * n, y0 + math.sin(a) * n), fill=int(r.uniform(70, 200)), width=1)
    dr = ImageDraw.Draw(rings)
    for (rx, ry), strength in (((L.MUG_XY[1] + 60, L.MUG_XY[0] + 8), 150), ((L.MUG_XY[1] + 55.5, L.MUG_XY[0] + 11), 90), ((L.MUG_XY[1] + 57, L.MUG_XY[0] + 3.5), 60), ((64, 28), 55)):
        s = scale
        dr.ellipse(((rx - 1.46) * s, (ry - 1.46) * s, (rx + 1.46) * s, (ry + 1.46) * s), outline=strength, width=2)
    plan = np.asarray(plan.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    rings = np.asarray(rings.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255

    def on_plan(img):
        return ndi.map_coordinates(img, (((X + 8.0) * scale), ((Y + 60.0) * scale)), order=1, mode="constant", cval=0.0)

    is_top = (finish == LAM) & (nor[..., 2] > 0.5)
    scratch = on_plan(plan) * is_top
    ring = on_plan(rings) * is_top
    arm = smooth(16.0, 5.0, np.abs(X - 27.0)) * smooth(52.0, 22.0, np.abs(Y + 2.0)) * smooth(0.25, 0.65, field(noise(pts, 0.16, 15, 2)))
    speck = field(noise(pts, 9.0, 16, 1))
    c = full((84, 92, 84)) * (0.94 + 0.12 * speck[..., None]) * (0.94 + 0.12 * big[..., None])
    c = mix(c, full((106, 112, 100)), arm * 0.6)
    c = mix(c, full((150, 152, 140)), scratch * 0.42)
    c = mix(c, full((58, 42, 28)), ring * 0.6)
    put(finish == LAM, c, 0.44 - arm * 0.14 + scratch * 0.2 + ring * 0.1, 0.0, -scratch * 0.002 + 0.0005 * (speck - 0.5))

    # The red telephone, rubbed pink on its corners; the mug; paper; plates.
    worn = smooth(0.42, 0.78, edge * 0.85 + (fine - 0.5) * 0.6 + (mid - 0.5) * 0.25)
    put(finish == RED, mix(full((122, 10, 8)) * (0.9 + 0.2 * mid[..., None]), full((168, 70, 60)), worn * 0.7), 0.3 + 0.12 * mid + worn * 0.1, 0.0, 0.0)
    rim = smooth(3.3, 3.55, Z - 31.5) * smooth(0.45, 0.65, fine)
    put(finish == ENAMEL, mix(full((206, 208, 198)), full((16, 16, 18)), np.clip(rim + worn * 0.8, 0, 1)), 0.25 + worn * 0.3, 0.0, 0.0)
    # The log's lines, from its plan position.
    lines = smooth(0.55, 0.9, 0.5 + 0.5 * np.sin(X * 2 * math.pi / 0.8)) * smooth(0.3, 0.55, field(noise(pts * np.array((3.0, 0.5, 0.0), np.float32), 1.0, 17, 2)))
    is_log = (finish == PAPER) & (Z > 31.0)
    ink = lines * is_log
    paper = full((190, 184, 164)) * (0.93 + 0.12 * mid[..., None]) * np.where(is_log, 1.0, 0.45)[..., None]
    put(finish == PAPER, mix(paper, full((50, 54, 84)), ink * 0.55), 0.8, 0.0, 0.0)
    put(finish == PLATE, full((120, 120, 112)) * (0.88 + 0.2 * mid[..., None]), 0.35 + 0.1 * mid, 0.0, 0.0)
    put(finish == BOARD, full((70, 52, 34)) * (0.85 + 0.3 * field(noise(pts * np.array((0.4, 6.0, 1.0), np.float32), 1.0, 18, 2))[..., None]), 0.62, 0.0, 0.0)

    # Dust settles on what faces up and in the corners, thin indoors; a scuffed band of boot marks in the kneehole's rail and fronts.
    settled = smooth(0.5, 0.95, up * 0.86 + (big - 0.5) * 0.24 + crevice * 0.24) * (1 - is_top * 0.75)
    boots = kick * smooth(0.55, 0.72, field(noise(pts * np.array((1.0, 0.25, 1.6), np.float32), 1.0, 19, 3)))
    dirt = np.clip(settled * (0.3 + high * 0.32) + crevice * 0.2 + boots * 0.36, 0, 0.8)
    dirt_c = full((86, 82, 76)) * (0.8 + 0.4 * fine[..., None])
    color = mix(color, dirt_c, dirt)
    rough = rough * (1 - dirt) + 0.9 * dirt
    metal = metal * (1 - dirt)

    color = color * (0.7 + 0.3 * ao[..., None])
    solid = ndi.binary_erosion(cover, iterations=1)
    height = fill_from(solid, height)[0]
    normal = to_normal(ndi.gaussian_filter(height, 0.5), density, 1.0)
    color, rough, metal, normal = fill_from(solid, np.clip(color, 0, 1), np.clip(rough, 0.1, 1), np.clip(metal, 0, 1), normal)
    save_rgb(os.path.join(OUT, "cd_body_color.png"), color)
    save_gray(os.path.join(OUT, "cd_body_rough.png"), rough)
    save_gray(os.path.join(OUT, "cd_body_metal.png"), metal)
    save_gray(os.path.join(OUT, "cd_body_ao.png"), np.clip(ao * 1.03, 0, 1))
    save_normal(os.path.join(OUT, "cd_body_normal.png"), normal)
    print("body painted", flush=True)


def paint_panel():
    W, H = L.PANEL_ATLAS
    k = L.PPI
    base = (150, 156, 150)
    img = Image.new("RGB", (W, H), base)
    hmap = Image.new("L", (W, H), 128)
    occl = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    dh = ImageDraw.Draw(hmap)
    do = ImageDraw.Draw(occl)

    def sxy(u, v):
        return (u * k, L.SLOPE_ROW + (L.SLOPE_L - v) * k)

    def uxy(u, v):
        return (u * k, L.UPRIGHT_ROW + (L.UPRIGHT_H - v) * k)

    # Upright panel: darker, to set off the dials.
    d.rectangle((0, 0, W, L.SLOPE_ROW - 1), fill=(40, 50, 66))

    def plate(xy, w, h, label, size, fill=(240, 240, 232), ink=(14, 14, 14), screws=True):
        x, y = xy
        box_ = (x - w * k / 2, y - h * k / 2, x + w * k / 2, y + h * k / 2)
        d.rectangle(box_, fill=fill)
        d.rectangle(box_, outline=(30, 30, 30), width=1)
        dh.rectangle(box_, fill=150)
        text(d, (x, y + 1), label, font(size * k), ink)
        if screws:
            for sx in (box_[0] + 0.22 * k, box_[2] - 0.22 * k):
                d.ellipse((sx - 3, y - 3, sx + 3, y + 3), fill=(120, 120, 116), outline=(50, 50, 50))

    blue, red_, amber, black_ = (22, 68, 170), (178, 28, 22), (210, 150, 20), (20, 20, 20)

    # The busbar runs right across the board, breaking only for the station bay.
    bus_v = 5.3
    d.line([sxy(0, bus_v), sxy(L.PANEL_W, bus_v)], fill=red_, width=int(0.42 * k))
    for i in range(L.BAYS):
        left = L.bay_left(i)
        mid = left + L.BAY_W / 2
        plate(sxy(mid, 20.7), 15.5, 1.5, L.BAY_TITLES[i], 0.92, fill=(16, 18, 22), ink=(236, 236, 226))
        if i == 2:
            # Station bay: the feeder out, and a tag for the stop.
            d.line([sxy(mid, bus_v), sxy(mid, 14.7)], fill=red_, width=int(0.42 * k))
            plate(sxy(mid, 0.95), 7.2, 0.82, "EMERGENCY STOP", 0.52, fill=(170, 22, 18), ink=(250, 250, 240), screws=False)
        elif i == 4:
            # Spill gates: the water's way through four gates to the river.
            for u, v in L.SWITCH_AT:
                gx, gy = sxy(left + u, v + 2.1)
                gx2, _ = sxy(left + u + 2.4, v)
                d.rectangle((gx + 1.4 * k, sxy(0, v + 2.3)[1], gx2 + 0.6 * k, sxy(0, v - 1.3)[1]), outline=black_, width=3)
                fill_to = v - 1.2 + 3.4 * (0.25 + ((u * 7 + v * 3) % 5) * 0.14)
                d.rectangle((gx + 1.5 * k, sxy(0, fill_to)[1], gx2 + 0.5 * k, sxy(0, v - 1.25)[1]), fill=blue)
            d.line([sxy(mid, 15.0), sxy(mid, bus_v + 0.8)], fill=blue, width=int(0.5 * k))
            d.line([sxy(left + 1.5, 10.2), sxy(left + L.BAY_W - 1.5, 10.2)], fill=blue, width=int(0.5 * k))
            d.line([sxy(left + 1.5, 15.0), sxy(left + L.BAY_W - 1.5, 15.0)], fill=blue, width=int(0.5 * k))
        else:
            # One unit: penstock to turbine to generator to breaker to the bus.
            d.line([sxy(mid, 15.2), sxy(mid, 12.9)], fill=blue, width=int(0.5 * k))
            for cy, label, colour in ((12.1, "T", blue), (8.6, "G", red_)):
                cx, cyy = sxy(mid, cy)
                r = 1.15 * k
                d.ellipse((cx - r, cyy - r, cx + r, cyy + r), outline=colour, width=5, fill=base)
                text(d, (cx, cyy + 1), label, font(1.2 * k, False), colour)
            d.line([sxy(mid, 11.0), sxy(mid, 9.7)], fill=black_, width=int(0.2 * k))
            d.line([sxy(mid, 7.5), sxy(mid, bus_v)], fill=red_, width=int(0.42 * k))
            bx, by = sxy(mid, 6.6)
            s = 0.5 * k
            d.rectangle((bx - s, by - s, bx + s, by + s), fill=base, outline=black_, width=4)
            # Thin leads to the switches that work each part.
            for u, v in L.SWITCH_AT:
                d.line([sxy(left + u + (1.3 if u < 11 else -1.3), v), sxy(mid + (-1.1 if u < 11 else 1.1), v)], fill=(70, 70, 66), width=2)
        if L.SWITCH_LABELS[i]:
            for (u, v), label in zip(L.SWITCH_AT, L.SWITCH_LABELS[i]):
                plate(sxy(left + u, v - 2.0), 4.4, 0.74, label, 0.52)
                for ang, mark in ((-40, "L"), (40, "R")):
                    a = math.radians(90 - ang)
                    tx, ty = sxy(left + u + 1.75 * math.cos(a), v + 1.75 * math.sin(a))
                    text(d, (tx, ty), mark, font(0.4 * k, False), (34, 34, 34))
        for u, v, _ in L.lamp_places(i):
            x, y = sxy(u, v)
            do.ellipse((x - 0.82 * k, y - 0.82 * k, x + 0.82 * k, y + 0.82 * k), fill=120)
        for u, v, n in L.button_places(i):
            x, y = sxy(u, v)
            do.ellipse((x - 0.82 * k, y - 0.82 * k, x + 0.82 * k, y + 0.82 * k), fill=120)
            text(d, (x, y + 0.92 * k), ("START", "HOLD", "STOP", "RESET", "TEST", "ACK")[n], font(0.32 * k), (30, 30, 30))
        if i != 2:
            for u, v in L.SWITCH_AT:
                x, y = sxy(left + u, v)
                do.ellipse((x - 1.65 * k, y - 1.65 * k, x + 1.65 * k, y + 1.65 * k), fill=170)
    # Under the rails and mullions.
    for kk in range(L.BAYS + 1):
        x, _ = sxy(kk * L.BAY_W, 0)
        do.rectangle((x - 0.62 * k, L.SLOPE_ROW, x + 0.62 * k, L.SLOPE_ROW + L.SLOPE_L * k), fill=150)
    do.rectangle((0, L.SLOPE_ROW, W, L.SLOPE_ROW + 0.8 * k), fill=170)
    do.rectangle((0, L.SLOPE_ROW + (L.SLOPE_L - 0.8) * k, W, L.SLOPE_ROW + L.SLOPE_L * k), fill=150)
    x0, _ = sxy(L.bay_left(2) + L.ESTOP[0], 0)
    _, y0 = sxy(0, L.ESTOP[1])
    do.ellipse((x0 - 2.3 * k, y0 - 2.3 * k, x0 + 2.3 * k, y0 + 2.3 * k), fill=170)
    # Round dials.
    for u, label, needle in zip(L.METER_U, L.METER_LABELS, L.METER_NEEDLES):
        x, y = uxy(u, L.METER_V)
        r = (L.METER_R - 0.36) * k
        d.ellipse((x - r, y - r, x + r, y + r), fill=(236, 234, 220))
        dial_r = r * 0.82
        for t in range(41):
            a = math.radians(210 - 240 * t / 40)
            inner = 0.86 if t % 5 else 0.78
            d.line((x + math.cos(a) * dial_r, y - math.sin(a) * dial_r, x + math.cos(a) * dial_r * inner, y - math.sin(a) * dial_r * inner), fill=(14, 14, 14), width=4 if t % 5 == 0 else 2)
        box_ = (x - dial_r * 1.04, y - dial_r * 1.04, x + dial_r * 1.04, y + dial_r * 1.04)
        d.arc(box_, -210 + 240 * 0.72, -210 + 240 * 0.86, fill=(40, 150, 60), width=7)
        d.arc(box_, -210 + 240 * 0.86, -210 + 240, fill=(190, 30, 24), width=7)
        for t in range(0, 41, 10):
            a = math.radians(210 - 240 * t / 40)
            text(d, (x + math.cos(a) * dial_r * 0.62, y - math.sin(a) * dial_r * 0.62), str(t * 25 // 10), font(0.42 * k), (14, 14, 14))
        text(d, (x, y + r * 0.52), label, font(0.62 * k), (14, 14, 14))
        do.ellipse((x - (L.METER_R + 0.5) * k, y - (L.METER_R + 0.5) * k, x + (L.METER_R + 0.5) * k, y + (L.METER_R + 0.5) * k), fill=110)
        do.ellipse((x - r, y - r, x + r, y + r), fill=70)
    # The chart recorder's paper, its trace running off the top.
    u0, v0, u1, v1 = L.CHART
    x0, y1_ = uxy(u0, v0)
    x1, y0_ = uxy(u1, v1)
    d.rectangle((x0, y0_, x1, y1_), fill=(226, 222, 200))
    for j in range(1, 16):
        xx = x0 + (x1 - x0) * j / 16
        d.line((xx, y0_, xx, y1_), fill=(190, 150, 140), width=1 if j % 5 else 2)
    for j in range(1, 8):
        yy = y0_ + (y1_ - y0_) * j / 8
        d.line((x0, yy, x1, yy), fill=(190, 150, 140), width=1 if j % 2 else 2)
    r = np.random.default_rng(5)
    for colour, level in (((180, 20, 18), 0.46), ((22, 50, 150), 0.28)):
        v = level
        pts = []
        for t in np.linspace(0, 1, 90):
            v = float(np.clip(v + r.normal(0, 0.012) + (level - v) * 0.05, 0.1, 0.9))
            pts.append((x0 + (x1 - x0) * v, y0_ + (y1_ - y0_) * t))
        d.line(pts, fill=colour, width=4)
    do.rectangle((x0, y0_, x1, y1_), fill=120)
    a = np.asarray(img, np.float32) / 255.0
    color = srgb_to_linear(a * 255.0)
    plates = (np.asarray(hmap, np.float32) - 128) / 22.0
    shadow = np.asarray(occl.filter(ImageFilter.GaussianBlur(0.26 * k)), np.float32) / 255.0

    # Fingers and years, in soft patches over the whole board. Coordinates as a position field so the noise is in inches.
    rows, cols = np.mgrid[0:H, 0:W].astype(np.float32)
    pts = np.column_stack((cols.ravel() / k, rows.ravel() / k, np.zeros(H * W, np.float32)))
    field = lambda f, s, o: noise(pts, f, s, o).reshape(H, W)
    big = field(0.09, 41, 3)
    mid = field(0.5, 42, 3)
    fine = field(3.0, 43, 2)
    rng = np.random.default_rng(31)
    scratches = Image.new("L", (W, H), 0)
    ds = ImageDraw.Draw(scratches)
    for _ in range(360):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        n = rng.uniform(16, 120)
        t = rng.uniform(0, math.pi)
        ds.line((x0, y0, x0 + math.cos(t) * n, y0 + math.sin(t) * n), fill=int(rng.uniform(60, 170)), width=1)
    scratches = np.asarray(scratches.filter(ImageFilter.GaussianBlur(0.5)), np.float32) / 255.0

    # Grime gathers round what fingers work, and in a soft tide under the top rail.
    fingers = np.asarray(occl.filter(ImageFilter.GaussianBlur(1.1 * k)), np.float32) / 255.0
    grime = np.clip(fingers * 1.1 * smooth(0.3, 0.7, mid) + smooth(0.55, 0.85, big) * 0.14, 0, 0.6)
    color = mix(color, srgb_to_linear((62, 58, 50)) * np.ones_like(color), grime * 0.5)
    color = color * (0.95 + 0.1 * fine[..., None])
    color = mix(color, srgb_to_linear((210, 208, 198)) * np.ones_like(color), scratches * 0.35)
    color = color * (1 - shadow[..., None] * 0.62)
    rough = np.clip(0.42 + 0.14 * mid + grime * 0.24 + scratches * 0.2, 0.1, 1)
    ao = np.clip(1 - shadow * 0.8, 0, 1)
    height = plates * 0.02 + 0.0009 * (fine - 0.5) - scratches * 0.0015
    # The kit's savers take rows bottom-up.
    normal = to_normal(ndi.gaussian_filter(height[::-1], 0.6), k, 1.0)

    def fit(a):
        """The UVs are fractions, so stretching the rows to a power of two changes nothing but the mips, which the compiler needs for normals."""
        factors = (2048 / H, 1) + (1,) * (a.ndim - 2)
        return ndi.zoom(a, factors, order=1)

    normal = fit(normal)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    save_rgb(os.path.join(OUT, "cd_panel_color.png"), fit(color[::-1]))
    save_gray(os.path.join(OUT, "cd_panel_rough.png"), fit(rough[::-1]))
    save_gray(os.path.join(OUT, "cd_panel_metal.png"), np.zeros((2048, W), np.float32))
    save_gray(os.path.join(OUT, "cd_panel_ao.png"), fit(ao[::-1]))
    save_normal(os.path.join(OUT, "cd_panel_normal.png"), normal)
    print("panel painted", flush=True)


def paint_glow():
    W, H = L.SCREEN_ATLAS
    # Drawn big and shrunk once, so thin lines and lettering stay clean.
    ss = 2
    img = Image.new("RGB", (W * ss, H * ss), (2, 4, 8))
    d = ImageDraw.Draw(img)
    r = np.random.default_rng(13)
    cyan, sky, pale, amber, green, red_, white = (44, 170, 205), (50, 120, 205), (120, 170, 220), (226, 150, 34), (56, 196, 116), (226, 48, 30), (190, 205, 216)

    def rect(name):
        x, y, w, h = L.SCREENS[name]
        return x * ss, y * ss, w * ss, h * ss

    def header(x, y, w, h, title, right="SCADA  UNIT 2"):
        d.rectangle((x, y, x + w, y + h), fill=(6, 22, 48))
        d.rectangle((x, y, x + w, y + h * 0.075), fill=(20, 72, 140))
        text(d, (x + w * 0.02, y + h * 0.04), title, font(h * 0.045), white, "lm")
        text(d, (x + w * 0.98, y + h * 0.04), right, font(h * 0.04), pale, "rm")

    # Main: the turbine seen from above, wicket gates round the runner, with the unit's numbers beside it.
    x, y, w, h = rect("main")
    header(x, y, w, h, "UNIT 2  TURBINE GENERATOR", "ONLINE  14:32:07")
    cx, cy = x + w * 0.33, y + h * 0.56
    R = h * 0.36
    for rr, wide in ((R, 5), (R * 0.82, 3), (R * 0.42, 4)):
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=cyan, width=wide)
    # The scroll case leading in.
    d.arc((cx - R * 1.12, cy - R * 1.12, cx + R * 1.12, cy + R * 1.12), 200, 340, fill=sky, width=int(h * 0.018))
    d.line((cx + R * 1.1, cy - R * 0.32, x + w * 0.61, cy - R * 0.32), fill=sky, width=int(h * 0.018))
    for j in range(20):
        a = 2 * math.pi * j / 20
        a2 = a + 0.42
        d.polygon(
            [(cx + math.cos(a) * R * 0.8, cy + math.sin(a) * R * 0.8), (cx + math.cos(a2) * R * 0.5, cy + math.sin(a2) * R * 0.5), (cx + math.cos(a2 + 0.08) * R * 0.5, cy + math.sin(a2 + 0.08) * R * 0.5), (cx + math.cos(a + 0.1) * R * 0.8, cy + math.sin(a + 0.1) * R * 0.8)],
            fill=(40, 120, 200),
        )
    cell = R * 0.115
    for j in range(7):
        for i in range(7):
            if (i - 3) ** 2 + (j - 3) ** 2 <= 10:
                col = green if r.random() < 0.82 else amber
                ax, ay = cx + (i - 3.5) * cell, cy + (j - 3.5) * cell
                d.rectangle((ax + 1, ay + 1, ax + cell - 2, ay + cell - 2), fill=col)
    for j, (name, value, unit, frac, col) in enumerate((("OUTPUT", "48.6", "MW", 0.71, cyan), ("SPEED", "150.0", "RPM", 0.5, cyan), ("NET HEAD", "61.2", "M", 0.64, cyan), ("FLOW", "87.4", "M3/S", 0.68, cyan), ("GATE", "68", "%", 0.68, cyan), ("BEARING", "62", "C", 0.57, amber), ("EXCITER", "312", "A", 0.46, cyan))):
        yy = y + h * (0.14 + 0.118 * j)
        lx = x + w * 0.66
        text(d, (lx, yy), name, font(h * 0.04), pale, "lm")
        text(d, (x + w * 0.97, yy), f"{value} {unit}", font(h * 0.05), white, "rm")
        bar_y = yy + h * 0.04
        d.rectangle((lx, bar_y, x + w * 0.97, bar_y + h * 0.018), fill=(16, 44, 84))
        d.rectangle((lx, bar_y, lx + (x + w * 0.97 - lx) * frac, bar_y + h * 0.018), fill=col)
    for j, state in enumerate(("U1", "U2", "U3", "GATES")):
        tx = x + w * (0.02 + 0.13 * j)
        ty = y + h * 0.9
        d.rectangle((tx, ty, tx + w * 0.115, ty + h * 0.07), fill=(26, 100, 60) if j != 2 else (120, 84, 20))
        text(d, (tx + w * 0.0575, ty + h * 0.035), state, font(h * 0.04), white)

    # Trends: three plots.
    x, y, w, h = rect("trend")
    header(x, y, w, h, "RESERVOIR AND LOAD  24H", "AUTO")
    for g, (title, col, level) in enumerate((("HEADWATER M", cyan, 0.62), ("TOTAL MW", green, 0.48), ("SPILL M3/S", amber, 0.3))):
        gy = y + h * (0.11 + 0.295 * g)
        gh = h * 0.26
        d.rectangle((x + w * 0.04, gy, x + w * 0.97, gy + gh), fill=(4, 14, 32), outline=(40, 86, 130), width=3)
        for j in range(1, 8):
            xx = x + w * (0.04 + 0.93 * j / 8)
            d.line((xx, gy, xx, gy + gh), fill=(16, 44, 76), width=2)
        for j in range(1, 4):
            d.line((x + w * 0.04, gy + gh * j / 4, x + w * 0.97, gy + gh * j / 4), fill=(16, 44, 76), width=2)
        v = level
        line = []
        for t in np.linspace(0, 1, 110):
            v = float(np.clip(v + r.normal(0, 0.03) + (level - v) * 0.05, 0.08, 0.92))
            line.append((x + w * (0.04 + 0.93 * t), gy + gh * (1 - v)))
        d.line(line, fill=col, width=5)
        text(d, (x + w * 0.055, gy + gh * 0.14), title, font(h * 0.042), col, "lm")

    # Alarms: a list, the newest in red.
    x, y, w, h = rect("alarms")
    header(x, y, w, h, "ALARMS AND EVENTS", "3 ACTIVE")
    rows = (("14:31:52", "U3 BEARING OIL TEMP HIGH", red_), ("14:28:10", "GATE 2 POSITION DEVIATION", amber), ("14:02:44", "INTAKE TRASH RACK DIFF", amber), ("13:57:13", "U2 GOVERNOR AUTO", green), ("13:40:06", "U1 SYNC CLOSED", green), ("13:22:38", "STATION SERVICE ON B", white), ("12:58:01", "HEADWATER LEVEL NORMAL", green), ("12:31:17", "SPILL GATE 4 CLOSED", white), ("12:04:50", "U1 EXCITER ON", white), ("11:47:29", "DRAIN PUMP 2 RUN", white))
    for j, (t, msg, col) in enumerate(rows):
        yy = y + h * (0.115 + 0.087 * j)
        if j < 3:
            d.rectangle((x + w * 0.015, yy, x + w * 0.985, yy + h * 0.074), fill=(70, 18, 16) if j == 0 else (60, 42, 12))
        text(d, (x + w * 0.03, yy + h * 0.037), t, font(h * 0.046), pale, "lm")
        text(d, (x + w * 0.26, yy + h * 0.037), msg, font(h * 0.05), col, "lm")

    # The small touch panel: big buttons.
    x, y, w, h = rect("hmi")
    header(x, y, w, h, "STATION", "OK")
    for j, (label, on) in enumerate((("UNIT 1", 1), ("UNIT 2", 1), ("UNIT 3", 2), ("GATES", 1), ("AUX", 1), ("FIRE", 0))):
        col_, row_ = j % 3, j // 3
        bx, by = x + w * (0.035 + 0.32 * col_), y + h * (0.13 + 0.42 * row_)
        fill = {0: (24, 48, 80), 1: (24, 110, 66), 2: (140, 96, 20)}[on]
        d.rectangle((bx, by, bx + w * 0.29, by + h * 0.37), fill=fill, outline=pale, width=4)
        text(d, (bx + w * 0.145, by + h * 0.185), label, font(h * 0.085), white)

    # A soft falloff to the edges and a faint pixel grid, so they read as lit panels and not as flat paint.
    a = np.asarray(img.resize((W, H), Image.LANCZOS), np.float32) / 255.0
    for name in L.SCREENS:
        x, y, w, h = L.SCREENS[name]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        fall = 1.0 - 0.3 * (((xx / w - 0.5) * 2) ** 4 + ((yy / h - 0.5) * 2) ** 4) * 0.5
        a[y : y + h, x : x + w] *= fall[..., None]
    img = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    d = ImageDraw.Draw(img)
    # Lamp swatches. Lit ones burn white at the centre; off ones are dark glass of the same colour.
    colours = {"G": (10, 176, 44), "R": (214, 16, 8), "A": (214, 112, 6), "W": (170, 176, 190), "g": (10, 34, 14), "r": (42, 8, 6), "a": (44, 28, 4), "w": (30, 30, 32)}
    for letter, cx in L.SWATCHES.items():
        c = colours[letter]
        for rad in range(L.SWATCH_R + 4, 0, -1):
            t = rad / L.SWATCH_R
            if letter.isupper():
                hot = max(0.0, 1 - t * 2.2)
                col = tuple(int(min(255, v * (0.72 + 0.3 * (1 - t)) + (255 - v) * hot * 0.22)) for v in c)
            else:
                col = tuple(int(v * (1.2 - t * 0.5)) for v in c)
            d.ellipse((cx - rad, L.SWATCH_Y - rad, cx + rad, L.SWATCH_Y + rad), fill=col)
    img.save(os.path.join(OUT, "cd_glow_color.png"), compress_level=6)
    print("glow painted", flush=True)


if "glow" in JOBS:
    paint_glow()
if "panel" in JOBS:
    paint_panel()
if "body" in JOBS:
    paint_body()
