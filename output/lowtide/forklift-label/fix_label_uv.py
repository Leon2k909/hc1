"""Apply the generator's corrected label U direction to the already rebuilt meshes."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "Tools"))
import map_kit as K

for relative in (
    "Assets/models/props/lowtide/forklift.obj",
    "Assets/models/props/lowtide/forklift_raised.obj",
    "Assets/models/maps/lowtide/lowtide_dress_east.obj",
    "Assets/models/maps/lowtide/lowtide_dress_west.obj",
):
    path = root / relative
    lines = path.read_text().splitlines()
    uv_lines, affected, material = [], set(), None
    for i, line in enumerate(lines):
        fields = line.split()
        if fields[0] == "vt":
            uv_lines.append(i)
        elif fields[0] == "usemtl":
            material = fields[1]
        elif fields[0] == "f" and material == "lt_fl_warning":
            affected.update(int(field.split("/")[1]) - 1 for field in fields[1:])
    for uv in affected:
        i = uv_lines[uv]
        _, u, v = lines[i].split()
        lines[i] = f"vt {1 - float(u):.5f} {v}"
    K.write_text(path, "\n".join(lines) + "\n")
    print(f"{path.stem}: corrected {len(affected)} label UVs")
