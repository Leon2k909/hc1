"""Riverdale's two spawn-yard guard huts (v2): a prefab steel-clad gatehouse cabin on a concrete pad.

python -X utf8 hut.py [out dir]     writes Assets/models/props/riverdale/guard_hut_v1/ (guard_hut_east.vmdl, guard_hut_west.vmdl, three LODs each)

- Shell: 5 in walls with real openings, light-grey profiled cladding with geometric ribs, square corner posts, a dark base channel and an eave band, a concrete pad.
- Glazing on three sides in real glass (the map's own control-room glass), dark frames, exterior sills, interior stools, a sliding transaction pane and a deal tray.
- Door: framed opening, recessed blue steel door with a wired vision panel, kick plate, lever, lock, hinges, closer, a PPE sign, a caged bulkhead lamp above.
- Roof: an overhanging deck (deeper over the door) with a fascia and soffit, a back gutter and downspout, a vent cap.
- Back wall: a through-wall air conditioner with grille, brackets and drain; a meter box with conduit.
- Weathering: the map's translucent splash grime along the wall foot.
- Interior (lit by the spot light riverdale_huts adds in the scene): epoxy floor, painted walls, tiled ceiling with a troffer, a worktop under the yard window with a cabinet,
  a monitor showing a camera feed, keyboard, phone, logbook, mug, an office chair facing the yard, notice board, whiteboard, clock, binders on a shelf, key box,
  a CCTV monitor on a bracket, an extinguisher with its sign, a heater.

Plan axes (K.Model's own): x east, y north, z up, origin the middle of the 100 x 100 footprint on the floor. "east" has its yard (main window) on +x and the door on +y; "west" is
the same hut mirrored in x. Only the map's own materials (materials/riverdale/*, plus materials/railhead/rw_glass, which riverdale_glass already uses).
The old hut was box( m, he-50, he+50, -1500, -1400, 0, 110, ..., METAL ) plus riverdale_map.guard_hut(). Its collision box stays in the map model.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K  # noqa: E402
import riverdale_hall as RH  # noqa: E402
import riverdale_materials as RM  # noqa: E402
import riverdale_parts as G  # noqa: E402
import riverdale_yard as RY  # noqa: E402

OUT = ROOT / "Assets" / "models" / "props" / "riverdale" / "guard_hut_v1"
RESOURCE_DIR = "models/props/riverdale/guard_hut_v1"
LOD_THRESHOLDS = (0.0, 30.0, 80.0)
X = np.array((1.0, 0.0, 0.0))
Y = np.array((0.0, 1.0, 0.0))
Z = np.array((0.0, 0.0, 1.0))
HALF = 50.0
T = 5.0
PAD = 3.0          # the concrete pad's top
FLOOR = 6.0        # the cabin floor's top
WALL_TOP = 104.0
EAVE = 108.0
CLAD = "rv_fc_clad_light"
TRIM = "rv_fc_flashing"
GLASS = "rw_glass"
PATHS = {GLASS: "materials/railhead/rw_glass.vmat"}
TILES = {"rv_hall_epoxy": 96.0, "rv_hall_ceiling": 48.0, "rv_hall_interior": 96.0, CLAD: 192.0}
WIN_Z = (42.0, 88.0)
DOOR = (-38.0, -2.0, PAD, 86.0)
# Openings per face: ( u0, u1, z0, z1 ), u being y on the x faces and x on the y faces.
OPENINGS = {
    "+x": [(-40.0, 40.0) + WIN_Z],
    "+y": [DOOR, (8.0, 40.0) + WIN_Z],
    "-y": [(6.0, 40.0) + WIN_Z],
    "-x": [],
}
INNER = {"+x": "-x", "-x": "+x", "+y": "-y", "-y": "+y"}


def split(u0, u1, z0, z1, holes):
    """ Rectangles covering u0..u1 x z0..z1 minus the holes. """
    us = sorted({u0, u1, *[min(max(h[0], u0), u1) for h in holes], *[min(max(h[1], u0), u1) for h in holes]})
    out = []
    for a, b in zip(us, us[1:]):
        if b - a < 1e-6:
            continue
        mid = (a + b) / 2
        z = z0
        for c0, c1 in sorted((h[2], h[3]) for h in holes if h[0] < mid < h[1]):
            if c0 > z + 1e-6:
                out.append((a, b, z, c0))
            z = max(z, c1)
        if z1 > z + 1e-6:
            out.append((a, b, z, z1))
    return out


def build(mir=1, lod=0):
    m = K.Model()
    d0 = lod == 0
    d1 = lod <= 1
    flip = {"+x": "-x", "-x": "+x"}

    def mx(p):
        return (mir * p[0], p[1], p[2])

    def bx(c, size, paint, bevel=0.0, skip=()):
        if mir < 0:                       # the mirrored hut: face names flip with x
            if isinstance(paint, dict):
                paint = {flip.get(k, k): val for k, val in paint.items()}
            skip = tuple(flip.get(k, k) for k in skip)
        G.bevel_box(m, mx(c), (X, Y, Z), size, paint, bevel=bevel if d0 else 0.0, skip=skip)

    def rod(a, b, r, paint, sides=8, caps=True):
        G.rod(m, mx(a), mx(b), r, paint, sides, caps=caps)

    def turn(c, profile, paint, sides=12):
        G.lathe_axis(m, mx(c), Z, profile, paint, sides=sides)

    def quad(c, n, w, h, paint, uv=None):
        """ an upright quad facing plan direction n (before mirroring), reading correctly from in front. """
        nn = np.array((mir * n[0], n[1], 0.0))
        G.quad(m, paint, mx(c), np.cross(Z, nn), Z, w, h, uv)

    def flat(c, w, h, paint, uv):
        """ a level quad facing up whose text reads from the -x side looking +x (the chair). """
        G.quad(m, paint, mx(c), np.array((0.0, -mir, 0.0)), np.array((mir * 1.0, 0.0, 0.0)), w, h, uv)

    def atlas(table, size, name):
        return [RM.atlas_uv(table, size, name, s, t) for s, t in ((0, 0), (1, 0), (1, 1), (0, 1))]

    hall = lambda name: atlas(RH.SIGNS, RH.SIGN_ATLAS, name)  # noqa: E731
    yard = lambda name: atlas(RY.SIGNS, RY.SIGN_ATLAS, name)  # noqa: E731
    screen = lambda name: atlas(RM.SCREENS, RM.SCREEN_ATLAS, name)  # noqa: E731

    def fp(face, u, z, d):
        """ plan point on a face: u along it, height z, d in front of its outer plane (negative: into the wall). """
        s = 1.0 if face[0] == "+" else -1.0
        return (s * (HALF + d), u, z) if face[1] == "x" else (u, s * (HALF + d), z)

    def fn(face):
        s = 1.0 if face[0] == "+" else -1.0
        return (s, 0.0, 0.0) if face[1] == "x" else (0.0, s, 0.0)

    def fbox(face, u0, u1, z0, z1, e0, e1, paint, bevel=0.0, skip=()):
        """ a box on a face: u0..u1 along it, z0..z1, e0..e1 along its outward normal from the outer plane. """
        c = fp(face, (u0 + u1) / 2, (z0 + z1) / 2, (e0 + e1) / 2)
        size = (e1 - e0, u1 - u0, z1 - z0) if face[1] == "x" else (u1 - u0, e1 - e0, z1 - z0)
        bx(c, size, paint, bevel, skip)

    # ---- Pad, floor, walls, ceiling -----------------------------------------------------------------------------------------------------------------------------------------------
    bx((0, 0, PAD / 2), (2 * HALF + 4.0, 2 * HALF + 4.0, PAD), {"default": "rv_plinth", "-z": None}, 0.6)
    bx((0, 0, (PAD + FLOOR) / 2), (2 * HALF - 2 * T, 2 * HALF - 2 * T, FLOOR - PAD), {"default": None, "+z": "rv_hall_epoxy"})
    for face, holes in OPENINGS.items():
        u0, u1 = (-HALF, HALF) if face[1] == "y" else (-HALF + T, HALF - T)
        for a, b, z0, z1 in split(u0, u1, PAD, WALL_TOP, holes):
            fbox(face, a, b, z0, z1, -T, 0.0, {"default": TRIM, face: CLAD, INNER[face]: "rv_wall_clean", "-z": None})
    bx((0, 0, (WALL_TOP + EAVE) / 2), (2 * HALF - 2 * T, 2 * HALF - 2 * T, EAVE - WALL_TOP), {"default": None, "-z": "rv_hall_ceiling"})

    # ---- Profiled cladding ribs, base channel, eave band, grime, corner posts -----------------------------------------------------------------------------------------------------
    margin = 3.0
    for face, holes in OPENINGS.items():
        grown = [(h[0] - margin, h[1] + margin, h[2] - margin, h[3] + margin) for h in holes]
        if d1:
            for u in np.arange(-HALF + 6.0, HALF - 5.0, 8.0):
                free = [(PAD + 6.0, WALL_TOP - 2.0)]
                for g in grown:
                    if g[0] < u < g[1]:
                        nxt = []
                        for z0, z1 in free:
                            if g[2] > z0:
                                nxt.append((z0, min(z1, g[2])))
                            if g[3] < z1:
                                nxt.append((max(z0, g[3]), z1))
                        free = [(a, b) for a, b in nxt if b - a > 2.0]
                for z0, z1 in free:
                    fbox(face, u - 0.9, u + 0.9, z0, z1, -0.05, 0.75, CLAD, 0.3, skip=("-z", "+z"))
        segs = [(-HALF, HALF)]
        for h in holes:
            if h[2] <= PAD + 0.1:
                segs = [s for a, b in segs for s in ((a, min(b, h[0] - 1.8)), (max(a, h[1] + 1.8), b)) if s[1] - s[0] > 0.5]
        for a, b in segs:
            fbox(face, a, b, PAD, PAD + 6.0, -0.2, 0.9, "rv_dark", 0.25)
            if d0:
                quad(fp(face, (a + b) / 2, PAD + 6.0 + 15.0, 0.12), fn(face), b - a, 30.0, "rv_grime_foot",
                     uv=[(a / 192.0, 0.0), (b / 192.0, 0.0), (b / 192.0, 0.625), (a / 192.0, 0.625)])
        fbox(face, -HALF, HALF, WALL_TOP - 2.0, EAVE, -0.2, 0.9, TRIM, 0.25)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bx((sx * (HALF - 0.6), sy * (HALF - 0.6), (PAD + EAVE) / 2), (3.6, 3.6, EAVE - PAD), "rv_dark", 0.35)

    # ---- Windows: reveal frame, glass, sill, stool; the yard window slides --------------------------------------------------------------------------------------------------------
    fw = 2.2
    for face, holes in OPENINGS.items():
        for u0, u1, z0, z1 in holes:
            if z0 <= PAD + 0.1:
                continue
            for a, b, c0, c1 in ((u0, u1, z1 - fw, z1), (u0, u1, z0, z0 + fw), (u0, u0 + fw, z0 + fw, z1 - fw), (u1 - fw, u1, z0 + fw, z1 - fw)):
                fbox(face, a, b, c0, c1, -3.0, 0.3, "rv_dark", 0.25)
            mid = (u0 + u1) / 2
            if face == "+x":
                fbox(face, u0 + fw, mid + 1.0, z0 + fw, z1 - fw, -1.4, -1.15, GLASS)                   # fixed pane
                fbox(face, mid - 1.0, u1 - fw, z0 + fw, z1 - fw, -2.6, -2.35, GLASS)                   # sliding pane, inboard
                fbox(face, mid - 0.2, mid + 1.8, z0 + fw, z1 - fw, -1.8, -0.8, "rv_dark", 0.15)
                fbox(face, mid - 1.8, mid + 0.2, z0 + fw, z1 - fw, -3.0, -2.0, "rv_dark", 0.15)
                if d1:
                    for c0, c1 in ((z0 + fw, z0 + fw + 1.4), (z1 - fw - 1.4, z1 - fw)):
                        fbox(face, mid - 1.0, u1 - fw, c0, c1, -3.0, -2.0, "rv_dark", 0.1)
                if d0:
                    fbox(face, mid - 4.4, mid - 3.2, (z0 + z1) / 2 - 3.0, (z0 + z1) / 2 + 3.0, -3.6, -3.0, "rv_stainless", 0.2)
                    ty = mid + 16.0                                                                    # deal tray through the sill
                    fbox(face, ty - 7.0, ty + 7.0, z0 - 1.0, z0 - 0.3, -7.0, 3.2, "rv_stainless", 0.2)
                    for a, b in ((ty - 7.0, ty - 6.4), (ty + 6.4, ty + 7.0)):
                        fbox(face, a, b, z0 - 0.3, z0 + 0.7, -7.0, 3.2, "rv_stainless", 0.1)
            else:
                fbox(face, u0 + fw, u1 - fw, z0 + fw, z1 - fw, -1.4, -1.15, GLASS)
                if d1:
                    fbox(face, u0 + fw, u1 - fw, z0 + 26.0, z0 + 27.6, -1.9, -0.6, "rv_dark", 0.1)           # transom
            fbox(face, u0 - 1.5, u1 + 1.5, z0 - 1.4, z0, -0.4, 2.4, TRIM, 0.3)                         # pressed-steel sill
            if d1:
                fbox(face, u0, u1, z0 - 0.8, z0, -T - 1.2, -3.0, "rv_desk", 0.2)                       # interior stool

    # ---- Door ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
    du0, du1, dz0, dz1 = DOOR
    dc = (du0 + du1) / 2
    for a, b, c0, c1 in ((du0 - 1.8, du1 + 1.8, dz1, dz1 + 1.8), (du0 - 1.8, du0, dz0, dz1), (du1, du1 + 1.8, dz0, dz1)):
        fbox("+y", a, b, c0, c1, -T, 1.0, "rv_dark", 0.3)
    fbox("+y", du0 + 0.2, du1 - 0.2, dz0 + 0.4, dz1 - 0.2, -2.6, -0.8, "rv_fc_door_blue", 0.3)
    vz0, vz1 = 56.0, 78.0
    if d1:
        fbox("+y", dc - 5.0, dc + 5.0, vz0, vz1, -0.85, -0.45, "rv_dark", 0.15)
        fbox("+y", dc - 3.8, dc + 3.8, vz0 + 1.2, vz1 - 1.2, -0.5, -0.38, GLASS)
        fbox("+y", du0 + 1.0, du1 - 1.0, dz0 + 1.0, dz0 + 11.0, -0.85, -0.6, "rv_stainless", 0.1)             # kick plate
    if d0:
        for zz in (vz0 + 5.0, vz0 + 11.0, vz0 + 17.0):                                                          # wire in the vision glass
            fbox("+y", dc - 3.8, dc + 3.8, zz - 0.06, zz + 0.06, -0.42, -0.36, "rv_steel")
        hz, hu = 40.0, du1 - 4.0
        rod(fp("+y", hu, hz, -0.8), fp("+y", hu, hz, 0.6), 1.3, "rv_stainless", 10)
        rod(fp("+y", hu, hz, 0.6), fp("+y", hu - 6.0, hz, 0.6), 0.5, "rv_stainless", 6)
        rod(fp("+y", hu, hz - 5.0, -0.8), fp("+y", hu, hz - 5.0, 0.0), 0.8, "rv_stainless", 8)
        for zz in (14.0, 44.0, 74.0):
            rod(fp("+y", du0 + 0.6, zz - 2.5, 0.2), fp("+y", du0 + 0.6, zz + 2.5, 0.2), 0.75, "rv_galv", 8)
        fbox("+y", dc + 2.0, dc + 11.0, dz1 - 5.0, dz1 - 2.0, -0.8, 1.6, "rv_steel", 0.3)                       # closer
        rod(fp("+y", dc + 3.0, dz1 - 3.5, 1.6), fp("+y", dc - 7.0, dz1 + 0.8, 1.2), 0.45, "rv_steel", 4)
        quad(fp("+y", dc, 47.0, -0.78), (0, 1, 0), 9.0, 6.0, "rv_yd_signs", yard("ppe"))
        lp = fp("+y", dc, 95.0, 1.8)                                                                            # caged bulkhead lamp
        bx(lp, (11.0, 3.6, 6.5), "rv_dark", 0.9)
        quad(fp("+y", dc, 95.0, 3.66), (0, 1, 0), 8.0, 4.0, "rv_lamp_warm")
        for k in (-1.0, 0.0, 1.0):
            rod(fp("+y", dc + k * 3.0, 92.4, 4.1), fp("+y", dc + k * 3.0, 97.6, 4.1), 0.2, "rv_dark", 4)
        quad(fp("-y", -26.0, 70.0, 0.8), (0, -1, 0), 8.0, 10.0, "rv_yd_signs", yard("no_smoking"))

    # ---- Roof ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
    rx0, rx1, ry0, ry1 = -57.0, 57.0, -57.0, 64.0
    bx(((rx0 + rx1) / 2, (ry0 + ry1) / 2, EAVE + 1.5), (rx1 - rx0, ry1 - ry0, 3.0), {"default": TRIM, "+z": "rv_dark", "-z": "rv_white"}, 0.2)
    for c, size in ((((rx0 + rx1) / 2, ry1 + 0.4, EAVE + 1.0), (rx1 - rx0 + 1.6, 0.8, 6.0)), (((rx0 + rx1) / 2, ry0 - 0.4, EAVE + 1.0), (rx1 - rx0 + 1.6, 0.8, 6.0)),
                    ((rx1 + 0.4, (ry0 + ry1) / 2, EAVE + 1.0), (0.8, ry1 - ry0, 6.0)), ((rx0 - 0.4, (ry0 + ry1) / 2, EAVE + 1.0), (0.8, ry1 - ry0, 6.0))):
        bx(c, size, TRIM, 0.2)
    if d1:
        gx = rx0 - 2.6
        rod((gx, ry0 + 1.0, EAVE - 0.4), (gx, ry1 - 1.0, EAVE - 0.4), 1.9, "rv_galv", 8)
        rod((gx, ry0 + 4.0, EAVE - 0.4), (gx, ry0 + 4.0, PAD + 4.0), 1.5, "rv_galv", 8)
        rod((gx, ry0 + 4.0, PAD + 4.0), (gx - 4.0, ry0 + 4.0, PAD + 1.5), 1.5, "rv_galv", 8)
    if d0:
        for zz in (24.0, 56.0, 88.0):
            bx(((gx - HALF) / 2 - 0.4, ry0 + 4.0, zz), (abs(gx + HALF) + 1.0, 3.4, 1.4), "rv_steel", 0.0)
        for yy in (ry0 + 20.0, 0.0, ry1 - 20.0):
            bx((gx + 1.6, yy, EAVE - 0.4), (2.4, 0.8, 3.4), "rv_steel", 0.0)
        turn((-30.0, 20.0, EAVE + 3.0), [(0, 0), (2.0, 0), (2.0, 8.0), (4.5, 8.0), (4.5, 10.0), (0, 11.0)], "rv_steel", 10)

    # ---- Back wall: through-wall AC and drain, meter box and conduit -------------------------------------------------------------------------------------------------------------
    if d1:
        fbox("-x", 8.0, 32.0, 72.0, 88.0, -0.5, 10.0, "rv_white", 0.8)
    if d0:
        for zz in np.arange(74.0, 86.5, 1.8):
            fbox("-x", 9.5, 30.5, zz, zz + 0.8, 10.0, 10.5, "rv_dark", 0.0, skip=("+x",))
        for uu in (12.0, 28.0):
            fbox("-x", uu - 1.0, uu + 1.0, 64.0, 72.0, 0.0, 9.0, "rv_steel", 0.1)
        rod(fp("-x", 30.0, 72.0, 4.0), fp("-x", 30.0, PAD + 2.0, 4.0), 0.55, "rv_black", 6)
        fbox("-x", -30.0, -16.0, 50.0, 66.0, -0.2, 4.2, "rv_steel", 0.5)
        fbox("-x", -27.0, -19.0, 56.0, 62.0, 4.2, 4.35, GLASS)
        rod(fp("-x", -23.0, 66.0, 1.2), fp("-x", -23.0, WALL_TOP - 1.0, 1.2), 0.75, "rv_galv", 6)
        rod(fp("-x", -23.0, 50.0, 1.2), fp("-x", -23.0, PAD + 6.0, 1.2), 0.75, "rv_galv", 6)

    # ---- Interior -----------------------------------------------------------------------------------------------------------------------------------------------------------------
    IX = HALF - T
    bx((0, 0, WALL_TOP - 0.4), (24.0, 12.0, 0.8), {"default": "rv_dark", "-z": "rv_hall_troffer"})
    wz = 36.0
    bx((IX - 10.5, 0, wz + 0.8), (21.0, 2 * IX - 1.0, 1.6), "rv_hall_worktop", 0.3)
    if d1:
        bx((IX - 9.5, -IX + 14.0, (FLOOR + wz) / 2), (18.0, 27.0, wz - FLOOR), {"default": "rv_desk", "+z": None}, 0.25)
        cx, cy = 14.0, -6.0                                                                                     # the chair
        bx((cx, cy, 25.0), (17.0, 17.0, 3.0), "rv_chair", 1.0)
        bx((cx - 9.5, cy, 38.0), (2.6, 16.0, 17.0), "rv_chair", 1.0)
        rod((cx - 8.5, cy, 25.0), (cx - 9.5, cy, 31.0), 0.8, "rv_steel", 6)
        rod((cx, cy, FLOOR + 4.0), (cx, cy, 23.5), 1.1, "rv_steel", 8)
    if d0:
        for k in range(5):
            a = 2 * np.pi * k / 5 + 0.3
            tip = (cx + 11.0 * np.cos(a), cy + 11.0 * np.sin(a), FLOOR + 2.6)
            rod((cx, cy, FLOOR + 4.0), tip, 0.7, "rv_black", 6)
            turn((tip[0], tip[1], FLOOR), [(0, 0), (1.3, 0), (1.3, 2.0), (0, 2.0)], "rv_black", 8)
        my = -26.0                                                                                             # monitor with a camera feed
        bx((IX - 6.0, my, wz + 2.0), (6.0, 6.0, 0.8), "rv_hall_console_dark", 0.2)
        rod((IX - 6.0, my, wz + 2.2), (IX - 6.0, my, wz + 6.0), 0.6, "rv_hall_console_dark", 6)
        bx((IX - 6.5, my, wz + 11.0), (1.6, 17.0, 10.5), "rv_hall_console_dark", 0.3)
        quad((IX - 7.32, my, wz + 11.0), (-1, 0, 0), 15.6, 9.2, "rv_screens", screen("camera"))
        bx((IX - 14.0, my + 2.0, wz + 1.9), (5.0, 14.0, 0.6), "rv_black", 0.15)
        flat((IX - 14.0, my + 2.0, wz + 2.22), 13.6, 4.3, "rv_hall_signs", hall("keyboard"))
        bx((IX - 8.0, 24.0, wz + 2.6), (6.0, 5.0, 2.0), "rv_black", 0.4)
        quad((IX - 11.02, 24.0, wz + 2.6), (-1, 0, 0), 3.6, 1.8, "rv_hall_signs", hall("phone"))
        bx((IX - 12.0, 8.0, wz + 1.9), (9.0, 12.0, 0.6), "rv_white", 0.1)
        flat((IX - 12.0, 8.0, wz + 2.22), 11.0, 8.4, "rv_hall_signs", hall("papers"))
        turn((IX - 13.0, 17.0, wz + 1.6), [(0, 0), (1.6, 0), (1.75, 3.8), (1.5, 3.8), (1.35, 0.4), (0, 0.4)], "rv_porcelain", 12)
        for yy, w, h, name in ((-20.0, 24.0, 12.0, "noticeboard"), (14.0, 26.0, 13.0, "whiteboard")):               # back wall boards
            bx((-IX + 0.4, yy, 66.0), (0.8, w + 1.6, h + 1.6), "rv_hall_stainless", 0.2)
            quad((-IX + 0.82, yy, 66.0), (1, 0, 0), w, h, "rv_hall_signs", hall(name))
        bx((-IX + 0.5, -2.0, 88.0), (1.0, 8.0, 8.0), "rv_white", 0.4)
        quad((-IX + 1.02, -2.0, 88.0), (1, 0, 0), 7.2, 7.2, "rv_hall_signs", hall("clock"))
        bx((-24.0, -IX + 4.5, 76.0), (26.0, 9.0, 0.8), "rv_steel", 0.15)                                         # binders shelf
        bx((-24.0, -IX + 4.0, 80.4), (22.0, 8.0, 7.2), "rv_black", 0.2)
        quad((-24.0, -IX + 8.02, 80.4), (0, 1, 0), 21.0, 6.8, "rv_hall_signs", hall("binders"))
        bx((-36.0, IX - 1.6, 66.0), (12.0, 3.2, 16.0), "rv_steel", 0.4)                                          # key box
        bx((-36.0, IX - 3.25, 66.0), (10.0, 0.1, 14.0), "rv_dark", 0.0, skip=("+y",))
        bx((-IX + 1.0, -IX + 10.0, 94.0), (2.0, 4.0, 4.0), "rv_dark", 0.2)                                       # CCTV monitor on a bracket
        rod((-IX + 1.5, -IX + 10.0, 94.0), (-IX + 7.0, -IX + 10.0, 94.0), 0.6, "rv_dark", 6)
        bx((-IX + 8.5, -IX + 10.0, 92.0), (2.4, 14.0, 9.0), "rv_hall_console_dark", 0.3)
        quad((-IX + 9.72, -IX + 10.0, 92.0), (1, 0, 0), 12.6, 7.6, "rv_screens", screen("camera"))
        ex, ey = -IX + 5.0, IX - 4.0                                                                           # extinguisher and sign
        bx((ex, ey + 3.0, 22.0), (3.0, 1.0, 4.0), "rv_steel", 0.1)
        turn((ex, ey, 12.0), [(0, 0), (3.0, 0), (3.0, 14.0), (2.2, 16.0), (0.8, 16.6), (0, 16.6)], "rv_hall_red", 12)
        turn((ex, ey, 28.6), [(0, 0), (0.9, 0), (0.9, 2.0), (0, 2.0)], "rv_black", 8)
        quad((ex + 8.0, IX - 0.02, 38.0), (0, -1, 0), 6.0, 7.5, "rv_hall_signs", hall("fire_ext"))
        bx((-10.0, -IX + 1.8, 14.0), (26.0, 3.6, 12.0), "rv_white", 0.6)                                         # heater
        for k in range(8):
            bx((-20.5 + k * 3.0, -IX + 3.62, 17.0), (1.6, 0.05, 4.0), "rv_dark", 0.0, skip=("-y",))
    for paint in m.polygons:
        m.material_overrides[paint] = PATHS.get(paint, f"{RM.RESOURCE_DIR}/{paint}.vmat")
        m.tile_overrides[paint] = TILES.get(paint, RM.TILES.get(paint, 64.0))
    return m


def vmdl_text(name, paints):
    remaps = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{PATHS.get(p, RM.RESOURCE_DIR + "/" + p + ".vmat")}" }}' for p in sorted(paints))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{RESOURCE_DIR}/{name}_lod{k}.obj" import_translation = [ 0.0, 0.0, 0.0 ] '
        'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] } }'
        for k in range(3))
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{k}" ] }}' for k, t in enumerate(LOD_THRESHOLDS))
    return ("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
            "// Generated by Sources/Riverdale/guard-hut-v1/hut.py\n"
            "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
            "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n"
            "\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n" + remaps + "\n\t\t\t\t\t\t]\n"
            "\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + groups + "\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n")


def write_all(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, mir in (("guard_hut_east", 1), ("guard_hut_west", -1)):
        paints, tris = set(), []
        for lod in range(3):
            model = build(mir, lod)
            model.uv_source_name = name
            tris.append(K.write_obj(out / f"{name}_lod{lod}.obj", model, name))
            paints |= set(model.polygons)
        K.write_text(out / f"{name}.vmdl", vmdl_text(name, paints))
        result[name] = tris
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    print("triangles by LOD", write_all(target), "->", target)
