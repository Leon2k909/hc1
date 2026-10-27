"""Give Spillway's two plain steel containers Lowtide's corrugated container finish.

python Tools/spillway_containers.py

Only the container bodies (and their side ribs) in spillway_west/east.obj change
material and UVs. Geometry, corner posts, rails and collision hulls are untouched.
Scene coords: x = north, y = -east; OBJ axes are (y, z, x).
"""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "Assets/models/maps/spillway"
PAINT = "lt_container_blue"
TILE = 48.0
# (model, east, north, length) from spillway_map.west_works / east_works; width 110, height 112.
CONTAINERS = (("spillway_west", -1380, -1560, 350), ("spillway_east", 2070, 1830, 370))


def face_uv(point, normal):
    n = normal / np.linalg.norm(normal)
    up = np.array((1.0, 0, 0)) if abs(n[2]) > .999 else (np.array((0, 0, 1.0)) - n[2] * n)
    up /= np.linalg.norm(up)
    right = np.cross(-n, up)
    return point @ right / TILE, point @ up / TILE


def patch(name, boxes):
    obj = MODELS / f"{name}.obj"
    lines = obj.read_text().splitlines()
    v = [np.array([float(c) for c in l.split()[1:4]]) for l in lines if l.startswith("v ")]
    vt_count = sum(1 for l in lines if l.startswith("vt "))
    world = lambda p: np.array((p[2], p[0], p[1]))  # OBJ (y, z, x) -> scene (x, y, z)
    keep, moved, new_vt, paint = [], [], [], None
    for line in lines:
        if line.startswith("usemtl "):
            paint = line.split()[1]
        if line.startswith("f ") and paint == "rv_steel":
            refs = [t.split("/") for t in line.split()[1:]]
            pts = [world(v[int(r[0]) - 1]) for r in refs]
            if any(all(lo[i] - .01 <= p[i] <= hi[i] + .01 for p in pts for i in range(3)) for lo, hi in boxes):
                normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                fields = []
                for r, p in zip(refs, pts):
                    new_vt.append("vt %.5f %.5f" % face_uv(p, normal))
                    fields.append(f"{r[0]}/{vt_count + len(new_vt)}/{r[2]}")
                moved.append("f " + " ".join(fields))
                continue
        keep.append(line)
    assert moved, name
    # New texture coordinates go after the last existing vt, before any face refers to them.
    last_vt = max(i for i, l in enumerate(keep) if l.startswith("vt "))
    out = keep[:last_vt + 1] + new_vt + keep[last_vt + 1:] + [f"usemtl {PAINT}"] + moved
    obj.write_text("\n".join(out) + "\n")
    mtl = obj.with_suffix(".mtl")
    if f"newmtl {PAINT}\n" not in mtl.read_text():
        mtl.write_text(mtl.read_text() + f"newmtl {PAINT}\nKd 1 1 1\nd 1\n")
    vmdl = obj.with_suffix(".vmdl")
    text = vmdl.read_text()
    anchor = next(l for l in text.splitlines() if 'from = "rv_steel.vmat"' in l)
    remap = anchor.replace('"rv_steel.vmat"', f'"{PAINT}.vmat"').replace(
        "materials/riverdale/rv_steel.vmat", f"materials/lowtide/containers/{PAINT}.vmat")
    if remap not in text:
        vmdl.write_text(text.replace(anchor, remap + "\n" + anchor))
    print(f"{name}: {len(moved)} faces now {PAINT}")


for name, e, n, length in CONTAINERS:
    # Body and the 3-unit-proud side ribs, in scene coordinates (x = north, y = -east).
    lo = np.array((n - 55 - 2, -(e + length / 2) - .5, -.5))
    hi = np.array((n + 55 + 2, -(e - length / 2) + .5, 112.5))
    patch(name, [(lo, hi)])
