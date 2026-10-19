"""Preserve the current assets, and stage only removal of the 13 visible hedge boxes."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
files = ["Tools/veridant_map.py", "Assets/scenes/maps/Veridant/veridant.scene",
         "Assets/models/maps/veridant/veridant_dress.obj", "Assets/models/maps/veridant/veridant_dress.vmdl",
         "Assets/models/maps/veridant/veridant_dress.mtl", "CLAUDE.md"]
hashes = {}
for name in files:
    source = root / name
    saved = out / "before" / name
    saved.parent.mkdir(parents=True, exist_ok=True)
    if saved.exists():
        raise RuntimeError(f"Baseline already exists: {saved}")
    shutil.copy2(source, saved)
    hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()

source = out / "before/Assets/models/maps/veridant/veridant_dress.obj"
lines = source.read_text().splitlines(keepends=True)
paint = None
removed = 0
staged = []
before_faces = Counter()
after_faces = Counter()
for line in lines:
    if line.startswith("usemtl "):
        paint = line.split()[1]
    if line.startswith("f "):
        before_faces[paint] += 1
        if paint == "vr_hedge":
            removed += 1
            continue
        after_faces[paint] += 1
    staged.append(line)
assert removed == 13 * 12, removed
assert {p: c for p, c in before_faces.items() if p != "vr_hedge"} == after_faces
stage = out / "stage"
stage.mkdir(exist_ok=True)
(stage / "veridant_dress.obj").write_text("".join(staged), newline="")
(out / "baseline.json").write_text(json.dumps({"hashes": hashes, "removed_hedge_triangles": removed,
    "other_faces_unchanged": True, "other_material_triangle_counts": after_faces}, indent=2))
print(f"Saved baseline; staged removal of {removed} hedge triangles; all other OBJ data preserved.")
