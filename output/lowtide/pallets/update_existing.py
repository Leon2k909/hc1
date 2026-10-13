"""Replace sack pallet materials and UVs while preserving the current map meshes."""
from collections import Counter, defaultdict
import itertools
import json
from pathlib import Path
import shutil
import sys

import numpy as np

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).parent
sys.path.insert(0, str(root / "Tools"))
import lowtide_map as LT
import lowtide_pallets as P
import map_kit as K

records = []
def record(model, e, n, z0, rows=2, cols=3, layers=3, along="e", pallet=True):
    if pallet:
        width = cols * 22 if along == "e" else rows * 34
        depth = rows * 34 if along == "e" else cols * 22
        records.append({"lo": [e - 2, n - 2, z0], "size": [width + 4, depth + 4, 5.5]})

saved = {name: getattr(LT, name) for name in ("sacks", "use", "crates", "quay_crane", "skip_bin", "tree")}
LT.sacks = record
for name in saved:
    if name != "sacks":
        setattr(LT, name, lambda *args, **kwargs: None)
layouts = {}
for name, constructor in (("lowtide_dress_east", lambda: LT.dress_side(1)),
                          ("lowtide_dress_west", lambda: LT.dress_side(-1)), ("lowtide_fleet", LT.fleet)):
    records = []
    constructor()
    layouts[name] = records
for name, value in saved.items():
    setattr(LT, name, value)
(folder / "layouts.json").write_text(json.dumps(layouts, indent=2))

for name, pallets in layouts.items():
    assert pallets, name
    corner_map = defaultdict(set)
    for index, pallet in enumerate(pallets):
        lo, size = np.array(pallet["lo"]), np.array(pallet["size"])
        for corner in itertools.product((0, 1), repeat=3):
            corner_map[tuple(np.round(lo + np.array(corner) * size, 3))].add(index)
    path = root / f"Assets/models/maps/lowtide/{name}.obj"
    # Save the current mesh immediately before its edit, including concurrent map additions.
    for suffix in (".obj", ".mtl", ".vmdl"):
        source = path.with_suffix(suffix)
        target = folder / "current-before" / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    lines = path.read_text().splitlines()
    vertices, normals, uv_lines = [], [], []
    changes, uv_values, totals = {}, {}, Counter()
    material = None
    for i, line in enumerate(lines):
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            x, y, z = map(float, fields[1:])
            vertices.append(np.array((-x, z, y)))
        elif fields[0] == "vn":
            x, y, z = map(float, fields[1:])
            normals.append(np.array((-x, z, y)))
        elif fields[0] == "vt":
            uv_lines.append(i)
        elif fields[0] == "usemtl":
            material = fields[1]
        elif fields[0] == "f" and material in ("planks", "lt_timber", P.TOP, P.SIDE):
            indices = [tuple(int(x) - 1 for x in field.split("/")) for field in fields[1:]]
            points = np.array([vertices[v] for v, _, _ in indices])
            candidates = set.intersection(*(corner_map.get(tuple(point), set()) for point in points))
            if not candidates:
                continue
            assert len(candidates) == 1, (name, candidates)
            pallet = pallets[next(iter(candidates))]
            lo, size = np.array(pallet["lo"]), np.array(pallet["size"])
            points = np.where(np.abs(points - lo) < .002, lo, lo + size)
            normal = normals[indices[0][2]]
            paint = P.TOP if normal[2] > .5 else P.SIDE
            coords = P.face_uv(paint, points, normal, lo, size)
            for (_, uv, _), (u, v) in zip(indices, coords):
                value = f"vt {u:.5f} {v:.5f}"
                assert uv not in uv_values or uv_values[uv] == value
                uv_values[uv] = value
            changes[i] = paint
            totals[paint] += 1
    assert totals == Counter({P.TOP: 2 * len(pallets), P.SIDE: 10 * len(pallets)}), (name, totals, len(pallets))
    for uv, value in uv_values.items():
        lines[uv_lines[uv]] = value
    output, material, active = [], None, None
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = active = line.split()[1]
        elif line.startswith("f "):
            target = changes.get(i, material)
            if target != active:
                output.append(f"usemtl {target}")
                active = target
        output.append(line)
    K.write_text(path, "\n".join(output) + "\n")
    mtl = path.with_suffix(".mtl")
    text = mtl.read_text()
    for paint in (P.SIDE, P.TOP):
        if f"newmtl {paint}\n" not in text:
            text += f"newmtl {paint}\nKd 1 1 1\nd 1\n"
    K.write_text(mtl, text)
    vmdl = path.with_suffix(".vmdl")
    text = vmdl.read_text()
    anchor = next(line for line in text.splitlines() if 'from = "lt_timber.vmat"' in line)
    prefix = anchor[:len(anchor) - len(anchor.lstrip())]
    for paint in (P.SIDE, P.TOP):
        if f'from = "{paint}.vmat"' not in text:
            remap = f'{prefix}{{ from = "{paint}.vmat" to = "{P.RESOURCE}/{paint}.vmat" }},'
            text = text.replace(anchor, remap + "\n" + anchor)
    K.write_text(vmdl, text)
    print(f"{name}: {len(pallets)} sack pallets updated; geometry and normals retained")
