"""Lowtide's mooring bollard v2: build, bake and export.

blender -b --factory-startup -t 4 --python bollard.py -- <work dir> <project root> <build|bake|export> ...

A cast-iron quay bollard inside the same box as `lowtide_map.mooring_bollard` (9 in round, 25 high), on the same origin at the ground: a flanged
foot held down by six bolts, a waisted neck for the ropes, and a flared, domed head. Being round, it can face any way. Inches, engine axes (Z up).
"""
import math
import os
import sys

sys.dont_write_bytecode = True

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
STAGES = argv[2:]
os.makedirs(WORK, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Sources", "Gameplay", "capture-flag-v2"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as kit  # noqa: E402
import prop_stages as stages  # noqa: E402

from build import Part, add, frame, lathe  # noqa: E402

PAINT, ZINC = kit.PAINT, kit.ZINC
NAME = "mooring_bollard"
FOLDER = "models/maps/lowtide/mooring_bollard_v2"
OUT = os.path.join(ROOT, "Assets", "models", "maps", "lowtide", "mooring_bollard_v2")
RES, RANGE = 1024, 64.0
BOLTS = 6
FLANGE_TOP = 1.35


def geometry():
    casting = add(Part(PAINT, 3, bevel=0.0, name="casting"))
    profile = [(8.72, 0.0), (8.98, 0.1), (9.0, FLANGE_TOP - 0.22), (8.82, FLANGE_TOP), (7.6, FLANGE_TOP + 0.12), (7.05, 2.25), (6.72, 3.5), (6.42, 5.4), (6.2, 8.0), (6.08, 11.0), (6.06, 14.0), (6.2, 16.6), (6.5, 18.4), (7.1, 19.5), (8.12, 20.3), (8.46, 21.0), (8.5, 22.0), (8.5, 23.2), (8.36, 23.9), (7.7, 24.5), (6.0, 24.82), (3.2, 24.98), (0.0, 25.0)]
    lathe(casting, profile, 48)
    for k in range(BOLTS):
        a = 2 * math.pi * (k + 0.5) / BOLTS
        kit.hex_bolt((7.95 * math.cos(a), 7.95 * math.sin(a), FLANGE_TOP - 0.06), (0, 0, 1), size=0.82, lod=1, washer=True, finish=ZINC)


if "build" in STAGES:
    stages.build_stage(kit, NAME, WORK, RES, RANGE, geometry, (PAINT,), ((1, 0.5), (3, 0.22)), 3, dict(flange=FLANGE_TOP, bolts=BOLTS))
if "bake" in STAGES:
    stages.bake_stage(NAME, WORK, RES, RANGE, 5.0)
if "export" in STAGES:
    stages.export_stage(NAME, WORK, OUT, FOLDER, ("",), (0.0, 30.0, 80.0), "Sources/Lowtide/mooring_bollard_v2/bollard.py")
print("bollard stages done", flush=True)
