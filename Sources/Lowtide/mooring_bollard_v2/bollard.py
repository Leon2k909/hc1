"""Lowtide's mooring bollard v2: build, bake and export.

blender -b --factory-startup -t 4 --python bollard.py -- <work dir> <project root> <build|bake|export> ...

A cast-iron quay bollard inside the same box as `lowtide_map.mooring_bollard` (9 in round, 25 high), on the same origin at the ground: a flanged
foot held down by six bolts, a waisted neck for the ropes, and a flared, domed head. Being round, it can face any way. Inches, engine axes (Z up).
"""
import math
import os
import sys

import numpy as np
from mathutils import Vector

sys.dont_write_bytecode = True

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as kit  # noqa: E402
import prop_stages as stages  # noqa: E402

from build import Part, add, frame, lathe, spline, tube  # noqa: E402

PAINT, ZINC = kit.PAINT, kit.ZINC
ROPE = 9
NAME = "mooring_bollard"
FOLDER = "models/maps/lowtide/mooring_bollard_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "lowtide", "mooring_bollard_v2")
RES, RANGE = 2048, 64.0
BOLTS = 6
FLANGE_TOP = 1.35


def rope_wrap():
    # A short discarded line, with its upper end tucked beneath the first turn.
    # Follow the casting's waist so the line rests against it instead of floating.
    waist = [(3.5, 6.72), (5.4, 6.42), (8.0, 6.2), (11.0, 6.08), (14.0, 6.06)]
    path = []
    for t in np.linspace(0, 1, 169):
        z = 12.4 - 3.3 * t
        a = 0.7 + 7 * math.pi * t
        radius = float(np.interp(z, *zip(*waist))) + 0.27
        path.append(Vector((radius * math.cos(a), radius * math.sin(a), z)))
    end_angle = 0.7 + 7 * math.pi
    tail = [path[-1]]
    for radius, z, turn in ((6.58, 8.1, 0.03), (6.7, 6.4, 0.10), (6.96, 4.5, 0.17),
                            (7.35, 2.8, 0.24), (8.15, 1.8, 0.31)):
        tail.append(Vector((radius*math.cos(end_angle+turn), radius*math.sin(end_angle+turn), z)))
    path.extend(spline(tail, 3)[1:])
    tube(add(Part(ROPE, 3, name="laid mooring line")), path, 0.31, 8)
    # Loose fibres at the cut end, inside the existing flange's footprint.
    end = path[-1]
    along = (path[-1] - path[-2]).normalized()
    across = along.cross(Vector((0, 0, 1))).normalized()
    up = across.cross(along).normalized()
    for k in range(7):
        a = k * 2 * math.pi / 7
        spread = across * math.cos(a) + up * math.sin(a)
        start = end + spread * 0.13
        fibre = spline([start, start+along*0.2+spread*0.05,
                        start+along*(0.35+0.03*k)+spread*0.14+Vector((0, 0, -0.08))], 2)
        tube(add(Part(ROPE, 0, name="cut rope fibres")), fibre, [0.04, 0.035, 0.03, 0.02, 0.008], 5)
    np.save(os.path.join(WORK, f"{NAME}_rope.npy"), np.array(path, np.float32))


def geometry():
    casting = add(Part(PAINT, 3, bevel=0.0, name="casting"))
    profile = [(8.72, 0.0), (8.98, 0.1), (9.0, FLANGE_TOP - 0.22), (8.82, FLANGE_TOP), (7.6, FLANGE_TOP + 0.12), (7.05, 2.25), (6.72, 3.5), (6.42, 5.4), (6.2, 8.0), (6.08, 11.0), (6.06, 14.0), (6.2, 16.6), (6.5, 18.4), (7.1, 19.5), (8.12, 20.3), (8.46, 21.0), (8.5, 22.0), (8.5, 23.2), (8.36, 23.9), (7.7, 24.5), (6.0, 24.82), (3.2, 24.98), (0.0, 25.0)]
    lathe(casting, profile, 48)
    for k in range(BOLTS):
        a = 2 * math.pi * (k + 0.5) / BOLTS
        kit.hex_bolt((7.95 * math.cos(a), 7.95 * math.sin(a), FLANGE_TOP - 0.06), (0, 0, 1), size=0.82, lod=1, washer=True, finish=ZINC)
    rope_wrap()


if "build" in STAGES:
    stages.build_stage(kit, NAME, WORK, RES, RANGE, geometry, (PAINT,), ((1, 0.5), (3, 0.22)), 3, dict(flange=FLANGE_TOP, bolts=BOLTS))
if "bake" in STAGES:
    stages.bake_stage(NAME, WORK, RES, RANGE, 5.0)
if "export" in STAGES:
    stages.export_stage(NAME, WORK, OUT, FOLDER, ("",), (0.0, 30.0, 80.0), "Sources/Lowtide/mooring_bollard_v2/bollard.py")
if "export-meshes" in STAGES:
    stages.export_stage(NAME, WORK, OUT, FOLDER, ("",), (0.0, 30.0, 80.0), "Sources/Lowtide/mooring_bollard_v2/bollard.py", write_resources=False)
print("bollard stages done", flush=True)
