"""Compare the targeted mesh edit with its snapshot and the maintained stair builder."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).parent
before = folder / "before"
sys.path.insert(0, str(root / "Tools"))
import lowtide_map as LT
import lowtide_stairs as S
import map_kit as K


def triangles(path):
    vertices, uvs, normals = [], [], []
    faces, geometry = defaultdict(Counter), Counter()
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
            corners, shape = [], []
            for field in fields[1:]:
                v, uv, n = (int(i) - 1 for i in field.split("/"))
                corners.extend((vertices[v], uvs[uv], normals[n]))
                shape.extend((vertices[v], normals[n]))
            faces[material][sha256("|".join(corners).encode()).digest()] += 1
            geometry[sha256("|".join(shape).encode()).digest()] += 1
    return faces, geometry


expected = K.Model()
LT.stairs(expected, LT.STAIR[0] + 2, LT.STAIR[1] - 2, LT.STAIR[3], LT.STAIR[2], LT.FLOOR1, 0,
          tread=S.TREAD, riser=S.RISER, side="lt_timber", surface=LT.WOOD)
LT.configure(expected)
for side, model in (("east", expected), ("west", expected.mirrored())):
    K.write_obj(folder / f"expected-{side}.obj", model, f"expected-{side}")
    desired, _ = triangles(folder / f"expected-{side}.obj")
    relative = f"Assets/models/maps/lowtide/lowtide_{side}"
    old, old_geometry = triangles(before / (relative + ".obj"))
    new, new_geometry = triangles(root / (relative + ".obj"))
    assert old_geometry == new_geometry, (side, "geometry or normals changed")
    for paint in set(old) | set(new):
        if paint not in ("planks_dark", "lt_timber", S.TREAD, S.RISER):
            assert old[paint] == new[paint], (side, paint, "unrelated texture mapping changed")
    for paint in ("planks_dark", "lt_timber"):
        assert not new[paint] - old[paint], (side, paint)
        assert sum((old[paint] - new[paint]).values()) == 48, (side, paint, "unexpected replacement count")
    for paint in (S.TREAD, S.RISER):
        assert new[paint] == desired[paint], (side, paint, "mesh does not match builder UVs")
        assert sum(new[paint].values()) == 48
    old_vmdl = (before / (relative + ".vmdl")).read_text()
    new_vmdl = (root / (relative + ".vmdl")).read_text()
    without_remaps = "\n".join(line for line in new_vmdl.splitlines() if S.TREAD + ".vmat" not in line and S.RISER + ".vmat" not in line) + "\n"
    assert old_vmdl == without_remaps, (side, "model setup or collision changed")
    print(f"Lowtide {side}: all 24 treads and 24 risers match the stair builder; other geometry, normals, UVs and collision identical")
scene = Path("Assets/scenes/maps/Lowtide/lowtide.scene")
assert (before / scene).read_bytes() == (root / scene).read_bytes(), "scene changed"
print("Scene file unchanged")
