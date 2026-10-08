"""Build the hand-launched recon drone: a Raven-class small unmanned aircraft, its LODs and its texture atlas.

Run with Blender 5.1:  blender -b --factory-startup --python Tools/build_recon_drone.py
or in a running Blender: exec(compile(open(p).read(), p, "exec"), {"__file__": p, "__name__": "__main__"})
The build empties the open .blend first, so in a running Blender use a new file (see reset_scene).

The aircraft follows the AeroVironment RQ-11B Raven's published figures and photographs, at real size: 1.37 m
span, 0.91 m long, a pod with a gimballed camera ball in its chin, a parasol wing on a pylon (a flat centre
panel and two outer panels at a steep dihedral), a pusher motor at the pylon's rear with its two-blade prop
just behind the wing, a boom to a tail of rudder and elevator (it has no ailerons). The markings are its own:
no maker's name, logo or designation.

Every part is a loft of an analytic shape, F(a, b): a runs along the part and b around it, both 0..1. Its UVs
are (a, b) placed in the part's rectangle of one atlas, so every LOD (the same F sampled more coarsely) maps
the same texture, and one bake of LOD 0 textures them all. Rectangles are sized by the part's own lengths
(times `density`), so the texel size is about even: ~0.6 mm on the wings, ~0.4 mm on the pod at 2048.

The bake (Cycles, into float images) records each texel's part, position, normal, edges, noise and ambient
occlusion; numpy then paints the colour, roughness, metalness, ambient occlusion and (from a height field)
normal maps. The prop is a model of its own, so the game can spin it; it shares the body's material.

Units while modelling: metres. X forward, Y left, Z up; the origin is the centre of gravity, at the wing's
quarter chord over the pod's centre line. The OBJs are written in inches as (Y, Z, X), the way ModelDoc's
Y-up OBJ import reads back to X forward, Z up.

Stages (DRONE_STAGES, comma separated, default all): geometry, preview (workbench shots), bake, textures,
export, beauty (Cycles renders). DRONE_TEX sets the atlas size (2048), PREVIEW_DIR where renders go (outside
the project by default).
"""
import bpy
import json
import math
import struct
import tempfile
import zlib
from pathlib import Path

import numpy as np
from mathutils import Matrix, Vector

SCRIPT = Path(globals().get("__file__") or r"D:\Documents\s&box projects\hc1\forked-shooter-main\Tools\build_recon_drone.py").resolve()
ROOT = SCRIPT.parents[1]
OUT = ROOT / "Assets/models/recon_drone"
ASSET = "models/recon_drone"
NAME = "recon_drone"
PROP = "recon_propeller"
STAGES = globals().get("DRONE_STAGES", "all")
PREVIEW_DIR = Path(globals().get("PREVIEW_DIR") or Path(tempfile.gettempdir()) / "recon_drone_preview")
TEX = int(globals().get("DRONE_TEX", 2048))
PAD = 8 / TEX  # gutter round each UV island, in UV units
INCH = 39.37008  # inches per metre
SHARP = 35.0  # degrees: edges sharper than this get split normals

HUB = np.array((-0.140, 0.0, 0.058))  # the prop's hub: the prop model's origin
POS_LO, POS_SPAN = np.array((-0.8, -0.8, -0.8)), 1.6  # bake encoding of positions (metres) into 0..1
BAKE_PROP_OFFSET = np.array((0.0, 0.0, 3.0))  # the prop is baked well away, so the body doesn't occlude it


# ---------------------------------------------------------------------------------------------------------
# Shapes


def sgnpow(v, e):
    return np.sign(v) * np.abs(v) ** e


def stack3(x, y, z):
    x, y, z = np.broadcast_arrays(x, y, z)
    return np.stack([x, y, z], axis=-1).astype(np.float64)


def naca(xc, t, m=0.0, p=0.4):
    """NACA four-digit thickness (half, of chord) and camber line at chord fraction xc."""
    yt = 5 * t * (0.2969 * np.sqrt(np.maximum(xc, 0)) - 0.1260 * xc - 0.3516 * xc ** 2 + 0.2843 * xc ** 3
                  - 0.1036 * xc ** 4)
    if m == 0:
        return yt, np.zeros_like(xc)
    yc = np.where(xc < p, m / p ** 2 * (2 * p * xc - xc ** 2), m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * xc - xc ** 2))
    return yt, yc


class Airfoil:
    """A section's perimeter: tau runs from the trailing edge under the section to the leading edge (0.5) and
    back over it, cosine-spaced in chord. b is tau re-measured by arc length, which the UVs use."""

    def __init__(self, t, m=0.0, p=0.4):
        self.t, self.m, self.p = t, m, p
        tau = np.linspace(0, 1, 4001)
        xc, z = self.unit(tau)
        s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xc), np.diff(z)))])
        self.tau, self.b = tau, s / s[-1]

    def unit(self, tau, t=None):
        xc = 0.5 * (1 + np.cos(2 * np.pi * tau))
        yt, yc = naca(xc, self.t if t is None else t, self.m, self.p)
        return xc, np.where(tau < 0.5, yc - yt, yc + yt)

    def tau_of(self, b):
        return np.interp(b, self.b, self.tau)

    def b_of(self, tau):
        return np.interp(tau, self.tau, self.b)


WING_FOIL = Airfoil(0.085, 0.03, 0.4)
TAIL_FOIL = Airfoil(0.06)
FIN_FOIL = Airfoil(0.07)
BLADE_FOIL = Airfoil(0.12, 0.04, 0.4)
PYLON_FOIL = Airfoil(0.22)


def tip_round(d, length):
    """Chord factor of an elliptical tip: 1 until `length` from the end, 0 at it (d = distance from the end)."""
    u = np.clip(1 - d / length, 0, 1)
    return np.sqrt(np.clip(1 - u ** 2, 0, 1))


# Pod: nose tip at x 0.30, an elliptical nose to 0.215 (the nose cap's seam is at 0.205), a straight body to
# -0.04, then a tail cone that narrows to 16 mm by x -0.125, its top dropping to the boom's line, and a
# rounded tail cap the boom comes out of, ending at -0.137.
POD_NOSE, POD_BODY_END, POD_CONE_END, POD_TAIL = 0.30, -0.04, -0.125, -0.137
POD_W, POD_H, POD_END_R = 0.043, 0.048, 0.016


def pod_section(x):
    d = POD_NOSE - x
    f = np.where(d < 0.085, np.sqrt(np.clip(1 - (1 - d / 0.085) ** 2, 0, 1)), 1.0)
    t = x - POD_TAIL
    g = np.where(t < 0.012, np.sqrt(np.clip(1 - (1 - t / 0.012) ** 2, 0, 1)), 1.0)
    u = np.clip((POD_BODY_END - x) / (POD_BODY_END - POD_CONE_END), 0, 1)
    e = 0.5 - 0.5 * np.cos(np.pi * u)
    hw = (POD_W + (POD_END_R - POD_W) * e) * f * g
    hh = (POD_H + (POD_END_R - POD_H) * e) * f * g
    zc = -0.028 * e
    ex = np.where(d < 0.085, 2.0 + 1.2 * np.clip(d / 0.085, 0, 1) ** 2, 3.2 - 1.2 * e)
    return hw, hh, zc, ex


_pod_x = np.linspace(POD_NOSE, POD_TAIL, 4001)
_hw, _hh, _zc, _ = pod_section(_pod_x)
_pod_s = np.concatenate([[0], np.cumsum(np.sqrt(np.diff(_pod_x) ** 2 + np.diff((_hw + _hh) / 2) ** 2
                                                + np.diff(_zc) ** 2))])
_pod_a = _pod_s / _pod_s[-1]


def pod(a, b):
    x = np.interp(a, _pod_a, _pod_x)
    hw, hh, zc, ex = pod_section(x)
    th = -np.pi / 2 + 2 * np.pi * b  # the seam runs along the belly
    p = stack3(x, hw * sgnpow(np.cos(th), 2 / ex), zc + hh * sgnpow(np.sin(th), 2 / ex))
    return p, stack3(x, 0, zc)


# The gimballed camera: a ball under the nose's chin on a yaw collar out of the belly. Its windows look 25
# degrees down; the ball's poles are on the axis square to that, upwards, so the windows are on its equator,
# and the top pole is inside the collar.
GIMBAL_C = np.array((0.250, 0.0, -0.063))
GIMBAL_R = 0.025
COLLAR_R, COLLAR_TOP, COLLAR_BOTTOM = 0.022, -0.030, -0.0495  # the ball meets r 0.022 at -0.0511
LOOK = np.array((math.cos(math.radians(25)), 0, -math.sin(math.radians(25))))
G_UP = np.array((math.sin(math.radians(25)), 0, math.cos(math.radians(25))))
G_SIDE = np.array((0.0, 1.0, 0.0))


def gimbal(a, b):
    phi, beta = np.pi * a, np.pi * (2 * b - 1)
    d = (np.cos(phi)[..., None] * G_UP + (np.sin(phi) * np.cos(beta))[..., None] * LOOK
         + (np.sin(phi) * np.sin(beta))[..., None] * G_SIDE)
    return GIMBAL_C + GIMBAL_R * d, np.broadcast_to(GIMBAL_C, d.shape)


COLLAR_WALL = 0.85  # a share of the collar that's its wall; the rest is the lip turning in under it
COLLAR_LIP_R, COLLAR_LIP_Z = 0.020, -0.049  # the lip's inner edge, just inside the ball, so the ball comes out of it


def gimbal_mount(a, b):
    # The wall goes down to the bottom, then a lip turns in and up onto the ball. Ending the wall on the ball's
    # surface made the two meet edge-on, and the join read as a wavy line.
    w = np.clip(a / COLLAR_WALL, 0, 1)
    lip = np.clip((a - COLLAR_WALL) / (1 - COLLAR_WALL), 0, 1)
    r = COLLAR_R + (COLLAR_LIP_R - COLLAR_R) * lip
    z = COLLAR_TOP + (COLLAR_BOTTOM - COLLAR_TOP) * w + (COLLAR_LIP_Z - COLLAR_BOTTOM) * lip
    th = 2 * np.pi * b
    return (stack3(GIMBAL_C[0] + r * np.cos(th), r * np.sin(th), z),
            stack3(GIMBAL_C[0], 0, z))


BOOM_X0, BOOM_X1 = -0.11, -0.57


def boom_at(x):
    u = (x - BOOM_X0) / (BOOM_X1 - BOOM_X0)
    return 0.0115 + (0.0085 - 0.0115) * u, -0.028 + (-0.034 + 0.028) * u


def boom(a, b):
    x = BOOM_X0 + (BOOM_X1 - BOOM_X0) * a
    r, zc = boom_at(x)
    th = -np.pi / 2 + 2 * np.pi * b
    return stack3(x, r * np.cos(th), zc + r * np.sin(th)), stack3(x, 0, zc)


# The pylon carries the wing over the pod and the motor at its rear: a streamlined fairing (a 22 % thick
# symmetric section, 0.145 long) from inside the pod up to the wing's camber line, so its top always ends
# inside the wing, flaring out under the wing like a fillet.
PYLON_LE, PYLON_C = 0.050, 0.145


def wing_mid_z(x):
    c = WING_ROOT_C
    xc = np.clip((WING_LE - x) / c, 0, 1)
    alpha = math.radians(2)
    return WING_Z + (x - (WING_LE - 0.25 * c)) * math.sin(alpha) + naca(xc, 0.085, 0.03, 0.4)[1] * c * math.cos(alpha)


def pylon(a, b):
    xc, yn = PYLON_FOIL.unit(PYLON_FOIL.tau_of(b))
    x = PYLON_LE - xc * PYLON_C
    flare = 1 + 0.45 * np.clip((a - 0.8) / 0.2, 0, 1) ** 2
    return stack3(x, yn * PYLON_C * flare, a * wing_mid_z(x)), stack3(PYLON_LE - 0.5 * PYLON_C, 0, a * WING_Z)


class Stations:
    """A lathe profile of (x, radius) stations, parameterised by its meridian length."""

    def __init__(self, pts):
        self.x, self.r = (np.array(c, np.float64) for c in zip(*pts))
        s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(self.x), np.diff(self.r)))])
        self.a = s / s[-1]

    def at(self, a):
        return np.interp(a, self.a, self.x), np.interp(a, self.a, self.r)

    def sampler(self, subsets):
        def pick(n, lod):
            return self.a[list(subsets[lod])]
        return pick


MOTOR_Z = HUB[2]
MOTOR = Stations([(-0.050, 0.0095), (-0.056, 0.0135), (-0.064, 0.0158), (-0.072, 0.0165), (-0.0965, 0.0165),
                  (-0.121, 0.0165), (-0.1255, 0.0158), (-0.1275, 0.0141), (-0.128, 0.0125), (-0.128, 0.0)])


def motor(a, b):
    x, r = MOTOR.at(a)
    th = -np.pi / 2 + 2 * np.pi * b
    return stack3(x, r * np.cos(th), MOTOR_Z + r * np.sin(th)), stack3(x, 0, MOTOR_Z)


# The wing: a straight leading edge at x 0.063, 0.18 chord at the root tapering to 0.15, elliptical tips over
# the last 0.03 m, 2 degrees of dihedral on the centre panel (|y| <= 0.23) and 12 on the outer panels, 2
# degrees of incidence washing out to 0 at the tips, 3 % camber and 8.5 % thickness thinning to 7.5 %.
WING_LE, WING_ROOT_C, WING_TIP_C, SEMI_SPAN, JOINT = 0.063, 0.18, 0.15, 0.685, 0.23
WING_Z = 0.085


def wing_chord(ay):
    return WING_ROOT_C + (WING_TIP_C - WING_ROOT_C) * ay / SEMI_SPAN


def wing_z(ay):
    return WING_Z + np.where(ay <= JOINT, ay * math.tan(math.radians(2)),
                             JOINT * math.tan(math.radians(2)) + (ay - JOINT) * math.tan(math.radians(12)))


def wing_section(y, b):
    ay = np.abs(y)
    c0 = wing_chord(ay)
    f = tip_round(SEMI_SPAN - ay, 0.03)
    pivot = WING_LE - 0.4 * c0
    c = c0 * f
    le = pivot + 0.4 * c
    t = 0.085 - 0.01 * ay / SEMI_SPAN
    xc, zc = WING_FOIL.unit(WING_FOIL.tau_of(b), t)
    alpha = np.radians(2 - 2 * ay / SEMI_SPAN)
    z0 = wing_z(ay)
    xq = le - 0.25 * c
    dx, dz = (le - xc * c) - xq, zc * c
    x = xq + dx * np.cos(alpha) - dz * np.sin(alpha)
    z = z0 + dx * np.sin(alpha) + dz * np.cos(alpha)
    return stack3(x, y, z), stack3(le - 0.5 * c, y, z0)


def wing_centre(a, b):
    return wing_section(-JOINT + 2 * JOINT * a, b)


def wing_left(a, b):
    return wing_section(JOINT + (SEMI_SPAN - JOINT) * a, b)


def wing_right(a, b):
    return wing_section(-(JOINT + (SEMI_SPAN - JOINT) * a), b)


# Tail: a moulded mount on the boom's end; the horizontal stabiliser through it (elevator hinge at 65 % chord)
# and the fin on top (rudder hinge at 60 %), both thin symmetric sections with rounded tips.
MOUNT_Z = -0.034
MOUNT = [(-0.495, 0.0, 0.0), (-0.4953, 0.006, 0.007), (-0.4975, 0.0105, 0.0122), (-0.503, 0.013, 0.015),
         (-0.550, 0.013, 0.015), (-0.597, 0.013, 0.015), (-0.6025, 0.0105, 0.0122), (-0.6047, 0.006, 0.007),
         (-0.605, 0.0, 0.0)]
_mx, _mw, _mh = (np.array(c) for c in zip(*MOUNT))
_ms = np.concatenate([[0], np.cumsum(np.hypot(np.diff(_mx), np.diff((_mw + _mh) / 2)))])
MOUNT_A = _ms / _ms[-1]


def mount(a, b):
    x, hw, hh = (np.interp(a, MOUNT_A, c) for c in (_mx, _mw, _mh))
    th = -np.pi / 2 + 2 * np.pi * b
    return stack3(x, hw * sgnpow(np.cos(th), 2 / 3), MOUNT_Z + hh * sgnpow(np.sin(th), 2 / 3)), stack3(x, 0, MOUNT_Z)


STAB_Z, STAB_SEMI = -0.030, 0.175


def stab_le_chord(ay):
    return -0.515 - 0.02 * ay / STAB_SEMI, 0.095 - 0.025 * ay / STAB_SEMI


def stab(a, b):
    y = -STAB_SEMI + 2 * STAB_SEMI * a
    ay = np.abs(y)
    le0, c0 = stab_le_chord(ay)
    c = c0 * tip_round(STAB_SEMI - ay, 0.02)
    le = le0 - 0.4 * c0 + 0.4 * c
    xc, zc = TAIL_FOIL.unit(TAIL_FOIL.tau_of(b))
    return stack3(le - xc * c, y, STAB_Z + zc * c), stack3(le - 0.5 * c, y, STAB_Z)


FIN_Z0, FIN_H = -0.030, 0.14


def fin_le_chord(h):
    return -0.500 - 0.055 * h / FIN_H, 0.11 - 0.04 * h / FIN_H


def fin(a, b):
    h = FIN_H * a
    le0, c0 = fin_le_chord(h)
    c = c0 * tip_round(FIN_H - h, 0.015)
    le = le0 - 0.4 * c0 + 0.4 * c
    xc, yc = FIN_FOIL.unit(FIN_FOIL.tau_of(b))
    z = FIN_Z0 + h
    return stack3(le - xc * c, yc * c, z), stack3(le - 0.5 * c, 0, z)


# The prop, in its own frame: origin at the hub, x the thrust axis. A bullet spinner, and two blades of 0.07 m
# radius (0.14 m, about 5.5 in), pitch 0.10 m: 37 degrees at 30 % radius, 13 at the tip.
SPINNER = Stations([(0.012, 0.0135), (0.007, 0.0139), (0.002, 0.0136), (-0.003, 0.0124), (-0.007, 0.0102),
                    (-0.010, 0.0075), (-0.012, 0.0045), (-0.0132, 0.0018), (-0.0135, 0.0)])
PROP_R, PROP_PITCH = 0.070, 0.10


def spinner(a, b):
    x, r = SPINNER.at(a)
    th = -np.pi / 2 + 2 * np.pi * b
    return stack3(x, r * np.cos(th), r * np.sin(th)), stack3(x, 0, 0)


def blade(a, b):
    r = 0.010 + (PROP_R - 0.010) * a
    rf = r / PROP_R
    c0 = np.interp(rf, [0.14, 0.3, 0.6, 0.94, 1.0], [0.013, 0.0165, 0.014, 0.0095, 0.009])
    c = c0 * tip_round(PROP_R - r, 0.004)
    t = np.interp(rf, [0.14, 0.3, 1.0], [0.16, 0.12, 0.08])
    beta = np.arctan(PROP_PITCH / (2 * np.pi * r))
    xc, yn = BLADE_FOIL.unit(BLADE_FOIL.tau_of(b), t)
    # The blade moves towards -y; the leading edge leads, and is forward, on the helix the prop screws along.
    d = stack3(-np.sin(beta), np.cos(beta), 0)  # leading edge to trailing edge
    n = stack3(np.cos(beta), np.sin(beta), 0)  # the suction side, forwards
    xi = (xc - 0.35) * c + 0.002 * rf ** 2  # a little sweep back towards the tip
    p = stack3(0, 0, r) + xi[..., None] * d + (yn * c)[..., None] * n
    return p, stack3(0, 0, r)


# ---------------------------------------------------------------------------------------------------------
# Parts, LODs and UVs


def uniform(n, lod):
    return np.linspace(0, 1, n + 1)


def ends_rounded(lin_n, tip_n, start, end):
    """Rows: linear over [start, end] of a, sine-spaced (dense at the very end) over the rounded ends."""
    def pick(n, lod):
        ln, tn = lin_n[lod], tip_n[lod]
        rows = [np.linspace(start, end, ln + 1)]
        u = np.sin(np.linspace(0, np.pi / 2, tn + 1))[1:]
        if end < 1:
            rows.append(end + (1 - end) * u)
        if start > 0:
            rows.insert(0, (start * (1 - u))[::-1])
        return np.unique(np.round(np.concatenate(rows), 9))
    return pick


def tau_rows(foil):
    def pick(n, lod):
        return foil.b_of(np.linspace(0, 1, n + 1))
    return pick


class Part:
    def __init__(self, name, surf, fn, lods, model="body", closed=True, density=1.0, a_rows=uniform,
                 b_rows=uniform, copies=1):
        self.name, self.surf, self.fn, self.lods, self.model = name, surf, fn, lods, model
        self.closed, self.density, self.a_rows, self.b_rows, self.copies = closed, density, a_rows, b_rows, copies
        A, B = np.meshgrid(np.linspace(0, 1, 97), np.linspace(0, 1, 97), indexing="ij")
        P, _ = fn(A, B)
        self.along = np.linalg.norm(np.diff(P, axis=0), axis=-1).sum(axis=0).max()
        self.around = np.linalg.norm(np.diff(P, axis=1), axis=-1).sum(axis=1).max()


OUTER_ROWS = ends_rounded({0: 8, 1: 4, 2: 2}, {0: 5, 1: 3, 2: 2}, 0.0, 1 - 0.03 / (SEMI_SPAN - JOINT))
PARTS = [
    Part("pod", "pod", pod, {0: (26, 20), 1: (13, 12), 2: (7, 8)}, density=1.5),
    Part("gimbal", "gimbal", gimbal, {0: (10, 16), 1: (6, 10), 2: (4, 6)}, density=2.0),
    Part("gimbal_mount", "gimbal", gimbal_mount, {0: (2, 16), 1: (1, 10), 2: (1, 6)}, density=2.0,
         a_rows=lambda n, lod: np.array([(0, COLLAR_WALL, 1), (0, 1), (0, 1)][lod], np.float64)),
    Part("pylon", "pod", pylon, {0: (3, 18), 1: (2, 10), 2: (1, 6)}, density=1.2,
         a_rows=lambda n, lod: np.array([(0, 0.45, 0.85, 1), (0, 0.45, 1), (0, 1)][lod], np.float64),
         b_rows=tau_rows(PYLON_FOIL)),
    Part("motor", "motor", motor, {0: (9, 16), 1: (6, 10), 2: (4, 6)}, density=1.6,
         a_rows=MOTOR.sampler({0: range(10), 1: (0, 2, 3, 5, 7, 9), 2: (0, 3, 5, 8, 9)})),
    Part("boom", "boom", boom, {0: (2, 12), 1: (1, 8), 2: (1, 5)}),
    Part("wing_centre", "wing", wing_centre, {0: (4, 24), 1: (2, 14), 2: (2, 8)}, b_rows=tau_rows(WING_FOIL)),
    Part("wing_left", "wing", wing_left, {0: (0, 24), 1: (0, 14), 2: (0, 8)}, a_rows=OUTER_ROWS,
         b_rows=tau_rows(WING_FOIL)),
    Part("wing_right", "wing", wing_right, {0: (0, 24), 1: (0, 14), 2: (0, 8)}, a_rows=OUTER_ROWS,
         b_rows=tau_rows(WING_FOIL)),
    Part("mount", "mount", mount, {0: (8, 12), 1: (4, 8)}, density=1.3,
         a_rows=lambda n, lod: MOUNT_A[list([(0, 1, 2, 3, 4, 5, 6, 7, 8), (0, 2, 3, 5, 6, 8)][lod])]),
    Part("stab", "tail", stab, {0: (0, 14), 1: (0, 10), 2: (0, 6)}, density=1.2,
         a_rows=ends_rounded({0: 4, 1: 2, 2: 2}, {0: 4, 1: 2, 2: 1}, 0.02 / 0.35, 1 - 0.02 / 0.35),
         b_rows=tau_rows(TAIL_FOIL)),
    Part("fin", "tail", fin, {0: (0, 14), 1: (0, 10), 2: (0, 6)}, density=1.2,
         a_rows=ends_rounded({0: 5, 1: 3, 2: 2}, {0: 4, 1: 2, 2: 1}, 0.0, 1 - 0.015 / FIN_H),
         b_rows=tau_rows(FIN_FOIL)),
    Part("spinner", "spinner", spinner, {0: (8, 12), 1: (4, 8)}, model="prop", density=2.0,
         a_rows=SPINNER.sampler({0: range(9), 1: (0, 2, 4, 6, 8)})),
    Part("blade", "prop", blade, {0: (0, 8), 1: (0, 4)}, model="prop", density=2.5, copies=2,
         a_rows=ends_rounded({0: 5, 1: 2}, {0: 3, 1: 1}, 0.0, 1 - 0.004 / (PROP_R - 0.010)),
         b_rows=tau_rows(BLADE_FOIL)),
]
PART_INDEX = {p.name: i for i, p in enumerate(PARTS)}
RECTS = {}


def pack():
    """Shelf-pack the parts' rectangles (landscape, tallest first) at the largest scale that fits."""
    items = []
    for p in PARTS:
        w, h = p.around * p.density, p.along * p.density
        rot = h > w
        items.append((p.name, max(w, h), min(w, h), rot))
    items.sort(key=lambda it: -it[2])

    def place(scale):
        x = y = row = 0.0
        out = {}
        for name, w, h, rot in items:
            W, H = w * scale + 2 * PAD, h * scale + 2 * PAD
            if W > 1:
                return None
            if x + W > 1:
                x, y, row = 0.0, y + row, 0.0
            out[name] = (x + PAD, y + PAD, w * scale, h * scale, rot)
            x, row = x + W, max(row, H)
        return out if y + row <= 1 else None

    lo, hi = 0.01, 20.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if place(mid) else (lo, mid)
    RECTS.clear()
    RECTS.update(place(lo))
    return lo


def rect_uv(name, a, b):
    x0, y0, w, h, rot = RECTS[name]
    return np.stack([x0 + a * w, y0 + b * h] if rot else [x0 + b * w, y0 + a * h], axis=-1)


def rot_x180(p):
    return p * np.array((1.0, -1.0, -1.0))


def build(model, lod):
    """The model's mesh at a LOD: vertices (m), faces (index tuples), corner UVs and each face's part."""
    verts, faces, uvs, part_of = [], [], [], []
    for pi, p in enumerate(PARTS):
        if p.model != model or lod not in p.lods:
            continue
        na, nb = p.lods[lod]
        A, B = p.a_rows(na, lod), p.b_rows(nb, lod)
        AA, BB = np.meshgrid(A, B, indexing="ij")
        P0, C0 = p.fn(AA, BB)
        UV = rect_uv(p.name, AA, BB)
        for copy in range(p.copies):
            P, C = (P0, C0) if copy == 0 else (rot_x180(P0), rot_x180(C0))
            rows, cols = P.shape[:2]
            ncols = cols - 1 if p.closed else cols
            vid = np.zeros((rows, cols), np.int64)
            for i in range(rows):
                if np.abs(P[i] - P[i, :1]).max() < 1e-7:  # a pole: the row has shrunk to a point
                    vid[i, :] = len(verts)
                    verts.append(P[i, 0])
                else:
                    vid[i, :ncols] = np.arange(len(verts), len(verts) + ncols)
                    verts.extend(P[i, :ncols])
                    if p.closed:
                        vid[i, -1] = vid[i, 0]
            mine, score = [], 0.0
            for i in range(rows - 1):
                for j in range(cols - 1):
                    corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                    keep = []
                    for c in corners:
                        if not keep or vid[c] != vid[keep[-1]]:
                            keep.append(c)
                    if len(keep) > 1 and vid[keep[0]] == vid[keep[-1]]:
                        keep.pop()
                    if len(keep) < 3:
                        continue
                    pts = np.array([P[c] for c in keep])
                    nrm = np.cross(pts[2] - pts[0], pts[-1] - pts[1] if len(keep) == 4 else pts[1] - pts[0])
                    if len(keep) == 3:
                        nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                    score += float(np.dot(nrm, pts.mean(0) - np.mean([C[c] for c in keep], axis=0)))
                    mine.append(keep)
            flip = score < 0
            for keep in mine:
                keep = keep[::-1] if flip else keep
                faces.append(tuple(int(vid[c]) for c in keep))
                uvs.extend(UV[c] for c in keep)
                part_of.append(pi)
    return np.array(verts), faces, np.array(uvs), np.array(part_of, np.float32)


# ---------------------------------------------------------------------------------------------------------
# Scene


def reset_scene():
    """Empty the open .blend. Only a new file, an earlier build or the drone's own .blend is emptied without
    DRONE_FORCE_RESET, so running this in a file with other work in it fails instead of deleting that work."""
    keep = bpy.context.window.scene if bpy.context.window else bpy.context.scene
    fresh = (not bpy.data.filepath and len(bpy.data.scenes) == 1
             and {o.name for o in bpy.data.objects} <= {"Cube", "Camera", "Light"})
    own_file = bool(bpy.data.filepath) and Path(bpy.data.filepath).resolve() == (OUT / f"{NAME}.blend").resolve()
    earlier_build = keep.get("recon_drone_build") and len(bpy.data.scenes) == 1
    if not (fresh or own_file or earlier_build or globals().get("DRONE_FORCE_RESET")):
        raise RuntimeError("The drone builder empties the open .blend. Run it in a new file, or set "
                           "DRONE_FORCE_RESET to empty this one.")
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for scene in list(bpy.data.scenes):
        if scene != keep:
            bpy.data.scenes.remove(scene)
    for data in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                 bpy.data.curves, bpy.data.node_groups, bpy.data.worlds):
        for item in list(data):
            data.remove(item)
    for image in list(bpy.data.images):
        if image.type == "IMAGE":
            bpy.data.images.remove(image)
    keep.name = "Recon Drone"
    keep["recon_drone_build"] = True
    keep.unit_settings.system = "METRIC"
    return keep


def make_object(name, verts, faces, uvs, part_of, rest=None, link=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], faces)
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", uvs.astype(np.float32).ravel())
    me.attributes.new("part_id", "FLOAT", "FACE").data.foreach_set("value", part_of)
    if rest is not None:
        me.attributes.new("rest", "FLOAT_VECTOR", "POINT").data.foreach_set("vector", rest.astype(np.float32).ravel())
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(SHARP))
    obj = bpy.data.objects.new(name, me)
    if link:
        bpy.context.scene.collection.objects.link(obj)
    return obj


def build_geometry():
    reset_scene()
    scale = pack()
    objs = {}
    for model, lods in (("body", (0, 1, 2)), ("prop", (0, 1))):
        for lod in lods:
            v, f, uv, part = build(model, lod)
            name = f"{NAME if model == 'body' else PROP}_lod{lod}"
            obj = make_object(name, v, f, uv, part)
            if model == "prop":
                obj.location = HUB
            obj.hide_set(lod != 0)
            obj.hide_render = lod != 0
            objs[name] = obj
            print(f"{name}: {len(f)} faces, {sum(len(x) - 2 for x in f)} triangles, {len(v)} vertices")
    print(f"UV scale {scale:.3f} (UV units per metre); texel {1000 / (scale * TEX):.2f} mm at density 1")
    return objs


# ---------------------------------------------------------------------------------------------------------
# Previews (workbench)


SHOTS = {  # view: direction to the camera, point looked at (m), distance (m), lens (mm; negative: orthographic
    # of that width), and the world direction that's up in the picture
    "three_quarter": ((0.85, 0.75, 0.42), (-0.12, 0, 0.04), 2.5, 50, (0, 0, 1)),
    "front": ((1, 0, 0), (-0.12, 0, 0.03), 3.0, -1.5, (0, 0, 1)),
    "side": ((0, 1, 0), (-0.15, 0, 0.0), 3.0, -1.05, (0, 0, 1)),
    "top": ((0, 0, 1), (-0.15, 0, 0.0), 3.0, -1.5, (1, 0, 0)),
    "rear": ((-0.9, -0.55, 0.38), (-0.15, 0, 0.05), 2.4, 50, (0, 0, 1)),
    "under": ((0.35, -0.55, -0.75), (-0.12, 0, 0.0), 2.4, 50, (0, 0, 1)),
    "nose": ((0.85, 0.55, 0.05), (0.22, 0, -0.03), 0.55, 50, (0, 0, 1)),
    "tail": ((-0.55, 0.8, 0.35), (-0.55, 0, 0.02), 0.55, 50, (0, 0, 1)),
    "motor": ((-0.7, -0.6, 0.45), (-0.12, 0, 0.055), 0.45, 50, (0, 0, 1)),
    "held": ((-0.75, -0.45, 0.42), (0.05, 0, 0.03), 0.95, 35, (0, 0, 1)),
}


def camera(scene, view):
    direction, look, distance, lens, up = SHOTS[view]
    cam = scene.camera
    if cam is None:
        cam = bpy.data.objects.new("drone_cam", bpy.data.cameras.new("drone_cam"))
        scene.collection.objects.link(cam)
        scene.camera = cam
    back = Vector(direction).normalized()
    right = Vector(up).cross(back).normalized()
    cam.location = Vector(look) + back * distance
    cam.rotation_euler = Matrix((right, back.cross(right), back)).transposed().to_euler()
    cam.data.type = "ORTHO" if lens < 0 else "PERSP"
    if lens < 0:
        cam.data.ortho_scale = -lens
    else:
        cam.data.lens = lens
    cam.data.clip_start = 0.01
    return cam


def preview(views=("three_quarter", "side", "top", "front", "nose", "tail", "motor")):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.6, 0.62, 0.6)
    scene.display.shading.show_cavity = True
    scene.display.render_aa = "16"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for view in views:
        camera(scene, view)
        scene.render.filepath = str(PREVIEW_DIR / f"geo_{view}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(scene.render.filepath)
    return paths


# ---------------------------------------------------------------------------------------------------------
# Bake


def socket(nt, value, target):
    if isinstance(value, bpy.types.NodeSocket):
        nt.links.new(value, target)
    else:
        target.default_value = value


def vmath(nt, op, *inputs):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    for i, value in enumerate(inputs):
        socket(nt, value, n.inputs[i])
    return n.outputs["Value" if op == "DOT_PRODUCT" else "Vector"]


def smath(nt, op, *inputs):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, value in enumerate(inputs):
        socket(nt, value, n.inputs[i])
    return n.outputs[0]


def xyz(nt, *values):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, value in enumerate(values):
        socket(nt, value, n.inputs[i])
    return n.outputs[0]


def attr(nt, name, out="Vector"):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_type = "GEOMETRY"
    n.attribute_name = name
    return n.outputs[out]


def noise(nt, vector, scale, detail, roughness):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "3D"
    nt.links.new(vector, n.inputs["Vector"])
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = roughness
    return n.outputs["Fac"]


def pass_ids(nt):
    return xyz(nt, smath(nt, "MULTIPLY_ADD", attr(nt, "part_id", "Fac"), 1 / 64, 1 / 64), 0.0, 0.0)


def pass_pos(nt):
    return vmath(nt, "MULTIPLY_ADD", attr(nt, "rest"), (1 / POS_SPAN,) * 3, tuple(-c / POS_SPAN for c in POS_LO))


def pass_nrm(nt):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    return vmath(nt, "MULTIPLY_ADD", geo.outputs["Normal"], (0.5,) * 3, (0.5,) * 3)


def pass_edge(nt):
    """1 - cos of the angle between the normal rounded over 1.5 and 4 mm and the shading normal: how near an
    edge a texel is (convex or concave; the cavity bake tells them apart)."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    outs = []
    for radius in (0.0015, 0.004):
        bev = nt.nodes.new("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = radius
        outs.append(smath(nt, "SUBTRACT", 1.0, vmath(nt, "DOT_PRODUCT", bev.outputs["Normal"], geo.outputs["Normal"])))
    return xyz(nt, *outs, 0.0)


def pass_noise(nt):
    rest = attr(nt, "rest")
    return xyz(nt, noise(nt, rest, 420, 4, 0.55), noise(nt, rest, 60, 5, 0.6), noise(nt, rest, 9, 3, 0.5))


# name: (bake type, emission builder, samples, AO distance)
BAKE_PASSES = {
    "ids": ("EMIT", pass_ids, 1, None),
    "pos": ("EMIT", pass_pos, 1, None),
    "nrm": ("EMIT", pass_nrm, 1, None),
    "noise": ("EMIT", pass_noise, 1, None),
    "edge": ("EMIT", pass_edge, 16, None),
    "ao": ("AO", None, 256, 0.10),
    "cav": ("AO", None, 64, 0.008),
}


def use_cycles(scene):
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = "GPU"
            break
    else:
        prefs.compute_device_type = "NONE"
        scene.cycles.device = "CPU"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("drone_world")


def bake_object():
    """LOD 0 of the body and the prop in one mesh, the prop moved well away; 'rest' keeps where it belongs."""
    vb, fb, uvb, pb = build("body", 0)
    vp, fp, uvp, pp = build("prop", 0)
    verts = np.concatenate([vb, vp + HUB + BAKE_PROP_OFFSET])
    rest = np.concatenate([vb, vp + HUB])
    faces = fb + [tuple(i + len(vb) for i in f) for f in fp]
    return make_object("drone_bake", verts, faces, np.concatenate([uvb, uvp]), np.concatenate([pb, pp]), rest)


def bake():
    """Bake the passes into float arrays (TEX, TEX, 4), rows bottom-up as Blender stores them."""
    scene = bpy.context.scene
    use_cycles(scene)
    if not RECTS:
        pack()
    obj = bake_object()
    mat = bpy.data.materials.new("drone_bake")
    obj.data.materials.append(mat)
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    out = {}
    try:
        for name, (kind, build_pass, samples, distance) in BAKE_PASSES.items():
            img = bpy.data.images.new(f"drone_bake_{name}", TEX, TEX, alpha=True, float_buffer=True)
            img.colorspace_settings.name = "Non-Color"
            nt = mat.node_tree
            nt.nodes.clear()
            output = nt.nodes.new("ShaderNodeOutputMaterial")
            shader = nt.nodes.new("ShaderNodeEmission" if build_pass else "ShaderNodeBsdfDiffuse")
            nt.links.new(shader.outputs[0], output.inputs["Surface"])
            if build_pass:
                nt.links.new(build_pass(nt), shader.inputs["Color"])
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            nt.nodes.active = tex
            scene.cycles.samples = samples
            if distance:
                scene.world.light_settings.distance = distance
            bpy.ops.object.bake(type=kind, margin=0, use_clear=True, target="IMAGE_TEXTURES")
            px = np.empty(TEX * TEX * 4, np.float32)
            img.pixels.foreach_get(px)
            bpy.data.images.remove(img)
            out[name] = px.reshape(TEX, TEX, 4)
            print(f"baked {name}")
    finally:
        bpy.data.objects.remove(obj)
        bpy.data.materials.remove(mat)
    return out


# ---------------------------------------------------------------------------------------------------------
# Paint: numpy turns the bakes into the material's maps. Colours are sRGB 0..255, the maths is linear.


def lin(c):
    c = np.asarray(c, np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if np.ndim(a) == 3 or np.ndim(b) == 3:
        t = t[..., None]
    return a + (b - a) * t


def hash01(x, *salt):
    v = np.sin(np.asarray(x, np.float64) * 12.9898 + sum(s * (78.233 + 37.719 * i) for i, s in enumerate(salt))) * 43758.5453
    return (v - np.floor(v)).astype(np.float32)


def groove(d, w=0.0006):
    """A rounded groove's depth profile, 1 at its middle, across half-width w (m)."""
    return np.clip(1 - (np.asarray(d) / w) ** 2, 0, 1)


def rrect(px, py, cx, cy, hx, hy, r):
    """Signed distance to a rounded rectangle (negative inside)."""
    qx, qy = np.abs(px - cx) - (hx - r), np.abs(py - cy) - (hy - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def streaks(across, along, spacing, seg, keep, seed, width=0.25):
    """Scratches running along `along`: lines every `spacing` across, broken into segments `seg` long."""
    s = across / spacing
    n = np.floor(s)
    d = np.abs(s - n - 0.5 - 0.35 * (hash01(n, seed, 1) - 0.5))
    line = 1 - smoothstep(width * 0.3, width, d)
    cell = np.floor(along / seg + hash01(n, seed, 2))
    return line * (hash01(n * 131.0 + cell, seed, 3) < keep) * (0.4 + 0.6 * hash01(n + cell * 7.0, seed, 4))


def text_mask(text):
    """Coverage (h, w) of `text` in Blender's own font, cropped, rows bottom-up: rendered white on clear."""
    cache = bpy.app.driver_namespace.setdefault("drone_text", {})
    if text in cache:
        return cache[text]
    sc = bpy.data.scenes.new("drone_text")
    cu = bpy.data.curves.new("drone_text", "FONT")
    cu.body = text
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.offset = 0.025
    cu.space_character = 1.1
    ob = bpy.data.objects.new("drone_text", cu)
    ob.scale.x = 0.85
    sc.collection.objects.link(ob)
    cam = bpy.data.objects.new("drone_text_cam", bpy.data.cameras.new("drone_text_cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 0.8 * len(text) + 1.0
    cam.location = (0, 0, 5)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (1, 1, 1)
    sc.display.render_aa = "16"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 1024
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    path = Path(bpy.app.tempdir or tempfile.gettempdir()) / f"drone_text_{len(cache)}.png"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=sc.name)
    img = bpy.data.images.load(str(path))
    px = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(px)
    a = px.reshape(img.size[1], img.size[0], 4)[..., 3]
    bpy.data.images.remove(img)
    for data, item in ((bpy.data.objects, ob), (bpy.data.objects, cam), (bpy.data.curves, cu),
                       (bpy.data.cameras, cam.data), (bpy.data.scenes, sc)):
        data.remove(item)
    path.unlink(missing_ok=True)
    rows, cols = np.nonzero(a.max(1) > 0.02)[0], np.nonzero(a.max(0) > 0.02)[0]
    a = np.ascontiguousarray(a[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1])
    cache[text] = a
    return a


def label_mask(seed, cols=26, rows=5):
    """A small printed label: coverage of its print (a bar code and a line of 'text'), rows bottom-up."""
    rng = np.random.default_rng(seed)
    h, w = rows * 8, cols * 6
    ink = np.zeros((h, w), np.float32)
    x = 3
    while x < w - 4:
        bw = int(rng.integers(1, 4))
        ink[14:h - 4, x:x + bw] = 1.0
        x += bw + int(rng.integers(1, 3))
    for x0 in range(3, w - 10, 7):
        if rng.random() < 0.8:
            ink[4:9, x0:x0 + 5] = 1.0
    return ink[::-1].copy()


def sample(mask, x, y):
    h, w = mask.shape
    fx, fy = np.clip(x, 0, 1) * (w - 1), np.clip(y, 0, 1) * (h - 1)
    x0, y0 = np.clip(np.floor(fx).astype(int), 0, w - 2), np.clip(np.floor(fy).astype(int), 0, h - 2)
    tx, ty = fx - x0, fy - y0
    return (mask[y0, x0] * (1 - tx) * (1 - ty) + mask[y0, x0 + 1] * tx * (1 - ty)
            + mask[y0 + 1, x0] * (1 - tx) * ty + mask[y0 + 1, x0 + 1] * tx * ty)


def shrink(mask, texels):
    k = max(1, mask.shape[0] // max(1, int(texels * 3)))
    h, w = (mask.shape[0] // k) * k, (mask.shape[1] // k) * k
    return mask[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def stamp(where, u, v, mask, height, width=None, texel=0.0005):
    """Coverage of `mask` centred on (0, 0) in surface coordinates u (right) and v (up), metres."""
    width = width or height * mask.shape[1] / mask.shape[0]
    x, y = u / width + 0.5, v / height + 0.5
    inside = where & (x >= 0) & (x <= 1) & (y >= 0) & (y <= 1)
    out = np.zeros(where.shape, np.float32)
    small = shrink(mask, height / texel)
    out[inside] = sample(small, x[inside], y[inside])
    return out


def dilate(maps, covered, steps=24):
    """Grow every island `steps` texels into the empty space round it, copying its edge texels outwards."""
    h, w = covered.shape
    idx = np.where(covered, np.arange(h * w).reshape(h, w), -1)
    for _ in range(steps):
        empty = idx < 0
        if not empty.any():
            break
        new = idx.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            shifted = np.roll(idx, (dy, dx), axis=(0, 1))
            take = (new < 0) & (shifted >= 0)
            new[take] = shifted[take]
        idx = new
    src = np.maximum(idx, 0).ravel()
    return {k: v.reshape(h * w, -1)[src].reshape(v.shape) for k, v in maps.items()}


def deriv(a, ok, axis):
    """Central difference along an axis, one-sided where a neighbour isn't on the same part."""
    fwd, bwd = np.roll(a, -1, axis), np.roll(a, 1, axis)
    okf, okb = np.roll(ok, -1, axis) == ok, np.roll(ok, 1, axis) == ok
    if a.ndim == 3:
        okf, okb = okf[..., None], okb[..., None]
    return np.where(okf & okb, (fwd - bwd) * 0.5, np.where(okf, fwd - a, np.where(okb, a - bwd, 0.0)))


def write_png(path, arr):
    """8-bit PNG of a (h, w[, c]) array in 0..1 (or uint8) whose row 0 is the bottom, as Blender's are."""
    a = arr if arr.dtype == np.uint8 else np.clip(np.rint(arr * 255.0), 0, 255).astype(np.uint8)
    a = np.ascontiguousarray(a[::-1])
    h, w = a.shape[:2]
    c = 1 if a.ndim == 2 else a.shape[2]
    rows = a.reshape(h, w * c).astype(np.int16)
    up = rows.copy()
    up[1:] -= rows[:-1]
    raw = np.empty((h, w * c + 1), np.uint8)
    raw[:, 0] = 2
    raw[:, 1:] = (up & 0xFF).astype(np.uint8)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    header = struct.pack(">IIBBBBB", w, h, 8, {1: 0, 2: 4, 3: 2, 4: 6}[c], 0, 0, 0)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                           + chunk(b"IDAT", zlib.compress(raw.tobytes(), 6)) + chunk(b"IEND", b""))


# Paint and finish per surface: colour (sRGB), roughness, metalness. The pod is a grey-green painted composite,
# the wing and tail a lighter grey over a Kevlar-skinned foam core, the motor a black anodised can.
SURF = {
    "pod": ((128, 133, 122), 0.55, 0.0),
    "wing": ((172, 175, 170), 0.6, 0.0),
    "tail": ((168, 171, 166), 0.6, 0.0),
    "boom": ((108, 111, 109), 0.45, 0.0),
    "mount": ((58, 60, 60), 0.62, 0.0),
    "motor": ((30, 30, 33), 0.36, 1.0),
    "gimbal": ((46, 48, 51), 0.42, 0.0),
    "spinner": ((24, 24, 26), 0.32, 1.0),
    "prop": ((20, 20, 21), 0.42, 0.0),
}
TAPE = (226, 104, 28)  # high-visibility orange tape squares on the outer panels
JOINT_MARK = {1: (190, 30, 28), -1: (24, 150, 70)}  # red at the left wing joint, green at the right
SERIAL = "RZ 04172"


def compose(maps, out_dir):
    covered = maps["ids"][..., 0] > 0.5 / 64
    maps = dilate(maps, covered)
    part = np.rint(maps["ids"][..., 0] * 64 - 1).astype(np.int32)
    part[~covered] = -1  # dilated texels keep their neighbour's values but stay off every part's details
    P = (maps["pos"][..., :3] * POS_SPAN + POS_LO).astype(np.float32)
    N = maps["nrm"][..., :3] * 2 - 1
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-6)
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    nx, ny, nz = N[..., 0], N[..., 1], N[..., 2]
    nz1, nz2, nz3 = (maps["noise"][..., i] for i in range(3))
    ao = np.clip(maps["ao"][..., 0], 0, 1)
    cav = np.clip(maps["cav"][..., 0], 0, 1)
    edge1, edge2 = maps["edge"][..., 0], maps["edge"][..., 1]
    rng = np.random.default_rng(11)
    grain = rng.random(part.shape, np.float32)

    def on(*names):
        return np.isin(part, [PART_INDEX[n] for n in names])

    surf_of = {i: p.surf for i, p in enumerate(PARTS)}
    shape = part.shape
    albedo = np.zeros(shape + (3,), np.float32)
    rough = np.zeros(shape, np.float32)
    metal = np.zeros(shape, np.float32)
    height = np.zeros(shape, np.float32)  # metres, relief for the normal map
    for i, s in surf_of.items():
        m = part == i
        colour, r, mt = SURF[s]
        albedo[m] = lin(colour)
        rough[m] = r
        metal[m] = mt
    painted = on("pod", "pylon", "wing_centre", "wing_left", "wing_right", "stab", "fin", "boom")

    # Large-scale unevenness of the paint, and grain.
    albedo *= (1 + 0.05 * (nz3 - 0.5) + 0.03 * (nz2 - 0.5) + 0.015 * (grain - 0.5))[..., None]
    rough += 0.06 * (nz2 - 0.5) + 0.03 * (grain - 0.5)

    # --- Pod ---------------------------------------------------------------------------------------------
    podm = on("pod")
    seam = groove(x - 0.205, 0.0006) * podm  # the nose cap's seam
    height -= 0.0003 * seam
    # Battery hatch on top, with a thumb latch at each end.
    top = podm & (nz > 0.35) & (z > 0.02)
    sdf = rrect(x, y, 0.130, 0.0, 0.062, 0.032, 0.006)
    hatch = groove(sdf, 0.0006) * top
    height -= 0.00035 * hatch
    for lx in (0.181, 0.079):
        latch = top & (rrect(x, y, lx, 0.0, 0.0045, 0.008, 0.002) < 0)
        rim = groove(rrect(x, y, lx, 0.0, 0.0045, 0.008, 0.002), 0.0005) * top
        height += 0.0005 * smoothstep(0.0, 0.0006, -rrect(x, y, lx, 0.0, 0.0045, 0.008, 0.002)) * top
        albedo[latch] = lin((36, 37, 38))
        rough[latch] = 0.62
        height -= 0.0002 * rim
    # Screws on the nose cap's seam, both sides.
    side = podm & (np.abs(ny) > 0.45)
    for sx, sz in ((0.198, 0.022), (0.198, -0.022), (0.060, 0.026), (-0.020, 0.026)):
        d = np.hypot(x - sx, z - sz)
        head = side & (d < 0.0019)
        height -= 0.0004 * groove(d - 0.0019, 0.0004) * side
        slot = head & (np.abs((x - sx) * 0.7 + (z - sz) * 0.7) < 0.0003)
        height -= 0.0003 * slot
        albedo[head] = lin((70, 72, 74))
        metal[head] = 0.9
        rough[head] = 0.4
    # Cooling vents at the rear of each side.
    vents = np.zeros(shape, np.float32)
    for vz in (0.0135, 0.0045, -0.0045, -0.0135):
        vsdf = rrect(x, z, -0.012, vz, 0.016, 0.0013, 0.0013)
        vents = np.maximum(vents, side * smoothstep(0.0003, -0.0003, vsdf))
    height -= 0.0009 * vents
    albedo = mix(albedo, lin((12, 12, 13)), vents * 0.9)
    rough = mix(rough, 0.7, vents)
    # A bar-code label on the right side.
    right = podm & (ny < -0.6)
    lab = right & (rrect(x, z, 0.125, 0.004, 0.025, 0.011, 0.0015) < 0)
    ink = stamp(lab, x - 0.125, z - 0.004, label_mask(5), 0.017, 0.044, 0.0004)
    albedo[lab] = lin((214, 212, 200))
    rough[lab] = 0.35
    height += 0.00008 * lab
    albedo = mix(albedo, lin((22, 22, 22)), ink)
    # Handling: the sides under the wing, where the pod is held to launch, are a little darker and polished.
    held = podm & (np.abs(ny) > 0.3) & (x > -0.04) & (x < 0.14)
    hold = held * smoothstep(0.35, 0.75, nz2) * 0.6
    albedo *= (1 - 0.12 * hold)[..., None]
    rough -= 0.12 * hold
    # The belly takes the landings (a deep stall onto the ground): scuffed and stained along its length.
    belly = (podm | on("gimbal")) & (nz < -0.45)
    sc = streaks(y, x, 0.0018, 0.03, 0.35, 3, 0.2) * belly * smoothstep(0.3, 0.6, nz2)
    albedo = mix(albedo, lin((150, 148, 138)), 0.5 * sc)
    rough += 0.15 * sc
    dirt = belly * smoothstep(0.45, 0.8, nz3) * 0.55
    albedo = mix(albedo, lin((86, 78, 60)), dirt)
    rough += 0.15 * dirt

    # --- Gimbal: the camera ball, a daylight lens and an infrared window side by side ----------------------
    gm = on("gimbal")
    v = (P - GIMBAL_C) / GIMBAL_R
    v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
    for sign, kind in ((1, "eo"), (-1, "ir")):
        c = math.cos(math.radians(13)) * LOOK + sign * math.sin(math.radians(13)) * G_SIDE
        ang = np.degrees(np.arccos(np.clip(v @ c.astype(np.float32), -1, 1)))
        r_win = 8.5 if kind == "eo" else 7.5
        win = gm & (ang < r_win)
        bez = gm & (ang >= r_win) & (ang < r_win + 2.5)
        height -= (0.0012 * smoothstep(r_win + 2.5, r_win, ang)) * gm
        albedo[bez] = lin((14, 14, 15))
        rough[bez] = 0.55
        if kind == "eo":
            albedo[win] = lin((10, 14, 22))
            rough[win] = 0.04
            metal[win] = 0.0
            ring = gm & (ang > 2.8) & (ang < 3.6)  # the coated inner element's rim
            albedo[ring] = lin((40, 30, 60))
        else:
            albedo[win] = lin((52, 52, 56))
            rough[win] = 0.12
            metal[win] = 0.75
    yoke = gm & (np.abs(np.abs(v[..., 1]) - 0.62) < 0.03)
    height -= 0.0003 * yoke

    # --- Pylon and motor -----------------------------------------------------------------------------------
    pyl = on("pylon")
    height -= 0.0003 * groove(z - 0.018, 0.0005) * pyl  # where the fairing meets the pod's moulding
    mot = on("motor")
    psi = np.degrees(np.arctan2(z - MOTOR_Z, y)) % 45.0
    slots = mot & (np.abs(psi - 22.5) < 4.5) & (x < -0.081) & (x > -0.112)
    height -= 0.0012 * slots
    albedo[slots] = lin((92, 52, 26))  # the copper windings showing through the can's slots
    metal[slots] = 1.0
    rough[slots] = 0.5
    mount_ring = mot & (x > -0.069)
    albedo[mount_ring] = lin((22, 22, 23))
    metal[mount_ring] = 0.0
    rough[mount_ring] = 0.6
    height -= 0.0003 * groove(x + 0.069, 0.0004) * mot
    face = mot & (nx < -0.9)
    height -= 0.0002 * groove(np.hypot(y, z - MOTOR_Z) - 0.009, 0.0004) * face

    # --- Boom ----------------------------------------------------------------------------------------------
    bm = on("boom")
    band = bm & (np.abs(x + 0.33) < 0.006)  # the breakaway joint's sleeve
    albedo[band] = lin((40, 41, 42))
    rough[band] = 0.55
    height -= 0.0003 * (groove(x + 0.324, 0.0004) + groove(x + 0.336, 0.0004)) * bm
    albedo = mix(albedo, albedo * 0.9, bm * streaks(np.arctan2(z, y) * 0.011, x, 0.0016, 0.05, 0.3, 9, 0.3))

    # --- Wing ----------------------------------------------------------------------------------------------
    wm = on("wing_centre", "wing_left", "wing_right")
    ay = np.abs(y)
    cf = (WING_LE - x) / wing_chord(ay)  # chord fraction, near enough
    upper = wm & (nz > 0)
    weave = np.sin(2 * np.pi * (x + y) / 0.004) * np.sin(2 * np.pi * (x - y) / 0.004)
    albedo *= (1 + 0.012 * weave * (wm | on("stab", "fin")))[..., None]
    rough += 0.02 * weave * (wm | on("stab", "fin"))
    joint = wm & (np.abs(ay - JOINT) < 0.0012)
    height -= 0.0004 * groove(ay - JOINT, 0.0009) * wm
    albedo[joint] *= 0.55
    for sgn, colour in JOINT_MARK.items():
        mark = upper & (np.sign(y) == sgn) & (np.abs(ay - JOINT) < 0.012) & (np.abs(cf - 0.17) < 0.009)
        albedo[mark] = lin(colour)
        rough[mark] = 0.5
    tape = upper & (rrect(ay, cf * wing_chord(ay), 0.505, 0.07, 0.02, 0.02, 0.002) < 0)
    tape_edge = groove(rrect(ay, cf * wing_chord(ay), 0.505, 0.07, 0.02, 0.02, 0.002), 0.0004) * upper
    albedo[tape] = lin(TAPE)
    rough[tape] = 0.45
    height += 0.0001 * tape
    height -= 0.00005 * tape_edge
    worn_tape = tape & (smoothstep(0.55, 0.8, nz1) > 0.5)
    albedo[worn_tape] = mix(albedo[worn_tape], lin((205, 120, 70)), 0.6)
    # The leading edges and tips take the knocks: rubbed paint and chips showing the light core.
    le = wm & (cf < 0.03)
    tip = wm & (ay > SEMI_SPAN - 0.02)
    rub = (le | tip) * smoothstep(0.35, 0.7, nz2)
    chips = (le | tip) * (nz1 > 0.62) * smoothstep(0.4, 0.6, nz2)
    albedo = mix(albedo, lin((196, 196, 188)), 0.35 * rub + 0.6 * chips)
    rough += 0.1 * rub
    height -= 0.00015 * chips
    # Underneath: grass and dirt from the landings, and spanwise scrapes.
    lower = (wm | on("stab")) & (nz < -0.2)
    stain = lower * smoothstep(0.5, 0.85, nz3) * smoothstep(0.3, 0.7, nz2)
    albedo = mix(albedo, lin((92, 96, 62)), 0.45 * stain)
    sc = streaks(x, y, 0.0022, 0.06, 0.25, 5, 0.22) * lower * smoothstep(0.45, 0.7, nz2)
    albedo = mix(albedo, lin((200, 200, 192)), 0.35 * sc)
    rough += 0.12 * (stain + sc)

    # --- Tail ----------------------------------------------------------------------------------------------
    st = on("stab")
    le_s, c_s = stab_le_chord(ay)
    cfs = (le_s - x) / c_s
    elevator = st & (ay > 0.012) & (ay < STAB_SEMI - 0.012)
    height -= 0.0004 * groove((cfs - 0.65) * c_s, 0.0006) * elevator
    height -= 0.0004 * groove(ay - 0.012, 0.0006) * st * (cfs > 0.65)
    fm = on("fin")
    h = z - FIN_Z0
    le_f, c_f = fin_le_chord(h)
    cff = (le_f - x) / c_f
    rudder = fm & (h > 0.012) & (h < FIN_H - 0.014)
    height -= 0.0004 * groove((cff - 0.6) * c_f, 0.0006) * rudder
    height -= 0.0004 * groove(h - 0.012, 0.0006) * fm * (cff > 0.6)
    # The servo's cover on the fin's right side, held by two screws.
    fin_right = fm & (y < 0) & (np.abs(ny) > 0.6)
    cover = rrect(x, z, -0.546, -0.010, 0.010, 0.0055, 0.0015)
    height -= 0.0003 * groove(cover, 0.0005) * fin_right
    for sx in (-0.5385, -0.5535):
        d = np.hypot(x - sx, z + 0.010)
        scr = fin_right & (d < 0.0012)
        albedo[scr] = lin((60, 62, 64))
        metal[scr] = 0.9
        height -= 0.0002 * groove(d - 0.0012, 0.0003) * fin_right
    # The serial, stencilled on both sides of the fin.
    for sgn in (1, -1):
        where = fm & (np.sign(y) == sgn) & (np.abs(ny) > 0.6)
        u = (-(x + 0.553) if sgn > 0 else (x + 0.553))
        cover_t = stamp(where, u, z - 0.034, text_mask(SERIAL), 0.0085, texel=0.0005)
        albedo = mix(albedo, lin((24, 24, 24)), 0.92 * cover_t)
        rough = mix(rough, 0.5, cover_t)
    mt = on("mount")
    height -= 0.0003 * groove(x + 0.55, 0.0005) * mt  # the moulding's parting line

    # --- Prop ----------------------------------------------------------------------------------------------
    pr = on("blade")
    albedo = mix(albedo, lin((70, 70, 72)), pr * smoothstep(0.05, 0.25, edge1) * smoothstep(0.4, 0.7, nz2))
    sp = on("spinner")
    height -= 0.0003 * groove(x - (HUB[0] + 0.004), 0.0004) * sp

    # --- Wear and grime everywhere ---------------------------------------------------------------------------
    convex = smoothstep(0.08, 0.3, edge1) * smoothstep(0.75, 0.95, cav)
    worn = convex * painted * smoothstep(0.35, 0.65, nz2)
    albedo = mix(albedo, albedo * 1.25 + 0.02, worn * 0.6)
    rough += 0.08 * worn
    crev = 1 - smoothstep(0.35, 0.9, cav)
    albedo *= (1 - 0.35 * crev)[..., None]
    rough += 0.1 * crev
    dust = (nz > 0.5) * painted * smoothstep(0.55, 0.9, nz3) * 0.12
    albedo = mix(albedo, lin((150, 142, 122)), dust)
    rough += 0.1 * dust

    # --- Maps ------------------------------------------------------------------------------------------------
    slope = []
    for axis in (1, 0):
        dh = deriv(height, part, axis)
        dp = np.linalg.norm(deriv(P, part, axis), axis=-1)
        slope.append(np.where(dp > 1e-6, dh / np.maximum(dp, 1e-6), 0.0))
    normal = np.stack([-slope[0], -slope[1], np.ones_like(slope[0])], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    ao_map = np.clip(ao, 0, 1) ** 0.85 * (0.75 + 0.25 * cav)
    # The texels between the islands were painted nothing (black). Filtering and mips reach into them, most where
    # the islands are slivers (the pod's nose and tail poles), which drew dark lines along the triangles' edges.
    # So every map takes its island's edge texels outwards again.
    finished = dilate({"albedo": albedo, "rough": rough[..., None], "metal": metal[..., None],
                       "normal": normal, "ao": ao_map[..., None]}, part >= 0, steps=64)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        f"{NAME}_color.png": to_srgb(np.clip(finished["albedo"], 0, 1)),
        f"{NAME}_rough.png": np.clip(finished["rough"][..., 0], 0.03, 1),
        f"{NAME}_metal.png": np.clip(finished["metal"][..., 0], 0, 1),
        f"{NAME}_normal.png": finished["normal"] * 0.5 + 0.5,
        f"{NAME}_ao.png": finished["ao"][..., 0],
    }
    for name, arr in files.items():
        write_png(out_dir / name, arr.astype(np.float32))
    return [str(out_dir / n) for n in files]


# ---------------------------------------------------------------------------------------------------------
# Export


def write_obj(path, obj, origin):
    """Triangles of `obj` with its split normals and UVs, in inches, as (Y, Z, X) for ModelDoc's Y-up import."""
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = (co.reshape(-1, 3) - origin) * INCH
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    nrm = np.empty(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", nrm)
    nrm = nrm.reshape(-1, 3)
    lines = [f"# Generated by Tools/build_recon_drone.py ({obj.name}); inches, Y-up as ModelDoc reads OBJ",
             f"o {obj.name}", "usemtl recon_drone"]
    lines += [f"v {p[1]:.5f} {p[2]:.5f} {p[0]:.5f}" for p in co]
    vt, vt_index = {}, []
    for t in np.round(uv, 6):
        key = (float(t[0]), float(t[1]))
        vt_index.append(vt.setdefault(key, len(vt)))
    vn, vn_index = {}, []
    for n in np.round(nrm, 4):
        key = (float(n[0]), float(n[1]), float(n[2]))
        vn_index.append(vn.setdefault(key, len(vn)))
    lines += [f"vt {u:.6f} {v:.6f}" for u, v in vt]
    lines += [f"vn {n[1]:.4f} {n[2]:.4f} {n[0]:.4f}" for n in vn]
    tris = 0
    for tri in me.loop_triangles:
        lines.append("f " + " ".join(f"{me.loops[l].vertex_index + 1}/{vt_index[l] + 1}/{vn_index[l] + 1}"
                                     for l in tri.loops))
        tris += 1
    Path(path).write_text("\n".join(lines) + "\n", newline="\n")
    return tris, co.min(0), co.max(0)


def write_vmdl(name, lods, thresholds):
    meshes = ",\n".join(
        f'    {{ _class = "RenderMeshFile" name = "lod{l}" filename = "{ASSET}/{name}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }' for l in lods)
    groups = ",\n".join(f'    {{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}'
                        for l, t in zip(lods, thresholds))
    text = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Tools/build_recon_drone.py
{{
 rootNode =
 {{
  _class = "RootNode"
  children =
  [
   {{ _class = "MaterialGroupList" children = [ {{ _class = "DefaultMaterialGroup" remaps = [ ] use_global_default = true global_default_material = "{ASSET}/{NAME}.vmat" }} ] }},
   {{ _class = "RenderMeshList" children = [
{meshes}
   ] }},
   {{ _class = "LODGroupList" children = [
{groups}
   ] }},
  ]
  model_archetype = ""
  primary_associated_entity = ""
  base_model_name = ""
 }}
}}
"""
    (OUT / f"{name}.vmdl").write_text(text, newline="\n")


def write_vmat():
    (OUT / f"{NAME}.vmat").write_text(f"""// Generated by Tools/build_recon_drone.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.500"
	g_flAmbientOcclusionDirectSpecular "0.600"
	TextureAmbientOcclusion "{ASSET}/{NAME}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{ASSET}/{NAME}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{ASSET}/{NAME}_metal.png"

	//---- Normal ----
	TextureNormal "{ASSET}/{NAME}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{ASSET}/{NAME}_rough.png"
}}
""", newline="\n")


def load_image(path, colorspace):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.reload()
    img.colorspace_settings.name = colorspace
    return img


def final_material(tex_dir=OUT):
    mat = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])

    def tex(name, colorspace):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = load_image(tex_dir / f"{NAME}_{name}.png", colorspace)
        return n
    nt.links.new(tex("color", "sRGB").outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex("rough", "Non-Color").outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(tex("metal", "Non-Color").outputs["Color"], bsdf.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nt.links.new(tex("normal", "Non-Color").outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    mat = final_material()
    info = {}
    # Both are written in their objects' own frames: the prop's mesh is already about its hub (its object sits at
    # HUB), so the prop model's origin is the hub.
    for model, name, lods, thresholds, origin in (("body", NAME, (0, 1, 2), (0.0, 10.0, 25.0), np.zeros(3)),
                                                   ("prop", PROP, (0, 1), (0.0, 10.0), np.zeros(3))):
        info[name] = {}
        for lod in lods:
            obj = bpy.data.objects[f"{name}_lod{lod}"]
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            tris, lo, hi = write_obj(OUT / f"{name}_lod{lod}.obj", obj, origin)
            info[name][f"lod{lod}"] = {"triangles": tris, "bounds_min": [round(float(lo[i]), 3) for i in (0, 1, 2)],
                                       "bounds_max": [round(float(hi[i]), 3) for i in (0, 1, 2)]}
        write_vmdl(name, lods, thresholds)
    info["prop_hub_inches"] = [round(float(c) * INCH, 3) for c in HUB]
    info["atlas"] = TEX
    (OUT / "asset-info.json").write_text(json.dumps(info, indent=2) + "\n", newline="\n")
    write_vmat()
    return info


def save_blend():
    path = OUT / f"{NAME}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, relative_remap=True, compress=True)
    Path(str(path) + "1").unlink(missing_ok=True)
    return path


# ---------------------------------------------------------------------------------------------------------
# Beauty renders: Cycles, the painted material, a grey studio.


def clear_beauty():
    for obj in [o for o in bpy.data.objects if o.name.startswith("beauty_")]:
        bpy.data.objects.remove(obj)
    for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras, bpy.data.materials):
        for item in list(coll):
            if item.name.startswith("beauty_") and item.users == 0:
                coll.remove(item)


def beauty(tag="beauty", views=("three_quarter", "side", "top", "rear", "under", "nose", "tail", "motor", "held")):
    scene = bpy.context.scene
    clear_beauty()
    use_cycles(scene)
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.film_transparent = False
    scene.world.color = (0.05, 0.055, 0.06)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    mat = final_material()
    for name in (f"{NAME}_lod0", f"{PROP}_lod0"):
        me = bpy.data.objects[name].data
        me.materials.clear()
        me.materials.append(mat)

    def add(obj):
        scene.collection.objects.link(obj)
        return obj
    floor_me = bpy.data.meshes.new("beauty_floor")
    floor_me.from_pydata([(-6, -6, -0.35), (6, -6, -0.35), (6, 6, -0.35), (-6, 6, -0.35)], [], [(0, 1, 2, 3)])
    floor = add(bpy.data.objects.new("beauty_floor", floor_me))
    floor_mat = bpy.data.materials.new("beauty_floor")
    fb = floor_mat.node_tree.nodes.get("Principled BSDF")
    fb.inputs["Base Color"].default_value = (0.09, 0.09, 0.095, 1)
    fb.inputs["Roughness"].default_value = 0.7
    floor_me.materials.append(floor_mat)
    for name, loc, energy, size, colour in (("key", (1.6, 2.2, 2.6), 150, 1.4, (1.0, 0.96, 0.9)),
                                            ("fill", (2.4, -2.2, 1.0), 30, 2.5, (0.85, 0.9, 1.0)),
                                            ("rim", (-2.4, -0.8, 2.2), 110, 1.2, (0.9, 0.95, 1.0))):
        light = bpy.data.lights.new(f"beauty_{name}", "AREA")
        light.energy, light.size, light.color = energy, size, colour
        obj = add(bpy.data.objects.new(f"beauty_{name}", light))
        obj.location = loc
        obj.rotation_euler = (Vector((0, 0, 0.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    try:
        for view in views:
            camera(scene, view)
            floor.hide_render = view == "under"
            scene.render.filepath = str(PREVIEW_DIR / f"{tag}_{view}.png")
            bpy.ops.render.render(write_still=True)
            paths.append(scene.render.filepath)
    finally:
        clear_beauty()
    return paths


def want(stage):
    return STAGES == "all" or stage in STAGES.split(",")


if __name__ == "__main__":
    if want("geometry"):
        build_geometry()
        if want("preview"):
            RESULT_PREVIEWS = preview()
    else:
        pack()
    if want("bake"):
        bpy.app.driver_namespace["drone_bake"] = bake()
    if want("textures"):
        RESULT_TEXTURES = compose(bpy.app.driver_namespace["drone_bake"], OUT)
    if want("export"):
        RESULT_EXPORT = export()
        print(json.dumps(RESULT_EXPORT, indent=1))
        save_blend()
    if want("beauty"):
        RESULT_BEAUTY = beauty()
