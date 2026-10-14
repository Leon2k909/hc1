"""Bake static warehouse floor occlusion from the saved render meshes in Blender.

Run Blender --background --factory-startup --python this_file -- --size 384.
Writes numerical lighting data to output only; apply assets through the editor.
Coordinates and occluders match the saved OBJ import convention. Re-bake after
changing warehouse architecture or static dressing. No light direction or colour
is baked, and this mask never affects exterior concrete or vertical surfaces.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/lowtide/quality-pass/floor-contact-stage"
NORTH = (-400.0, 1150.0)
EAST = (240.0, 1000.0)
RANGE_SHORT, RANGE_BROAD = 24.0, 96.0
SAMPLES = 96


def read_occluders(paths, side):
    vertices, faces = [], []
    counts = {}
    for path in paths:
        source_vertices = []
        kept = 0
        with path.open() as file:
            for line in file:
                if line.startswith("v "):
                    y, z, x = map(float, line.split()[1:4])
                    # OBJ y,z,x -> engine x,y,z -> plan east,north,up.
                    source_vertices.append((-y, x, z))
                elif line.startswith("f "):
                    polygon = [source_vertices[int(token.split("/")[0])-1] for token in line.split()[1:]]
                    if max(p[2] for p in polygon) <= .25 or min(p[2] for p in polygon) > RANGE_BROAD + .4:
                        continue
                    if max(side*p[0] for p in polygon) < EAST[0]-RANGE_BROAD or min(side*p[0] for p in polygon) > EAST[1]+RANGE_BROAD:
                        continue
                    if max(p[1] for p in polygon) < NORTH[0]-RANGE_BROAD or min(p[1] for p in polygon) > NORTH[1]+RANGE_BROAD:
                        continue
                    start = len(vertices)
                    vertices.extend(polygon)
                    for k in range(1, len(polygon)-1):
                        faces.append((start, start+k, start+k+1))
                        kept += 1
        counts[path.name] = kept
    return BVHTree.FromPolygons(vertices, faces, all_triangles=True), counts


def directions(samples):
    # Deterministic cosine-weighted low-discrepancy hemisphere.
    for i in range(samples):
        radius = math.sqrt((i+.5)/samples)
        angle = i * (math.pi * (3-math.sqrt(5)))
        yield Vector((radius*math.cos(angle), radius*math.sin(angle), math.sqrt(1-radius*radius)))


def bake(tree, side, width):
    height = width*2
    data = np.ones((height, width, 4), dtype=np.float32)
    rays = list(directions(SAMPLES))
    for row in range(height):
        north = NORTH[0] + (row+.5)/height*(NORTH[1]-NORTH[0])
        for col in range(width):
            east = side*(EAST[0]+(col+.5)/width*(EAST[1]-EAST[0]))
            origin = Vector((east, north, .35))
            short = broad = 0.0
            for ray in rays:
                hit, normal, face, distance = tree.ray_cast(origin, ray, RANGE_BROAD)
                if hit is None:
                    continue
                short += max(0, 1-distance/RANGE_SHORT)
                broad += max(0, 1-distance/RANGE_BROAD)
            data[row, col, 0] = 1-short/SAMPLES
            data[row, col, 1] = 1-broad/SAMPLES
        if row % 128 == 0:
            print(f"Floor contact {side:+}: row {row}/{height}", flush=True)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=384)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / f"Assets/models/maps/lowtide/lowtide_{name}.obj" for name in ("east", "west", "dress_east", "dress_west")]
    # These four meshes contain all static floor contacts. Hanging fixtures and
    # exterior detail meshes are outside the 96-inch ray distance.
    records = {}
    images = []
    started = time.time()
    for side in (1, -1):
        tree, counts = read_occluders(paths, side)
        data = bake(tree, side, args.size)
        images.append(data)
        records[str(side)] = {"occluder_triangles": counts, "minimum": data[:, :, :2].min(axis=(0, 1)).tolist(), "mean": data[:, :, :2].mean(axis=(0, 1)).tolist()}
    # East and west are adjacent atlas cells; outer texel centres are clamped in
    # the shader to prevent the two warehouses bleeding into each other.
    atlas = np.concatenate(images, axis=1)
    image = bpy.data.images.new("Lowtide warehouse contact", width=atlas.shape[1], height=atlas.shape[0], alpha=True, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    image.pixels.foreach_set(atlas.ravel())
    image.filepath_raw = str(OUT / "floor_contact.png")
    image.file_format = "PNG"
    image.save()
    records.update({"inputs": {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                    "resolution": list(atlas.shape[:2][::-1]), "samples": SAMPLES, "ranges_inches": [RANGE_SHORT, RANGE_BROAD],
                    "floor_z": 0, "ray_origin_z": .35, "uv_origin": "Blender image bottom-left: e=240,n=-400; west cell uses abs(e)",
                    "elapsed_seconds": round(time.time()-started, 2)})
    (OUT / "bake.json").write_text(json.dumps(records, indent=2)+"\n")
    print(json.dumps(records), flush=True)


if __name__ == "__main__":
    main()
