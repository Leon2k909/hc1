"""Riverside watch deck v1: the survivors' timber deck on the spawn pad, rebuilt as real timber framing.

Replaces the render geometry of `riverside_map.watch_deck`: four thin posts, flat joists, boards with a pinstripe grain,
pipe-style rails and a steel-style stair, all painted `rs_wood`. The new deck has concrete piers with galvanised post
bases, six 6x6 posts, doubled 2x8 beams, 2x6 joists at 16 in, 2x8 rim boards, sixteen gapped deck boards, bolted guard
rails, X braces and a three-stringer stair with two-board treads. Footprint (96 x 96 in), 5 ft height, the stair's
8 x 7.5 in rise and 80 in run, and every collision shape are unchanged: the collision stays in the Pad model.

Materials are the project's existing ones: the approved Riverside crate atlas (weathered CC0 brown_planks_03 crops, as
the Lucky Stop timber steps use), Lowtide galvanised steel and Riverside concrete. No new textures.

Local frame: plan units (inches), x = east, y = north, z up from the pad, origin at the deck's centre on the pad.
The scene object sits at world (-445, -60, 96) with no rotation (`map_kit.to_world` maps plan (e, n) to (n, -e)).

Usage: python build.py            writes Assets/models/props/riverside/watch_deck_v1/ (three LODs and the ModelDoc)
"""
from pathlib import Path
import sys, json, math, random, hashlib

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K          # noqa: E402
import riverdale_parts as G  # noqa: E402
import riverside_map as R    # noqa: E402

RES = 'models/props/riverside/watch_deck_v1'
OUT = ROOT / 'output/riverside/watch-deck-v1'
MODEL_DIR = ROOT / 'Assets' / RES

E0, E1, N0, N1, TOP = R.DECK                      # 12, 108, -493, -397, 60: the deck's plan box and floor height
CX, CY = (E0 + E1) / 2.0, (N0 + N1) / 2.0         # 60, -445
GZ = R.HIGH                                       # 96: the pad
ORIGIN_PLAN = (CX, CY, GZ)
ORIGIN_WORLD = tuple(float(c) for c in K.to_world(ORIGIN_PLAN))

X = np.array((1.0, 0.0, 0.0))
Y = np.array((0.0, 1.0, 0.0))
Z = np.array((0.0, 0.0, 1.0))
AX = (X, Y, Z)
HALF = 48.0

# Weathered plank bands of the approved crate atlas (x0, y0, height in pixels; each 1008 px wide). They skip the
# stencilled lettering and the dark joint lines.
CROPS = [(8, 342, 138), (8, 547, 129), (8, 700, 140), (8, 848, 137), (8, 1012, 138), (8, 1382, 138), (8, 1534, 138),
         (8, 1700, 130), (8, 1858, 134), (1032, 370, 120), (1032, 540, 140), (1032, 692, 144), (1032, 856, 134),
         (1032, 1014, 138), (1032, 1216, 124), (1032, 1364, 136), (1032, 1512, 142), (1032, 1676, 142), (1032, 1822, 134)]
CROP_W = 1008

# Lumber, actual inches
DECK_T = 1.25      # 5/4 deck board
JOIST_H = 5.5      # 2x6
BEAM_H = 7.25      # 2x8
POST = 5.5         # 6x6
Z_JOIST0 = TOP - DECK_T - JOIST_H      # 53.25: the joists' underside, the beams' top
Z_BEAM0 = Z_JOIST0 - BEAM_H            # 46.0
Z_RIM0 = TOP - DECK_T - BEAM_H         # 51.5: a 2x8 rim board hides the joist ends

POST_X = (-41.0, 41.0)
ROWS = (-41.0, 0.0, 41.0)

# The stair, from the old deck: foot at the deck's south face less 80 in, 8 treads of 7.5 in rise and 10 in going
Y_FOOT = (N0 - 80.0) - CY      # -128
Y_HEAD = N0 - CY               # -48
STEPS, RISE, GOING, TREAD_T = 8, 7.5, 10.0, 1.5
SLAB = 2.0                     # the thin concrete footing the stair stands on (drawn only, like the old pier pads)
STAIR_X = (-17.5, 0.0, 17.5)   # three 2x12 stringers, 1.5 in thick
TREAD_LEN = 36.5               # between the outer stringers' outer faces
SLOPE = RISE / GOING
THROAT = 5.5 / 0.8             # vertical offset of the stringer's lower edge from the notch corners (5.5 in throat)


def unit(a):
    a = np.asarray(a, float)
    return a / np.linalg.norm(a)


def zn(y):
    """ The tread nosing line's height at plan y (the stair's, then the landing's) """
    return min(TOP, RISE + SLOPE * (y - Y_FOOT))


def zb(y):
    """ The stringers' lower edge """
    return max(SLAB, SLOPE * (y - Y_FOOT) - 1.5 - THROAT)


class Deck:
    def __init__(self, lod):
        self.lod = lod
        self.m = K.Model()
        self.wood_rng = random.Random(20261106)    # the same pieces on every LOD, so the grain doesn't change at a switch
        self.last_crop = -1
        self.pieces = []

    # Wood ------------------------------------------------------------------------------------------------------------
    def next_crop(self):
        k = self.wood_rng.randrange(len(CROPS))
        while k == self.last_crop:
            k = self.wood_rng.randrange(len(CROPS))
        self.last_crop = k
        return CROPS[k], self.wood_rng.random() < 0.5

    def wood_uv(self, start, c, axes, grain):
        """ The crop of the atlas on this piece: u along its grain, v across; each face spans the whole crop. """
        polys = self.m.polygons['wood'][start:]
        if not polys:
            return
        c = np.asarray(c, float)
        order = [axes[grain]] + [axes[i] for i in range(3) if i != grain]
        allp = np.array([p for pts, _ in polys for p in pts]) - c
        lo = [float((allp @ a).min()) for a in order]
        span = [max(float(np.ptp(allp @ a)), 0.01) for a in order]
        (x0, y0, h), flip = self.next_crop()
        for j, (pts, _) in enumerate(polys, start):
            rel = np.array(pts) - c
            co = [rel @ a for a in order]
            ext = [float(np.ptp(k)) for k in co]
            if ext[0] > 0.01:
                iu, iv = 0, (1 if ext[1] >= ext[2] else 2)
            else:                       # a cut end: the grain's end, drawn with the same crop
                iu, iv = (1, 2) if ext[1] >= ext[2] else (2, 1)
            uv = []
            for k in range(len(pts)):
                fu = (co[iu][k] - lo[iu]) / span[iu]
                fv = (co[iv][k] - lo[iv]) / span[iv]
                if flip:
                    fu = 1.0 - fu
                uv.append(((x0 + fu * CROP_W) / 2048.0, 1.0 - (y0 + fv * h) / 2048.0))
            self.m.polygon_uvs[('wood', j)] = uv

    def timber(self, name, c, size, axes=AX, grain=None, bevel=0.14, convex=True):
        c = np.array(c, float)
        if grain is None:
            grain = int(np.argmax(size))
        start = len(self.m.polygons['wood'])
        G.bevel_box(self.m, c, axes, size, 'wood', bevel if self.lod < 2 else 0.0)
        end = len(self.m.polygons['wood'])
        self.wood_uv(start, c, axes, grain)
        self.pieces.append((name, start, end, c, convex))

    def diag(self, name, p0, p1, width, thick, normal, bevel=0.14):
        """ A timber from p0 to p1: width in the plane of the brace, thick along normal """
        p0, p1 = np.array(p0, float), np.array(p1, float)
        length = float(np.linalg.norm(p1 - p0))
        d = (p1 - p0) / length
        n = np.array(normal, float)
        n = unit(n - d * float(n @ d))
        a = np.cross(d, n)
        self.timber(name, (p0 + p1) / 2, (length, thick, width), (d, n, a), 0, bevel)

    # Hardware (LOD 0 only) ---------------------------------------------------------------------------------------------
    def bolt(self, p, n):
        """ A carriage bolt's domed head, on a face whose outward normal is n """
        if self.lod > 0:
            return
        p, n = np.array(p, float), unit(n)
        G.lathe_axis(self.m, p + n * 0.3, -n, [(0, 0), (0.42, 0.07), (0.62, 0.2), (0.62, 0.3)], 'steel', sides=6)

    def screw(self, p, n):
        """ A deck screw's head: a flat hexagon, just proud of the board """
        if self.lod > 0:
            return
        p, n = np.array(p, float), unit(n)
        e1, e2 = G.perp(n)
        pts = [p + n * 0.04 + (e1 * math.cos(math.pi * k / 3) + e2 * math.sin(math.pi * k / 3)) * 0.28 for k in range(6)]
        if float(np.dot(np.cross(pts[1] - pts[0], pts[2] - pts[1]), n)) < 0:
            pts.reverse()
        self.m.polygon('steel', pts, n)

    def plate(self, c, size, paint='steel'):
        G._box3(self.m, c, AX, size, paint)

    # Frame -------------------------------------------------------------------------------------------------------------
    def piers_and_posts(self):
        m = self.m
        for rx in POST_X:
            for ry in ROWS:
                G.bevel_box(m, (rx, ry, 2.25), AX, (11, 11, 4.5), 'rs_concrete', 0.7 if self.lod < 2 else 0.0)
                self.plate((rx, ry, 4.65), (6.4, 6.4, 0.3))
                for s in (-1, 1):
                    self.plate((rx, ry + s * 2.85, 7.05), (5.7, 0.2, 4.5))
                    self.bolt((rx, ry + s * 2.95, 7.2), (0, s, 0))
                self.timber('post', (rx, ry, (4.8 + Z_JOIST0) / 2), (POST, POST, Z_JOIST0 - 4.8), grain=2, bevel=0.25)

    def beams(self):
        """ Doubled 2x8s either side of each row of posts, bolted through. """
        for ry in ROWS:
            for s in (-1, 1):
                yb = ry + s * 3.5
                self.timber('beam', (0, yb, Z_BEAM0 + BEAM_H / 2), (93.0, 1.5, BEAM_H))
                for rx in POST_X:
                    for dx, z in ((-1.5, Z_BEAM0 + 2.4), (1.5, Z_BEAM0 + 5.0)):
                        self.bolt((rx + dx, yb + s * 0.75, z), (0, s, 0))

    def framing(self):
        zr = Z_RIM0 + BEAM_H / 2
        self.timber('rim S', (0, -HALF + 0.75, zr), (96.0, 1.5, BEAM_H))
        self.timber('rim N', (0, HALF - 0.75, zr), (96.0, 1.5, BEAM_H))
        self.timber('rim W', (-HALF + 0.75, 0, zr), (1.5, 93.0, BEAM_H))
        self.timber('rim E', (HALF - 0.75, 0, zr), (1.5, 93.0, BEAM_H))
        for x in (-31.5, -15.75, 0.0, 15.75, 31.5):
            self.timber('joist', (x, 0, Z_JOIST0 + JOIST_H / 2), (1.5, 93.0, JOIST_H), bevel=0.0)

    def decking(self):
        count = 16
        pitch = (96.0 - 5.5) / (count - 1)
        supports = (-47.25, -31.5, -15.75, 0.0, 15.75, 31.5, 47.25)
        for k in range(count):
            y = -HALF + 2.75 + pitch * k
            self.timber('board', (0, y, TOP - DECK_T / 2), (96.0, 5.5, DECK_T), bevel=0.16)
            for i, x in enumerate(supports):
                self.screw((x, y + (1.25 if (i + k) % 2 else -1.25), TOP), Z)

    def braces(self):
        for sx in (-1, 1):
            xa, xb = sx * 44.5, sx * 46.0
            for ya, yb in ((-41.0, 0.0), (0.0, 41.0)):
                self.diag('brace', (xa, ya + 1.5, 12.0), (xa, yb - 1.5, 44.0), 3.5, 1.5, X)
                self.diag('brace', (xb, yb - 1.5, 12.0), (xb, ya + 1.5, 44.0), 3.5, 1.5, X)
                self.bolt((xa + sx * 0.75, ya + 2.2, 13.2), (sx, 0, 0))
                self.bolt((xa + sx * 0.75, yb - 2.2, 42.8), (sx, 0, 0))
                self.bolt((xb + sx * 0.75, yb - 2.2, 13.2), (sx, 0, 0))
                self.bolt((xb + sx * 0.75, ya + 2.2, 42.8), (sx, 0, 0))

    # Guard rails -------------------------------------------------------------------------------------------------------
    def rail_post(self, name, cx, cy, z0, z1, face):
        """ A 4x4 bolted to the rim's outside face; face is that face's outward normal """
        self.timber(name, (cx, cy, (z0 + z1) / 2), (3.5, 3.5, z1 - z0), grain=2, bevel=0.12)
        n = np.array(face, float)
        out = np.array((cx, cy, 0.0)) + n * 1.75
        for z in (z0 + 3.9, z0 + 7.1):
            self.bolt((out[0], out[1], z), n)

    def guard_rails(self):
        z0, z1 = Z_RIM0 - 1.0, TOP + 36.0        # 36 in over the deck
        top_c, mid_c = z1 + 0.75, TOP + 17.75
        for sx in (-1, 1):
            px = sx * 49.75
            for y in (-49.75, -24.9, 0.0, 24.9, 49.75):
                self.rail_post('rail post', px, y, z0, z1, (sx, 0, 0))
            self.timber('rail top', (px, 0, top_c), (5.5, 105.0, 1.5), bevel=0.12)
            self.timber('rail mid', (sx * 47.25, 0, mid_c), (1.5, 103.0, 3.5), bevel=0.1)
            # the south edge, open over the stair: posts at 35 and at 20, where the stair's rails land
            self.rail_post('rail post', sx * 34.9, -49.75, z0, z1, (0, -1, 0))
            self.timber('rail top', (sx * (47.0 + 22.75) / 2, -49.75, top_c), (24.25, 5.5, 1.5), bevel=0.12)
            self.timber('rail mid', (sx * (46.5 + 18.25) / 2, -47.25, mid_c), (28.25, 1.5, 3.5), bevel=0.1)

    # Stair -------------------------------------------------------------------------------------------------------------
    def stair(self):
        m = self.m
        for xc in STAIR_X:                      # a concrete paver under each stringer's foot
            G.bevel_box(m, (xc, -122.0, SLAB / 2), AX, (9.0, 24.0, SLAB), 'rs_concrete', 0.4 if self.lod < 2 else 0.0)
        pts = [(Y_FOOT, SLAB), (Y_FOOT, RISE - TREAD_T)]
        for i in range(STEPS):
            y1 = Y_FOOT + GOING * (i + 1)
            pts.append((y1, RISE * (i + 1) - TREAD_T))
            if i < STEPS - 1:
                pts.append((y1, RISE * (i + 2) - TREAD_T))
        pts.append((Y_HEAD, zb(Y_HEAD)))
        pts.append((Y_FOOT + (SLAB + 1.5 + THROAT) / SLOPE, SLAB))
        slope_dir = unit((0.0, GOING, RISE))
        axes = (slope_dir, X, np.cross(slope_dir, X))
        profile = [(-y, z) for y, z in pts]
        for xc in STAIR_X:
            start = len(m.polygons['wood'])
            G.extrude(m, (xc - 0.75, 0, 0), (xc + 0.75, 0, 0), profile, 'wood', up=Z, smooth=0)
            self.wood_uv(start, (xc, -88.0, 30.0), axes, 0)
            self.pieces.append(('stringer', start, len(m.polygons['wood']), np.array((xc, -88.0, 30.0)), False))
            for s in (-1, 1):                    # bolted through the rim
                self.bolt((xc + s * 0.75, -51.0, 55.0), (s, 0, 0))
        # cross ties between the stringers
        for y in (-100.0, -74.0):
            self.timber('tie', (0, y, zb(y) + 3.2), (33.5, 1.5, 3.5))
        # treads: two boards a step, a little nosing, each screwed to each stringer
        for i in range(STEPS):
            y0 = Y_FOOT + GOING * i
            ztop = RISE * (i + 1)
            spans = [(y0 - 0.75, y0 + 4.65), (y0 + 4.85, y0 + 10.25)]
            if i == STEPS - 1:
                spans[1] = (y0 + 4.85, Y_HEAD)
            for ya, yb in spans:
                self.timber('tread', (0, (ya + yb) / 2, ztop - TREAD_T / 2), (TREAD_LEN, yb - ya, TREAD_T))
                for xc in STAIR_X:
                    for dy in (-1.4, 1.4):
                        self.screw((xc, (ya + yb) / 2 + dy, ztop), Z)
        # rails: posts bolted to the outside of the outer stringers, a flat 2x6 on top, a 2x4 rail between
        for sx in (-1, 1):
            for yk in (-126.25, -98.0, -70.0):
                z0 = max(zb(yk), SLAB) + 0.8
                z1 = zn(yk) + 36.0
                self.timber('stair post', (sx * 20.0, yk, (z0 + z1) / 2), (3.5, 3.5, z1 - z0), grain=2, bevel=0.12)
                for dz in (2.4, 5.4):
                    self.bolt((sx * 21.75, yk, z0 + dz), (sx, 0, 0))
            self.rail_post('rail post', sx * 20.0, -49.75, Z_RIM0 - 1.0, TOP + 36.0, (0, -1, 0))
            d = unit((0.0, 70.0, 52.5))
            p0 = np.array((sx * 20.0, Y_FOOT, zn(Y_FOOT) + 36.75))
            p1 = np.array((sx * 20.0, -58.0, TOP + 36.75))
            self.timber('stair rail', (p0 + p1) / 2, (float(np.linalg.norm(p1 - p0)), 5.5, 1.5), (d, X, np.cross(d, X)), 0, 0.12)
            self.timber('stair rail', (sx * 20.0, -53.0, TOP + 36.75), (5.5, 10.0, 1.5), bevel=0.12)
            q0 = np.array((sx * 17.5, Y_FOOT + 2.0, zn(Y_FOOT + 2.0) + 17.75))
            q1 = np.array((sx * 17.5, -58.0, TOP + 17.75))
            dm = unit(q1 - q0)
            self.timber('stair mid', (q0 + q1) / 2, (float(np.linalg.norm(q1 - q0)), 1.5, 3.5), (dm, X, np.cross(dm, X)), 0, 0.1)
            self.timber('stair mid', (sx * 17.5, -53.0, TOP + 17.75), (1.5, 10.0, 3.5), bevel=0.1)

    # -------------------------------------------------------------------------------------------------------------------
    def build(self):
        self.piers_and_posts()
        self.beams()
        self.framing()
        self.decking()
        self.braces()
        self.guard_rails()
        self.stair()
        m = self.m
        m.material_overrides.update({'wood': 'materials/riverside/crate_v2/crate.vmat',
                                     'steel': 'materials/lowtide/lt_steel.vmat',
                                     'dark': 'materials/riverside/rs_dark.vmat'})
        R.configure(m)
        for paint in ('wood', 'steel', 'dark'):
            m.tile_overrides[paint] = 48
        return m

    def check_outward(self):
        """ Every face of every convex timber faces away from its centre """
        bad = 0
        polys = self.m.polygons['wood']
        for name, start, end, c, convex in self.pieces:
            if not convex:
                continue
            for j in range(start, end):
                pts, n = polys[j]
                if float(np.dot(n, np.mean(pts, axis=0) - c)) < -1e-3:
                    bad += 1
        return bad

    def check_winding(self):
        """ (faces wound against their own normal, faces with no area): the OBJ's winding is what the engine culls by """
        wound = flat = 0
        for polys in self.m.polygons.values():
            for pts, n in polys:
                g = np.zeros(3)
                for k in range(1, len(pts) - 1):
                    g += np.cross(pts[k] - pts[0], pts[k + 1] - pts[0])
                if np.linalg.norm(g) < 1e-8:
                    flat += 1
                elif float(np.dot(g, n)) < 0:
                    wound += 1
        return wound, flat


def make(lod):
    deck = Deck(lod)
    model = deck.build()
    return model, deck


def write_all():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    counts, inward, wound = [], [], []
    for lod in range(3):
        model, deck = make(lod)
        counts.append(K.write_obj(MODEL_DIR / f'deck_lod{lod}.obj', model, 'deck'))
        inward.append(deck.check_outward())
        wound.append(deck.check_winding())
    model0, _ = make(0)
    K.write_vmdl(MODEL_DIR / 'deck.vmdl', RES, 'deck_lod0', model0)
    text = (MODEL_DIR / 'deck.vmdl').read_text()
    a = text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"')
    b = text.index('\n\t\t\t},', a) + len('\n\t\t\t},')
    files = ''.join(
        f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/deck_lod{i}.obj" import_scale=1 align_origin_x_type="None" '
        f'align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},'
        for i in range(3))
    groups = ''.join(f'{{_class="LODGroup" switch_threshold={t} meshes=["lod{i}"]}},' for i, t in enumerate(THRESHOLDS))
    (MODEL_DIR / 'deck.vmdl').write_text(text[:a] + f'{{_class="RenderMeshList" children=[{files}]}},\n'
                                         f'{{_class="LODGroupList" children=[{groups}]}},' + text[b:])
    info = dict(triangles=counts, inward_faces=inward, wound_and_flat_faces=wound, thresholds=list(THRESHOLDS),
                resource=RES + '/deck.vmdl',
                position=list(ORIGIN_WORLD), yaw=0,
                files={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(MODEL_DIR.iterdir()) if p.is_file()})
    (OUT / 'manifest.json').write_text(json.dumps(info, indent=2))
    return info


THRESHOLDS = (0, 35, 80)

if __name__ == '__main__':
    info = write_all()
    print(json.dumps({k: v for k, v in info.items() if k != 'files'}, indent=1))
