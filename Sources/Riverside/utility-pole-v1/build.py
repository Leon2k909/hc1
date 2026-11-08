"""Riverside utility pole v1: the lane's creosoted timber poles, rebuilt as real poles.

Replaces the render geometry of `riverside_parts.pole()` (four 8-sided tapering segments, two plain box crossarms, four 1.4 in
square braces, all in a flat 512 px paint at 8 px per inch). The new pole keeps the old pole's size, taper, crossarm
heights and the crossarm tops the pin insulators sit on, and its collision stays in the dressing model (the old hull).

What is in it: a 24-sided trunk with a butt flare, a faint sweep, out-of-round growth and a pitched top, all shaded smooth and
mapped round the pole with the real-scan creosote texture (utility_pole_v1/pole_wood_*.png, 27-37 px per inch); chamfered
4x5 crossarms with a carriage bolt through each (domed head in front, square washer, nut and bolt end behind); flat steel
angle braces with bolts; a ground wire stapled down the pole into a half-round guard that runs from the ground to 8 ft; steps
(bolts) up one side; an aluminium tag; and a low earth mound round the foot in Riverside's own mud paint.

Two variants, as the lane has two: pole_2arm (430 in, two arms; the west side) and pole_1arm (400 in, one arm; the east side).
Local frame: plan units (inches), origin at the foot on the ground, z up, forward (the arms' face) = plan north (+y), so the
scene object's yaw is `map_kit.plan_yaw(facing)`, like every other prop. Three LODs; the small hardware is LOD 0 only.

Usage: python -B build.py            writes Assets/models/props/riverside/utility_pole_v1/ (LOD OBJs, vmdl, vmat) + manifest
"""
from pathlib import Path
import sys, json, math, hashlib

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K          # noqa: E402
import riverdale_parts as G  # noqa: E402
import riverside_map as R    # noqa: E402

RES = 'models/props/riverside/utility_pole_v1'
MODEL_DIR = ROOT / 'Assets' / RES
MAT_DIR = ROOT / 'Assets/materials/riverside/utility_pole_v1'
OUT = ROOT / 'output/riverside/utility-pole-v1'
WOOD_VMAT = 'materials/riverside/utility_pole_v1/pole_wood.vmat'

UP = np.array((0.0, 0.0, 1.0))
F = np.array((0.0, 1.0, 0.0))            # the arms' face (plan north); the object's yaw turns it to the pole's facing
S = np.cross(UP, F)                      # the arms' length: 90 degrees counter-clockwise of F (plan west)

VARIANTS = {'pole_2arm': dict(height=430.0, arms=2), 'pole_1arm': dict(height=400.0, arms=1)}
THRESHOLDS = (0, 35, 90)

# Texture: 1024 x 2048, 30 px per inch along the grain (one repeat every 68.3 in), u once round the trunk
V_PER_IN = 30.0 / 2048.0
U_PER_IN = 30.0 / 1024.0
TWIST = 0.20                             # the grain turns a fifth of a turn up the pole, so repeats don't line up

R_BASE, R_TOP = 6.0, 4.4                 # the old pole's radii at the foot and the top
ARM_DEPTH, ARM_HEIGHT = 3.6, 4.5         # a 4x5 arm (the old arm was 4 x 4.5)
ARM_AT = 5.0                             # the arm's centre in front of the pole's axis (the old pole's, so the insulators sit right)
GROUND_WIRE_AT = math.radians(38.0)      # angles are from F, counter-clockwise
STEP_ANGLES = (math.radians(-58.0), math.radians(-122.0))
TAG_AT = math.radians(-32.0)


def unit(a):
    a = np.asarray(a, float)
    return a / np.linalg.norm(a)


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


class Pole:
    def __init__(self, lod, height, arms):
        self.lod, self.H, self.arms = lod, float(height), arms
        self.m = K.Model()
        self.pieces = []
        self.sides = (24, 12, 8)[lod]
        self.phase = (0.7, 2.1)

    # Trunk ---------------------------------------------------------------------------------------------------------
    def radius(self, z):
        t = max(z, 0.0) / self.H
        r = R_BASE + (R_TOP - R_BASE) * t
        return r + 0.75 * math.exp(-max(z, 0.0) / 16.0)                    # butt flare

    def axis(self, z):
        return np.array((0.30 * math.sin(z / 110.0 + self.phase[0]), 0.30 * math.sin(z / 150.0 + self.phase[1]), z))

    def surface(self, z, theta, lift=0.0):
        d = F * math.cos(theta) + S * math.sin(theta)
        return self.axis(z) + d * (self.radius(z) + lift), d

    def trunk(self):
        H = self.H
        zs = {0: [-3, 2, 6, 12, 22, 38, 60, 90, 130, 180, 240, 310, 370, H - 1.5],
              1: [-3, 6, 22, 60, 130, 240, H - 1.5],
              2: [-3, 120, H - 1.5]}[self.lod]
        top = [(H + 0.9, 0.62), (H + 2.1, 0.0)]                           # the pitched top, as a low cone
        N = self.sides
        rings = []                                                       # (z, [points], radius_scale)
        for z in zs + [t[0] for t in top]:
            scale = 1.0
            for tz, s in top:
                if z == tz:
                    scale = s
            r = self.radius(min(z, H - 1.5)) * scale
            pts = []
            for k in range(N):
                th = math.pi + 2 * math.pi * k / N
                ovalness = 1.0 + 0.012 * math.sin(2 * th + z / 90.0) + 0.008 * math.sin(3 * th + z / 55.0)
                d = F * math.cos(th) + S * math.sin(th)
                pts.append(self.axis(min(z, H - 1.5)) + np.array((0, 0, z - min(z, H - 1.5))) + d * r * ovalness)
            rings.append((z, pts))
        # smooth normals from the grid itself
        def normal(i, k):
            a = rings[i][1][(k + 1) % N] - rings[i][1][(k - 1) % N]
            lo, hi = max(i - 1, 0), min(i + 1, len(rings) - 1)
            b = rings[hi][1][k] - rings[lo][1][k]
            n = np.cross(a, b)
            if np.linalg.norm(n) < 1e-9:
                return UP
            n = unit(n)
            return n if float(np.dot(n, rings[i][1][k] - self.axis(rings[i][0]))) > -1e-6 or rings[i][0] > H else -n
        for i in range(len(rings) - 1):
            z0, z1 = rings[i][0], rings[i + 1][0]
            for k in range(N):
                k1 = (k + 1) % N
                pts = [rings[i][1][k], rings[i][1][k1], rings[i + 1][1][k1], rings[i + 1][1][k]]
                ns = [normal(i, k), normal(i, k1), normal(i + 1, k1), normal(i + 1, k)]
                u0, u1 = k / N, (k + 1) / N
                v0, v1 = z0 * V_PER_IN, z1 * V_PER_IN
                tw0, tw1 = TWIST * z0 / H, TWIST * z1 / H
                uv = [(u0 + tw0, v0), (u1 + tw0, v0), (u1 + tw1, v1), (u0 + tw1, v1)]
                mid = (pts[0] + pts[1] + pts[2] + pts[3]) / 4
                towards = mid - self.axis(min(z0, H))
                towards[2] = 0.0
                start = len(self.m.polygons['wood'])
                if np.linalg.norm(pts[2] - pts[3]) < 1e-6:               # a triangle at the apex
                    pts, ns, uv = [pts[0], pts[1], pts[2]], [ns[0], ns[1], ns[2]], [uv[0], uv[1], uv[2]]
                if i == len(rings) - 2:
                    towards = towards + UP * 0.5
                G.card(self.m, 'wood', pts, towards, uv=uv, normals=ns)
                self.pieces.append(('trunk', 'wood', start, len(self.m.polygons['wood']), None))

    # Timber --------------------------------------------------------------------------------------------------------
    def wood_uv(self, start, c, axes, grain, offset):
        c = np.asarray(c, float)
        polys = self.m.polygons['wood'][start:]
        others = [i for i in range(3) if i != grain]
        for j, (pts, n) in enumerate(polys, start):
            nl = [abs(float(np.dot(n, axes[i]))) for i in range(3)]
            if nl[grain] > 0.8:                                          # a cut end
                a, b = others
                uv = [(float(np.dot(p - c, axes[a])) * U_PER_IN + offset[0], float(np.dot(p - c, axes[b])) * V_PER_IN + offset[1]) for p in pts]
            else:
                across = others[0] if nl[others[0]] < nl[others[1]] else others[1]
                uv = [(float(np.dot(p - c, axes[across])) * U_PER_IN + offset[0], float(np.dot(p - c, axes[grain])) * V_PER_IN + offset[1]) for p in pts]
            self.m.polygon_uvs[('wood', j)] = uv

    def timber(self, name, c, axes, size, grain, offset, bevel):
        start = len(self.m.polygons['wood'])
        G.bevel_box(self.m, c, axes, size, 'wood', bevel)
        end = len(self.m.polygons['wood'])
        self.wood_uv(start, c, axes, grain, offset)
        self.pieces.append((name, 'wood', start, end, np.asarray(c, float)))

    # Hardware (the small parts are LOD 0 only) -----------------------------------------------------------------------
    def dome(self, p, n, r=0.62):
        if self.lod > 0:
            return
        G.lathe_axis(self.m, p, n, [(r, 0.0), (r * 0.97, 0.12), (r * 0.62, 0.30), (0.14, 0.38)], 'steel', sides=8, cap='steel')

    def nut(self, p, n):
        if self.lod > 0:
            return
        G.lathe_axis(self.m, p, n, [(0.56, 0.0), (0.56, 0.52)], 'steel', sides=6, cap='steel')
        G.lathe_axis(self.m, p + unit(n) * 0.52, n, [(0.3, 0.0), (0.3, 0.42)], 'steel', sides=6, cap='steel')

    def plate(self, c, n, size, thick=0.2):
        if self.lod > 0:
            return
        e1, e2 = G.perp(unit(n))
        G._box3(self.m, c, (e1, e2, unit(n)), (size, size, thick), 'steel')

    def arm(self, k):
        H = self.H
        z = H - 14 - 28 * k
        L = 96.0 if k == 0 else 72.0
        c = self.axis(z) + F * ARM_AT
        axes = (S, UP, F)                                                # right-handed; x is the arm's length
        self.timber('arm', c, axes, (L, ARM_HEIGHT, ARM_DEPTH), 0, (0.13 + 0.31 * k, 0.17 + 0.23 * k), 0.30 if self.lod == 0 else 0.0)
        front = c + F * (ARM_DEPTH / 2)
        # the through bolt: domed head in front, washer plate, nut and the bolt's end behind the pole
        self.dome(front + F * 0.0, F)
        back = self.axis(z) - F * self.radius(z)
        self.plate(back - F * 0.1, -F, 2.4)
        self.nut(back - F * 0.2, -F)
        # the braces: flat steel from the arm's face down to the pole
        for s in (-1, 1):
            p0 = front + S * (s * 0.3 * L) + F * 0.16 - UP * 0.6
            p1 = self.axis(z - 22) + F * (self.radius(z - 22) * 0.92 + 0.18) + S * (s * 2.3)
            a = unit(p1 - p0)
            wd = unit(np.cross(F, a))
            th = unit(np.cross(a, wd))
            if float(np.dot(th, F)) < 0:
                th = -th
            length = float(np.linalg.norm(p1 - p0))
            G._box3(self.m, (p0 + p1) / 2, (a, wd, th), (length, 1.6, 0.28), 'steel')
            self.dome(p0 + th * 0.14, th, 0.5)
            self.dome(p1 + th * 0.14, th, 0.5)

    # Details down the pole --------------------------------------------------------------------------------------------
    def ground_wire(self):
        if self.lod > 1:
            return
        H = self.H
        z_top, z_guard = H - 8.0, 98.0
        zs = [z_top - 36.0 * i for i in range(int((z_top - z_guard) / 36.0) + 1)] + [z_guard]
        pts = [self.surface(z, GROUND_WIRE_AT, 0.16)[0] for z in zs]
        if self.lod == 0:
            for a, b in zip(pts, pts[1:]):
                G.rod(self.m, a, b, 0.15, 'steel', 5)
            for z in zs[:-1]:                                            # staples
                p, d = self.surface(z - 14.0, GROUND_WIRE_AT, 0.2)
                tangent = unit(np.cross(UP, d))
                G.card(self.m, 'steel', [p - tangent * 0.55 - UP * 0.16, p + tangent * 0.55 - UP * 0.16, p + tangent * 0.55 + UP * 0.16, p - tangent * 0.55 + UP * 0.16], d)
        # the guard: a half-round moulding from the ground to 8 ft, topped with a slope
        zg = [-1.0, 30.0, 62.0, z_guard]
        half = 1.5
        profile = [(-1.0, 0.0), (-0.55, 0.62), (0.0, 0.95), (0.55, 0.62), (1.0, 0.0)]
        for i in range(len(zg) - 1):
            for j in range(len(profile) - 1):
                quad, norms, uvs = [], [], []
                for (z, a) in ((zg[i], profile[j]), (zg[i], profile[j + 1]), (zg[i + 1], profile[j + 1]), (zg[i + 1], profile[j])):
                    th = GROUND_WIRE_AT + a[0] * half / self.radius(z)
                    p, d = self.surface(z, th, a[1])
                    quad.append(p)
                    norms.append(unit(d + UP * 0.0 + np.cross(UP, d) * (a[0] * 0.5)))
                    uvs.append((0.5 + a[0] * 0.05 + 0.11 * i, z * V_PER_IN + 0.5))
                mid = sum(quad) / 4
                start = len(self.m.polygons['wood'])
                G.card(self.m, 'wood', quad, mid - self.axis(mid[2]) + np.array((0, 0, 0)), uv=uvs, normals=norms)
                self.pieces.append(('guard', 'wood', start, len(self.m.polygons['wood']), None))
        # its top slope
        row = []
        for a in profile:
            th = GROUND_WIRE_AT + a[0] * half / self.radius(z_guard)
            row.append(self.surface(z_guard, th, a[1])[0])
        G.card(self.m, 'wood', [row[0], row[1], row[2], row[3], row[4]], UP, uv=[(0.5 + a[0] * 0.05, 0.3) for a in profile])

    def steps(self):
        if self.lod > 0:
            return
        for i, z in enumerate((102.0, 120.0, 138.0, 156.0)):
            th = STEP_ANGLES[i % 2]
            p, d = self.surface(z, th, 0.0)
            e1, e2 = G.perp(d)
            self.plate(p + d * 0.1, d, 1.9, 0.2)
            G.lathe_axis(self.m, p + d * 0.2, d, [(0.34, 0.0), (0.34, 6.4)], 'steel', sides=6, cap='steel')
            G.lathe_axis(self.m, p + d * 6.0, d, [(0.58, 0.0), (0.58, 0.5)], 'steel', sides=6, cap='steel')

    def tag(self):
        if self.lod > 0:
            return
        p, d = self.surface(150.0, TAG_AT, 0.0)
        t = unit(np.cross(UP, d))
        G._box3(self.m, p + d * 0.06, (t, UP, d), (2.6, 1.7, 0.1), 'alu')
        for s in (-1, 1):
            G.lathe_axis(self.m, p + d * 0.1 + UP * 0.0 + t * (s * 0.95) + UP * 0.45, d, [(0.22, 0.0), (0.22, 0.08)], 'steel', sides=5, cap='steel')

    def mound(self):
        if self.lod > 1:
            return
        rng = np.random.default_rng(11)
        sides = 14 if self.lod == 0 else 8
        profile = [(5.4, 3.9), (7.2, 3.5), (9.6, 2.6), (12.2, 1.5), (14.8, 0.7), (16.8, 0.05)]
        if self.lod > 0:
            profile = [(5.4, 3.9), (9.6, 2.6), (14.8, 0.7), (16.8, 0.05)]
        rings = []
        for r, z in profile:
            ring = []
            for k in range(sides):
                th = 2 * math.pi * k / sides + 0.2
                jr = 1.0 + 0.10 * math.sin(3 * th + r) + 0.07 * (rng.random() - 0.5) * (r > 6)
                jz = 0.45 * (rng.random() - 0.5) * (r > 6)
                ring.append(np.array((math.cos(th) * r * jr, math.sin(th) * r * jr, max(z + jz, 0.05))))
            rings.append(ring)
        for i in range(len(rings) - 1):
            for k in range(sides):
                k1 = (k + 1) % sides
                G.card(self.m, 'rs_mud', [rings[i][k], rings[i][k1], rings[i + 1][k1], rings[i + 1][k]], UP)

    # ----------------------------------------------------------------------------------------------------------------
    def build(self):
        self.trunk()
        for k in range(self.arms):
            self.arm(k)
        self.ground_wire()
        self.steps()
        self.tag()
        self.mound()
        m = self.m
        m.material_overrides.update({'wood': WOOD_VMAT, 'steel': 'materials/lowtide/lt_steel.vmat',
                                     'alu': 'materials/riverside/rs_alu.vmat'})
        R.configure(m)
        for paint in ('wood', 'steel', 'alu'):
            m.tile_overrides[paint] = 48                                   # unused for wood (explicit UVs); plain tints for the rest
        return m

    def check_outward(self):
        """ Every face of every convex timber faces away from its centre """
        bad = 0
        polys = self.m.polygons['wood']
        for name, paint, start, end, c in self.pieces:
            if c is None:
                continue
            for j in range(start, end):
                pts, n = polys[j]
                if float(np.dot(n, np.mean(pts, axis=0) - c)) < -1e-3:
                    bad += 1
        return bad

    def check_winding(self):
        """ (faces wound against their own normal, faces with no area) """
        wound = flat = 0
        for paint, polys in self.m.polygons.items():
            for idx, (pts, n) in enumerate(polys):
                g = np.zeros(3)
                for k in range(1, len(pts) - 1):
                    g += np.cross(pts[k] - pts[0], pts[k + 1] - pts[0])
                if np.linalg.norm(g) < 1e-8:
                    flat += 1
                elif float(np.dot(g, n)) < 0:
                    wound += 1
        return wound, flat


def make(variant, lod):
    spec = VARIANTS[variant]
    pole = Pole(lod, spec['height'], spec['arms'])
    return pole.build(), pole


def write_variant(variant):
    counts, inward, wound = [], [], []
    for lod in range(3):
        model, pole = make(variant, lod)
        counts.append(K.write_obj(MODEL_DIR / f'{variant}_lod{lod}.obj', model, variant))
        inward.append(pole.check_outward())
        wound.append(pole.check_winding())
    model0, _ = make(variant, 0)
    path = MODEL_DIR / f'{variant}.vmdl'
    K.write_vmdl(path, RES, f'{variant}_lod0', model0)
    text = path.read_text()
    a = text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"')
    b = text.index('\n\t\t\t},', a) + len('\n\t\t\t},')
    files = ''.join(
        f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/{variant}_lod{i}.obj" import_scale=1 align_origin_x_type="None" '
        f'align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},'
        for i in range(3))
    groups = ''.join(f'{{_class="LODGroup" switch_threshold={t} meshes=["lod{i}"]}},' for i, t in enumerate(THRESHOLDS))
    path.write_text(text[:a] + f'{{_class="RenderMeshList" children=[{files}]}},\n'
                    f'{{_class="LODGroupList" children=[{groups}]}},' + text[b:])
    return dict(triangles=counts, inward_faces=inward, wound_and_flat_faces=wound, resource=f'{RES}/{variant}.vmdl')


def write_vmat():
    MAT_DIR.mkdir(parents=True, exist_ok=True)
    (MAT_DIR / 'pole_wood.vmat').write_text(
        '// Riverside utility pole v1: creosoted timber from the project\'s real brown_planks_03 scan (crate atlas crops),\n'
        '// graded to the old rs_pole\'s brown; see Sources/Riverside/utility-pole-v1/README.md.\n'
        'Layer0\n{\n'
        ' shader "shaders/complex.shader"\n'
        ' F_SPECULAR 1\n'
        ' TextureColor "materials/riverside/utility_pole_v1/pole_wood_color.png"\n'
        ' TextureNormal "materials/riverside/utility_pole_v1/pole_wood_normal.png"\n'
        ' TextureRoughness "materials/riverside/utility_pole_v1/pole_wood_rough.png"\n'
        ' g_flRoughnessScaleFactor "1.0"\n'
        ' g_flModelTintAmount "1.0"\n'
        ' g_vColorTint "[1.0 1.0 1.0 0.0]"\n'
        ' g_bFogEnabled "1"\n'
        '}\n', encoding='utf-8')


def write_all():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    write_vmat()
    info = {v: write_variant(v) for v in VARIANTS}
    info['thresholds'] = list(THRESHOLDS)
    info['files'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for d in (MODEL_DIR, MAT_DIR) for p in sorted(d.iterdir()) if p.is_file() and not p.name.endswith('.meta')}
    (OUT / 'manifest.json').write_text(json.dumps(info, indent=2))
    return info


if __name__ == '__main__':
    info = write_all()
    print(json.dumps({k: v for k, v in info.items() if k != 'files'}, indent=1))
