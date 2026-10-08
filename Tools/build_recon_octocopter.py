"""Build the tablet-flown recon multirotor: a coaxial X8 recon drone and its rugged tablet ground control station.

Run with Blender 5.1:  blender -b --factory-startup --python Tools/build_recon_octocopter.py
or in a running Blender: exec(compile(open(p).read(), p, "exec"), {"__file__": p, "__name__": "__main__"})
The build empties the open .blend first, so in a running Blender use a new file.

The aircraft is a class of small military recon multirotor (the user's photo: a coaxial X8 of the IF800 Tomcat's
kind, about 10 kg), at real size, with its own markings and no maker's name or logo:
- a low composite hull, 0.52 m long, with a vented nose panel, a battery hatch and a GPS mast;
- four round arms in an X, 1.20 m motor to motor, each through a folding collar out of the hull;
- on each arm's end a mount carrying two motors, one up and one down, each with a 26 inch (0.66 m) two-blade
  folding prop: the pair counter-rotates, and neighbouring arms' top props turn opposite ways;
- two black carbon-tube hoop skids, 0.43 m tall;
- a gimballed camera ball (daylight and thermal windows) under the nose, pitched by the game.

The tablet is a rugged ground control station: a 10.1 inch 16:10 screen between two thumbsticks, grip handles on
both sides, button pads and two paddle antennas. Its screen is a self-lit material of its own, drawn here: the
station's standby page (a map, telemetry and buttons; no brand).

Everything is built the way Tools/build_recon_drone.py builds the Raven, and with its helpers: every part is a loft
of an analytic shape F(a, b), its UVs (a, b) in the part's rectangle of an atlas, so every LOD maps the same texture;
Cycles bakes LOD 0's facts into float images, and numpy paints the maps from them. Copies of a part (the arms,
motors, gear hoops, blades) share their rectangle; only the first is baked, the others stand by as occluders.
There are two atlases: the drone's (body, gimbal ball and props) and the tablet's.

Models (OBJ, inches, written (Y, Z, X) for ModelDoc's Y-up import), each about its own origin:
- recon_octocopter: the body, about the centre of gravity (arm height, hull middle). X forward, Z up.
- recon_octocopter_gimbal: the camera ball, about its pitch axis; it looks along +X.
- recon_octocopter_prop_ccw / _cw: a prop about its hub, thrust +Z; ccw turns anticlockwise seen from above.
- recon_octocopter_disc: a spinning prop's blur, a translucent disc about the hub.
- recon_tablet: the station about its middle; the screen faces -X, Y is the holder's left, Z up.
asset-info.json gives the hubs, spin directions, the gimbal's pivot and lens, the skids' height and the tablet's
grips and screen, in inches, for the game.

Units while modelling: metres. Stages (OCTO_STAGES, comma separated, default all): geometry, preview, bake,
textures, export, beauty. OCTO_TEX sets the atlas size (2048), PREVIEW_DIR where renders go.
"""
import bpy
import importlib.util
import json
import math
import tempfile
from pathlib import Path

import numpy as np
from mathutils import Matrix, Vector

SCRIPT = Path(globals().get("__file__") or r"D:\Documents\s&box projects\hc1\forked-shooter-main\Tools\build_recon_octocopter.py").resolve()
ROOT = SCRIPT.parents[1]


def _raven():
    spec = importlib.util.spec_from_file_location("build_recon_drone", SCRIPT.parent / "build_recon_drone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rd = _raven()
sgnpow, stack3, Airfoil, tip_round, Stations = rd.sgnpow, rd.stack3, rd.Airfoil, rd.tip_round, rd.Stations
lin, smoothstep, mix, groove, rrect, streaks = rd.lin, rd.smoothstep, rd.mix, rd.groove, rd.rrect, rd.streaks

OUT = ROOT / "Assets/models/recon_octocopter"
ASSET = "models/recon_octocopter"
NAME = "recon_octocopter"
TABLET = "recon_tablet"
STAGES = globals().get("OCTO_STAGES", "all")
PREVIEW_DIR = Path(globals().get("PREVIEW_DIR") or Path(tempfile.gettempdir()) / "recon_octocopter_preview")
TEX = int(globals().get("OCTO_TEX", 2048))
PAD = 8 / TEX
INCH = 39.37008
POS_LO, POS_SPAN = rd.POS_LO, rd.POS_SPAN
BAKE_PROP_OFFSET = np.array((0.0, 0.0, 3.0))


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array(((c, -s, 0), (s, c, 0), (0, 0, 1.0)))


def diag(x, y, z):
    return np.diag((float(x), float(y), float(z)))


I3 = np.eye(3)
MIRROR_Y, MIRROR_Z = diag(1, -1, 1), diag(1, 1, -1)


# ---------------------------------------------------------------------------------------------------------
# Shapes: general lofts


def lathe(st, origin, axis, side):
    """A solid of revolution of Stations (s along `axis` from `origin`, radius r); the seam faces `side`."""
    o, w = np.asarray(origin, np.float64), np.asarray(axis, np.float64)
    u = np.asarray(side, np.float64)
    u = u - w * (u @ w)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)

    def fn(a, b):
        s, r = st.at(a)
        th = 2 * np.pi * b
        c = o + s[..., None] * w
        return c + (r * np.cos(th))[..., None] * u + (r * np.sin(th))[..., None] * v, c
    return fn


def rbox(centre, half, e=0.3, frame=I3):
    """A superellipsoid (Barr's, both exponents e): a box with rounded edges, its poles on the frame's z."""
    c, h = np.asarray(centre, np.float64), np.asarray(half, np.float64)

    def fn(a, b):
        phi, th = -np.pi / 2 + np.pi * a, -np.pi + 2 * np.pi * b
        cp = sgnpow(np.cos(phi), e)
        local = stack3(h[0] * cp * sgnpow(np.cos(th), e), h[1] * cp * sgnpow(np.sin(th), e), h[2] * sgnpow(np.sin(phi), e))
        return c + local @ frame.T, np.broadcast_to(c, local.shape)
    return fn


def rounded_loop(corners, radius, steps=24):
    """A convex polygon (2D, anticlockwise) with its corners rounded, as a dense closed polyline from the middle of
    its first edge: points, outward normals, arc-length fractions, and each corner's arc as (start, end) fractions."""
    q = np.asarray(corners, np.float64)
    n = len(q)
    pts, nrm, arcs = [], [], []
    mid = (q[0] + q[1]) / 2
    d0 = (q[1] - q[0]) / np.linalg.norm(q[1] - q[0])
    pts.append(mid)
    nrm.append(np.array((d0[1], -d0[0])))
    for k in range(1, n + 1):
        i = k % n
        d1 = (q[i] - q[i - 1]) / np.linalg.norm(q[i] - q[i - 1])
        d2 = (q[(i + 1) % n] - q[i]) / np.linalg.norm(q[(i + 1) % n] - q[i])
        turn = math.acos(np.clip(d1 @ d2, -1, 1))
        t = radius * math.tan(turn / 2)
        s = q[i] - d1 * t
        o = s + np.array((-d1[1], d1[0])) * radius
        a0 = math.atan2(s[1] - o[1], s[0] - o[0])
        start = len(pts)
        for j in range(steps + 1):
            ang = a0 + turn * j / steps
            dirn = np.array((math.cos(ang), math.sin(ang)))
            pts.append(o + dirn * radius)
            nrm.append(dirn)
        arcs.append((start, len(pts) - 1))
    pts.append(mid)
    nrm.append(np.array((d0[1], -d0[0])))
    pts, nrm = np.array(pts), np.array(nrm)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    f = s / s[-1]
    return pts, nrm, f, [(f[a], f[b]) for a, b in arcs], s[-1]


def loop_rows(arcs, seg_n, arc_n):
    """Rows along a rounded loop: each straight run split in seg_n, each arc in arc_n."""
    def pick(n, lod):
        rows = [0.0, 1.0]
        edges = [0.0] + [x for arc in arcs for x in arc] + [1.0]
        for i in range(0, len(edges), 2):
            rows.extend(np.linspace(edges[i], edges[i + 1], seg_n[lod] + 1))
        for a0, a1 in arcs:
            rows.extend(np.linspace(a0, a1, arc_n[lod] + 1))
        return np.unique(np.round(rows, 9))
    return pick


def loop_eval(loop, a):
    pts, nrm, f = loop[:3]
    p = np.stack([np.interp(a, f, pts[:, 0]), np.interp(a, f, pts[:, 1])], axis=-1)
    n = np.stack([np.interp(a, f, nrm[:, 0]), np.interp(a, f, nrm[:, 1])], axis=-1)
    return p, n / np.linalg.norm(n, axis=-1, keepdims=True)


# ---------------------------------------------------------------------------------------------------------
# The drone. Metres; X forward, Y left, Z up; the origin is the centre of gravity, on the arms' axis line.

# Hull: a superellipse section lofted along x. The plan narrows a little fore and aft of the arms (symmetrically, so
# the four folding collars sit alike), the nose rounds over its last 0.10 m and the tail over 0.075 m; the top is a
# low, flat lid sloping down to the nose, over a dark lower body and a flat belly tray.
HULL_NOSE, HULL_TAIL, HULL_W = 0.265, -0.255, 0.150
HULL_TOP, HULL_BOT, HULL_Z0 = 0.064, -0.068, -0.006
HULL_E_TOP, HULL_E_BOT = 3.6, 3.6


def hull_section(x):
    dn, dt = HULL_NOSE - x, x - HULL_TAIL
    f = np.where(dn < 0.10, np.sqrt(np.clip(1 - (1 - dn / 0.10) ** 2, 0, 1)), 1.0)
    f = f * np.where(dt < 0.075, np.sqrt(np.clip(1 - (1 - dt / 0.075) ** 2, 0, 1)), 1.0)
    hw = HULL_W * (1 - 0.13 * smoothstep(0.02, 0.21, np.abs(x)))
    ht = (HULL_TOP - HULL_Z0) * (1 - 0.30 * smoothstep(-0.02, 0.24, x)) * (1 - 0.12 * smoothstep(-0.05, -0.24, x))
    hb = HULL_Z0 - HULL_BOT
    return hw * f, ht * f, hb * f


_hx = np.linspace(HULL_NOSE, HULL_TAIL, 4001)
_hw, _ht, _hb = hull_section(_hx)
_hs = np.concatenate([[0], np.cumsum(np.sqrt(np.diff(_hx) ** 2 + np.diff((_hw + _ht + _hb) / 2.5) ** 2))])
_ha = _hs / _hs[-1]


def hull(a, b):
    x = np.interp(a, _ha, _hx)
    hw, ht, hb = hull_section(x)
    th = -np.pi / 2 + 2 * np.pi * b  # the seam runs along the belly
    s, c = np.sin(th), np.cos(th)
    e = np.where(s > 0, HULL_E_TOP, HULL_E_BOT)
    z = HULL_Z0 + np.where(s > 0, ht, hb) * sgnpow(s, 2 / e)
    return stack3(x, hw * sgnpow(c, 2 / e), z), stack3(x, 0, HULL_Z0)


def hull_top(x, y):
    hw, ht, _ = hull_section(np.asarray(x, np.float64))
    return HULL_Z0 + ht * np.clip(1 - np.abs(y / hw) ** HULL_E_TOP, 0, 1) ** (1 / HULL_E_TOP)


def _hull_reach(deg):
    """How far the hull reaches along a level direction from the centre line, at the arms' height."""
    d = np.array((math.cos(math.radians(deg)), math.sin(math.radians(deg))))
    r = np.linspace(0.05, 0.3, 2501)
    x, y = r * d[0], r * d[1]
    hw, ht, hb = hull_section(x)
    zr = (0 - HULL_Z0) / ht
    inside = (np.abs(y) / np.maximum(hw, 1e-9)) ** HULL_E_TOP + np.abs(zr) ** HULL_E_TOP <= 1
    return float(r[inside].max())


# Arms: 32 mm round tubes at 45, 135, 225 and 315 degrees, motors 0.60 m out (1.20 m motor to motor). Arm parts are
# modelled along +X (the arm frame) and placed by turning about Z.
ARM_ANGLES = (45.0, 135.0, 225.0, 315.0)
ARM_R0, R_M, ARM_TUBE = 0.10, 0.600, 0.016
COLLAR_AT = max(_hull_reach(a) for a in ARM_ANGLES)  # the hull's edge along the arms


def arm(a, b):
    x = ARM_R0 + (R_M - ARM_R0) * a
    th = 2 * np.pi * b
    return stack3(x, ARM_TUBE * np.cos(th), ARM_TUBE * np.sin(th)), stack3(x, 0, 0)


# The folding collar: a black anodised sleeve where the arm leaves the hull, its hinge and latch on top.
COLLAR = Stations([(COLLAR_AT - 0.014, 0.0158), (COLLAR_AT - 0.014, 0.0232), (COLLAR_AT - 0.010, 0.0242),
                   (COLLAR_AT + 0.018, 0.0242), (COLLAR_AT + 0.020, 0.0225), (COLLAR_AT + 0.023, 0.0225),
                   (COLLAR_AT + 0.025, 0.0242), (COLLAR_AT + 0.046, 0.0242), (COLLAR_AT + 0.050, 0.0232),
                   (COLLAR_AT + 0.054, 0.0190), (COLLAR_AT + 0.055, 0.0158)])
CLAMP = Stations([(R_M - 0.078, 0.0158), (R_M - 0.077, 0.0178), (R_M - 0.074, 0.0195), (R_M - 0.040, 0.0195),
                  (R_M - 0.035, 0.0180)])
# The motor mount: a short finned black drum on the arm's end, the upper motor on its top face and the lower on its
# bottom.
MOUNT = Stations([(-0.020, 0.0), (-0.020, 0.0350), (-0.0175, 0.0380), (0.0175, 0.0380), (0.020, 0.0350), (0.020, 0.0)])
# A motor for 26 inch props on a 10 kg coaxial machine: a 96 mm pancake outrunner, wide and short. Its base flange on
# the mount, the stator's foot, the turning bell (finned, with the windings' slots in its side), its chamfered top
# face and the prop adapter. The stack from prop to prop is 1.5 times a motor's width, as on the real machine.
MOTOR = Stations([(0.0195, 0.0), (0.0195, 0.0390), (0.0210, 0.0415), (0.0225, 0.0430), (0.0240, 0.0465),
                  (0.0260, 0.0480), (0.0400, 0.0480), (0.0530, 0.0480), (0.0550, 0.0465), (0.0565, 0.0430),
                  (0.0565, 0.0190), (0.0578, 0.0150), (0.0625, 0.0125), (0.0635, 0.0105), (0.0635, 0.0)])
PROP_Z = 0.072  # each prop's hub, over and under the arm
GEAR_TUBE = 0.011
# Gear: each hoop is one bent 22 mm carbon tube, a top bar under the belly, two legs splaying out and down, a skid.
G_TOP_X, G_TOP_Y, G_TOP_Z = 0.125, 0.085, HULL_BOT - 0.006 - GEAR_TUBE
G_BOT_X, G_BOT_Y, G_BOT_Z = 0.170, 0.215, -0.425 + GEAR_TUBE
_g_down = np.array((0.0, G_BOT_Y - G_TOP_Y, G_BOT_Z - G_TOP_Z))
G_LEN = float(np.linalg.norm(_g_down))
G_S, G_T = np.array((1.0, 0, 0)), _g_down / G_LEN
G_N = np.cross(G_S, G_T)
G_O = np.array((0.0, G_TOP_Y, G_TOP_Z))
GEAR_LOOP = rounded_loop([(-G_TOP_X, 0), (G_TOP_X, 0), (G_BOT_X, G_LEN), (-G_BOT_X, G_LEN)], 0.038)


def gear(a, b):
    p, n = loop_eval(GEAR_LOOP, a)
    th = 2 * np.pi * b
    c = G_O + p[..., :1] * G_S + p[..., 1:] * G_T
    out = n[..., :1] * G_S + n[..., 1:] * G_T
    return c + GEAR_TUBE * (np.cos(th)[..., None] * out + np.sin(th)[..., None] * G_N), c


# The gimbal: a yaw puck out of the belly under the nose, a fork's two cheeks, and the ball between them (its own
# model, pitched by the game) with a daylight lens and a thermal window side by side.
GIMBAL_C = np.array((0.170, 0.0, -0.152))
GIMBAL_R = 0.050
PUCK = Stations([(-0.045, 0.0), (-0.045, 0.0410), (-0.088, 0.0410), (-0.092, 0.0385), (-0.0945, 0.0330), (-0.0945, 0.0)])
CHEEK_Y = 0.0575
PITCH_CAP = Stations([(CHEEK_Y + 0.0035, 0.0), (CHEEK_Y + 0.0035, 0.0125), (CHEEK_Y + 0.0060, 0.0118),
                      (CHEEK_Y + 0.0080, 0.0095), (CHEEK_Y + 0.0085, 0.0)])


def ball(a, b):
    phi, beta = np.pi * a, 2 * np.pi * b - np.pi  # poles on the pitch axis (Y), the seam at the back
    d = stack3(np.sin(phi) * np.cos(beta), np.cos(phi), np.sin(phi) * np.sin(beta))
    return GIMBAL_R * d, np.zeros_like(d)


# GPS mast at the top's rear, and two datalink antennas on the tail, raked back and out.
GPS_X = -0.120
GPS_MAST = Stations([(0.050, 0.0), (0.050, 0.0065), (0.130, 0.0065), (0.130, 0.0)])
GPS_PUCK = Stations([(0.128, 0.0), (0.128, 0.0300), (0.1315, 0.0320), (0.1400, 0.0318), (0.1460, 0.0280),
                     (0.1495, 0.0180), (0.1505, 0.0)])
ANT_BASE = np.array((-0.205, 0.062, 0.0))
ANT_BASE[2] = float(hull_top(ANT_BASE[0], ANT_BASE[1])) - 0.004
ANT_AXIS = np.array((-math.sin(math.radians(25)), math.sin(math.radians(12)), math.cos(math.radians(25))))
ANT_AXIS /= np.linalg.norm(ANT_AXIS)
ANTENNA = Stations([(0.0, 0.0), (0.0, 0.0085), (0.018, 0.0085), (0.021, 0.0068), (0.026, 0.0052), (0.120, 0.0040),
                    (0.124, 0.0028), (0.1255, 0.0)])

# Props: 26 inch (0.33 m radius), 8.7 inch pitch, folding carbon blades on a clevis hub. In the prop's frame: the hub
# at the origin, thrust +Z. The ccw prop's blade along +X moves towards +Y (anticlockwise seen from above).
PROP_R, PROP_PITCH = 0.330, 0.22
PROP_FOIL = Airfoil(0.10, 0.04, 0.4)
HUB = Stations([(-0.0085, 0.0), (-0.0085, 0.0120), (-0.0072, 0.0205), (-0.0050, 0.0240), (0.0050, 0.0240),
                (0.0072, 0.0205), (0.0085, 0.0120), (0.0085, 0.0)])
BLADE_R0 = 0.034


def blade_chord(r):
    rf = r / PROP_R
    return np.interp(rf, [0.10, 0.16, 0.26, 0.45, 0.70, 0.88, 1.0], [0.026, 0.044, 0.050, 0.046, 0.036, 0.027, 0.020])


def blade(a, b):
    r = BLADE_R0 + (PROP_R - BLADE_R0) * a
    rf = r / PROP_R
    c = blade_chord(r) * tip_round(PROP_R - r, 0.014)
    t = np.interp(rf, [0.10, 0.15, 0.24, 1.0], [0.34, 0.18, 0.11, 0.075])
    beta = np.arctan(PROP_PITCH / (2 * np.pi * np.maximum(r, 0.055)))
    xc, yn = PROP_FOIL.unit(PROP_FOIL.tau_of(b), t)
    q = 0.010 * np.sin(np.pi * np.clip((rf - 0.12) / 0.88, 0, 1)) - 0.028 * np.clip((rf - 0.62) / 0.38, 0, 1) ** 2
    d = stack3(0, -np.cos(beta), -np.sin(beta))  # leading edge to trailing edge
    n = stack3(0, -np.sin(beta), np.cos(beta))  # the suction side, up
    p = stack3(r, q, 0) + ((xc - 0.25) * c)[..., None] * d + (yn * c)[..., None] * n
    return p, stack3(r, q, 0)


# Hub positions in the drone's frame, and each prop's turn: the top props alternate arm to arm, each lower prop turns
# against its top one. +1 is anticlockwise seen from above.
HUBS = []
for k, ang in enumerate(ARM_ANGLES):
    xy = R_M * np.array((math.cos(math.radians(ang)), math.sin(math.radians(ang))))
    top = 1 if k % 2 == 0 else -1
    HUBS.append(((xy[0], xy[1], PROP_Z), top))
    HUBS.append(((xy[0], xy[1], -PROP_Z), -top))
DISC_R0, DISC_R1 = 0.004, 0.338


def disc(side):
    def fn(a, b):
        r = DISC_R0 + (DISC_R1 - DISC_R0) * a
        th = 2 * np.pi * b * side
        z = 0.0004 * side
        p = stack3(r * np.cos(th), r * np.sin(th), z)
        return p, p - stack3(0, 0, 0.01 * side)
    return fn


def disc_uv(a, b, p):
    return np.stack([0.5 + p[..., 0] / (2 * DISC_R1), 0.5 + p[..., 1] / (2 * DISC_R1)], axis=-1)


# ---------------------------------------------------------------------------------------------------------
# The tablet: in its own frame, the screen faces -X, Y is the holder's left, Z up; the origin is the case's middle.
TW, TH, T_FRONT, T_BACK, T_RC, T_RE = 0.170, 0.100, -0.014, 0.016, 0.022, 0.007
SCREEN_W, SCREEN_H, SCREEN_Z = 0.2235, 0.1397, 0.012  # 10.1 inches, 16:10
STICK_Y, STICK_Z = 0.140, -0.045
_rr = rounded_loop([(TW, -TH), (TW, TH), (-TW, TH), (-TW, -TH)], T_RC, steps=32)
# (y, z) seen from the back (+X), anticlockwise: the loop starts at the right edge's middle. The rows: each corner
# in 6/3, each edge in 2/1.
RR_ROWS = loop_rows(_rr[3], {0: 2, 1: 1}, {0: 6, 1: 3})


def rr_point(b, inset=0.0):
    p, n = loop_eval(_rr, b)
    return p - inset[..., None] * n if np.ndim(inset) else p - inset * n


def tab_face(x, side):
    def fn(a, b):
        p = rr_point(b, T_RE) * a[..., None]
        P = stack3(np.full(a.shape, x), p[..., 0], p[..., 1])
        return P, P + stack3(0.01 * side, 0, 0)
    return fn


def face_uv(p):
    return np.stack([TW - p[..., 1], p[..., 2] + TH], axis=-1)


_rim_l = np.array([math.pi / 2 * T_RE, (T_BACK - T_FRONT) - 2 * T_RE, math.pi / 2 * T_RE])
_rim_c = np.concatenate([[0], np.cumsum(_rim_l)]) / _rim_l.sum()


def tab_rim(a, b):
    s = a * _rim_l.sum()
    s1, s2 = _rim_l[0], _rim_l[0] + _rim_l[1]
    p1 = np.clip(s / T_RE, 0, math.pi / 2)
    p3 = np.clip((s - s2) / T_RE, 0, math.pi / 2)
    x = np.where(s < s1, T_FRONT + T_RE - T_RE * np.cos(p1),
                 np.where(s < s2, T_FRONT + T_RE + (s - s1), T_BACK - T_RE + T_RE * np.sin(p3)))
    inset = np.where(s < s1, T_RE - T_RE * np.sin(p1), np.where(s < s2, 0.0, T_RE - T_RE * np.cos(p3)))
    p = rr_point(b, inset)
    return stack3(x, p[..., 0], p[..., 1]), stack3(x, 0, 0)


def rim_rows(n_arc, n_side):
    def pick(n, lod):
        return np.unique(np.round(np.concatenate([np.linspace(0, _rim_c[1], n_arc[lod] + 1),
                                                  np.linspace(_rim_c[1], _rim_c[2], n_side[lod] + 1),
                                                  np.linspace(_rim_c[2], 1, n_arc[lod] + 1)]), 9))
    return pick


# Grips: rounded handles along both sides, behind the case's edge, where the hands hold it.
GRIP_C = np.array((0.026, TW + 0.004, -0.010))
GRIP_HX, GRIP_HY, GRIP_Z0, GRIP_Z1 = 0.027, 0.021, -0.090, 0.068


def grip(a, b):
    z = GRIP_Z0 + (GRIP_Z1 - GRIP_Z0) * a
    d = np.minimum(z - GRIP_Z0, GRIP_Z1 - z)
    f = np.where(d < 0.022, np.sqrt(np.clip(1 - (1 - d / 0.022) ** 2, 0, 1)), 1.0)
    th = 2 * np.pi * b
    bulge = 1 + 0.10 * np.sin(np.pi * a)
    x = GRIP_C[0] + GRIP_HX * f * bulge * sgnpow(np.cos(th), 2 / 2.6)
    y = GRIP_C[1] + GRIP_HY * f * bulge * sgnpow(np.sin(th), 2 / 2.6)
    return stack3(x, y, z), stack3(GRIP_C[0], GRIP_C[1], z)


STICK = Stations([(0.0, 0.0), (0.0, 0.0195), (0.0025, 0.0195), (0.0035, 0.0180), (0.0035, 0.0150), (0.0020, 0.0125),
                  (0.0020, 0.0080), (0.0045, 0.0062), (0.0075, 0.0042), (0.0140, 0.0036), (0.0150, 0.0060),
                  (0.0160, 0.0105), (0.0175, 0.0116), (0.0205, 0.0116), (0.0215, 0.0102), (0.0207, 0.0060),
                  (0.0202, 0.0)])
ANT_T_HINGE = np.array((0.010, TW - 0.026, TH - 0.010))
_aw = np.array((0.0, math.sin(math.radians(14)), math.cos(math.radians(14))))
TAB_ANT_FRAME = np.stack([np.array((1.0, 0, 0)), np.cross(_aw, (1.0, 0, 0)), _aw], axis=1)


def screen(a, b):
    p = stack3(T_FRONT - 0.0003, SCREEN_W / 2 - b * SCREEN_W, SCREEN_Z - SCREEN_H / 2 + a * SCREEN_H)
    return p, p + stack3(0.01, 0, 0)


def screen_uv(a, b, p):
    return np.stack([b, a], axis=-1)


# ---------------------------------------------------------------------------------------------------------
# Parts


def arms(*extra):
    return [rot_z(a) @ e for a in ARM_ANGLES for e in (extra or (I3,))]


class Part:
    """A loft placed in models: {model: [3x3 linear maps]}; the first map of the first model is the one baked."""

    def __init__(self, name, surf, fn, lods, place, atlas="drone", closed=True, density=1.0, a_rows=rd.uniform,
                 b_rows=rd.uniform, uv=None, extent=None, material=None):
        self.name, self.surf, self.fn, self.lods, self.place = name, surf, fn, lods, place
        self.atlas, self.closed, self.density, self.a_rows, self.b_rows = atlas, closed, density, a_rows, b_rows
        self.uv, self.material = uv, material or {"drone": NAME, "tablet": TABLET}.get(atlas)
        if extent:
            self.around, self.along = extent
        else:
            A, B = np.meshgrid(np.linspace(0, 1, 97), np.linspace(0, 1, 97), indexing="ij")
            P, _ = fn(A, B)
            self.along = np.linalg.norm(np.diff(P, axis=0), axis=-1).sum(axis=0).max()
            self.around = np.linalg.norm(np.diff(P, axis=1), axis=-1).sum(axis=1).max()


def lathe_rows(st, subsets):
    return st.sampler(subsets)


# Navigation lights, a lens on each motor mount's outer face: red on the left front arm, green on the right front,
# white on the rear arms, as on aircraft (left is +Y). Each colour is a self-lit material of its own.
LAMPS = {"red": (45.0,), "green": (315.0,), "white": (135.0, 225.0)}
LAMP_RGB = {"red": (255, 32, 24), "green": (30, 255, 90), "white": (255, 246, 230)}
G_ROWS = loop_rows(GEAR_LOOP[3], {0: 2, 1: 1, 2: 1}, {0: 5, 1: 3, 2: 2})
BODY = {"body": [I3]}
PARTS = [
    Part("hull", "hull", hull, {0: (34, 32), 1: (18, 18), 2: (9, 10)}, BODY, density=1.0),
    Part("arm", "arm", arm, {0: (3, 16), 1: (1, 10), 2: (1, 6)}, {"body": arms()}, density=1.1),
    Part("collar", "collar", lathe(COLLAR, (0, 0, 0), (1, 0, 0), (0, 0, -1)), {0: (10, 16), 1: (5, 10), 2: (3, 6)},
         {"body": arms()}, density=1.6, a_rows=COLLAR.sampler({0: range(11), 1: (0, 1, 3, 7, 9, 10), 2: (0, 1, 9, 10)})),
    Part("clamp", "mount", lathe(CLAMP, (0, 0, 0), (1, 0, 0), (0, 0, -1)), {0: (4, 16), 1: (2, 10), 2: (1, 6)},
         {"body": arms()}, density=1.6, a_rows=CLAMP.sampler({0: range(5), 1: (0, 2, 4), 2: (0, 4)})),
    Part("mount", "mount", lathe(MOUNT, (R_M, 0, 0), (0, 0, 1), (-1, 0, 0)), {0: (5, 18), 1: (3, 12), 2: (1, 8)},
         {"body": arms()}, density=1.6, a_rows=MOUNT.sampler({0: range(6), 1: (0, 1, 4, 5), 2: (0, 2, 3, 5)})),
    *[Part(f"lamp_{colour}", "lamp", rbox((R_M + 0.0375, 0, 0), (0.0042, 0.0105, 0.0078), 0.35),
           {0: (6, 8), 1: (4, 6), 2: (2, 4)}, {"body": [rot_z(a) for a in angles]}, atlas=None,
           uv=lambda a, b, p: np.full(p.shape[:-1] + (2,), 0.5), material=f"{NAME}_lamp_{colour}")
      for colour, angles in LAMPS.items()],
    Part("motor", "motor", lathe(MOTOR, (R_M, 0, 0), (0, 0, 1), (-1, 0, 0)), {0: (14, 18), 1: (8, 12), 2: (4, 8)},
         {"body": arms(I3, MIRROR_Z)}, density=1.6,
         a_rows=MOTOR.sampler({0: range(15), 1: (0, 1, 2, 4, 5, 7, 8, 10, 12, 14), 2: (0, 2, 5, 8, 10, 14)})),
    Part("gear", "gear", gear, {0: (0, 10), 1: (0, 7), 2: (0, 5)}, {"body": [I3, MIRROR_Y]}, density=0.8,
         a_rows=G_ROWS),
    Part("gear_clamp", "clamp", rbox((G_TOP_X - 0.022, G_TOP_Y, G_TOP_Z + 0.005), (0.016, 0.016, 0.014), 0.35),
         {0: (8, 12), 1: (4, 8)}, {"body": [I3, MIRROR_Y, diag(-1, 1, 1), diag(-1, -1, 1)]}, density=1.4),
    Part("puck", "gimbal", lathe(PUCK, (GIMBAL_C[0], 0, 0), (0, 0, 1), (-1, 0, 0)), {0: (5, 20), 1: (3, 12), 2: (2, 8)},
         BODY, density=1.8, a_rows=PUCK.sampler({0: range(6), 1: (0, 1, 3, 5), 2: (0, 1, 3, 5)})),
    Part("cheek", "gimbal", rbox((GIMBAL_C[0], CHEEK_Y, -0.127), (0.0225, 0.0045, 0.041), 0.32),
         {0: (10, 14), 1: (6, 8), 2: (4, 6)}, {"body": [I3, MIRROR_Y]}, density=1.8),
    Part("pitch_cap", "gimbal", lathe(PITCH_CAP, (GIMBAL_C[0], 0, GIMBAL_C[2]), (0, 1, 0), (0, 0, -1)),
         {0: (4, 14), 1: (2, 8)}, {"body": [I3, MIRROR_Y]}, density=1.8),
    Part("gps_mast", "gps", lathe(GPS_MAST, (GPS_X, 0, 0), (0, 0, 1), (-1, 0, 0)), {0: (3, 10), 1: (1, 6), 2: (1, 4)},
         BODY, density=1.2),
    Part("gps_puck", "gps", lathe(GPS_PUCK, (GPS_X, 0, 0), (0, 0, 1), (-1, 0, 0)), {0: (6, 20), 1: (4, 12), 2: (2, 8)},
         BODY, density=1.5),
    Part("antenna", "antenna", lathe(ANTENNA, ANT_BASE, ANT_AXIS, (1, 0, 0)), {0: (7, 10), 1: (4, 6), 2: (2, 4)},
         {"body": [I3, MIRROR_Y]}, density=1.4),
    Part("ball", "ball", ball, {0: (12, 20), 1: (7, 12)}, {"gimbal": [I3]}, density=2.2),
    Part("hub", "hub", lathe(HUB, (0, 0, 0), (0, 0, 1), (-1, 0, 0)), {0: (7, 16), 1: (3, 10)},
         {"prop_ccw": [I3], "prop_cw": [MIRROR_Y]}, density=2.0, a_rows=HUB.sampler({0: range(8), 1: (0, 2, 5, 7)})),
    Part("yoke", "hub", rbox((0.036, 0, 0), (0.016, 0.0135, 0.0078), 0.3), {0: (6, 10), 1: (4, 6)},
         {"prop_ccw": [I3, rot_z(180)], "prop_cw": [MIRROR_Y, MIRROR_Y @ rot_z(180)]}, density=2.0),
    Part("blade", "blade", blade, {0: (0, 9), 1: (0, 5)},
         {"prop_ccw": [I3, rot_z(180)], "prop_cw": [MIRROR_Y, MIRROR_Y @ rot_z(180)]}, density=1.4,
         a_rows=rd.ends_rounded({0: 12, 1: 5}, {0: 4, 1: 2}, 0.0, 1 - 0.014 / (PROP_R - BLADE_R0)),
         b_rows=rd.tau_rows(PROP_FOIL)),
    Part("disc_top", "disc", disc(1), {0: (3, 48)}, {"disc": [I3]}, atlas=None, uv=disc_uv, material=f"{NAME}_disc",
         a_rows=lambda n, lod: np.array((0.0, 0.06, 0.25, 1.0))),
    Part("disc_bottom", "disc", disc(-1), {0: (3, 48)}, {"disc": [I3]}, atlas=None, uv=disc_uv,
         material=f"{NAME}_disc", a_rows=lambda n, lod: np.array((0.0, 0.06, 0.25, 1.0))),
    # The tablet
    Part("tab_front", "case", tab_face(T_FRONT, 1), {0: (1, 0), 1: (1, 0)}, {"tablet": [I3]}, atlas="tablet",
         b_rows=RR_ROWS, uv=face_uv, extent=(2 * TW, 2 * TH), density=1.1),
    Part("tab_back", "case", tab_face(T_BACK, -1), {0: (1, 0), 1: (1, 0)}, {"tablet": [I3]}, atlas="tablet",
         b_rows=RR_ROWS, uv=face_uv, extent=(2 * TW, 2 * TH), density=0.8),
    Part("tab_rim", "case", tab_rim, {0: (0, 0), 1: (0, 0)}, {"tablet": [I3]}, atlas="tablet", b_rows=RR_ROWS,
         a_rows=rim_rows({0: 4, 1: 2}, {0: 1, 1: 1}), density=1.0),
    Part("grip", "grip", grip, {0: (18, 18), 1: (10, 10)}, {"tablet": [I3, MIRROR_Y]}, atlas="tablet", density=1.0),
    Part("stick", "stick", lathe(STICK, (T_FRONT + 0.0005, STICK_Y, STICK_Z), (-1, 0, 0), (0, 0, -1)),
         {0: (16, 20), 1: (8, 12)}, {"tablet": [I3, MIRROR_Y]}, atlas="tablet", density=1.6,
         a_rows=STICK.sampler({0: range(17), 1: (0, 1, 3, 5, 7, 9, 11, 13, 16)})),
    Part("tab_antenna", "antenna", rbox(ANT_T_HINGE + _aw * 0.052, (0.0065, 0.0135, 0.060), 0.35, TAB_ANT_FRAME),
         {0: (12, 12), 1: (6, 8)}, {"tablet": [I3, MIRROR_Y]}, atlas="tablet", density=1.2),
    Part("screen", "screen", screen, {0: (1, 1), 1: (1, 1)}, {"tablet": [I3]}, atlas=None, closed=False,
         uv=screen_uv, material=f"{TABLET}_screen"),
]
PART_INDEX = {p.name: i for i, p in enumerate(PARTS)}
GIMBAL_PARTS = ("ball",)

# Each model: its file name, LODs and switch thresholds, where it sits in the drone for the bake (as an occluder),
# and the 'rest' frame its paint is worked out in.
MODELS = {
    "body": dict(file=NAME, lods=(0, 1, 2), thresholds=(0.0, 12.0, 30.0), at=np.zeros(3), group="drone"),
    "gimbal": dict(file=f"{NAME}_gimbal", lods=(0, 1), thresholds=(0.0, 12.0), at=GIMBAL_C, group="drone"),
    "prop_ccw": dict(file=f"{NAME}_prop_ccw", lods=(0, 1), thresholds=(0.0, 10.0), at=BAKE_PROP_OFFSET, group="prop"),
    "prop_cw": dict(file=f"{NAME}_prop_cw", lods=(0, 1), thresholds=(0.0, 10.0), at=BAKE_PROP_OFFSET, group="prop"),
    "disc": dict(file=f"{NAME}_disc", lods=(0,), thresholds=(0.0,), at=None, group=None),
    "tablet": dict(file=TABLET, lods=(0, 1), thresholds=(0.0, 8.0), at=np.zeros(3), group="tablet"),
}
RECTS = {"drone": {}, "tablet": {}}


def pack(atlas):
    items = []
    for p in PARTS:
        if p.atlas != atlas:
            continue
        w, h = p.around * p.density, p.along * p.density
        items.append((p.name, max(w, h), min(w, h), h > w))
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

    lo, hi = 0.01, 40.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if place(mid) else (lo, mid)
    RECTS[atlas].clear()
    RECTS[atlas].update(place(lo))
    return lo


def rect_uv(atlas, name, a, b):
    x0, y0, w, h, rot = RECTS[atlas][name]
    return np.stack([x0 + a * w, y0 + b * h] if rot else [x0 + b * w, y0 + a * h], axis=-1)


def part_uv(p, A, B, P):
    if p.atlas is None:
        return p.uv(A, B, P)
    if p.uv is not None:  # planar: metres across the part's extent
        st = p.uv(P)
        return rect_uv(p.atlas, p.name, st[..., 1] / p.along, st[..., 0] / p.around)
    return rect_uv(p.atlas, p.name, A, B)


def build(model, lod, which="all", atlas=None):
    """A model's mesh: vertices, faces, corner UVs, each face's part and material, and each vertex's place in its
    part's own frame (before the copy's map: what the paint is worked out in). which: all, or the baked copy
    ('first') or the rest of the copies ('others') of an atlas's parts."""
    verts, faces, uvs, part_of, mat_of, rest = [], [], [], [], [], []
    for pi, p in enumerate(PARTS):
        maps = p.place.get(model)
        if not maps or lod not in p.lods or (atlas and p.atlas != atlas):
            continue
        first_model = next(iter(p.place))
        if which == "first":
            maps = maps[:1] if model == first_model else []
        elif which == "others":  # the other models' copies (the cw prop) aren't in the drone at all
            maps = maps[1:] if model == first_model else []
        if not maps:
            continue
        na, nb = p.lods[lod]
        A, B = p.a_rows(na, lod), p.b_rows(nb, lod)
        AA, BB = np.meshgrid(A, B, indexing="ij")
        P0, C0 = p.fn(AA, BB)
        UV = part_uv(p, AA, BB, P0)
        for M in maps:
            P, C = P0 @ M.T, C0 @ M.T
            rows, cols = P.shape[:2]
            ncols = cols - 1 if p.closed else cols
            vid = np.zeros((rows, cols), np.int64)
            for i in range(rows):
                if np.abs(P[i] - P[i, :1]).max() < 1e-7:
                    vid[i, :] = len(verts)
                    verts.append(P[i, 0])
                    rest.append(P0[i, 0])
                else:
                    vid[i, :ncols] = np.arange(len(verts), len(verts) + ncols)
                    verts.extend(P[i, :ncols])
                    rest.extend(P0[i, :ncols])
                    if p.closed:
                        vid[i, -1] = vid[i, 0]
            mine, score = [], 0.0
            for i in range(rows - 1):
                for j in range(cols - 1):
                    keep = []
                    for c in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                        if not keep or vid[c] != vid[keep[-1]]:
                            keep.append(c)
                    if len(keep) > 1 and vid[keep[0]] == vid[keep[-1]]:
                        keep.pop()
                    if len(keep) < 3:
                        continue
                    pts = np.array([P[c] for c in keep])
                    nrm = (np.cross(pts[1] - pts[0], pts[2] - pts[0]) if len(keep) == 3
                           else np.cross(pts[2] - pts[0], pts[3] - pts[1]))
                    score += float(np.dot(nrm, pts.mean(0) - np.mean([C[c] for c in keep], axis=0)))
                    mine.append(keep)
            flip = score < 0
            for keep in mine:
                keep = keep[::-1] if flip else keep
                faces.append(tuple(int(vid[c]) for c in keep))
                uvs.extend(UV[c] for c in keep)
                part_of.append(pi)
                mat_of.append(p.material)
    return (np.array(verts).reshape(-1, 3), faces, np.array(uvs).reshape(-1, 2), np.array(part_of, np.float32),
            mat_of, np.array(rest).reshape(-1, 3))


# ---------------------------------------------------------------------------------------------------------
# Scene


def reset_scene():
    keep = bpy.context.window.scene if bpy.context.window else bpy.context.scene
    fresh = (not bpy.data.filepath and len(bpy.data.scenes) == 1
             and {o.name for o in bpy.data.objects} <= {"Cube", "Camera", "Light"})
    own_file = bool(bpy.data.filepath) and Path(bpy.data.filepath).resolve() == (OUT / f"{NAME}.blend").resolve()
    earlier = keep.get("recon_octocopter_build") and len(bpy.data.scenes) == 1
    if not (fresh or own_file or earlier or globals().get("OCTO_FORCE_RESET")):
        raise RuntimeError("The octocopter builder empties the open .blend. Run it in a new file, or set "
                           "OCTO_FORCE_RESET to empty this one.")
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for data in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights,
                 bpy.data.curves, bpy.data.node_groups, bpy.data.worlds):
        for item in list(data):
            data.remove(item)
    for image in list(bpy.data.images):
        if image.type == "IMAGE":
            bpy.data.images.remove(image)
    keep.name = "Recon Octocopter"
    keep["recon_octocopter_build"] = True
    keep.unit_settings.system = "METRIC"
    return keep


def make_object(name, verts, faces, uvs, part_of, mat_of=None, rest=None, link=True):
    obj = rd.make_object(name, verts, faces, uvs, part_of, rest, link)
    if mat_of is not None:
        names = list(dict.fromkeys(mat_of))
        for n in names:
            obj.data.materials.append(bpy.data.materials.get(n) or bpy.data.materials.new(n))
        idx = np.array([names.index(m) for m in mat_of], np.int32)
        obj.data.polygons.foreach_set("material_index", idx)
    return obj


VIEW_TABLET = np.array((0.0, -1.6, 0.4))  # where the tablet stands in the previews


def build_geometry():
    reset_scene()
    for atlas in RECTS:
        print(f"{atlas} atlas: UV scale {pack(atlas):.3f} per metre")
    for model, info in MODELS.items():
        for lod in info["lods"]:
            v, f, uv, part, mats, _ = build(model, lod)
            name = f"{info['file']}_lod{lod}"
            obj = make_object(name, v, f, uv, part, mats)
            obj.hide_set(lod != 0)
            obj.hide_render = lod != 0 or model in ("prop_ccw", "prop_cw", "disc")
            if model == "tablet":
                obj.location = VIEW_TABLET
            elif model == "gimbal":
                obj.location = GIMBAL_C
            print(f"{name}: {sum(len(x) - 2 for x in f)} triangles, {len(v)} vertices")
    # Stand-ins for the previews: the props on their hubs.
    for i, (pos, spin) in enumerate(HUBS):
        src = bpy.data.objects[f"{NAME}_prop_{'ccw' if spin > 0 else 'cw'}_lod0"]
        inst = bpy.data.objects.new(f"view_prop_{i}", src.data)
        inst.location = pos
        inst.rotation_euler = (0, 0, math.radians(30 + 47 * i))
        bpy.context.scene.collection.objects.link(inst)


# ---------------------------------------------------------------------------------------------------------
# Previews

SHOTS = {  # direction to the camera, point looked at, distance, lens (negative: orthographic width), up
    "three_quarter": ((0.8, 0.6, 0.42), (0, 0, -0.12), 3.6, 50, (0, 0, 1)),
    "photo": ((0.62, -0.72, 0.28), (0, 0, -0.14), 3.3, 40, (0, 0, 1)),
    "front": ((1, 0, 0), (0, 0, -0.12), 4.0, -1.9, (0, 0, 1)),
    "side": ((0, 1, 0), (0, 0, -0.12), 4.0, -1.9, (0, 0, 1)),
    "top": ((0, 0, 1), (0, 0, 0), 4.0, -1.9, (1, 0, 0)),
    "under": ((0.35, -0.5, -0.8), (0, 0, -0.1), 3.4, 50, (0, 0, 1)),
    "motor": ((0.3, 0.9, 0.35), (R_M * 0.7071, R_M * 0.7071, 0), 0.75, 50, (0, 0, 1)),
    "gimbal": ((0.85, -0.45, 0.05), (0.17, 0, -0.13), 0.55, 50, (0, 0, 1)),
    "hull": ((0.55, -0.6, 0.6), (0, 0, 0), 1.0, 50, (0, 0, 1)),
    "tablet": ((-0.92, -0.22, 0.32), tuple(VIEW_TABLET), 0.72, 50, (0, 0, 1)),
    "tablet_back": ((0.8, 0.45, 0.3), tuple(VIEW_TABLET), 0.72, 50, (0, 0, 1)),
}


def camera(scene, view):
    direction, look, distance, lens, up = SHOTS[view]
    cam = scene.camera
    if cam is None:
        cam = bpy.data.objects.new("octo_cam", bpy.data.cameras.new("octo_cam"))
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


def preview(views=("photo", "three_quarter", "side", "front", "top", "motor", "gimbal", "tablet", "tablet_back")):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.6, 0.62, 0.6)
    scene.display.shading.show_cavity = True
    scene.display.render_aa = "16"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for o in bpy.data.objects:
        if o.name.startswith("view_prop_"):
            o.hide_render = False
    paths = []
    for view in views:
        camera(scene, view)
        show_for(view)
        scene.render.filepath = str(PREVIEW_DIR / f"geo_{view}.png")
        bpy.ops.render.render(write_still=True)
        paths.append(scene.render.filepath)
    return paths


def show_for(view):
    """The tablet stands beside the drone in the scene: each view shows only what it's of."""
    tablet = view in ("tablet", "tablet_back")
    for o in bpy.data.objects:
        if o.name == f"{TABLET}_lod0":
            o.hide_render = not tablet
        elif o.name in (f"{NAME}_lod0", f"{NAME}_gimbal_lod0") or o.name.startswith("view_prop_"):
            o.hide_render = tablet


# ---------------------------------------------------------------------------------------------------------
# Bake: one atlas at a time. The bake object is the first copy of each of the atlas's parts, where its model sits
# in the drone (the props well above it); the occluder holds their other copies. Everything else is hidden.


def bake_object(atlas):
    first, others = [], []
    for model, info in MODELS.items():
        if info["at"] is None:
            continue
        for which, out in (("first", first), ("others", others)):
            v, f, uv, part, _, rest = build(model, 0, which, atlas)
            if len(v):
                out.append((v + info["at"], f, uv, part, rest))

    def join(items, name):
        if not items:
            return None
        verts, faces, uvs, parts, rests, base = [], [], [], [], [], 0
        for v, f, uv, part, rest in items:
            verts.append(v)
            faces += [tuple(i + base for i in face) for face in f]
            uvs.append(uv)
            parts.append(part)
            rests.append(rest)
            base += len(v)
        return make_object(name, np.concatenate(verts), faces, np.concatenate(uvs), np.concatenate(parts), None,
                           np.concatenate(rests))
    return join(first, f"{atlas}_bake"), join(others, f"{atlas}_occluder")


def bake(atlas):
    """The atlas's passes as float arrays (TEX, TEX, 4), rows bottom-up as Blender stores them."""
    scene = bpy.context.scene
    rd.use_cycles(scene)
    if not RECTS[atlas]:
        pack(atlas)
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        o.hide_render = True
    obj, occluder = bake_object(atlas)
    mat = bpy.data.materials.new(f"{atlas}_bake")
    obj.data.materials.append(mat)
    for o in bpy.context.view_layer.objects:
        o.select_set(o is obj)
    bpy.context.view_layer.objects.active = obj
    out = {}
    try:
        for name, (kind, build_pass, samples, distance) in rd.BAKE_PASSES.items():
            img = bpy.data.images.new(f"{atlas}_bake_{name}", TEX, TEX, alpha=True, float_buffer=True)
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
            print(f"baked {atlas} {name}")
    finally:
        for o in (obj, occluder):
            if o:
                bpy.data.objects.remove(o)
        bpy.data.materials.remove(mat)
        for name, value in hidden.items():
            if name in bpy.data.objects:
                bpy.data.objects[name].hide_render = value
    return out


# ---------------------------------------------------------------------------------------------------------
# Paint. Colours are sRGB 0..255, the maths linear; heights in metres make the normal map.

SURF = {
    # The airframe: a blue-grey painted composite hull and arms (the photo's ~83, 91, 99), black anodised metal
    # round the arms' joints and on the motors, black carbon gear and props.
    "hull": ((83, 91, 99), 0.48, 0.0),
    "arm": ((90, 97, 104), 0.42, 0.0),
    "collar": ((34, 35, 37), 0.42, 1.0),
    "mount": ((36, 37, 39), 0.46, 1.0),
    "motor": ((30, 30, 33), 0.38, 1.0),
    "gear": ((26, 26, 28), 0.3, 0.0),
    "clamp": ((34, 35, 37), 0.55, 0.0),
    "gimbal": ((52, 55, 59), 0.45, 0.0),
    "ball": ((60, 63, 67), 0.4, 0.0),
    "gps": ((158, 161, 160), 0.55, 0.0),
    "antenna": ((24, 24, 25), 0.78, 0.0),
    "hub": ((32, 32, 35), 0.34, 1.0),
    "blade": ((21, 21, 22), 0.34, 0.0),
    # The tablet: a dark olive drab glass-filled nylon case, black rubber grips, bumpers and sticks.
    "case": ((60, 62, 55), 0.62, 0.0),
    "grip": ((30, 30, 30), 0.86, 0.0),
    "stick": ((28, 28, 29), 0.72, 0.0),
}
SERIAL = "RZ 08311"
TABLET_MODEL = "RZ-GCS 10"
# The station's buttons: legend, y (the holder's left is +Y), z. Return to launch and hold by the left stick,
# camera and record by the right, menu keys under the screen.
BUTTONS = [("RTL", 0.140, 0.064), ("HOLD", 0.140, 0.034), ("CAM", -0.140, 0.064), ("REC", -0.140, 0.034),
           ("MAP", 0.045, -0.078), ("PWR", 0.0, -0.078), ("MENU", -0.045, -0.078)]


def prepared(maps):
    covered = maps["ids"][..., 0] > 0.5 / 64
    maps = rd.dilate(maps, covered)
    part = np.rint(maps["ids"][..., 0] * 64 - 1).astype(np.int32)
    part[~covered] = -1
    P = (maps["pos"][..., :3] * POS_SPAN + POS_LO).astype(np.float32)
    N = maps["nrm"][..., :3] * 2 - 1
    for i, p in enumerate(PARTS):  # the normals into the part's own frame, where its positions are
        M0 = next(iter(p.place.values()))[0]
        if not np.allclose(M0, I3):
            m = part == i
            N[m] = N[m] @ M0.astype(np.float32)
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-6)
    return maps, part, P, N


class Canvas:
    """The maps being painted for one atlas, and the helpers that paint them."""

    def __init__(self, maps):
        self.maps, self.part, self.P, self.N = prepared(maps)
        self.shape = self.part.shape
        self.noise = [self.maps["noise"][..., i] for i in range(3)]
        self.ao = np.clip(self.maps["ao"][..., 0], 0, 1)
        self.cav = np.clip(self.maps["cav"][..., 0], 0, 1)
        self.edge = self.maps["edge"][..., 0]
        self.grain = np.random.default_rng(23).random(self.shape, np.float32)
        self.albedo = np.zeros(self.shape + (3,), np.float32)
        self.rough = np.zeros(self.shape, np.float32)
        self.metal = np.zeros(self.shape, np.float32)
        self.height = np.zeros(self.shape, np.float32)
        for i, p in enumerate(PARTS):
            m = self.part == i
            if m.any():
                colour, r, mt = SURF[p.surf]
                self.albedo[m] = lin(colour)
                self.rough[m], self.metal[m] = r, mt
        n1, n2, n3 = self.noise
        self.albedo *= (1 + 0.05 * (n3 - 0.5) + 0.03 * (n2 - 0.5) + 0.015 * (self.grain - 0.5))[..., None]
        self.rough += 0.06 * (n2 - 0.5) + 0.03 * (self.grain - 0.5)

    def on(self, *names):
        return np.isin(self.part, [PART_INDEX[n] for n in names])

    def paint(self, where, colour=None, rough=None, metal=None, amount=1.0):
        w = np.asarray(where, np.float32) * amount
        if colour is not None:
            self.albedo = mix(self.albedo, lin(colour), w)
        if rough is not None:
            self.rough = mix(self.rough, rough, w)
        if metal is not None:
            self.metal = mix(self.metal, metal, w)

    def text(self, where, u, v, text, height, colour, amount=0.92, texel=0.0004):
        cover = rd.stamp(where, u, v, rd.text_mask(text), height, texel=texel)
        self.paint(cover, colour, 0.5, 0.0, amount)
        return cover

    def screw(self, where, d, r=0.0016, slot=None):
        """A screw head of radius r, d metres from its middle, in a countersink; `slot` is the distance across
        its slot."""
        head = where & (d < r)
        self.height -= 0.0004 * groove(d - r, 0.0004) * where
        self.height += 0.0002 * smoothstep(r, 0.0, d) * where
        self.paint(head, (74, 76, 78), 0.38, 0.9)
        if slot is not None:
            self.height -= 0.00035 * (head & (np.abs(slot) < 0.00028))

    def wear(self, painted, dusty):
        n1, n2, n3 = self.noise
        convex = smoothstep(0.08, 0.3, self.edge) * smoothstep(0.75, 0.95, self.cav)
        worn = convex * painted * smoothstep(0.35, 0.65, n2)
        self.albedo = mix(self.albedo, self.albedo * 1.3 + 0.02, worn * 0.6)
        self.rough += 0.08 * worn
        crev = 1 - smoothstep(0.35, 0.9, self.cav)
        self.albedo *= (1 - 0.35 * crev)[..., None]
        self.rough += 0.1 * crev
        dust = (self.N[..., 2] > 0.45) * dusty * smoothstep(0.5, 0.9, n3) * 0.2
        self.albedo = mix(self.albedo, lin((168, 150, 118)), dust)
        self.rough += 0.12 * dust

    def finish(self, out_dir, name):
        slope = []
        for axis in (1, 0):
            dh = rd.deriv(self.height, self.part, axis)
            dp = np.linalg.norm(rd.deriv(self.P, self.part, axis), axis=-1)
            slope.append(np.where(dp > 1e-6, dh / np.maximum(dp, 1e-6), 0.0))
        normal = np.stack([-slope[0], -slope[1], np.ones_like(slope[0])], axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        ao_map = self.ao ** 0.85 * (0.75 + 0.25 * self.cav)
        done = rd.dilate({"albedo": self.albedo, "rough": self.rough[..., None], "metal": self.metal[..., None],
                          "normal": normal, "ao": ao_map[..., None]}, self.part >= 0, steps=64)
        out_dir.mkdir(parents=True, exist_ok=True)
        files = {
            f"{name}_color.png": rd.to_srgb(np.clip(done["albedo"], 0, 1)),
            f"{name}_rough.png": np.clip(done["rough"][..., 0], 0.03, 1),
            f"{name}_metal.png": np.clip(done["metal"][..., 0], 0, 1),
            f"{name}_normal.png": done["normal"] * 0.5 + 0.5,
            f"{name}_ao.png": done["ao"][..., 0],
        }
        for fname, arr in files.items():
            rd.write_png(out_dir / fname, arr.astype(np.float32))
        return [str(out_dir / f) for f in files]


def compose_drone(maps, out_dir):
    c = Canvas(maps)
    P, N = c.P, c.N
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    nx, ny, nz = N[..., 0], N[..., 1], N[..., 2]
    n1, n2, n3 = c.noise

    # --- Hull ------------------------------------------------------------------------------------------------
    hm = c.on("hull")
    # The lid meets the lower body along the sides; the body is a dark charcoal.
    c.height -= 0.0004 * groove(z + 0.018, 0.0007) * hm
    c.paint(hm & (z < -0.018), (40, 43, 46), 0.55, amount=0.92)
    # The nose's vent panel: dark, with horizontal louvres.
    nose = hm & (nx > 0.3)
    g_sdf = rrect(y, z, 0.0, 0.004, 0.072, 0.030, 0.008)
    panel = nose & (g_sdf < 0)
    c.height -= 0.0005 * groove(g_sdf, 0.0007) * nose
    slat = np.abs(((z - 0.004) / 0.0062) % 1.0 - 0.5)
    louvre = panel & (rrect(y, z, 0.0, 0.004, 0.064, 0.024, 0.004) < 0) & (slat < 0.26)
    c.height -= 0.0016 * louvre
    c.paint(panel, (22, 24, 26), 0.6)
    c.paint(louvre, (30, 50, 36), 0.7)  # the green filter mesh behind the louvres
    for sy, sz in ((0.062, 0.027), (-0.062, 0.027), (0.062, -0.019), (-0.062, -0.019)):
        c.screw(nose, np.hypot(y - sy, z - sz), 0.0015, (y - sy) * 0.7 - (z - sz) * 0.7)
    # The battery hatch along the top, held by two latches at its back.
    top = hm & (nz > 0.45)
    c.height -= 0.0005 * groove(rrect(x, y, -0.010, 0.0, 0.140, 0.088, 0.014), 0.0008) * top
    for ly in (0.048, -0.048):
        l_sdf = rrect(x, y, -0.158, ly, 0.0065, 0.013, 0.003)
        latch = top & (l_sdf < 0)
        c.height += 0.0006 * smoothstep(0.0, 0.0007, -l_sdf) * top
        c.height -= 0.0002 * groove(l_sdf, 0.0004) * top
        c.paint(latch, (34, 35, 37), 0.6)
        c.paint(latch & (np.abs(x + 0.152) < 0.0012), (200, 92, 30), 0.5)  # its lock indicator
    # Screws along the top shell's edge, both sides.
    side = hm & (np.abs(ny) > 0.5)
    for sx in (-0.195, -0.075, 0.045, 0.165):
        c.screw(side, np.hypot(x - sx, z + 0.011), 0.0017, (x - sx) * 0.7 + (z + 0.011) * 0.7)
    # Exhaust vents in the tail.
    tail = hm & (nx < -0.45)
    vents = np.zeros(c.shape, np.float32)
    for vz in (0.018, 0.006, -0.006, -0.018):
        vents = np.maximum(vents, tail * smoothstep(0.0004, -0.0004, rrect(y, z, 0.0, vz, 0.045, 0.0022, 0.0022)))
    c.height -= 0.0012 * vents
    c.paint(vents, (10, 10, 11), 0.75, amount=0.9)
    # The serial, stencilled on both sides, and a data plate on the right.
    for sgn in (1, -1):
        where = hm & (np.sign(y) == sgn) & (np.abs(ny) > 0.6)
        c.text(where, -sgn * (x + 0.055), z - 0.012, SERIAL, 0.0115, (26, 27, 28))
    plate = hm & (ny < -0.6) & (rrect(x, z, 0.040, 0.010, 0.026, 0.012, 0.0015) < 0)
    ink = rd.stamp(plate, x - 0.040, z - 0.010, rd.label_mask(8), 0.019, 0.046, 0.0004)
    c.paint(plate, (206, 204, 194), 0.35)
    c.height += 0.0001 * plate
    c.albedo = mix(c.albedo, lin((22, 22, 22)), ink)
    # The belly: grit thrown up on landings scuffs it.
    c.paint(hm * (nz < -0.5) * smoothstep(0.5, 0.85, n3) * smoothstep(0.3, 0.7, n2), (110, 100, 80), 0.75,
            amount=0.45)

    # --- Arms (the arm frame: along +X) --------------------------------------------------------------------------
    am = c.on("arm")
    c.albedo = mix(c.albedo, c.albedo * 0.92, am * streaks(np.arctan2(z, y) * ARM_TUBE, x, 0.0015, 0.08, 0.25, 7, 0.3))
    for edge_x in (COLLAR_AT + 0.055, R_M - 0.078):  # sealant where the tube goes into the collar and the clamp
        c.height -= 0.0003 * groove(x - edge_x, 0.0006) * am
    # A prop hazard band, red between white, inside the clamp.
    band = am & (np.abs(x - (R_M - 0.110)) < 0.012)
    c.paint(band, (226, 224, 214), 0.45)
    c.paint(band & (np.abs(x - (R_M - 0.110)) < 0.005), (178, 32, 28), 0.45)
    cl = c.on("collar")
    c.height -= 0.0005 * groove(x - (COLLAR_AT + 0.0215), 0.0007) * cl  # the hinge's line
    lever_sdf = rrect(x, y, COLLAR_AT + 0.036, 0.0, 0.0085, 0.0065, 0.002)
    lever = cl & (z > 0.012) & (lever_sdf < 0)
    c.height += 0.0007 * smoothstep(0.0, 0.0008, -lever_sdf) * cl * (z > 0.012)
    c.paint(lever, (46, 47, 50), 0.4, 1.0)
    c.paint(lever & (np.abs(x - (COLLAR_AT + 0.043)) < 0.0013), (205, 96, 30), 0.5, 0.0)
    c.screw(cl & (np.abs(ny) > 0.6), np.hypot(x - (COLLAR_AT + 0.0215), z - 0.006), 0.0028)  # the hinge pin
    for k in (1, -1):  # the clamp's two bolts underneath
        c.screw(c.on("clamp") & (z < -0.013), np.hypot(x - (R_M - 0.057) - 0.010 * k, y), 0.0019)
    mn = c.on("mount")
    c.height -= 0.0003 * groove(z, 0.0006) * mn * (np.abs(nz) < 0.5)  # the drum's two halves
    psi_m = np.degrees(np.arctan2(y, x - R_M))
    fins = mn & (np.abs(nz) < 0.5) & (np.abs(z) < 0.0125) & (np.abs(psi_m) > 28) & (np.abs(psi_m) < 152)
    fin = np.abs((psi_m / 10.0) % 1.0 - 0.5) < 0.22  # cooling fins round the drum, clear of the light and the clamp
    c.height -= 0.0010 * (fins & ~fin)
    c.paint(fins & ~fin, (10, 10, 11), 0.7, 0.0)
    for a in (22.0, -22.0):  # the halves' screws, either side of the light
        ang = np.radians(a)
        px, py = R_M + 0.038 * math.cos(ang), 0.038 * math.sin(ang)
        c.screw(mn & (np.abs(nz) < 0.5), np.hypot(np.hypot(x - px, y - py), z - 0.0125), 0.0015)
        c.screw(mn & (np.abs(nz) < 0.5), np.hypot(np.hypot(x - px, y - py), z + 0.0125), 0.0015)

    # --- Motors ------------------------------------------------------------------------------------------------
    mo = c.on("motor")
    rr = np.hypot(x - R_M, y)
    psi = np.degrees(np.arctan2(y, x - R_M)) % 30.0
    bell = mo & (z > 0.026) & (z < 0.053) & (rr > 0.046)
    slots = bell & (np.abs(psi - 15.0) < 3.6) & (z > 0.030) & (z < 0.049)
    c.height -= 0.0014 * slots
    c.paint(slots, (118, 66, 30), 0.45, 1.0)  # the copper windings through the bell's vents
    c.height += 0.0004 * (bell & ~slots & (np.abs(psi - 15.0) > 13.6))
    c.paint(mo & (z < 0.0235), (24, 24, 26), 0.55, 0.0)  # the stator's black base
    c.height -= 0.0003 * groove(z - 0.0235, 0.0004) * mo
    cap = mo & (z > 0.0555)
    for k in range(4):  # the bell's top face, outside the hub
        a = math.radians(45 + 90 * k)
        c.screw(cap, np.hypot(x - R_M - 0.031 * math.cos(a), y - 0.031 * math.sin(a)), 0.0014)
    c.paint(mo & (z > 0.057) & (rr < 0.0185), (150, 152, 156), 0.3, 1.0, amount=0.6)  # the adapter's bare face

    # --- Gear ----------------------------------------------------------------------------------------------------
    gm = c.on("gear")
    weave = np.sin(2 * np.pi * (x + z * 0.5) / 0.006) * np.sin(2 * np.pi * (x - z * 0.5) / 0.006)
    c.albedo *= (1 + 0.03 * weave * gm)[..., None]
    c.rough += 0.03 * weave * gm
    skid = gm & (z < G_BOT_Z + 0.004) & (nz < 0.2)
    c.paint(streaks(y * 3, x, 0.0015, 0.04, 0.4, 13, 0.25) * skid, (120, 118, 112), 0.6, amount=0.7)
    c.paint(skid * smoothstep(0.4, 0.8, n3), (108, 96, 74), 0.8, amount=0.55)
    c.screw(c.on("gear_clamp") & (np.abs(nx) > 0.6), np.hypot(y - G_TOP_Y, z - (G_TOP_Z + 0.006)), 0.0021)

    # --- Gimbal ---------------------------------------------------------------------------------------------------
    gb = c.on("ball")
    v = P / GIMBAL_R
    v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
    for sgn, kind in ((1, "eo"), (-1, "ir")):  # the daylight lens and the thermal window, side by side
        cdir = math.cos(math.radians(19)) * np.array((1.0, 0, 0)) + sgn * math.sin(math.radians(19)) * np.array((0, 1.0, 0))
        ang = np.degrees(np.arccos(np.clip(v @ cdir.astype(np.float32), -1, 1)))
        r_win = 13.5 if kind == "eo" else 11.0
        c.height -= 0.0016 * smoothstep(r_win + 3.5, r_win, ang) * gb
        c.paint(gb & (ang >= r_win) & (ang < r_win + 3.5), (16, 16, 17), 0.55, 0.0)
        if kind == "eo":
            c.paint(gb & (ang < r_win), (10, 13, 22), 0.04, 0.0)
            c.paint(gb & (ang > 4.0) & (ang < 5.0), (44, 30, 66), 0.05, 0.0)  # the coated inner element's rim
        else:
            c.paint(gb & (ang < r_win), (54, 54, 58), 0.1, 0.8)  # germanium
    c.height -= 0.0004 * groove(np.abs(v[..., 1]) - 0.86, 0.02) * gb  # the shells meet round the sides
    c.height -= 0.0003 * groove(z + 0.075, 0.0006) * c.on("puck")

    # --- GPS mast and antennas ---------------------------------------------------------------------------------------
    gp = c.on("gps_puck")
    c.paint(gp & (z > 0.146), (120, 122, 122), 0.5)
    c.height -= 0.0003 * groove(z - 0.1315, 0.0005) * gp
    s_ant = (P - ANT_BASE) @ ANT_AXIS.astype(np.float32)
    c.height -= 0.0003 * (groove(s_ant - 0.018, 0.0006) + groove(s_ant - 0.021, 0.0006)) * c.on("antenna")

    # --- Props (the prop frame: hub at the origin, thrust +Z) -----------------------------------------------------------
    bl = c.on("blade")
    rb = np.hypot(x, y)
    c.paint(bl & (rb > PROP_R - 0.036) & (rb < PROP_R - 0.022), (232, 232, 228), 0.42)  # tip stripes
    c.paint(bl * (c.edge > 0.12) * (rb > 0.12) * smoothstep(0.35, 0.7, n2), (64, 64, 66), 0.5, amount=0.6)
    weave_b = np.sin(2 * np.pi * (rb + y * 0.3) / 0.005) * np.sin(2 * np.pi * (rb - y * 0.3) / 0.005)
    c.albedo *= (1 + 0.04 * weave_b * bl)[..., None]
    hub = c.on("hub") & (np.abs(nz) > 0.9)
    c.height -= 0.0003 * groove(rb - 0.0095, 0.0005) * hub
    c.paint(hub & (rb < 0.005), (160, 162, 166), 0.3, 1.0)
    c.screw(c.on("yoke") & (np.abs(nz) > 0.7), np.hypot(x - 0.040, y), 0.0035)  # the blade's pivot bolt

    c.wear(c.on("hull", "arm", "gps_puck").astype(np.float32),
           c.on("hull", "arm", "collar", "mount", "motor", "gps_puck", "gear").astype(np.float32))
    return c.finish(out_dir, NAME)


def compose_tablet(maps, out_dir):
    c = Canvas(maps)
    P = c.P
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    n1, n2, n3 = c.noise
    front, back, rim = c.on("tab_front"), c.on("tab_back"), c.on("tab_rim")
    case = front | back | rim
    c.height += 0.00004 * (c.grain - 0.5) * case  # the moulding's fine texture
    # The screen's black border, and the gasket round it.
    s_sdf = rrect(y, z, 0.0, SCREEN_Z, SCREEN_W / 2 + 0.0045, SCREEN_H / 2 + 0.0045, 0.004)
    c.paint(front & (s_sdf < 0), (12, 12, 13), 0.12, 0.0)
    c.height -= 0.0008 * groove(s_sdf, 0.0009) * front
    # Rubber bumpers on the corners.
    cy, cz = TW - T_RC - 0.004, TH - T_RC - 0.004
    c.paint(case & (np.abs(y) > cy) & (np.abs(z) > cz), SURF["grip"][0], 0.85)
    c.height -= 0.0004 * case * (groove(np.abs(y) - cy, 0.0006) * (np.abs(z) > cz)
                                 + groove(np.abs(z) - cz, 0.0006) * (np.abs(y) > cy))
    # The sticks' guard rings.
    for sy in (STICK_Y, -STICK_Y):
        d = np.hypot(y - sy, z - STICK_Z)
        c.paint(front & (d < 0.0245), (30, 31, 32), 0.7)
        c.height -= 0.0005 * groove(d - 0.0245, 0.0007) * front
        c.height += 0.0004 * front * smoothstep(0.0215, 0.0235, d) * (d < 0.0245)
    # Buttons and their legends. Seen from the front the holder's right is -Y, so text runs that way.
    for label, by, bz in BUTTONS:
        hw, hh = (0.0135, 0.0085) if bz > 0 else (0.012, 0.006)
        b_sdf = rrect(y, z, by, bz, hw, hh, 0.003)
        btn = front & (b_sdf < 0)
        c.paint(btn, (34, 35, 36), 0.8)
        c.height += 0.0009 * smoothstep(0.0, 0.0012, -b_sdf) * front
        c.height -= 0.0004 * groove(b_sdf, 0.0006) * front
        c.text(btn, -(y - by), z - bz, label, hh * 0.9, (214, 214, 206), 0.95, texel=0.0002)
    c.paint(front & (np.hypot(y - 0.020, z + 0.078) < 0.0016), (60, 210, 90), 0.2)  # the power light
    c.text(front & (np.abs(z + 0.078) < 0.006) & (y < -0.07), -(y + 0.098), z + 0.078, TABLET_MODEL, 0.0045,
           (150, 152, 140), 0.9, texel=0.0002)
    # The back: the battery door with two latches, four screws, a data label and the model moulded in.
    c.height -= 0.0006 * groove(rrect(y, z, 0.0, -0.010, 0.105, 0.060, 0.008), 0.0008) * back
    for ly in (0.06, -0.06):
        l_sdf = rrect(y, z, ly, 0.052, 0.012, 0.005, 0.002)
        c.paint(back & (l_sdf < 0), (40, 41, 40), 0.6)
        c.height += 0.0006 * smoothstep(0.0, 0.0008, -l_sdf) * back
    for sy, sz in ((0.13, 0.072), (-0.13, 0.072), (0.13, -0.072), (-0.13, -0.072)):
        c.screw(back, np.hypot(y - sy, z - sz), 0.0021, (y - sy) * 0.7 + (z - sz) * 0.7)
    lab = back & (rrect(y, z, 0.0, -0.040, 0.030, 0.012, 0.0015) < 0)
    ink = rd.stamp(lab, y, z + 0.040, rd.label_mask(19), 0.02, 0.054, 0.0003)
    c.paint(lab, (210, 208, 196), 0.35)
    c.albedo = mix(c.albedo, lin((22, 22, 22)), ink)
    c.text(back & (np.abs(z + 0.020) < 0.005), y, z + 0.020, TABLET_MODEL, 0.006, (30, 31, 28), 0.9, texel=0.0002)
    # Grips: ribbed rubber.
    gr = c.on("grip")
    c.height -= 0.0006 * gr * smoothstep(0.18, 0.08, np.abs((z / 0.006) % 1.0 - 0.5))
    # The sticks' caps: a knurled ring round a dished top.
    st = c.on("stick")
    s_cap = T_FRONT + 0.0005 - x  # along the stick from the case
    knurl = st & (s_cap > 0.0168) & (s_cap < 0.0203)
    ang = np.arctan2(z - STICK_Z, np.abs(y) - STICK_Y)
    c.height -= 0.0004 * (knurl & (np.abs(((ang / (2 * np.pi)) * 36) % 1.0 - 0.5) < 0.2))
    c.paint(st & (s_cap > 0.0206), (40, 40, 41), 0.6)
    # Handling: the grips and the case's sides polished by hands.
    handled = (gr | (rim & (np.abs(y) > TW - 0.02))) * smoothstep(0.4, 0.8, n2)
    c.rough -= 0.15 * handled
    c.albedo *= (1 - 0.1 * handled)[..., None]
    c.wear(case.astype(np.float32), case.astype(np.float32) * 0.5)
    return c.finish(out_dir, TABLET)


# ---------------------------------------------------------------------------------------------------------
# The tablet's screen: the station's standby page at 1280 x 800, a 10.1 inch rugged tablet's panel, drawn
# top-down (row 0 the top) and flipped for write_png. The aircraft is on the ground: disarmed, at home, full battery.

SCREEN_PX = (800, 1280)


def blit(img, mask, x0, y0, h, colour, align="left"):
    """Text coverage `mask` (rows bottom-up) drawn into img, its top-left at (x0, y0), h pixels tall."""
    m = mask[::-1]
    w = max(2, int(round(h * m.shape[1] / m.shape[0])))
    if align == "right":
        x0 -= w
    elif align == "centre":
        x0 -= w // 2
    k = max(1, m.shape[0] // max(1, h))
    small = m[: (m.shape[0] // k) * k, : (m.shape[1] // k) * k]
    small = small.reshape(small.shape[0] // k, k, small.shape[1] // k, k).mean(axis=(1, 3))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cov = rd.sample(small, xs / (w - 1), ys / max(1, h - 1))
    y1, x1 = min(img.shape[0], y0 + h), min(img.shape[1], x0 + w)
    if y1 <= y0 or x1 <= x0 or x0 < 0 or y0 < 0:
        return
    cov = cov[: y1 - y0, : x1 - x0, None]
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - cov) + np.asarray(colour, np.float32) / 255 * cov


def screen_texture():
    H, W = SCREEN_PX
    rng = np.random.default_rng(5)
    img = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # The map: shaded hills, woods, contours, a river, roads and the grid.
    map_w = 900
    f = np.zeros((H, W), np.float32)
    for k in range(7):
        fx, fy, ph = rng.uniform(0.003, 0.02), rng.uniform(0.003, 0.02), rng.uniform(0, 6.3, 2)
        f += np.sin(xx * fx + ph[0]) * np.sin(yy * fy + ph[1]) / (k + 1)
    land = np.stack([0.52 + 0.08 * f, 0.56 + 0.07 * f, 0.44 + 0.05 * f], axis=-1)
    woods = (np.sin(xx * 0.031 + 1.3) * np.sin(yy * 0.027) + 0.4 * f) > 0.55
    land[woods] *= np.array((0.72, 0.85, 0.66), np.float32)
    land[np.abs(((f + 2) * 6) % 1.0 - 0.5) < 0.04] *= 0.82
    land[np.abs(yy - (420 + 90 * np.sin(xx * 0.006) + 30 * np.sin(xx * 0.017))) < 6] = (0.30, 0.46, 0.62)
    for road in (np.abs(xx * 0.45 - yy + 120) < 3.0, np.abs(xx - (610 + 0.2 * yy)) < 3.0):
        land[road] = (0.86, 0.82, 0.70)
    grid = ((xx % 128) < 1.2) | ((yy % 128) < 1.2)
    land[grid] = land[grid] * 0.7 + 0.08
    img[:, :map_w] = land[:, :map_w]
    # The planned route, dashed, its numbered waypoints; home; the aircraft beside it.
    pts = np.array(((180, 600), (330, 380), (560, 300), (720, 470), (520, 640)), np.float32)
    cyan = (0.10, 0.85, 0.95)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        t = np.clip(((xx - x0) * (x1 - x0) + (yy - y0) * (y1 - y0)) / ((x1 - x0) ** 2 + (y1 - y0) ** 2), 0, 1)
        d = np.hypot(xx - (x0 + t * (x1 - x0)), yy - (y0 + t * (y1 - y0)))
        img[(d < 2.4) & ((t * np.hypot(x1 - x0, y1 - y0)) % 24 < 15) & (xx < map_w)] = cyan
    for i, (px, py) in enumerate(pts[1:]):
        img[np.abs(np.hypot(xx - px, yy - py) - 11) < 2.5] = cyan
        blit(img, rd.text_mask(str(i + 1)), int(px) + 14, int(py) - 30, 22, (20, 230, 250))
    img[np.hypot(xx - 180, yy - 600) < 16] = (0.95, 0.80, 0.15)
    blit(img, rd.text_mask("H"), 180, 591, 18, (20, 20, 20), "centre")
    ax, ay = 222, 586  # an arrowhead, nose up
    img[(yy > ay - 18) & (yy < ay + 10) & (np.abs(xx - ax) < (yy - (ay - 18)) * 0.45)
        & ~((yy > ay + 2) & (np.abs(xx - ax) < (yy - (ay + 2)) * 0.9))] = (0.98, 0.98, 0.98)
    # The side panel's telemetry.
    img[:, map_w:] = (0.07, 0.08, 0.09)
    img[:, map_w:map_w + 3] = (0.2, 0.22, 0.24)
    green, white, amber, grey = (90, 220, 110), (230, 232, 230), (240, 190, 40), (140, 150, 156)
    rows = [("MODE", "STANDBY", amber), ("ARM", "SAFE", green), ("ALT", "0 M", white), ("SPD", "0.0 M/S", white),
            ("BAT", "100 %", green), ("LINK", "98 %", green), ("GPS", "18 SAT", green), ("CAM", "EO 1X", white)]
    for i, (key, value, colour) in enumerate(rows):
        y0 = 100 + i * 70
        blit(img, rd.text_mask(key), map_w + 30, y0, 24, grey)
        blit(img, rd.text_mask(value), W - 30, y0, 28, colour, "right")
        img[y0 + 48:y0 + 50, map_w + 30:W - 30] = (0.16, 0.18, 0.2)
    # The top bar and the buttons along the bottom.
    img[:64] = (0.05, 0.06, 0.07)
    blit(img, rd.text_mask("UAS 1"), 24, 18, 30, white)
    blit(img, rd.text_mask("14:03"), W - 24, 18, 30, white, "right")
    for i, label in enumerate(("TAKE OFF", "RTL", "CAMERA")):
        x0 = 30 + i * 290
        img[H - 92:H - 24, x0:x0 + 260] = (0.12, 0.14, 0.16)
        img[H - 92:H - 89, x0:x0 + 260] = cyan if i == 0 else (0.3, 0.32, 0.34)
        blit(img, rd.text_mask(label), x0 + 130, H - 74, 32, white, "centre")
    # The panel itself: a faint pixel grid and a little vignette.
    img *= (1 - 0.06 * ((xx % 3 < 0.6) | (yy % 3 < 0.6)))[..., None]
    img *= (1 - 0.15 * np.hypot((xx - W / 2) / W, (yy - H / 2) / H) ** 2)[..., None]
    return np.clip(img, 0, 1)


def disc_texture(size=512):
    """A turning prop's blur: each radius covered by its blades' share of the circle (two blades), the tip
    stripes' ring over it. Colour and opacity."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.hypot(xx + 0.5 - size / 2, yy + 0.5 - size / 2) / (size / 2) * DISC_R1
    chord = blade_chord(np.clip(r, BLADE_R0, PROP_R)) * tip_round(np.clip(PROP_R - r, 0, None), 0.014)
    share = 2 * chord / (2 * np.pi * np.maximum(r, 0.01))
    alpha = np.clip(1.8 * share, 0, 0.55) * (r < PROP_R) * smoothstep(0.026, 0.034, r)
    stripe = (r > PROP_R - 0.036) & (r < PROP_R - 0.022)
    colour = np.where(stripe[..., None], lin((232, 232, 228)), lin((26, 26, 27))).astype(np.float32)
    alpha = np.where(stripe, np.maximum(alpha, 0.16), alpha)
    return rd.to_srgb(colour), alpha.astype(np.float32)


def write_extras(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    rd.write_png(out_dir / f"{TABLET}_screen.png", screen_texture()[::-1].copy())
    colour, alpha = disc_texture()
    rd.write_png(out_dir / f"{NAME}_disc_color.png", colour)
    rd.write_png(out_dir / f"{NAME}_disc_trans.png", alpha)
    for name, rgb in LAMP_RGB.items():
        rd.write_png(out_dir / f"{NAME}_lamp_{name}.png", np.broadcast_to(np.array(rgb, np.float32) / 255, (8, 8, 3)).copy())


# ---------------------------------------------------------------------------------------------------------
# Export


def write_obj(path, obj, mats):
    """Triangles of `obj` with split normals, UVs and materials, in inches, as (Y, Z, X) for ModelDoc's Y-up
    import; the materials are listed in a .mtl beside it."""
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) * INCH
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["UVMap"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    nrm = np.empty(len(me.loops) * 3, np.float32)
    me.corner_normals.foreach_get("vector", nrm)
    nrm = nrm.reshape(-1, 3)
    names = [m.name for m in me.materials]
    lines = [f"# Generated by Tools/build_recon_octocopter.py ({obj.name}); inches, Y-up as ModelDoc reads OBJ",
             f"mtllib {Path(path).stem}.mtl", f"o {obj.name}"]
    lines += [f"v {p[1]:.5f} {p[2]:.5f} {p[0]:.5f}" for p in co]
    vt, vt_index = {}, []
    for t in np.round(uv, 6):
        vt_index.append(vt.setdefault((float(t[0]), float(t[1])), len(vt)))
    vn, vn_index = {}, []
    for n in np.round(nrm, 4):
        vn_index.append(vn.setdefault((float(n[0]), float(n[1]), float(n[2])), len(vn)))
    lines += [f"vt {u:.6f} {v:.6f}" for u, v in vt]
    lines += [f"vn {n[1]:.4f} {n[2]:.4f} {n[0]:.4f}" for n in vn]
    by_mat = {}
    for tri in me.loop_triangles:
        by_mat.setdefault(names[tri.material_index] if names else NAME, []).append(tri)
    tris = 0
    for name, group in by_mat.items():
        lines.append(f"usemtl {name}")
        for tri in group:
            lines.append("f " + " ".join(f"{me.loops[l].vertex_index + 1}/{vt_index[l] + 1}/{vn_index[l] + 1}"
                                         for l in tri.loops))
            tris += 1
    Path(path).write_text("\n".join(lines) + "\n", newline="\n")
    Path(path).with_suffix(".mtl").write_text(
        "# Generated by Tools/build_recon_octocopter.py\n" + "".join(f"newmtl {n}\nKd 1 1 1\nd 1\n" for n in by_mat),
        newline="\n")
    for n in by_mat:
        mats.setdefault(n, None)
    return tris, co.min(0), co.max(0)


def write_vmdl(name, lods, thresholds, mats):
    remaps = ",\n".join(f'    {{ from = "{m}.vmat" to = "{ASSET}/{m}.vmat" }}' for m in mats)
    meshes = ",\n".join(
        f'    {{ _class = "RenderMeshFile" name = "lod{l}" filename = "{ASSET}/{name}_lod{l}.obj" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }' for l in lods)
    groups = ",\n".join(f'    {{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{l}" ] }}'
                        for l, t in zip(lods, thresholds))
    text = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Tools/build_recon_octocopter.py
{{
 rootNode =
 {{
  _class = "RootNode"
  children =
  [
   {{ _class = "MaterialGroupList" children = [ {{ _class = "DefaultMaterialGroup" remaps = [
{remaps}
   ] use_global_default = false global_default_material = "" }} ] }},
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


def atlas_vmat(name):
    return f"""// Generated by Tools/build_recon_octocopter.py

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_METALNESS_TEXTURE 1
	F_SPECULAR 1

	//---- Ambient Occlusion ----
	g_flAmbientOcclusionDirectDiffuse "0.500"
	g_flAmbientOcclusionDirectSpecular "0.600"
	TextureAmbientOcclusion "{ASSET}/{name}_ao.png"

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{ASSET}/{name}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	TextureMetalness "{ASSET}/{name}_metal.png"

	//---- Normal ----
	TextureNormal "{ASSET}/{name}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{ASSET}/{name}_rough.png"
}}
"""


def lit_vmat(texture, brightness, what):
    return f"""// Generated by Tools/build_recon_octocopter.py: {what}, self-lit

Layer0
{{
	shader "shaders/complex.shader"
	F_SELF_ILLUM 1
	F_SPECULAR 1
	TextureColor "{ASSET}/{texture}"
	TextureSelfIllumMask "{ASSET}/{texture}"
	TextureRoughness "[0.080000 0.080000 0.080000 0.000000]"
	g_flSelfIllumBrightness "{brightness:.1f}"
	g_flSelfIllumAlbedoFactor "1.0"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	g_flModelTintAmount "0.000"
	g_flMetalness "0.000"
	g_bFogEnabled "1"
}}
"""


DISC_VMAT = f"""// Generated by Tools/build_recon_octocopter.py: a turning prop's blur

Layer0
{{
	shader "shaders/complex.shader"
	F_TRANSLUCENT 1
	F_SPECULAR 1
	TextureColor "{ASSET}/{NAME}_disc_color.png"
	TextureTranslucency "{ASSET}/{NAME}_disc_trans.png"
	TextureRoughness "[0.400000 0.400000 0.400000 0.000000]"
	g_flMetalness "0.000"
	g_bFogEnabled "1"
}}
"""


def write_vmats():
    files = {f"{NAME}.vmat": atlas_vmat(NAME), f"{TABLET}.vmat": atlas_vmat(TABLET),
             f"{TABLET}_screen.vmat": lit_vmat(f"{TABLET}_screen.png", 1.6, "the station's screen"),
             f"{NAME}_disc.vmat": DISC_VMAT}
    for colour in LAMP_RGB:
        files[f"{NAME}_lamp_{colour}.vmat"] = lit_vmat(f"{NAME}_lamp_{colour}.png", 5.0, f"the {colour} navigation light")
    for fname, text in files.items():
        (OUT / fname).write_text(text, newline="\n")


def inches(v):
    return [round(float(c) * INCH, 3) for c in v]


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    info = {}
    for model, m in MODELS.items():
        name, mats = m["file"], {}
        info[name] = {}
        for lod in m["lods"]:
            tris, lo, hi = write_obj(OUT / f"{name}_lod{lod}.obj", bpy.data.objects[f"{name}_lod{lod}"], mats)
            info[name][f"lod{lod}"] = {"triangles": tris, "bounds_min": [round(float(c), 3) for c in lo],
                                       "bounds_max": [round(float(c), 3) for c in hi]}
        write_vmdl(name, m["lods"], m["thresholds"], list(mats))
    # Where the game puts things, in the models' own frames (inches; X forward, Y left, Z up).
    info["hubs"] = [{"position": inches(pos), "spin": spin} for pos, spin in HUBS]
    info["rotor_radius"] = round(PROP_R * INCH, 3)
    info["gimbal_pivot"] = inches(GIMBAL_C)
    info["gimbal_lens"] = inches((GIMBAL_R, 0, 0))  # in the gimbal model, before its pitch
    info["skid_bottom"] = round((G_BOT_Z - GEAR_TUBE) * INCH, 3)
    info["hull_centre"] = inches(((HULL_NOSE + HULL_TAIL) / 2, 0, (HULL_TOP + HULL_BOT) / 2))
    info["hull_half_extents"] = inches(((HULL_NOSE - HULL_TAIL) / 2, HULL_W, (HULL_TOP - HULL_BOT) / 2))
    info["tablet"] = {"grip_left": inches((GRIP_C[0], GRIP_C[1], (GRIP_Z0 + GRIP_Z1) / 2)),
                      "grip_right": inches((GRIP_C[0], -GRIP_C[1], (GRIP_Z0 + GRIP_Z1) / 2)),
                      "screen_centre": inches((T_FRONT, 0, SCREEN_Z)), "screen_size": inches((SCREEN_W, SCREEN_H)),
                      "sticks": [inches((T_FRONT - 0.02, STICK_Y, STICK_Z)), inches((T_FRONT - 0.02, -STICK_Y, STICK_Z))]}
    info["atlas"] = TEX
    (OUT / "asset-info.json").write_text(json.dumps(info, indent=2) + "\n", newline="\n")
    write_vmats()
    return info


def save_blend():
    path = OUT / f"{NAME}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, relative_remap=True, compress=True)
    Path(str(path) + "1").unlink(missing_ok=True)
    return path


# ---------------------------------------------------------------------------------------------------------
# Beauty renders: Cycles, the painted materials, a dusty floor under the skids.


def node_tree(mat):
    nt = mat.node_tree
    nt.nodes.clear()
    return nt, nt.nodes.new("ShaderNodeOutputMaterial")


def final_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, out = node_tree(mat)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])

    def tex(kind, colorspace):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = rd.load_image(OUT / f"{name}_{kind}.png", colorspace)
        return n
    nt.links.new(tex("color", "sRGB").outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex("rough", "Non-Color").outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(tex("metal", "Non-Color").outputs["Color"], bsdf.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nt.links.new(tex("normal", "Non-Color").outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def glow_material(name, image, strength):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, out = node_tree(mat)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = rd.load_image(OUT / image, "sRGB")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def beauty(tag="beauty", views=("photo", "three_quarter", "side", "front", "top", "under", "motor", "gimbal",
                                 "tablet", "tablet_back")):
    scene = bpy.context.scene
    rd.clear_beauty()
    rd.use_cycles(scene)
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.film_transparent = False
    scene.world.color = (0.05, 0.055, 0.06)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    final_material(NAME)
    final_material(TABLET)
    glow_material(f"{TABLET}_screen", f"{TABLET}_screen.png", 1.4)
    for colour in LAMP_RGB:
        glow_material(f"{NAME}_lamp_{colour}", f"{NAME}_lamp_{colour}.png", 6.0)

    def add(obj):
        scene.collection.objects.link(obj)
        return obj
    floor_z = G_BOT_Z - GEAR_TUBE - 0.0005
    floor_me = bpy.data.meshes.new("beauty_floor")
    floor_me.from_pydata([(-8, -8, floor_z), (8, -8, floor_z), (8, 8, floor_z), (-8, 8, floor_z)], [], [(0, 1, 2, 3)])
    floor = add(bpy.data.objects.new("beauty_floor", floor_me))
    floor_mat = bpy.data.materials.new("beauty_floor")
    fb = floor_mat.node_tree.nodes.get("Principled BSDF")
    fb.inputs["Base Color"].default_value = (0.20, 0.17, 0.13, 1)
    fb.inputs["Roughness"].default_value = 0.85
    floor_me.materials.append(floor_mat)
    for name, loc, energy, size, colour in (("key", (2.6, 3.2, 3.8), 420, 2.0, (1.0, 0.96, 0.9)),
                                            ("fill", (3.4, -3.2, 1.4), 90, 3.0, (0.85, 0.9, 1.0)),
                                            ("rim", (-3.4, -1.2, 3.0), 300, 1.6, (0.9, 0.95, 1.0))):
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
            show_for(view)
            floor.hide_render = view in ("under", "tablet", "tablet_back")
            scene.render.filepath = str(PREVIEW_DIR / f"{tag}_{view}.png")
            bpy.ops.render.render(write_still=True)
            paths.append(scene.render.filepath)
    finally:
        rd.clear_beauty()
    return paths


def want(stage):
    return STAGES == "all" or stage in STAGES.split(",")


if __name__ == "__main__":
    if want("geometry"):
        build_geometry()
        if want("preview"):
            RESULT_PREVIEWS = preview()
    else:
        for atlas in RECTS:
            pack(atlas)
    if want("bake"):
        bpy.app.driver_namespace["octo_bake"] = {atlas: bake(atlas) for atlas in RECTS}
    if want("textures"):
        baked = bpy.app.driver_namespace["octo_bake"]
        RESULT_TEXTURES = compose_drone(baked["drone"], OUT) + compose_tablet(baked["tablet"], OUT)
        write_extras(OUT)
    if want("export"):
        RESULT_EXPORT = export()
        print(json.dumps({k: v for k, v in RESULT_EXPORT.items() if isinstance(v, dict) and "lod0" in v}, indent=1))
        save_blend()
    if want("beauty"):
        RESULT_BEAUTY = beauty()
