"""Surgical replacement: retain every unrelated OBJ face and scene object."""
from collections import Counter
from pathlib import Path
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import railhead_signal_frame as FRAME


def read_obj(path):
    lines = path.read_text().splitlines(keepends=True)
    vertices, faces, material = [], {}, ""
    for i, line in enumerate(lines):
        if line.startswith("v "):
            vertices.append(tuple(round(float(v), 3) for v in line.split()[1:4]))
        elif line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f "):
            points = tuple(sorted(vertices[int(v.split("/")[0]) - 1] for v in line.split()[1:]))
            faces[i] = (material, points)
    return lines, faces


out = ROOT / "output/railhead/signal-frame"
old_lines, old_faces = read_obj(out / "legacy_frame.obj")
target = ROOT / "Assets/models/maps/railhead/railhead_centre.obj"
lines, faces = read_obj(target)
wanted = Counter(old_faces.values())
removed = []
for i, face in faces.items():
    if wanted[face]:
        wanted[face] -= 1
        removed.append(i)
missing = +wanted
if missing:
    raise RuntimeError(f"Missing {sum(missing.values())} of {len(old_faces)} exact legacy triangles; no writes performed.")
vmdl = target.with_suffix(".vmdl")
source = vmdl.read_text()
blocks = list(re.finditer(r"\{[^{}]*_class = \"PhysicsShapeBox\"[^{}]*\},?", source))
boxes = [b for b in blocks if "origin = [ -2161.0000, -0.0000," in b.group() and
         any(f"{z:.4f}" in b.group() for z in (133.5, 146.5)) and "232.0000, 22.0000" in b.group()]
assert len(boxes) == 2, f"Expected two legacy base boxes, found {len(boxes)}."
for p in (target, vmdl):
    shutil.copy2(p, out / (p.name + ".before"))
for b in reversed(boxes):
    source = source[:b.start()] + source[b.end():]
removed = set(removed)
remaining = [s for i, s in enumerate(lines) if i not in removed]
# s&box's OBJ importer rejects empty material sections; these four colours
# belonged exclusively to the replaced mechanisms.
counts, current = Counter(), ""
for s in remaining:
    if s.startswith("usemtl "):
        current = s.split()[1]
        counts[current] += 0
    elif s.startswith("f "):
        counts[current] += 1
empty = {name for name, n in counts.items() if not n}
K.write_text(target, "".join(s for s in remaining if not (s.startswith("usemtl ") and s.split()[1] in empty)), newline=None)
K.write_text(vmdl, source, newline=None)
scene_path = ROOT / "Assets/scenes/maps/Railhead/railhead.scene"
scene = json.loads(scene_path.read_text())
station = next(g for g in scene["GameObjects"] if g["Name"] == "Station")
assert not any(g["Name"] == "Mechanical Signal Frame" for g in station["Children"])
station["Children"].append(FRAME.scene_group())
shutil.copy2(scene_path, out / "railhead.scene.before")
K.write_text(scene_path, json.dumps(scene, indent=2), newline=None)
report = {"removed_legacy_triangles": len(removed), "preserved_other_triangles": len(faces) - len(removed),
          "replaced_legacy_boxes": len(boxes), "shared_model": FRAME.MODEL}
(out / "migration.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
