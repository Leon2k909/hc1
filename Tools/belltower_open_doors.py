"""Town Hall's north entrances: weathered timber leaves held open on their hinges.

This is an independent visual model. It adds no collision or moving-door logic,
and does not replace any of the shared town meshes. Coordinates are map plan
inches (east, north, up), as in belltower_map.py.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import belltower_furniture as F
import belltower_detail as Detail
import map_kit as K

NAME = "belltower_open_doors"
RESOURCE_DIR = "models/maps/belltower"
ENTRANCES = (-260.0, 260.0)
OPENING_WIDTH = 56.0
OPENING_HEIGHT = 100.0
OPEN_ANGLE = 165.0
WIDTH = 27.45
BOTTOM, TOP = 1.0, 98.6
WOOD = F.WOOD
IRON = F.IRON
BRASS = "door_brass"


def leaf(model, origin, hand, seed):
    """A real, closed timber assembly with matching joinery on both faces."""
    angle = math.radians(OPEN_ANGLE * hand)
    along = np.array((hand * math.cos(angle), hand * math.sin(angle), 0.0))
    across = np.array((-along[1], along[0], 0.0))
    up = np.array((0.0, 0.0, 1.0))
    origin = np.asarray(origin, float)
    axes = (along, across, up)

    def at(x, y, z):
        return origin + along * x + across * y + up * z

    def timber(x0, x1, y0, y1, z0, z1, extra=0, bevel=.10):
        F.bevel_box(model, at((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), axes,
                    (x1-x0, y1-y0, z1-z0), WOOD, bevel, seed+extra)

    # Separate stiles and rails keep grain aligned with each piece of timber.
    stile = 3.6
    timber(.08, stile, -.9, .9, BOTTOM, TOP, 1)
    timber(WIDTH-stile, WIDTH-.08, -.9, .9, BOTTOM, TOP, 2)
    for index, (low, high) in enumerate(((BOTTOM, 9.4), (38.2, 45.4), (93.2, TOP))):
        timber(stile, WIDTH-stile, -.9, .9, low, high, 3+index)

    for index, (low, high) in enumerate(((9.4, 38.2), (45.4, 93.2))):
        # Recessed solid panels and narrow planted beads cast their own shadows.
        # Five joined boards retain the photograph's real plank width; mapping
        # one narrow scan strip across a whole panel would stretch the grain.
        panel_left, panel_right = stile-.03, WIDTH-stile+.03
        for board in range(5):
            x0 = panel_left + (panel_right-panel_left)*board/5
            x1 = panel_left + (panel_right-panel_left)*(board+1)/5
            timber(x0+.008, x1-.008, -.38, .38, low-.03, high+.03,
                   9+index*7+board, bevel=.025)
        for side in (-1, 1):
            y0, y1 = sorted((side*.35, side*.78))
            for x0, x1 in ((stile, stile+.48), (WIDTH-stile-.48, WIDTH-stile)):
                timber(x0, x1, y0, y1, low, high, 15+index, bevel=.12)
            for z0, z1 in ((low, low+.48), (high-.48, high)):
                timber(stile+.48, WIDTH-stile-.48, y0, y1, z0, z1,
                       20+index, bevel=.12)

    # A compact latch on both faces, attached at realistic hand height.
    for side in (-1, 1):
        normal = across * side
        F.bevel_box(model, at(WIDTH-1.85, side*.96, 41.9), axes,
                    (1.05, .12, 5.5), BRASS, .10)
        F.turned(model, at(WIDTH-1.85, side*1.02, 42.5), normal, up,
                 [(.55, 0), (.55, .15), (.25, .23), (.25, .88),
                  (.74, 1.05), (.86, 1.35), (.69, 1.72), (.14, 1.9)],
                 BRASS, 16)
        F.turned(model, at(WIDTH-1.85, side*1.04, 40.3), normal, up,
                 [(.15, 0), (.15, .025)], IRON, 12)
        for z in (39.6, 44.2):
            F.turned(model, at(WIDTH-1.85, side*1.04, z), normal, up,
                     [(.10, 0), (.10, .06)], BRASS, 10)

    # Butt hinges join the leaf to fixed plates on the existing jamb.
    for z in (18.0, 50.0, 82.0):
        F.bevel_box(model, at(.8, .03, z), axes, (1.6, .15, 3.6), IRON, .05)
        F.turned(model, origin + up*z, up, along,
                 [(.27, -2.0), (.38, -1.78), (.38, 1.78), (.27, 2.0)],
                 IRON, 16)
        jamb = origin + np.array((-hand*.35, -.65, z))
        F.bevel_box(model, jamb, np.eye(3), (1.0, .75, 3.6), IRON, .05)
        for dz in (-1.15, 1.15):
            F.bolt(model, jamb + np.array((0., .4, dz)), (0., 1., 0.), .12, False)

    # A small iron holdback makes the permanently open pose read as intentional.
    catch = at(WIDTH-2.5, 0, 14)
    wall = np.array((catch[0], 1101.8, catch[2]))
    F.bevel_box(model, wall, np.eye(3), (1.4, .35, 2.6), IRON, .08)
    F.beam(model, wall + (0., .2, 0.), catch, (.23, .23), IRON, .07)


def build():
    model = K.Model()
    for entrance in ENTRANCES:
        for hand in (-1, 1):
            # hand +1 is the low-east jamb; each leaf swings out and back.
            hinge = entrance - hand*OPENING_WIDTH/2
            leaf(model, (hinge, 1102.6, 0.), hand, 30 if hand == 1 else 47)
    Detail.configure(model)
    return model


def write(out_dir, resource_dir=RESOURCE_DIR):
    return K.write_model(Path(out_dir), resource_dir, NAME, build())


def stage(directory):
    directory = Path(directory).resolve()
    assets = directory / "models"
    count = write(assets)
    model = build()
    vertices = np.array([point for faces in model.polygons.values()
                         for points, _ in faces for point in points])
    assert len(model.boxes) == len(model.hulls) == 0
    assert vertices[:, 2].min() >= BOTTOM - .001
    assert vertices[:, 2].max() < OPENING_HEIGHT
    for entrance in ENTRANCES:
        # Both door assemblies stay outside a 54-inch clear central passage.
        near = vertices[np.abs(vertices[:, 0]-entrance) < 70]
        assert not np.any(np.abs(near[:, 0]-entrance) < 27), "Door intrudes on passage"
    bad = []
    for paint, faces in model.polygons.items():
        for index, (points, normal) in enumerate(faces):
            area = np.linalg.norm(np.cross(points[1]-points[0], points[2]-points[0]))
            if not np.isfinite(points).all() or area < 1e-8:
                bad.append((paint, index))
    assert not bad, bad[:5]
    files = []
    for path in sorted(assets.glob(NAME+".*")):
        relative = f"{RESOURCE_DIR}/{path.name}"
        installed = K.ASSETS / relative
        files.append(dict(path=relative,
                          source=str(path.relative_to(K.ROOT)).replace("\\", "/"),
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          expected_before_sha256=hashlib.sha256(installed.read_bytes()).hexdigest()
                          if installed.exists() else None))
    report = dict(revision="open-doors-v1", model=f"{RESOURCE_DIR}/{NAME}.vmdl",
                  triangles=count, entrances=len(ENTRANCES), leaves=4,
                  open_degrees=OPEN_ANGLE, minimum_clear_width_inches=54,
                  collision_shapes=0, degenerate_faces=len(bad), files=files)
    (directory/"staged.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "files"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True,
                        help="Stage source files outside Assets for native import")
    stage(parser.parse_args().stage)
