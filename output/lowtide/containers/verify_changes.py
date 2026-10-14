"""Audit the isolated container replacement against the meshes saved before it."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "Tools"))
import lowtide_container as C

def scan(path, limits=None):
    counts = Counter()
    vectors = defaultdict(hashlib.sha256)
    faces = hashlib.sha256()
    materials = Counter()
    paint = None
    for line in path.open():
        fields = line.split()
        if not fields:
            continue
        kind = fields[0]
        if kind in ("v", "vt", "vn"):
            counts[kind] += 1
            if limits is None or counts[kind] <= limits[kind]:
                vectors[kind].update(line.encode())
        elif kind == "usemtl":
            paint = fields[1]
        elif kind == "f":
            materials[paint] += 1
            if not paint.startswith(("rw_container_", "lt_container_")):
                faces.update(paint.encode() + b":" + line.encode())
    return counts, {kind: digest.hexdigest() for kind, digest in vectors.items()}, faces.hexdigest(), materials

report = {}
for name in ("lowtide_dress_east", "lowtide_dress_west"):
    relative = Path(f"Assets/models/maps/lowtide/{name}.obj")
    before = root / "output/lowtide/containers/current-before" / relative
    after = root / relative
    old_counts, old_vectors, old_faces, old_materials = scan(before)
    new_counts, new_vectors, new_faces, new_materials = scan(after, old_counts)
    assert old_vectors == new_vectors, f"{name}: an existing vertex, UV or normal changed"
    assert old_faces == new_faces, f"{name}: non-container faces changed"
    before_vmdl = before.with_suffix(".vmdl").read_text()
    after_vmdl = after.with_suffix(".vmdl").read_text()
    restored = "".join(line for line in after_vmdl.splitlines(keepends=True)
                       if 'from = "lt_container_' not in line)
    assert restored == before_vmdl, f"{name}: existing model or collision data changed"
    assert after.with_suffix(".mtl").read_bytes().startswith(before.with_suffix(".mtl").read_bytes())
    _, actual = C.parse_obj(after.read_text())
    _, expected = C.parse_obj((C.REPORT / "generated" / f"{name}.obj").read_text())
    assert actual == expected, f"{name}: container sheets do not match the generated replacement"
    report[name] = {
        "original_vertex_uv_normal_data_preserved": True,
        "non_container_faces_preserved": True,
        "original_model_and_collision_data_preserved": True,
        "replacement_container_geometry_verified": True,
        "old_container_triangles": sum(n for p, n in old_materials.items() if p.startswith("rw_container_")),
        "new_container_triangles": sum(n for p, n in new_materials.items() if p.startswith("lt_container_")),
        "added_vertices": new_counts["v"] - old_counts["v"],
    }
    print(f"{name}: original geometry buffers, all unrelated faces, hardware and collision preserved")

for colour in C.COLOURS:
    source = Image.open(root / f"Tools/lowtide_container_{colour}_source.png").convert("RGB")
    colour_map = Image.open(C.OUT / f"lt_container_{colour}_color.png").convert("RGB")
    assert colour_map.size == (2048, 2048)
    assert np.array_equal(np.asarray(colour_map),
                          np.asarray(source.resize((2048, 2048), Image.Resampling.LANCZOS)))
    for suffix in ("normal", "frame_normal"):
        normal = np.asarray(Image.open(C.OUT / f"lt_container_{colour}_{suffix}.png"), float) / 127.5 - 1
        assert normal.shape == (2048, 2048, 3)
        assert np.max(np.abs(np.linalg.norm(normal, axis=-1) - 1)) < .008
    report[colour] = {"generated_albedo_colour_preserved": True, "dimensions": [2048, 2048],
                     "normal_lengths_verified": True}
    print(f"{colour}: generated colour preserved; 2048-pixel albedo and normalized surface maps")

(C.REPORT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
