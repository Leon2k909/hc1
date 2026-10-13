"""Audit this visual edit against the workspace snapshot taken before it."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

root = Path(__file__).resolve().parents[3]
before = Path(__file__).parent / "before"


def triangles(path):
    vertices, uvs, normals = [], [], []
    faces = defaultdict(Counter)
    material = None
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            vertices.append(" ".join(fields[1:]))
        elif fields[0] == "vt":
            uvs.append(" ".join(fields[1:]))
        elif fields[0] == "vn":
            normals.append(" ".join(fields[1:]))
        elif fields[0] == "usemtl":
            material = fields[1]
        elif fields[0] == "f":
            corners = []
            for field in fields[1:]:
                v, uv, n = (int(i) - 1 for i in field.split("/"))
                corners.extend((vertices[v], uvs[uv], normals[n]))
            faces[material][sha256("|".join(corners).encode()).digest()] += 1
    return faces


models = [
    ("Assets/models/props/lowtide/forklift", 88, 12),
    ("Assets/models/props/lowtide/forklift_raised", 88, 12),
    ("Assets/models/maps/lowtide/lowtide_dress_east", 176, 24),
    ("Assets/models/maps/lowtide/lowtide_dress_west", 176, 24),
]
for relative, removed_count, added_count in models:
    old = triangles(before / (relative + ".obj"))
    new = triangles(root / (relative + ".obj"))
    for material in set(old) | set(new):
        if material not in ("lt_fl_warning", "lt_fl_amber"):
            assert old[material] == new[material], (relative, material, "unrelated geometry changed")
    assert not new["lt_fl_amber"] - old["lt_fl_amber"], (relative, "amber additions")
    assert sum((old["lt_fl_amber"] - new["lt_fl_amber"]).values()) == removed_count
    assert sum(new["lt_fl_warning"].values()) == added_count
    old_vmdl = (before / (relative + ".vmdl")).read_text()
    new_vmdl = (root / (relative + ".vmdl")).read_text()
    without_remap = "\n".join(line for line in new_vmdl.splitlines() if "lt_fl_warning.vmat" not in line) + "\n"
    assert old_vmdl == without_remap, (relative, "model setup or collision changed")
    print(f"{Path(relative).name}: removed {removed_count} panel triangles; added {added_count} label triangles; other geometry, UVs, normals and collision identical")
