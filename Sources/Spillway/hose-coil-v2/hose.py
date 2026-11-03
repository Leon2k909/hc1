"""Continuous yard hose with two open cam couplings. Blender: -- <work> <root> build bake export.

Engine inches and axes, origin on the floor. Local X follows plan north, local Y follows -east.
Reuses the pallet's verified UV, bake and OBJ pipeline; intermediate Blender objects retain its internal prefix.
"""
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
import bmesh
import bpy
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
WORK, ROOT, *STAGES = args
sys.path.insert(0, os.path.join(ROOT, 'Sources/Spillway/cargo-props-v2'))
original_argv = sys.argv[:]
sys.argv = [sys.argv[0], '--', WORK, ROOT]
import pallet as pipe
sys.argv = original_argv
kit = pipe.kit
pipe.NAME = 'hose_coil'
pipe.FOLDER = 'models/maps/spillway/hose_coil_v2'
pipe.OUT = os.path.join(ROOT, 'Assets', pipe.FOLDER)
pipe.BLEND = os.path.join(WORK, 'hose_build.blend')
pipe.POS_RANGE = 160.0
pipe.RES = 2048
RUBBER, ALLOY, STEEL, LABEL, GASKET = range(5)
path_record = []


def part(finish, lod=3, bevel=0, name=''):
    return kit.add(kit.Part(finish, lod, bevel=bevel, segs=1, angle=35, name=name))


def shell(p, profile, sides, transform):
    """Closed radial section, including the bore; no disk across the hose opening."""
    rings = [[p.bm.verts.new(transform @ Vector((r * math.cos(a), r * math.sin(a), z)))
              for a in np.linspace(0, 2 * math.pi, sides, endpoint=False)] for r, z in profile]
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for k in range(sides):
            p.bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))


def coupling(at, axis, female):
    m = kit.frame(at, axis)
    # Crimp sleeve ends in a real rolled lip. Rubber continues inside it, away from the mouth.
    shell(part(ALLOY, bevel=.025, name='crimp ferrule'),
          [(1.21, -.8), (1.34, -.65), (1.36, 1.5), (1.29, 1.7), (1.01, 1.7), (1.01, -.8)], 24, m)
    for z in (-.3, .35, 1.0):
        shell(part(ALLOY, 1, name='crimp shoulder'),
              [(1.35, z), (1.4, z + .07), (1.4, z + .2), (1.35, z + .27)], 24, m)
    if female:
        profile = [(1.29, 1.45), (1.69, 1.8), (1.76, 2.1), (1.76, 4.2), (1.9, 4.3),
                   (1.9, 4.6), (1.79, 4.75), (1.35, 4.75), (1.3, 4.45), (1.3, 2.0), (1.0, 1.7)]
    else:
        profile = [(1.29, 1.45), (1.49, 1.8), (1.49, 2.2), (1.36, 2.3), (1.36, 2.75),
                   (1.55, 2.9), (1.55, 4.2), (1.42, 4.55), (1.07, 4.55), (1.0, 4.3), (1.0, 1.7)]
    shell(part(ALLOY, bevel=.025, name='female socket' if female else 'male adapter'), profile, 32, m)
    shell(part(GASKET, name='bore lining'), [(1.01, -.5), (1.01, 2.1), (.88, 2.1), (.88, -.5)], 20, m)
    if female:
        shell(part(GASKET, 1, name='socket seal'), [(1.31, 2.6), (1.31, 2.85), (1.12, 2.85), (1.12, 2.6)], 24, m)
        # Folded cam arms on opposing sides, hinge ears and pins. Closed so nothing sticks up into a player's path.
        for sign in (-1, 1):
            p = part(ALLOY, 2, bevel=.04, name='cam lever')
            kit.box(p, (sign * 1.65 - .18, -.32, 2.35), (sign * 1.65 + .18, .32, 3.15), m)
            kit.box(p, (sign * 1.85 - .11, -.24, .35), (sign * 1.85 + .11, .24, 2.95), m)
            ring = kit.frame(m @ Vector((sign * 1.85, 0, .45)), m.to_3x3() @ Vector((1, 0, 0)))
            kit.tube(part(STEEL, 1, name='retaining ring'), kit.ring_path(.31, 14, ring), .045, 5, closed=True)
            pin = kit.frame(m @ Vector((sign * 1.82, 0, 2.85)), m.to_3x3() @ Vector((1, 0, 0)))
            kit.lathe(part(STEEL, 2, name='hinge pin'), [(.17, -.23), (.17, .23)], 10, pin)


def bezier(a, b, c, d, count):
    return [(1 - t)**3 * a + 3 * (1 - t)**2 * t * b + 3 * (1 - t) * t*t * c + t**3 * d
            for t in map(float, np.linspace(0, 1, count, endpoint=False))]


def geometry():
    turns, steps = 2.65, 300
    angles = np.linspace(-math.pi * .4, -math.pi * .4 + turns * 2 * math.pi, steps)
    points = []
    for k, angle in enumerate(angles):
        turn = k / (steps - 1) * turns
        rx, ry = 25 - 3.5 * turn, 49 - 3.5 * turn
        # Slight unevenness in how a real stiff hose settles, without the regular joints of the old rods.
        points.append(Vector((rx * math.cos(angle) + .34 * math.sin(angle * 2.3),
                              ry * math.sin(angle) + .32 * math.sin(angle * 1.7),
                              1.3 + .08 * (1 + math.sin(angle * 1.2)))))
    tangent = (points[1] - points[0]).normalized()
    start = Vector((-13, -44, 1.95))
    lead = bezier(start, Vector((-5, -47, 1.7)), points[0] - tangent * 6, points[0], 24)
    end_tangent = (points[-1] - points[-2]).normalized()
    tail = bezier(points[-1], points[-1] + end_tangent * 12, Vector((-11, -18, 1.4)), Vector((4, -16, 1.95)), 42)
    path = lead + points + tail[1:] + [Vector((4, -16, 1.95))]
    # Slight flattening at the floor; minimum underside stays above z=0.
    radii = [1.2 * (1 + .012 * math.sin(k * .28)) for k in range(len(path))]
    kit.tube(part(RUBBER, name='one continuous hose'), path, radii, 14, caps=False, flatten=.96)
    for endpoint, axis, female in ((path[0], path[0] - path[1], True), (path[-1], path[-1] - path[-2], False)):
        axis.z = 0
        coupling(endpoint, axis.normalized(), female)
    # A short faded yellow identification wrap on the outer turn.
    segment = points[41:48]
    kit.tube(part(LABEL, 2, name='identification wrap'), segment, 1.225, 14, caps=False, flatten=.96)
    global path_record
    path_record = [list(p) for p in path]


pipe.geometry = geometry
original_pack = kit.pack_real_scale


def pack_hose(mesh, res, pad):
    """Unroll the hose in short strips, with seams underneath; keep the shared unwrap for metal fittings."""
    points = np.asarray(path_record)
    lengths = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    count = len(points) * 14
    uv = mesh.uv_layers.active.data
    for poly in mesh.polygons:
        indices = list(poly.vertices)
        if not all(i < count for i in indices):
            continue
        rings = [i // 14 for i in indices]
        origin = min(rings) // 20 * 20
        across = [((i % 14 - 4) % 14) / 14 for i in indices]
        if max(across) - min(across) > .5:
            across = [v + 1 if v < .5 else v for v in across]
        for loop, ring, v in zip(poly.loop_indices, rings, across):
            uv[loop].uv = (lengths[ring] - lengths[origin], v * 2 * math.pi * 1.2)
    original_pack(mesh, res, pad)


kit.pack_real_scale = pack_hose
if 'build' in STAGES:
    pipe.build_stage()
    np.save(os.path.join(WORK, 'hose_path.npy'), np.asarray(path_record, np.float32))
    # Keep descriptive model metadata beside the generic pipeline's bake facts.
    mesh = bpy.data.objects['pallet_lod0'].data
    coords = np.asarray([tuple(v.co) for v in mesh.vertices])
    with open(os.path.join(WORK, 'hose.json'), 'w') as out:
        json.dump(dict(bounds=[coords.min(0).tolist(), coords.max(0).tolist()],
                       continuous_hose=True, couplings=2, collision=False,
                       length_inches=float(np.linalg.norm(np.diff(path_record, axis=0), axis=1).sum())), out, indent=2)
if 'bake' in STAGES:
    pipe.bake_stage()
if 'export' in STAGES:
    pipe.export_stage()
    path = os.path.join(pipe.OUT, 'hose_coil.vmdl')
    doc = open(path, encoding='utf-8').read()
    doc, removed = re.subn(r'\t\t\t\{\n\t\t\t\t_class = "PhysicsShapeList"\n.*?\n\t\t\t\},\n', '', doc, flags=re.S)
    assert removed == 1, 'The generic pipeline physics block changed; do not export a pallet collider on a hose.'
    doc = doc.replace('Sources/Spillway/cargo-props-v2/pallet.py', 'Sources/Spillway/hose-coil-v2/hose.py (shared pallet mesh pipeline)')
    with open(path, 'w', encoding='utf-8', newline='\n') as out:
        out.write(doc)
print('hose stages done', flush=True)
