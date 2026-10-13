"""Audit the pallet material edit against the current workspace snapshot and builder."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import re
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).parent
before = folder / "before"
current_before = folder / "current-before"
sys.path.insert(0, str(root / "Tools"))
import lowtide_pallets as P
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


layouts = json.loads((folder / "layouts.json").read_text())
for name, pallets in layouts.items():
    expected = K.Model()
    old_collision = K.Model()
    for pallet in pallets:
        P.build(expected, pallet["lo"], pallet["size"])
        lo, size = K.np.asarray(pallet["lo"]), K.np.asarray(pallet["size"])
        old_collision.box(lo, lo + size, {"default": "lt_timber", "+z": "planks"}, "wood")
    assert repr(expected.boxes) == repr(old_collision.boxes), (name, "builder changed pallet collision")
    P.configure(expected)
    K.write_obj(folder / f"expected-{name}.obj", expected, f"expected-{name}")
    desired, _ = triangles(folder / f"expected-{name}.obj")
    relative = f"Assets/models/maps/lowtide/{name}"
    old, old_geometry = triangles(current_before / (relative + ".obj"))
    new, new_geometry = triangles(root / (relative + ".obj"))
    assert old_geometry == new_geometry, (name, "positions or normals changed")
    for paint in set(old) | set(new):
        if paint not in ("planks", "lt_timber", P.TOP, P.SIDE):
            assert old[paint] == new[paint], (name, paint, "unrelated texture mapping changed")
    for paint in ("planks", "lt_timber"):
        assert old[paint] == new[paint], (name, paint, "unrelated wood changed")
    for paint in (P.TOP, P.SIDE):
        assert new[paint] == desired[paint], (name, paint, "UVs do not match pallet builder")
    old_vmdl = (current_before / (relative + ".vmdl")).read_text()
    new_vmdl = (root / (relative + ".vmdl")).read_text()
    assert old_vmdl == new_vmdl, (name, "model setup or collision changed")
    # The first snapshot preceded a concurrent map rebuild. Verify that all original
    # pallet collisions also remain, while allowing that rebuild's unrelated additions.
    original_vmdl = (before / (relative + ".vmdl")).read_text()
    pattern = r'\{\s*_class = "PhysicsShapeBox".*?\n\s*\},'
    original_boxes = re.findall(pattern, original_vmdl, re.S)
    new_boxes = Counter(re.findall(pattern, new_vmdl, re.S))
    pallet_boxes = []
    for pallet in pallets:
        centre = K.to_world(K.np.asarray(pallet["lo"]) + K.np.asarray(pallet["size"]) / 2)
        matches = []
        for block in original_boxes:
            match = re.search(r'origin = \[([^\]]+)\]', block)
            origin = K.np.array([float(value.strip()) for value in match[1].split(',')])
            if K.np.allclose(origin, centre, atol=.0001):
                matches.append(block)
        assert len(matches) == 1, (name, "original pallet collider", centre, len(matches))
        pallet_boxes.extend(matches)
    assert not Counter(pallet_boxes) - new_boxes, (name, "original pallet collision removed")
    print(f"{name}: {len(pallets)} pallets match the builder; other materials, bags, positions, normals and collision unchanged")
