"""Apply the new step materials/UVs without regenerating unrelated map geometry."""
from collections import Counter
from pathlib import Path
import sys

import numpy as np

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "Tools"))
import lowtide_map as LT
import lowtide_stairs as S
import map_kit as K

e0, e1 = LT.STAIR[0] + 2, LT.STAIR[1] - 2
n_top, n_foot, z_top = LT.STAIR[3], LT.STAIR[2], LT.FLOOR1
count = int(np.ceil(z_top / 7.4))
step_z, step_n = z_top / count, (n_top - n_foot) / count

for side, sign in (("east", 1), ("west", -1)):
    path = root / f"Assets/models/maps/lowtide/lowtide_{side}.obj"
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
            vertices.append(np.array((-x * sign, z, y)))
        elif fields[0] == "vn":
            normals.append(tuple(map(float, fields[1:])))
        elif fields[0] == "vt":
            uv_lines.append(i)
        elif fields[0] == "usemtl":
            material = fields[1]
        elif fields[0] == "f":
            indices = [tuple(int(x) - 1 for x in field.split("/")) for field in fields[1:]]
            points = np.array([vertices[v] for v, _, _ in indices])
            normal = normals[indices[0][2]]
            across = set(points[:, 0]) == {e0, e1}
            bounds = points[:, 1].min() >= n_foot - .002 and points[:, 1].max() <= n_top + .002
            if not (across and bounds):
                continue
            if material in ("planks_dark", S.TREAD) and normal == (0, 1, 0) and np.ptp(points[:, 2]) < .001:
                paint = S.TREAD
            elif material in ("lt_timber", S.RISER) and normal == (0, 0, -1) and points[:, 2].min() == -12:
                paint = S.RISER
            else:
                continue
            index = int(round((z_top - points[:, 2].max()) / step_z))
            assert 0 <= index < count, (side, index)
            top = z_top - index * step_z
            na, nb = n_top - index * step_n, n_top - (index + 1) * step_n
            # Recover the exact authored step grid from the OBJ's rounded coordinates.
            points[:, 1] = np.where(np.abs(points[:, 1] - na) < .002, na, nb)
            points[:, 2] = np.where(points[:, 2] == -12, -12, top)
            coords = S.face_uv(paint, points, e0, nb, top, step_z, index)
            for (_, uv, _), (u, v) in zip(indices, coords):
                value = f"vt {u:.5f} {v:.5f}"
                assert uv not in uv_values or uv_values[uv] == value
                uv_values[uv] = value
            changes[i] = paint
            totals[paint] += 1
    assert totals == Counter({S.TREAD: count * 2, S.RISER: count * 2}), (side, totals)
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
    for paint in (S.TREAD, S.RISER):
        if f"newmtl {paint}\n" not in text:
            text += f"newmtl {paint}\nKd 1 1 1\nd 1\n"
    K.write_text(mtl, text)
    vmdl = path.with_suffix(".vmdl")
    text = vmdl.read_text()
    anchor = next(line for line in text.splitlines() if 'from = "lt_steel.vmat"' in line)
    prefix = anchor[:len(anchor) - len(anchor.lstrip())]
    for paint in (S.RISER, S.TREAD):
        if f'from = "{paint}.vmat"' not in text:
            remap = f'{prefix}{{ from = "{paint}.vmat" to = "{S.RESOURCE}/{paint}.vmat" }},'
            text = text.replace(anchor, remap + "\n" + anchor)
    K.write_text(vmdl, text)
    print(f"Lowtide {side}: {count} treads and {count} risers updated; positions and normals retained")
