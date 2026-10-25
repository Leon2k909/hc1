"""Railhead's close-range track-end detail, with authored PBR wear and reusable steel fittings.

Run this module to rebuild its materials; railhead_map.py uses the geometry. All small fittings and ballast
are visual only. The buffer stop retains the original gameplay collider and footprint.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import map_kit as K

OUT = K.ASSETS / "materials/railhead"
RESOURCE = "materials/railhead"
PAINTS = {
    "rw_buffer_red": 48.0,
    "rw_buffer_beam": 1.0,
    "rw_buffer_contact": 1.0,
    "rw_buffer_contact_b": 1.0,
    "rw_buffer_plate": 24.0,
    "rw_buffer_edge": 48.0,
    "rw_buffer_bolt": 8.0,
    "rw_buffer_white": 32.0,
    "rw_buffer_led": 1.0,
    "rw_buffer_lens": 1.0,
    "rw_track_stone": 8.0,
    "rw_track_stone_dark": 8.0,
    "rw_track_stone_warm": 8.0,
}
# What railhead_map's missing()/write() pair looks for in Assets: only the paints that have always been there, so a
# paint added since never makes the map write Assets. The rest come from write( root ) into a stage or at integration.
BASE_PAINTS = dict(PAINTS)
PAINTS.update({
    "rw_buffer_beam_b": 1.0,        # the second variant's beam, a different seed and more grime
    "rw_buffer_frame_dark": 48.0,   # the second variant's anthracite frame (only its beam is red)
    "rw_buffer_grime": 48.0,        # the red frame's lowest 300 mm: brake dust and ballast dust over the paint
    "rw_buffer_grime_dark": 48.0,   # the anthracite frame's
    "rw_track_stone_oily": 8.0,     # the crib between the rails, blackened by brake dust and oil drips
})
try:
    import railhead_prop_materials as _PM
    PAINTS.update(_PM.PAINTS)
except Exception as _error:      # the props' own materials are optional: the map still builds without them
    print(f"railhead_prop_materials isn't usable: {_error}")
_TARGET = [OUT]


def configure(model):
    for paint, tile in PAINTS.items():
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = tile


def bevel_box(model, frame, lo, hi, paint, bevel=0.15, edge=None, face_uv=False):
    """A real bevel on all twelve edges, including the eight corner triangles. UVs stay attached to the part."""
    from railhead_props import outward
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    b = min(bevel, float(np.min(hi - lo)) * 0.45)
    centre = (lo + hi) / 2
    half = (hi - lo) / 2
    axes = (frame.x, frame.y, frame.z)

    def world(q):
        return frame.p(*q)

    def draw(points, normal, material, uv=False):
        coords = None
        if uv:
            coords = [((q[0] - lo[0]) / (hi[0] - lo[0]), (q[2] - lo[2]) / (hi[2] - lo[2])) for q in points]
        outward(model, material, [world(q) for q in points], sum(axes[i] * normal[i] for i in range(3)), uv=coords)

    # The six broad faces.
    for i in range(3):
        j, k = (i + 1) % 3, (i + 2) % 3
        for sign in (-1, 1):
            points = []
            for sj, sk in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                q = centre.copy()
                q[i] += sign * half[i]
                q[j] += sj * (half[j] - b)
                q[k] += sk * (half[k] - b)
                points.append(q)
            normal = np.zeros(3)
            normal[i] = sign
            draw(points, normal, paint, face_uv and i == 1)
    # The bevel strips joining each adjacent pair of broad faces.
    for i, j, k in ((0, 1, 2), (0, 2, 1), (1, 2, 0)):
        for si in (-1, 1):
            for sj in (-1, 1):
                points = []
                for sk, inset in ((-1, i), (1, i), (1, j), (-1, j)):
                    q = centre.copy()
                    q[i] += si * half[i]
                    q[j] += sj * half[j]
                    q[k] += sk * (half[k] - b)
                    q[inset] -= (si if inset == i else sj) * b
                    points.append(q)
                normal = np.zeros(3)
                normal[i], normal[j] = si, sj
                draw(points, normal, edge or paint)
    # The corner triangles close the gaps where three bevel strips meet: each point is a broad face's corner (out on
    # its own axis, in by b on the other two). Points b in from the box's corner along each edge stood out past the
    # bevels as shards and left the gaps open.
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                signs = np.array((sx, sy, sz))
                inner = centre + signs * (half - b)
                points = [inner + np.eye(3)[i] * signs[i] * b for i in range(3)]
                draw(points, signs, edge or paint)


def bolt(model, frame, x, y, z, radius=0.65, axis="front", screw=False):
    """Washer, bevelled hex nut or slotted domed screw, sitting proud of its mounting face."""
    from railhead_props import rod, disc
    normal = frame.y if axis == "front" else frame.z
    p = frame.p(x, y, z)
    rod(model, p, p + normal * 0.15, radius * 1.35, "rw_buffer_plate", 16, caps=(False, True))
    rod(model, p + normal * 0.15, p + normal * 0.44, radius, "rw_buffer_bolt", 12 if screw else 6,
        caps=(False, True), turn=math.pi / 6)
    rod(model, p + normal * 0.44, p + normal * 0.52, radius * 0.82, "rw_buffer_bolt", 12 if screw else 6,
        caps=(False, True), turn=math.pi / 6)
    if screw:
        centre = p + normal * 0.535
        right = frame.x
        model.beam(centre - right * radius * 0.62, centre + right * radius * 0.62, (0.05, 0.05), "rw_buffer_plate")


def contact(model, frame, x):
    from railhead_props import outward, disc, rod
    # The buffer plate, four attachment bolts, barrel and slightly dished steel contact face.
    bevel_box(model, frame, (x - 11.2, -4.2, 30.5), (x + 11.2, -2.7, 52.9), "rw_buffer_plate", 0.35)
    for dx in (-9.1, 9.1):
        for dz in (-9.1, 9.1):
            bolt(model, frame, x + dx, -2.65, 41.7 + dz, 0.78)
    rod(model, frame.p(x, -3, 41.7), frame.p(x, -1.8, 41.7), 5.3, "rw_buffer_plate", 32)
    for k, (y0, y1, r) in enumerate(((-2.7, -2.5, 6.4), (-2.5, -2.35, 5.9), (-2.35, -2.15, 6.4))):
        rod(model, frame.p(x, y0, 41.7), frame.p(x, y1, 41.7), r, "rw_rubber", 24, caps=(k == 0, False))
    rings = [(-2.1, 8.35), (-1.75, 9.0), (-0.45, 9.12), (0.0, 8.7)]
    segments = 64
    angles = np.arange(segments) * 2 * math.pi / segments
    for (ya, ra), (yb, rb) in zip(rings, rings[1:]):
        for i, a in enumerate(angles):
            b = angles[(i + 1) % segments]
            dirs = [frame.x * math.cos(t) + frame.z * math.sin(t) for t in (a, b)]
            pts = [frame.p(x + ra * math.cos(a), ya, 41.7 + ra * math.sin(a)),
                   frame.p(x + ra * math.cos(b), ya, 41.7 + ra * math.sin(b)),
                   frame.p(x + rb * math.cos(b), yb, 41.7 + rb * math.sin(b)),
                   frame.p(x + rb * math.cos(a), yb, 41.7 + rb * math.sin(a))]
            normals = [d + frame.y * ((ra - rb) / max(yb - ya, 0.01)) for d in dirs]
            outward(model, "rw_buffer_edge", pts, dirs[0] + dirs[1], normals=[normals[0], normals[1], normals[1], normals[0]])
    paint = "rw_buffer_contact" if x < 0 else "rw_buffer_contact_b"
    # A buffer's contact plate is very slightly convex, with uninterrupted circular UVs.
    def front(r, angle):
        return frame.p(x + r*math.cos(angle), 0.55*(1-(r/8.7)**2), 41.7 + r*math.sin(angle))
    def normal(r, angle):
        return frame.y + (frame.x*math.cos(angle)+frame.z*math.sin(angle)) * (1.1*r/(8.7**2))
    for ra, rb in ((0, 3), (3, 6.5), (6.5, 8.7)):
        for i, a in enumerate(angles):
            b = angles[(i+1)%segments]
            corners = [(ra,a),(rb,a),(rb,b),(ra,b)] if ra else [(0,a),(rb,a),(rb,b)]
            outward(model, paint, [front(r,t) for r,t in corners], frame.y,
                    uv=[(0.5+r*math.cos(t)/17.4,0.5+r*math.sin(t)/17.4) for r,t in corners],
                    normals=[normal(r,t) for r,t in corners])


def _variant(e):
    """ 0: the red frame; 1: the anthracite frame with only its beam red. Alternates track by track, mirrored. """
    base = {236: 0, 416: 1, 848: 0}.get(int(round(abs(e))), int(abs(e)) % 2)
    return base ^ (1 if e < 0 else 0)


def _clamp_pair(model, f, x, y):
    """ A friction element on one rail: two grey cast clamp blocks (300 x 150 x 120 mm) gripping its web either side,
    tied by a bridge over the head, four bolt heads on each outer face. """
    for side in (-1, 1):
        x0, x1 = sorted((x + side * 1.2, x + side * 5.6))
        bevel_box(model, f, (x0, y - 5.9, -6.1), (x1, y + 5.9, -1.4), "rw_buffer_plate", 0.3, "rw_buffer_edge")
        face = x + side * 5.62
        for dy in (-3.4, 3.4):
            for dz in (-4.9, -2.6):
                p = f.p(face, y + dy, dz)
                from railhead_props import rod
                rod(model, p, p + f.x * side * 0.45, 0.42, "rw_buffer_bolt", 6, caps=(False, True))
    bevel_box(model, f, (x - 3.2, y - 4.6, 0.05), (x + 3.2, y + 4.6, 0.75), "rw_buffer_plate", 0.18, "rw_buffer_edge")


def buffer_stop(model, e, n, facing, rail_z=-30.0):
    """ A friction buffer stop (Rawie type): a red beam with two buffers on a welded frame of uprights and rear
    braces, the frame's sole plates clamped to the rails by three pairs of friction elements a metre apart, an Sh 2
    board and its LED cluster. Two variants alternate by track: a flame-red frame, or an anthracite one with only its
    beam red; both dusty and brake-dust brown at the foot. """
    from railhead_props import vehicle_frame, rod, disc
    f = vehicle_frame(e, n, facing, rail_z)
    v = _variant(e)
    red, dark = ("rw_buffer_red", "rw_buffer_grime") if v == 0 else ("rw_buffer_frame_dark", "rw_buffer_grime_dark")
    plate = "rw_buffer_plate"
    beam = "rw_buffer_beam" if v == 0 else "rw_buffer_beam_b"
    bevel_box(model, f, (-47, -16, 30), (47, -4.6, 54), beam, 0.65, "rw_buffer_edge", face_uv=True)
    # White retro-reflective strips across the beam's ends.
    for x0, x1 in ((-46.2, -40.6), (40.6, 46.2)):
        bevel_box(model, f, (x0, -4.66, 32.0), (x1, -4.5, 52.0), "rw_reflective", 0.04)
    for x in (-34.45, 34.45):
        contact(model, f, x)
    for z in (33.1, 50.9):
        bolt(model, f, -2.1, -4.58, z, 0.67)
    for x in (-29.6, 29.6):
        bevel_box(model, f, (x - 4.5, -140, -1.9), (x + 4.5, -7, 6), plate, 0.28)
        # The uprights: brake-dust brown for their lowest 300 mm, the paint above, a weld bead between.
        bevel_box(model, f, (x - 3.4, -16.8, 6), (x + 3.4, -8.7, 17.8), dark, 0.28, "rw_buffer_edge")
        bevel_box(model, f, (x - 3.4, -16.8, 17.8), (x + 3.4, -8.7, 30.3), red, 0.28, "rw_buffer_edge")
        bevel_box(model, f, (x - 3.55, -16.95, 17.6), (x + 3.55, -8.55, 18.0), plate, 0.1)
        # Rear braces are box sections; welded collars make their joints read as assembled steel.
        low = f.p(x, -121, 6.2)
        top = f.p(x, -13.1, 45)
        mid = low + (top - low) * 0.3
        model.beam(top, mid, (6, 6), red)
        model.beam(mid, low, (6, 6), dark)
        model.beam(mid - (top - low) * 0.004, mid + (top - low) * 0.004, (6.35, 6.35), plate)
        for yy in (-124, -86, -48, -12.8):
            bevel_box(model, f, (x - 4.7, yy - 3, 6), (x + 4.7, yy + 3, 6.65), plate, 0.12)
            for dx in (-3.4, 3.4):
                bolt(model, f, x + dx, yy, 6.68, 0.55, axis="up")
        bevel_box(model, f, (x - 4.35, -18.8, 6.6), (x + 4.35, -7.2, 7.3), plate, 0.15)
        for dx in (-2.7, 2.7):
            for yy in (-17.1, -9):
                bolt(model, f, x + dx, yy, 7.35, 0.48, axis="up")
        # Three friction elements on each rail, a metre apart under the sole plate.
        for yy in (-33.0, -72.4, -111.8):
            _clamp_pair(model, f, x, yy)
    bevel_box(model, f, (-25, -140, 1), (25, -130, 7), dark, 0.22, "rw_buffer_edge")
    for x in (-23, 23):
        bolt(model, f, x, -129.95, 4.1, 0.52)
    # Sh 2 board: an enamel square on a steel back with screw fixings, instead of a floating decal.
    bevel_box(model, f, (-2.9, -12.5, 54), (0.1, -9.5, 93.8), dark, 0.16)
    bevel_box(model, f, (-13.2, -9.6, 71.3), (10.4, -8.8, 93.2), "rw_buffer_white", 0.22)
    # Its back is the steel plate it's enamelled on, painted grey, with a stiffening frame: not the white face again.
    bevel_box(model, f, (-13.25, -9.75, 71.25), (10.45, -9.5, 93.25), "rw_buffer_plate", 0.06)
    for z0, z1 in ((72.6, 73.6), (90.9, 91.9)):
        bevel_box(model, f, (-12.0, -10.6, z0), (9.2, -9.7, z1), "rw_buffer_plate", 0.1)
    bevel_box(model, f, (-1.4 - 9.03, -8.86, 82.25 - 8.33), (-1.4 + 9.03, -8.64, 82.25 + 8.33), "rw_black", 0.05)
    bevel_box(model, f, (-1.4 - 8.95, -8.86, 82.25 - 8.25), (-1.4 + 8.95, -8.5, 82.25 + 8.25), "rw_sh2_red", 0.12)
    for x in (-11.7, 8.9):
        for z in (72.8, 91.7):
            bolt(model, f, x, -8.73, z, 0.32, screw=True)
    # LED clusters retain their red housing and dark lens at daylight exposures.
    bevel_box(model, f, (-5.5, -10, 58), (5.5, -7.2, 69), red, 0.48)
    disc(model, "rw_buffer_lens", f.p(0, -7.16, 63.5), f.y, 3.3, 48)
    rod(model, f.p(0, -7.17, 63.5), f.p(0, -6.95, 63.5), 3.5, dark, 48)
    for ix in range(-5, 6):
        for iz in range(-5, 6):
            x, z = ix * 0.48, iz * 0.48
            if x*x + z*z <= 2.6*2.6:
                disc(model, "rw_buffer_led", f.p(x, -6.9, 63.5 + z), f.y, 0.145, 8)
    for x in (-4.5, 4.5):
        for z in (59, 68):
            bolt(model, f, x, -7.16, z, 0.25, screw=True)
    f.collide(model, -50, 50, -140, 0, -7, 54, "metal")
    configure(model)


def track_fittings(model, e0, e1, n, rail_z, rails):
    """Rail seats with insulator pads, bolts and bent spring clips, only in the close-range buffer approach."""
    from railhead_props import Frame, rod
    f = Frame((0, 0, 0), (0, 1))
    top = rail_z - 6.8
    for x in rails:
        bevel_box(model, f, (-x - 5.4, n - 3.5, top + 0.04), (-x + 5.4, n + 3.5, top + 0.32), "rw_buffer_plate", 0.12)
        for side in (-1, 1):
            xx = x + side * 4.55
            bolt(model, f, -xx, n, top + 0.34, 0.44, axis="up")
            points = [(x + side * 2.65, n - 1.6, top + 1.35), (xx, n - 1.6, top + 1.6),
                      (xx + side * 0.5, n, top + 1.6), (xx, n + 1.6, top + 1.6),
                      (x + side * 2.65, n + 1.6, top + 1.35)]
            for a, b in zip(points, points[1:]):
                rod(model, a, b, 0.28, "rw_buffer_edge", 6)
    configure(model)


def track_fittings_lod(model, n, rail_z, rails):
    """The far track's rail seats, cheap: W14 angled guide plates either side of each rail foot and the Skl 14 tension
    clamps' loops over them. No bolts or pads: at more than a few metres they're lost in the clamps' shadow."""
    from railhead_props import polyline
    top = rail_z - 6.8
    for x in rails:
        for side in (-1, 1):
            a, b = sorted((x + side * 2.95, x + side * 5.3))
            model.box((a, n - 3.0, top), (b, n + 3.0, top + 1.05), "rw_buffer_plate", skip=("-z",))
            xx = x + side * 4.1
            polyline(model, [(x + side * 2.7, n - 1.5, top + 1.3), (xx, n - 1.7, top + 1.75),
                             (xx + side * 0.9, n, top + 1.55), (xx, n + 1.7, top + 1.75),
                             (x + side * 2.7, n + 1.5, top + 1.3)], 0.3, "rw_buffer_edge", 4)


def crib_band(model, e, n0, n1, rail_z=-30.0):
    """The brake-dust-dark band down the crib between a track's rails, on the lowered crib ballast (railhead_station's
    CRIB_DROP: rail_z - 9.5 within 52 of the centre), darkest in the middle: what tells a used track from a model's at
    20 m. Visual only, and only over the shed's track bands, where the crib is lowered (anywhere else it lies under the
    bed's plane and doesn't show)."""
    try:
        import railhead_station as S
        centres = tuple(S.TRACKS.values())
        drop = getattr(S, "CRIB_DROP", 0.0)
        lo_n, hi_n = S.SOUTH_N, S.PLATFORM_N1
    except Exception:
        return
    if drop < 1.0 or not any(abs(abs(e) - c) < 1.0 for c in centres):
        return
    lo, hi = max(min(n0, n1), lo_n), min(max(n0, n1), hi_n)
    if hi - lo < 1.0:
        return
    z = rail_z - 7.0 - drop + 0.08
    for paint, a, b, dz in (("rw_track_stone_dark", -27.0, 27.0, 0.0), ("rw_track_stone_oily", -19.0, 19.0, 0.06)):
        model.polygon(paint, [(e + a, lo, z + dz), (e + b, lo, z + dz), (e + b, hi, z + dz), (e + a, hi, z + dz)])


def sleeper_shoulders(model, e0, e1, n, width, top):
    """Ballast heaped against a sleeper's long sides: a strip from just under its top edge sloping down and out under
    the ballast's plane (BED_Z -37), in the dark stone, so each sleeper reads as set into its bed with a shadow line
    along it, whether the bed's drawn at -37 or a little lower. Visual only."""
    from railhead_props import outward
    for side in (-1, 1):
        y_in = n + side * width / 2
        y_out = y_in + side * 3.2
        pts = [(e0 + 1.5, y_in, top - 0.35), (e1 - 1.5, y_in, top - 0.35), (e1 - 1.5, y_out, top - 3.3),
               (e0 + 1.5, y_out, top - 3.3)]
        outward(model, "rw_track_stone_dark", pts, (0, side, 1.0))


def ballast_detail(model):
    """Scattered angular ballast at the six track heads; no physical stones or navigation obstacles."""
    from railhead_props import outward
    rng = np.random.default_rng(4728)
    # Read the generated ties, whose phase differs between the crossover runs on each side.
    ties = []
    for points, normal in model.polygons.get("rw_sleeper", []):
        pts = np.asarray(points)
        if normal[2] > 0.9 and 305 < pts[:,1].mean() < 885:
            ties.append((pts.min(axis=0), pts.max(axis=0)))
    for e in (-848, -416, -236, 236, 416, 848):
        for _ in range(9000 if abs(e) == 416 else 3000):
            x, n = e + rng.uniform(-63, 63), rng.uniform(310, 875)
            # Sleeper tops stay readable. Bury stones between the concrete ties and alongside their ends.
            if any(lo[0]-0.8 < x < hi[0]+0.8 and lo[1]-0.8 < n < hi[1]+0.8 for lo,hi in ties):
                continue
            r = rng.uniform(0.65, 1.7)
            # On the crib, which lies 2.5 under the shoulders within 52 of the track's centre (railhead_station's
            # CRIB_DROP), rising to the bed's plane at 60.
            off = abs(x - e)
            z = -39.45 + 2.5 * min(max((off - 52.0) / 8.0, 0.0), 1.0)
            angle = rng.uniform(0, 2*math.pi)
            h = r * rng.uniform(0.55, 1.1)
            ring = [np.array((x + r * rng.uniform(0.75,1.05) * math.cos(angle + k*math.pi/3),
                              n + r * math.sin(angle + k*math.pi/3) * 0.75, z + h*rng.uniform(0.15,0.45))) for k in range(6)]
            upper = [np.array((x + r * 0.45*math.cos(angle+k*2*math.pi/3),
                               n + r * 0.38*math.sin(angle+k*2*math.pi/3), z+h*rng.uniform(0.75,1))) for k in range(3)]
            bottom = np.array((x, n, z-0.2))
            paint = rng.choice(("rw_track_stone", "rw_track_stone_dark", "rw_track_stone_warm"), p=(0.67, 0.23, 0.1))
            outward(model, paint, upper, (0,0,1))
            for k in range(6):
                a, b = ring[k], ring[(k+1)%6]
                u = upper[k//2]
                outward(model, paint, [a, b, u], (a+b+u)/3 - bottom)
                if k % 2 == 1:
                    v = upper[((k+1)//2)%3]
                    outward(model, paint, [b, v, u], (b+v+u)/3 - bottom)
                outward(model, paint, [a, bottom, b], (a+b)/2 - np.array((x,n,z+h)))
    configure(model)


def field(rng, shape, sigma):
    a = ndimage.gaussian_filter(rng.normal(size=shape).astype(np.float32), sigma, mode="wrap")
    return a / (a.std() + 1e-6)


def save(name, colour, roughness, height, metalness, units, ao=None, detail=None):
    """Linear roughness/metalness, OpenGL tangent-space normal, and sRGB albedo."""
    OUT = _TARGET[0]
    OUT.mkdir(parents=True, exist_ok=True)
    shape = height.shape
    pixels = shape[1] / units
    dy, dx = np.gradient(height)
    normal = np.dstack((-dx * pixels, dy * pixels, np.ones(shape)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    if detail is not None:
        from railhead_scanned import combine_normals
        normal = combine_normals(normal*0.5+0.5, detail, 0.45)*2-1
    channels = {"color": colour, "normal": (normal*0.5+0.5)*255,
                "rough": np.clip(roughness,0,1)*255, "metal": np.broadcast_to(metalness,shape)*255,
                "ao": np.ones(shape)*255 if ao is None else ao*255}
    for channel, data in channels.items():
        Image.fromarray(np.clip(np.rint(data),0,255).astype(np.uint8)).save(OUT / f"{name}_{channel}.png", optimize=True)
    text = ["// Tools/railhead_buffer.py", '"Layer0"', "{", '    shader "shaders/complex.shader"',
            '    F_SPECULAR "1"', '    F_METALNESS_TEXTURE "1"', '    g_flRoughnessScaleFactor "1"',
            f'    g_flMetalness "{float(np.mean(metalness)):.3f}"', '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1"']
    for parameter, channel in (("TextureColor","color"),("TextureNormal","normal"),("TextureRoughness","rough"),
                               ("TextureMetalness","metal"),("TextureAmbientOcclusion","ao")):
        text.append(f'    {parameter} "{RESOURCE}/{name}_{channel}.png"')
    (OUT / f"{name}.vmat").write_text("\n".join(text + ["}", ""]), encoding="utf-8")


def worn_paint(name, shape, base, seed, units, edges=False, white=False, grime=0.0, desat=0.0, bleed=(), faded_top=0.0,
               chip_scale=1.0):
    rng = np.random.default_rng(seed)
    h, w = shape
    broad, fine = field(rng,shape,22), field(rng,shape,0.65)
    mid = field(rng,shape,4)
    y,x = np.mgrid[:h,:w]
    # Torn paint islands and fine individual pitting, concentrated at handled edges.
    edge = np.maximum(np.exp(-np.minimum(y,h-1-y)/(12*chip_scale)), np.exp(-np.minimum(x,w-1-x)/(14*chip_scale))) if edges else 0
    erosion = field(rng,shape,1.8*chip_scale) + 0.7*mid + 2.3*edge
    chips = np.clip((erosion-2.75)*2.4,0,1)
    dust = np.clip(broad*0.035+0.035,0,0.14)
    detail = None
    if not white:
        from railhead_scanned import paint_detail
        grain, detail, scan_rough, exposed = paint_detail(shape)
        chips = np.maximum(chips, exposed*0.6)
    colour = np.broadcast_to(np.array(base,float),(*shape,3)).copy()
    colour *= (1 + 0.07*broad + 0.026*fine)[...,None]
    if not white:
        colour *= (0.6+0.4*grain)[...,None]
    metal = np.dstack([79+15*mid, 70+13*mid, 57+11*mid])
    colour = colour*(1-chips[...,None]) + metal*chips[...,None]
    colour *= (1-dust[...,None])
    if grime:
        # Brake dust and ballast dust: a dull brown-grey film, patchy, with drips running down.
        drip = field(rng,shape,(18,1.2))
        film = np.clip(grime*(0.75+0.35*broad+0.25*mid+0.3*np.maximum(drip,0)),0,0.85)
        colour = colour*(1-film[...,None]) + np.array((78,70,61))[None,None,:]*film[...,None]
        dust = dust + 0.6*film
    if faded_top:
        # The sun fades the enamel's top towards a chalky pink, most at the top edge (row 0).
        fade = np.clip(faded_top*(1.0 - y/h)**1.5*(0.8+0.3*broad), 0, 0.6)[..., None]
        colour = colour*(1-fade) + np.array((196,150,140))[None,None,:]*fade
    for u0, v0, half in bleed:
        # Rust and grease run down from a fitting at ( u0, v0 ) (0..1, v up): ragged streaks below it.
        cx, cy = u0*w, (1-v0)*h
        streak_cols = field(rng,(1,w),(0,2.5))[0]
        reach = np.clip((y-cy)/(h-cy+1e-6), 0, 1)
        across = np.exp(-((x-cx)/(half*w))**2)
        run = np.clip(across*(0.55+0.45*np.clip(streak_cols[None,:],-1,1))*(y > cy)*(1-0.7*reach)*(0.8+0.3*mid), 0, 0.85)
        colour = colour*(1-run[...,None]) + np.array((96,48,30))[None,None,:]*run[...,None]
    if desat:
        # Sun and dust take the red's saturation down, patchily: a grey film over the enamel.
        lum = (colour @ np.array((0.299, 0.587, 0.114)))[..., None]
        amount = np.clip(desat*(1 + 0.4*broad), 0, 0.6)[..., None]
        colour = colour*(1-amount) + lum*amount*np.array((1.02, 1.0, 0.96))
    # Thin scratches are visible in the normal and roughness rather than flat white streaks.
    scratches = Image.new("L",(w,h))
    draw = ImageDraw.Draw(scratches)
    for _ in range(int(w*h/4600)):
        xx, yy = rng.uniform(0,w), rng.uniform(0,h)
        length = rng.uniform(3,22)
        angle = rng.uniform(0,2*math.pi)
        draw.line((xx,yy,xx+length*math.cos(angle),yy+length*math.sin(angle)), fill=int(rng.uniform(70,180)),width=1)
    s = np.asarray(scratches)/255
    colour = colour*(1-0.35*s[...,None])+np.array((125,118,107))*0.35*s[...,None]
    rough = np.clip(0.48+0.03*mid+0.2*chips+0.1*dust+0.08*s,0.35,0.9)
    if not white:
        rough = rough*0.65+scan_rough*0.35
    height = 0.0025*fine-0.008*chips-0.003*s
    save(name,colour,rough,height,0.02+0.65*chips,units,detail=detail)


def write(root=None):
    """Draws the buffer stops' and ballast's materials into root/materials/railhead (a stage laid out as Assets), or
    Assets with no root."""
    _TARGET[0] = (K.ASSETS / RESOURCE) if root is None else Path(root) / RESOURCE
    OUT = _TARGET[0]
    OUT.mkdir(parents=True, exist_ok=True)
    # RAL 3000 flame red, sun-faded and dusted: the beam, and a second beam with more grime for the other variant.
    heads = ((0.133,0.46,0.06),(0.867,0.46,0.06),(0.48,0.15,0.02),(0.48,0.85,0.02))
    worn_paint("rw_buffer_beam",(512,2048),(170,46,36),4701,94,True,grime=0.1,desat=0.34,bleed=heads,faded_top=0.5,
               chip_scale=2.2)
    worn_paint("rw_buffer_beam_b",(512,2048),(164,44,36),4711,94,True,grime=0.24,desat=0.36,bleed=heads,faded_top=0.4,
               chip_scale=2.2)
    worn_paint("rw_buffer_red",(1024,1024),(164,44,35),4702,48,grime=0.12,desat=0.36,chip_scale=1.8)
    worn_paint("rw_buffer_grime",(1024,1024),(120,52,42),4712,48,grime=0.55,desat=0.35,chip_scale=1.8)
    worn_paint("rw_buffer_frame_dark",(1024,1024),(56,58,57),4713,48,grime=0.06)
    worn_paint("rw_buffer_grime_dark",(1024,1024),(66,63,58),4714,48,grime=0.38)
    worn_paint("rw_buffer_white",(1024,1024),(228,225,213),4703,32,white=True)
    rng = np.random.default_rng(4704)
    shape=(1024,1024)
    y,x=np.mgrid[:1024,:1024]
    rad=np.sqrt((x-511.5)**2+(y-511.5)**2)/512
    fine,mid,broad=field(rng,shape,0.7),field(rng,shape,3),field(rng,shape,30)
    rim=np.clip((rad-0.79+0.045*mid)*7,0,1)*(0.65+0.28*np.clip(mid,-1,1))
    score = Image.new("L",(1024,1024))
    draw=ImageDraw.Draw(score)
    for _ in range(1300):
        xx,yy=rng.uniform(0,1024,2)
        length=rng.uniform(2,27)
        draw.line((xx,yy,xx+length,yy+rng.uniform(-15,15)),fill=int(rng.uniform(30,210)),width=1)
    for _ in range(210):
        xx,yy=rng.uniform(0,1024,2)
        draw.line((xx,yy,xx+rng.uniform(15,75),yy+rng.uniform(-30,30)),fill=int(rng.uniform(80,190)),width=2)
    s=np.asarray(score)/255
    wear=np.clip(rim+0.52*s+0.06*np.clip(mid,0,2),0,0.92)
    from railhead_scanned import contact_detail
    grain,detail,scan_rough=contact_detail(shape)
    dark=np.dstack([115+2*broad+8*fine,111+2*broad+8*fine,104+2*broad+8*fine])*(.5+.5*grain)[...,None]
    bright=np.dstack([167+12*mid,160+12*mid,147+12*mid])
    grease=np.clip((0.85-rad)*1.6+0.45*field(rng,shape,14),0,1)*np.clip(1.2-rad,0,1)
    for name,turn in (("rw_buffer_contact",0),("rw_buffer_contact_b",2)):
        face=dark*(1-wear[...,None])+bright*wear[...,None]
        face=face*(1-0.55*grease[...,None])+np.array((34,30,24))*0.55*grease[...,None]
        save(name,np.rot90(face,turn),
              np.rot90(np.clip(0.6-0.2*wear+0.04*mid-0.3*grease,0.18,0.8)*.8+scan_rough*.2,turn),
              np.rot90(0.008*fine-0.008*s,turn),0.35,17.4,detail=np.rot90(detail,turn))
    for name,base,rough,metal in (("rw_buffer_plate",(33,31,29),0.72,0.35),
                                 ("rw_buffer_edge",(82,73,60),0.6,0.65),
                                 ("rw_buffer_bolt",(166,163,151),0.35,0.55),
                                 ("rw_track_stone",(143,143,136),0.95,0),
                                 ("rw_track_stone_dark",(84,89,86),0.95,0),
                                 ("rw_track_stone_warm",(159,142,122),0.95,0),
                                 ("rw_track_stone_oily",(60,56,52),0.85,0)):
        shape=(512,512)
        a,b=field(rng,shape,4),field(rng,shape,0.6)
        colour=np.array(base)[None,None,:]*(1+0.09*a+0.03*b)[...,None]
        stone=name.startswith("rw_track")
        save(name,colour,np.clip(rough+0.04*a,0,1),b*(0.035 if stone else 0.004),metal,PAINTS[name])
    for name,colour,rough,illum in (("rw_buffer_led",(1.0,0.14,0.055),0.15,8.0),
                                   ("rw_buffer_lens",(0.5,0.025,0.006),0.22,1.6)):
        colour_file = f"{name}_color.png"
        Image.new("RGB",(64,64),tuple(round(v*255) for v in colour)).save(OUT/colour_file)
        lines=["// Tools/railhead_buffer.py",'"Layer0"',"{",'    shader "shaders/complex.shader"',
               '    F_SPECULAR "1"', f'    TextureColor "{RESOURCE}/{colour_file}"',
               '    TextureNormal "materials/default/default_normal.tga"',
               f'    TextureRoughness "[{rough:.6f} {rough:.6f} {rough:.6f} 0.000000]"','    g_flMetalness "0"',
               '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
               '    g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"', '    g_flModelTintAmount "1"']
        if illum:
            lines += ['    F_SELF_ILLUM "1"', f'    g_flSelfIllumBrightness "{illum}"',
                      '    TextureSelfIllumMask "[1.000000 1.000000 1.000000 0.000000]"', '    g_flSelfIllumAlbedoFactor "1.0"',
                      '    g_vSelfIllumTint "[1.000000 1.000000 1.000000 0.000000]"']
        (OUT/f"{name}.vmat").write_text("\n".join(lines+["}",""]),encoding="utf-8")
    print(f"Wrote {len(PAINTS)} Railhead buffer and ballast materials")


def missing():
    return any(not (OUT/f"{name}.vmat").exists() for name in BASE_PAINTS)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", metavar="ROOT", help="a root laid out as Assets (a stage); default Assets")
    args = parser.parse_args()
    write(args.out)
