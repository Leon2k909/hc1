"""Coopered casks for Belltower (v3): every barrel on the map, built as a cooper builds one.

The user (2026-10-25) found the barrels "too perfect/round". The original cask was a 48-sided tube that curved in like
a pill at both ends, its lid flush with the rim, with thick black bands and every stave one shade. The four clock-
frontage casks (belltower_barrels_v2) had real staves but still twenty equal ones and thick black bands.

A real cask (a 53-gallon whiskey barrel is 34.5 in tall, 25 in across the bilge and 21 in at the heads):
- its staves bow on one gentle arc, so near the ends they run in straight at ~12 degrees, not round like a capsule;
- the staves are 2.6-4.4 in wide at the bilge and about 1 in thick, each its own shade, with hairline joints;
- they stand 1.5-1.8 in proud of each head (the chime): their ends are cut square, eased outside and bevelled
  inside, so the head sits recessed in its croze and the staves' thickness shows all round the top;
- the head is four to six boards across, the middle ones widest;
- the hoops are flat mild steel 1.6-2.1 in wide and about 1/16 in thick, riveted at a lapped joint, the head hoops
  driven down near the ends, the quarter hoops a hand's width in, and on most casks a pair at the bilge;
- the paint on the hoops goes to rust, the bottom ones first;
- the bung sits in one stave at the bilge;
- it's never quite round, never quite upright, and no two are alike.

Everything here is drawn only. belltower_map.barrel keeps the old ten-sided collision hull, so cover is unchanged.
Plan inches, z up; build() takes the cask's bottom centre.

Two of the old barrel groups stood their casks into each other (centres 20.6 and 23.9 in apart, for 26 in casks), which
the pill-shaped barrels hid and real staves don't. NUDGED moves the third cask of each group straight away from its
neighbour until they're 27 in apart like the others, hull and all (placed()); both spots were checked clear of the
map's collision.
"""
import argparse
import math
from pathlib import Path
import numpy as np

import belltower_furniture as F

ROOT = Path(__file__).resolve().parents[1]

# One photographed oak (the furniture's brown_planks_03 scan) in five shades, so each stave can be its own.
STAVES = ('barrel_stave_a', 'barrel_stave_b', 'barrel_stave_c', 'barrel_stave_d')
HEAD = 'barrel_head'
HOOP = 'sh_hoop'               # black-painted steel with rust coming through (the Stillhouse map's hoops)
RUST = 'barrel_hoop_rust'      # aged charcoal iron, with scattered brown corrosion and worn steel
ENDGRAIN = 'barrel_endgrain'   # the stave ends: the range's oak end grain, weathered darker
# Each private material is an existing picture set with its own tint, so no new textures.
SCAN = {'TextureColor': 'materials/belltower/scans/brown_planks_03_diffuse_4k.png',
        'TextureNormal': 'materials/belltower/scans/brown_planks_03_nor_gl_4k.png',
        'TextureRoughness': 'materials/belltower/scans/brown_planks_03_rough_4k.png',
        'TextureAmbientOcclusion': 'materials/belltower/scans/brown_planks_03_ao_4k.png'}
SOURCES = {'barrel_stave_a': (SCAN, (1.06, .94, .80), .85), 'barrel_stave_b': (SCAN, (.90, .80, .68), .85),
           'barrel_stave_c': (SCAN, (.79, .77, .73), .9), 'barrel_stave_d': (SCAN, (.66, .57, .47), .85),
           HEAD: (SCAN, (.95, .86, .74), .85),
           ENDGRAIN: ({'TextureColor': 'materials/gunsmith_range/bench_oak_endgrain_color.png',
                       'TextureNormal': 'materials/gunsmith_range/bench_oak_endgrain_normal.png',
                       'TextureRoughness': 'materials/gunsmith_range/bench_oak_endgrain_roughness.png',
                       'TextureAmbientOcclusion': 'materials/default/default_ao.tga'}, (.74, .67, .60), 1),
           RUST: ({'TextureColor': 'materials/stillhouse/sh_hoop_color.png',
                   'TextureNormal': 'materials/stillhouse/hoop_normal.png',
                   'TextureRoughness': 'materials/stillhouse/hoop_rough.png',
                   'TextureAmbientOcclusion': 'materials/default/default_ao.tga'}, (.86, .88, .92), 1)}
MATERIALS = {name: f'materials/belltower/barrels-v3/{name}.vmat' for name in SOURCES}
MATERIALS.update({F.DARK: 'materials/belltower/furniture_wood_dark.vmat', HOOP: 'materials/stillhouse/sh_hoop.vmat'})
HOOP_TILE = 64.0   # sh_hoop and sh_rust are drawn at 8 px an inch on 512 px


# West plan centres: where belltower_map's random draws put the cask, and where it stands now.
NUDGED = {(-1033.096, -486.016): (-1032.1, -479.6), (-1269.11, -582.337): (-1266.9, -584.7)}


def placed(centre):
    """ Where a barrel drawn at centre (west plan) stands. """
    for old, new in NUDGED.items():
        if math.dist(old, centre) < .01:
            return new
    return tuple(centre)


def profile(t, bilge, head):
    """ The staves' outside radius at fraction t of the height: one arc (a parabola) from head to bilge to head. """
    return head + (bilge - head) * (1 - (2 * t - 1) ** 2)


class Cask:
    def __init__(self, r, h, seed):
        rng = self.rng = np.random.default_rng(seed + 50311)
        self.R = r - rng.uniform(.05, .3)                      # stays inside the old render radius
        self.H = h - rng.uniform(0, .9)
        self.Re = self.R * rng.uniform(.83, .87)
        self.T = rng.uniform(.85, 1.0)                         # stave thickness
        self.recess = rng.uniform(1.45, 1.8)                   # head below the stave ends
        # Never quite round: up to 1.2% oval; never quite upright on the cobbles: up to 0.8 degrees.
        e, phi = rng.uniform(.003, .012), rng.uniform(0, math.pi)
        d = np.array((math.cos(phi), math.sin(phi), 0.))
        q = np.array((-d[1], d[0], 0.))
        oval = np.outer(d, d) * (1 + e) + np.outer(q, q) * (1 - e) + np.outer((0, 0, 1), (0, 0, 1))
        lean, towards = math.radians(rng.uniform(0, .8)), rng.uniform(0, math.tau)
        axis = np.array((-math.sin(towards), math.cos(towards), 0.))
        k = np.array(((0, -axis[2], axis[1]), (axis[2], 0, -axis[0]), (-axis[1], axis[0], 0)))
        tilt = np.eye(3) + math.sin(lean) * k + (1 - math.cos(lean)) * (k @ k)
        self.M, self.N = tilt @ oval, tilt

        # Staves of the widths a cooper gets from his wood, 2.6-4.4 in at the bilge.
        count = int(round(math.tau * self.R / rng.uniform(3.1, 3.5)))
        widths = rng.uniform(.75, 1.3, count)
        self.A = rng.uniform(0, math.tau) + np.concatenate(((0.,), np.cumsum(widths))) / widths.sum() * math.tau
        self.count = count
        self.offset = np.clip(rng.normal(0, .016, count), -.035, .035)       # staves not quite flush
        base = int(rng.choice(4, p=(.3, .35, .2, .15)))
        # Mostly the cask's own shade and its neighbours', and now and then a replaced stave of any shade.
        self.tone = [STAVES[int(rng.integers(4)) if rng.random() < .1 else int(np.clip(base + rng.choice((-1, 0, 1)), 0, 3))]
                     for _ in range(count)]
        self.end = self.H + rng.uniform(-.06, .02, count)                    # stave ends not quite level
        self.dip = np.where(rng.random(count) < .18, rng.uniform(.05, .1, count), 0)   # a worn end here and there
        # Where every stave's outside meets its eased end: one height all round, so neighbours share their edges.
        self.top = float((self.end - self.dip).min()) - .05
        self.strip = [F.STRIPS[int(i)] for i in rng.integers(0, len(F.STRIPS), count)]
        self.shift = rng.uniform(0, 1, count)
        self.faces = []

    # ---------------------------------------------------------------------------------------------------------------
    def r(self, z):
        return profile(np.clip(z / self.H, 0, 1), self.R, self.Re)

    def at(self, a, radius, z):
        return np.array((radius * math.cos(a), radius * math.sin(a), z))

    def face(self, paint, points, normal, uv=None, normals=None):
        self.faces.append((paint, points, normal, uv, normals))

    def quad_strip(self, paint, rows, outward, uv=None, normals=None):
        """ Quads between consecutive rows of points (each row the same length); outward(i, j) gives a face normal. """
        for j in range(len(rows) - 1):
            for i in range(len(rows[j]) - 1):
                pts = [rows[j][i], rows[j][i+1], rows[j+1][i+1], rows[j+1][i]]
                self.face(paint, pts, outward(i, j), None if uv is None else
                          [uv[j][i], uv[j][i+1], uv[j+1][i+1], uv[j+1][i]],
                          None if normals is None else [normals[j][i], normals[j][i+1], normals[j+1][i+1], normals[j+1][i]])

    # ---------------------------------------------------------------------------------------------------------------
    def staves(self):
        H, T = self.H, self.T
        levels = (0, .04, .11, .2, .32, .44, .56, .68, .8, .89, .96)
        head_z = H - self.recess
        for s in range(self.count):
            a0, a1 = self.A[s], self.A[s+1]
            left, right = s - 1, (s + 1) % self.count
            o, oj0, oj1 = self.offset[s], min(self.offset[left], self.offset[s]), min(self.offset[s], self.offset[right])
            g0, g1 = .05 / self.R, .05 / self.R                       # the joints' little V
            angles = (a0, a0 + g0, (a0 + a1) / 2, a1 - g1, a1)
            u0, u1 = self.strip[s]
            us = [u0 + (a - a0) / (a1 - a0) * (u1 - u0) for a in angles]
            end_l = min(self.end[left], self.end[s])
            end_r = min(self.end[s], self.end[right])
            end_m = self.end[s] - self.dip[s]
            top = self.top
            zs = [t * H for t in levels if t * H < top - .3] + [top]

            def radii(z, joint_depth):
                base = self.r(z)
                return (base + oj0 - joint_depth, base + o, base + o, base + o, base + oj1 - joint_depth)

            rows, uvs, norms = [], [], []
            for z in zs:
                rad = radii(z, .055)
                rows.append([self.at(a, rr, z) for a, rr in zip(angles, rad)])
                uvs.append([(u, z / F.TILE + self.shift[s]) for u in us])
                slope = (self.r(z + .05) - self.r(z - .05)) / .1
                norms.append([_unit((math.cos(a), math.sin(a), -slope)) for a in angles])
            mid = (a0 + a1) / 2
            # The outside: two facets across the face, and the joints' chamfers in the darker wood.
            for j in range(len(rows) - 1):
                for i in range(4):
                    pts = [rows[j][i], rows[j][i+1], rows[j+1][i+1], rows[j+1][i]]
                    uv = [uvs[j][i], uvs[j][i+1], uvs[j+1][i+1], uvs[j+1][i]]
                    if i in (1, 2):
                        nm = [norms[j][i], norms[j][i+1], norms[j+1][i+1], norms[j+1][i]]
                        self.face(self.tone[s], pts, sum(nm), uv, nm)
                    else:
                        side = (angles[i] + angles[i+1]) / 2
                        self.face(F.DARK, pts, (math.cos(side), math.sin(side), 0), uv)

            # Over the end: eased outside edge, square-cut end grain, the inside bevel and the inside down to the head.
            ends = (end_l, end_m, end_m, end_m, end_r)
            ro = [self.r(e) for e in ends]
            joint_off = (oj0, o, o, o, oj1)
            sections = [
                [self.at(a, rr, top) for a, rr in zip(angles, radii(top, .055))],
                [self.at(a, r0 + jo - .07, e) for a, r0, jo, e in zip(angles, ro, joint_off, ends)],
                [self.at(a, r0 + jo - .45, e) for a, r0, jo, e in zip(angles, ro, joint_off, ends)],
                [self.at(a, self.r(e - .6) + jo - T, e - .6) for a, jo, e in zip(angles, joint_off, ends)],
                [self.at(a, self.r(head_z - .12) + jo - T, head_z - .12) for a, jo in zip(angles, joint_off)],
            ]
            # Ease: outward and up; end grain: up; bevel and inside: towards the axis.
            ease = lambda i, j: (math.cos(mid), math.sin(mid), 1)
            self.quad_strip(self.tone[s], sections[0:2], ease,
                            uv=[[(u, sections[0][0][2] / F.TILE + self.shift[s]) for u in us],
                                [(u, (sections[0][0][2] + .1) / F.TILE + self.shift[s]) for u in us]])
            self.quad_strip(ENDGRAIN, sections[1:3], lambda i, j: (0, 0, 1))
            inward = lambda i, j: (-math.cos(mid), -math.sin(mid), .4 if j == 0 else 0)
            rows_in = sections[2:5]
            self.quad_strip(F.DARK, rows_in, inward,
                            uv=[[(u, p[2] / F.TILE + self.shift[s]) for u, p in zip(us, row)] for row in rows_in])

    def bottom(self):
        """ The underside, so a cask resting a little tilted on the cobbles shows no light under its chime. """
        ring = [self.at(-k * math.tau / 24, self.r(0) - .02, .02) for k in range(24)]
        self.face(F.DARK, ring, (0, 0, -1))

    def head(self):
        """ The head: boards across, the middle ones widest, recessed in the croze. Its rim runs under the staves. """
        rng = self.rng
        z = self.H - self.recess
        rh = self.r(z) - self.T + .08
        n = int(rng.choice((4, 5, 5, 6)))
        widths = rng.uniform(.8, 1.2, n) * (1.0 - .35 * np.abs(np.linspace(-1, 1, n)) ** 2)
        edges = -rh + np.concatenate(((0.,), np.cumsum(widths))) / widths.sum() * 2 * rh
        turn = rng.uniform(0, math.pi)
        c, s = math.cos(turn), math.sin(turn)
        rot = lambda x, y, zz: np.array((x * c - y * s, x * s + y * c, zz))
        for b in range(n):
            x0, x1 = edges[b], edges[b+1]
            ia = .035 if b > 0 else 0
            ib = .035 if b < n - 1 else 0
            dz = rng.uniform(-.03, .03)
            xa, xb = x0 + ia, x1 - ib
            xs = np.linspace(xa, xb, 6)
            half = lambda x: math.sqrt(max(0., rh * rh - x * x))
            outline = [(x, -half(x)) for x in xs] + [(x, half(x)) for x in xs[::-1]]
            u0, u1 = F.STRIPS[int(rng.integers(len(F.STRIPS)))]
            v0 = rng.uniform(0, 1)
            pts = [rot(x, y, z + dz) for x, y in outline]
            uv = [(u0 + (x - xa) / max(xb - xa, 1e-6) * (u1 - u0), y / F.TILE + v0) for x, y in outline]
            self.face(HEAD, pts, (0, 0, 1), uv)
            # The joints' chamfers, down to the joint line.
            for x_edge, x_in, inset in ((x0, xa, ia), (x1, xb, ib)):
                if not inset:
                    continue
                y_in, y_edge = half(x_in), half(x_edge)
                quad = [rot(x_in, -y_in, z + dz), rot(x_in, y_in, z + dz), rot(x_edge, y_edge, z - .05),
                        rot(x_edge, -y_edge, z - .05)]
                sign = -1 if x_edge < x_in else 1
                self.face(F.DARK, quad, rot(sign, 0, 1))

    def hoops(self):
        rng, H = self.rng, self.H
        six = rng.random() < .65
        rust = int(rng.choice(3, p=(.35, .4, .25)))       # 0 painted, 1 the bottom ones rusted, 2 all rusted
        bands = []
        w_head, w_quarter = rng.uniform(1.85, 2.1), rng.uniform(1.6, 1.8)
        top_head, top_quarter = rng.uniform(.65, .95), rng.uniform(5.4, 6.4)
        bands += [(H - top_head - w_head, w_head, 'head'), (rng.uniform(.6, .9), w_head, 'head'),
                  (H - top_quarter - w_quarter, w_quarter, 'quarter'), (rng.uniform(5.2, 6.2), w_quarter, 'quarter')]
        if six:
            w_bilge, gap = rng.uniform(1.6, 1.8), rng.uniform(4.0, 4.8)
            bands += [(H / 2 + gap - w_bilge / 2, w_bilge, 'bilge'), (H / 2 - gap - w_bilge / 2, w_bilge, 'bilge')]
        segments = 48
        thick = .07
        for z0, width, kind in bands:
            low = z0 < H / 2
            paint = RUST if rust == 2 or (rust == 1 and low and kind != 'bilge') else HOOP
            tilt, towards = rng.uniform(0, .007), rng.uniform(0, math.tau)    # never driven quite square
            phase = rng.uniform(0, 1)
            lift = lambda a: tilt * self.R * math.cos(a - towards)
            rows_in, rows_out, uv_out, norms = [[], []], [[], []], [[], []], [[], []]
            for k in range(segments + 1):
                a = k * math.tau / segments
                for side, z in enumerate((z0, z0 + width)):
                    zz = z + lift(a)
                    base = self.r(zz) + .05
                    rows_in[side].append(self.at(a, base, zz))
                    rows_out[side].append(self.at(a, base + thick, zz))
                    uv_out[side].append((a * self.R / HOOP_TILE + phase, zz / HOOP_TILE))
                    slope = (self.r(zz + .05) - self.r(zz - .05)) / .1
                    norms[side].append(_unit((math.cos(a), math.sin(a), -slope)))
            for k in range(segments):
                a = (k + .5) * math.tau / segments
                radial = (math.cos(a), math.sin(a), 0)
                pts = [rows_out[0][k], rows_out[0][k+1], rows_out[1][k+1], rows_out[1][k]]
                nm = [norms[0][k], norms[0][k+1], norms[1][k+1], norms[1][k]]
                self.face(paint, pts, sum(nm), [uv_out[0][k], uv_out[0][k+1], uv_out[1][k+1], uv_out[1][k]], nm)
                self.face(paint, [rows_in[1][k], rows_in[1][k+1], rows_out[1][k+1], rows_out[1][k]], (0, 0, 1))
                self.face(paint, [rows_in[0][k], rows_in[0][k+1], rows_out[0][k+1], rows_out[0][k]], (0, 0, -1))
            # The riveted lap: a second thickness of strap for two inches, and two domed rivets through it.
            a = rng.uniform(0, math.tau)
            zc = z0 + width / 2 + lift(a)
            normal = np.array((math.cos(a), math.sin(a), 0.))
            tangent = np.array((-normal[1], normal[0], 0.))
            rr = self.r(zc) + .05 + thick
            self.parts.append(('lap', paint, self.at(a, rr + thick / 2, zc), (tangent, normal, (0, 0, 1)), (2.1, thick, width)))
            for dz in (-.22, .22):
                for du in (-.55, .55):
                    if dz > 0 and du > 0 or dz < 0 and du < 0:
                        self.parts.append(('rivet', paint, self.at(a, rr + thick, zc + dz * width) + tangent * du, normal, tangent))

    def bung(self):
        s = int(self.rng.integers(self.count))
        a = (self.A[s] + self.A[s+1]) / 2
        z = self.H / 2 + self.rng.uniform(-.6, .6)
        normal = np.array((math.cos(a), math.sin(a), 0.))
        self.parts.append(('bung', None, self.at(a, self.r(z) + self.offset[s] - .06, z), normal,
                           np.array((-normal[1], normal[0], 0.))))

    # ---------------------------------------------------------------------------------------------------------------
    def emit(self, model, centre, z):
        self.parts = []
        self.staves()
        self.bottom()
        self.head()
        self.hoops()
        self.bung()
        origin = np.array((centre[0], centre[1], z), float)
        place = lambda p: origin + self.M @ np.asarray(p, float)
        turn = lambda n: self.N @ np.asarray(n, float)
        for paint, points, normal, uv, normals in self.faces:
            F.face(model, paint, [place(p) for p in points], turn(normal), uv,
                   None if normals is None else [_unit(turn(n)) for n in normals])
        for part in self.parts:
            if part[0] == 'lap':
                _, paint, at, axes, size = part
                F.bevel_box(model, place(at), [turn(v) for v in axes], size, paint, .02)
            elif part[0] == 'rivet':
                _, paint, at, normal, tangent = part
                F.turned(model, place(at), turn(normal), turn(tangent), [(.15, -.02), (.16, .02), (.11, .07), (.03, .09)],
                         paint, 8)
            else:
                _, _, at, normal, tangent = part
                F.turned(model, place(at), turn(normal), turn(tangent), [(.66, 0), (.66, .1), (.6, .15)], ENDGRAIN, 16)
        return model


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def seed_for(centre):
    """ The same cask for the same place, whichever tool builds it. """
    return (int(round(centre[0] * 7)) * 73856093 ^ int(round(centre[1] * 7)) * 19349663) & 0x7fffffff


def build(model, centre, z=0., r=13., h=36., seed=None):
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({F.DARK: F.TILE, ENDGRAIN: 18, HOOP: HOOP_TILE, RUST: 32, **{n: F.TILE for n in (*STAVES, HEAD)}})
    return Cask(r, h, seed_for(centre) if seed is None else seed).emit(model, centre, z)


def vmat(name):
    textures, t, rough = SOURCES[name]
    lines = ['// Tools/belltower_barrels_v3.py: an existing picture set in its own tint', '"Layer0"', '{',
             '    shader "shaders/complex.shader"', '    F_SPECULAR "1"']
    lines += [f'    {key} "{path}"' for key, path in textures.items()]
    lines += [f'    g_vColorTint "[{t[0]:.2f} {t[1]:.2f} {t[2]:.2f} 1]"', f'    g_flRoughnessScaleFactor "{rough}"',
              '    g_flModelTintAmount "1"', f'    g_flMetalness "{.40 if name == RUST else 0}"', '}']
    return '\n'.join(lines) + '\n'


def write_materials(out):
    folder = Path(out) / 'Assets/materials/belltower/barrels-v3'
    folder.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        (folder / f'{name}.vmat').write_text(vmat(name), newline='\r\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--materials', help='write the stave materials under this folder, laid out as the project')
    args = parser.parse_args()
    if args.materials:
        write_materials(args.materials)
