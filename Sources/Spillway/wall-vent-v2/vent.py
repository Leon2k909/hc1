"""Folded sheet-metal turbine hall wall vent. Blender -- <work> <root> build bake export.

Local X across the face, -Y out from the wall, Z up; origin at bottom centre against the wall.
100 x 93 in body, 24 in projection. Shared pallet pipeline handles bakes, UVs, LOD and OBJ conventions.
"""
import inspect
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Matrix

WORK, ROOT, *STAGES = sys.argv[sys.argv.index('--') + 1:]
original = sys.argv[:]
sys.argv = [sys.argv[0], '--', WORK, ROOT]
sys.path.insert(0, os.path.join(ROOT, 'Sources/Spillway/cargo-props-v2'))
import pallet as pipe
sys.argv = original
kit = pipe.kit
pipe.NAME = 'wall_vent'
pipe.FOLDER = 'models/maps/spillway/wall_vent_v2'
pipe.OUT = os.path.join(ROOT, 'Assets', pipe.FOLDER)
pipe.BLEND = os.path.join(WORK, 'vent_build.blend')
pipe.POS_RANGE = 256.0
PAINT, ALLOY, STEEL, BLACK, PLATE = range(5)
bolt_positions = []


def part(finish, lod=3, bevel=.035, name=''):
    return kit.add(kit.Part(finish, lod, bevel=bevel, segs=1, name=name))


def box(finish, low, high, lod=3, bevel=.06, name=''):
    kit.box(part(finish, lod, bevel, name), low, high)


def blade(x0, x1, z):
    # Cross section (depth, height) of a folded drainable blade: outward drip and upturned rear edge.
    outline = [(-21.8, z - .6), (-21.8, z + .35), (-20.1, z + .65), (-9.1, z + 6.1),
               (-8.9, z + 6.9), (-8.8, z + 6.9), (-9.0, z + 6.04), (-20.06, z + .55),
               (-21.7, z + .27), (-21.7, z - .6)]
    # local 2D XY is world YZ; extrusion Z is world X. Cyclic permutation keeps winding.
    transform = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
    kit.prism(part(ALLOY, 3, bevel=0, name='folded blade'), outline, x0, x1, transform)


def geometry():
    # Separate folded body panels leave an actual cavity behind the louvres.
    box(PAINT, (-50, -21.5, 0), (-48.7, 0, 93), name='left cheek')
    box(PAINT, (48.7, -21.5, 0), (50, 0, 93), name='right cheek')
    box(PAINT, (-48.7, -21.5, 0), (48.7, 0, 1.3), name='bottom pan')
    box(PAINT, (-48.7, -21.5, 91.7), (48.7, 0, 93), name='top panel')
    box(BLACK, (-48.7, -5.1, 1.3), (48.7, -4.9, 91.7), bevel=.01, name='dark plenum')
    # Plain access panels below and above the removable louvre cassette.
    box(PAINT, (-48.7, -21.5, 1.3), (48.7, -20.7, 14.6), name='lower access panel')
    box(PAINT, (-48.7, -21.5, 83.9), (48.7, -20.7, 91.7), name='top panel face')
    # Four channel rails and a central mullion; front return lips catch the light.
    for x0, x1 in [(-48.7, -43.5), (43.5, 48.7)]:
        box(PAINT, (x0, -23.6, 14.4), (x1, -20.2, 84.1), bevel=.09, name='cassette upright')
    box(PAINT, (-1.4, -23.6, 18), (1.4, -20.2, 81), bevel=.09, name='centre mullion')
    for z0, z1 in [(14.4, 18), (81, 84.1)]:
        box(PAINT, (-43.5, -23.6, z0), (43.5, -20.2, z1), bevel=.09, name='cassette horizontal')
    # Eight slightly overlapping blades per bank, seated into the channels.
    for k in range(8):
        z = 18 + k * 8
        blade(-43.5, -1.45, z)
        blade(1.45, 43.5, z)
    # A projecting rain cap with a small turned-down front edge.
    box(PAINT, (-50.5, -24, 92.9), (50.5, .5, 93.6), bevel=.08, name='rain cap')
    box(PAINT, (-50.5, -24, 91.8), (50.5, -23.3, 92.9), bevel=.06, name='cap drip')
    # Backing mesh has geometry only at close range; the black plenum persists at every LOD.
    for z in range(20, 81, 4):
        kit.tube(part(STEEL, 1, bevel=0, name='screen horizontal'), [(-43.5, -7, z), (43.5, -7, z)], .055, 4)
    for x in range(-40, 44, 4):
        kit.tube(part(STEEL, 1, bevel=0, name='screen vertical'), [(x, -7, 18), (x, -7, 82)], .055, 4)
    # Captive fasteners on the flange and access panels, including two on the centre mullion.
    for x, z in [(x, z) for x in (-46, 46) for z in (18, 39, 61, 80)] + [(0, 20), (0, 79)] + [(x, z) for x in (-43, 43) for z in (7, 88)]:
        y = -23.7 if 14 < z < 84 else -21.6
        kit.hex_bolt((x, y, z), (0, -1, 0), .74, lod=1, finish=STEEL)
        bolt_positions.append([x, y, z])
    box(PLATE, (20, -21.75, 5), (39, -21.55, 10.5), lod=2, bevel=.04, name='asset plate')


pipe.geometry = geometry
# The AO occluder is the wall behind the vent rather than the shared pipeline's pallet floor.
bake_code = inspect.getsource(pipe.bake_stage)
floor = '[(-80, -80, 0), (80, -80, 0), (80, 80, 0), (-80, 80, 0)]'
assert bake_code.count(floor) == 1
bake_code = bake_code.replace(floor, '[(-90, .1, -20), (90, .1, -20), (90, .1, 120), (-90, .1, 120)]')
exec(compile(bake_code, '<shared-bake-with-wall>', 'exec'), pipe.__dict__)
if 'build' in STAGES:
    pipe.build_stage()
    np.save(os.path.join(WORK, 'vent_bolts.npy'), np.asarray(bolt_positions))
    with open(os.path.join(WORK, 'vent_parts.json'), 'w') as out:
        json.dump([dict(name=p.name, triangles=len(p.done.faces)) for p in kit.parts], out, indent=2)
if 'bake' in STAGES:
    pipe.bake_stage()
if 'export' in STAGES:
    pipe.export_stage()
    path = os.path.join(pipe.OUT, 'wall_vent.vmdl')
    doc = open(path, encoding='utf-8').read()
    doc, removed = re.subn(r'\t\t\t\{\n\t\t\t\t_class = "PhysicsShapeList"\n.*?\n\t\t\t\},\n', '', doc, flags=re.S)
    assert removed == 1
    doc = doc.replace('Sources/Spillway/cargo-props-v2/pallet.py', 'Sources/Spillway/wall-vent-v2/vent.py (shared mesh pipeline)')
    with open(path, 'w', encoding='utf-8', newline='\n') as out:
        out.write(doc)
print('vent stages done', flush=True)
