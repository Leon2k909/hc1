"""Replace Spillway's two plain box containers with Lowtide's detailed ISO container.

python Tools/spillway_containers.py

Run once on the original spillway_west/east meshes. The old container (box body,
side ribs, frame bars, end rods and its "03" stencil) is cut out of the OBJ, and a
40 ft high-cube built by lowtide_container.build (corrugated sheets, doors, locking
bars, corner castings, code markings) is appended in its place. Its collision box in
the vmdl is resized to the new container. Plan coords are (east, north, up).
"""
import re
from pathlib import Path

import numpy as np

import building_textures as BT
import map_kit as K
import lowtide_container as LC

MODELS = K.ROOT / "Assets/models/maps/spillway"
SCRATCH = K.ROOT / "output/spillway/containers"
# model, plan centre (east, north), old length; old boxes were 110 wide and 112 tall.
CONTAINERS = (("spillway_west", (-1380, -1560), 350, "blue", +1),
              ("spillway_east", (2070, 1830), 370, "blue", -1))
SIZE, HIGH_CUBE = "40", True
REMAPS = {"lt_container_blue": "materials/lowtide/containers/lt_container_blue.vmat",
          "lt_container_blue_frame": "materials/lowtide/containers/lt_container_blue_frame.vmat",
          "rw_black": "materials/railhead/rw_black.vmat",
          "rw_container_code": "materials/railhead/rw_container_code.vmat",
          "rw_steel_dark": "materials/railhead/rw_steel_dark.vmat",
          "rw_steel_grey": "materials/railhead/rw_steel_grey.vmat",
          "rw_yellow_paint": "materials/railhead/rw_yellow_paint.vmat"}


def cut_old(lines, centre, length):
    """Drop every face lying wholly inside the old container's envelope, except ground at z 0."""
    e, n = centre
    lo = np.array((-(e + length / 2 + 6), -.5, n - 58))   # OBJ axes: (-east, up, north)
    hi = np.array((-(e - length / 2 - 6), 114.5, n + 58))
    v = [np.array([float(c) for c in l.split()[1:4]]) for l in lines if l.startswith("v ")]
    out, removed = [], 0
    for line in lines:
        if line.startswith("f "):
            pts = np.array([v[int(t.split("/")[0]) - 1] for t in line.split()[1:]])
            if (pts >= lo).all() and (pts <= hi).all() and pts[:, 1].max() > .5:
                removed += 1
                continue
        out.append(line)
    return out, removed


def new_container(name, centre, colour, door_end):
    model = K.Model()
    LC.build(model, *centre, 0, size=SIZE, axis="e", paint=f"rw_container_{colour}",
             high_cube=HIGH_CUBE, door_end=door_end)
    # Railhead's hardware paints aren't in building_textures; give them its usual 48-inch tile.
    for paint in model.polygons:
        if paint not in BT.PAINTS:
            model.tile_overrides.setdefault(paint, 1.0 if paint == "rw_container_code" else 48.0)
    path = SCRATCH / f"{name}_container.obj"
    path.parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(path, model, path.stem)
    return path.read_text().splitlines(), model.boxes[0]


def append(lines, extra):
    counts = {k: sum(1 for l in lines if l.startswith(k + " ")) for k in ("v", "vt", "vn")}
    # Vertex data goes before the first face group so every index resolves.
    first = next(i for i, l in enumerate(lines) if l.startswith("usemtl "))
    data = [l for l in extra if l.split(" ", 1)[0] in ("v", "vt", "vn")]
    faces = []
    for l in extra:
        if l.startswith("usemtl "):
            faces.append(l)
        elif l.startswith("f "):
            refs = []
            for t in l.split()[1:]:
                vi, ti, ni = (int(x) for x in t.split("/"))
                refs.append(f"{vi + counts['v']}/{ti + counts['vt']}/{ni + counts['vn']}")
            faces.append("f " + " ".join(refs))
    return lines[:first] + data + lines[first:] + faces


def patch_vmdl(path, centre, length, box):
    text = path.read_text()
    e, n = centre
    # The old box: origin (north, -east, 56), dimensions (length, 110, 112).
    old = re.compile(r"(origin = \[ )%s\.0000, %s\.0000, 56\.0000( \]\s*angles = \[[^\]]*\]\s*dimensions = \[ )"
                     r"%s\.0000, 110\.0000, 112\.0000( \])" % (n, -e, length))
    size = box[2]
    text, count = old.subn(r"\g<1>%s.0000, %s.0000, %.4f\g<2>%.4f, %.4f, %.4f\g<3>"
                           % (n, -e, size[2] / 2, size[0], size[1], size[2]), text)
    assert count == 1, (path, count)
    anchor = next(l for l in text.splitlines() if 'from = "rv_steel.vmat"' in l)
    for paint, target in sorted(REMAPS.items()):
        if f'from = "{paint}.vmat"' not in text:
            remap = anchor.replace('"rv_steel.vmat"', f'"{paint}.vmat"').replace(
                "materials/riverdale/rv_steel.vmat", target)
            text = text.replace(anchor, remap + "\n" + anchor)
    path.write_text(text)


for name, centre, length, colour, door_end in CONTAINERS:
    obj = MODELS / f"{name}.obj"
    lines, removed = cut_old(obj.read_text().splitlines(), centre, length)
    extra, box = new_container(name, centre, colour, door_end)
    obj.write_text("\n".join(append(lines, extra)) + "\n")
    mtl = obj.with_suffix(".mtl")
    text = mtl.read_text()
    for paint in REMAPS:
        if f"newmtl {paint}\n" not in text:
            text += f"newmtl {paint}\nKd 1 1 1\nd 1\n"
    mtl.write_text(text)
    patch_vmdl(obj.with_suffix(".vmdl"), centre, length, box)
    print(f"{name}: removed {removed} old container faces, added a {SIZE} ft container")
