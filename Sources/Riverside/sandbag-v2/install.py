"""Install only the approved sandbag mesh replacements; the editor saves the new scene group.

python install.py <project-root> [--apply]
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import shutil
import sys

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverside_map as M
import riverside_parts as P

OUT = ROOT / "output/asset-improvement-20261030/riverside-sandbags/installed"
BACKUP = OUT / "before-install"
OUT.mkdir(parents=True, exist_ok=True)
scene_path = ROOT / "Assets/scenes/maps/Riverside/riverside.scene"
scene = json.loads(scene_path.read_text())
if any(g.get("Name") == "Sandbags" for g in scene["GameObjects"]):
    print("Sandbags already saved; run verify-install.py")
    sys.exit(0)
P.reset()
zones = {name: K.Model() for name in ("riverside_pad", "riverside_store", "riverside_dressing")}
M.pad(zones["riverside_pad"])
M.store(zones["riverside_store"])
M.dressing(zones["riverside_dressing"])
assert len(P.SANDBAGS) == 54
approved = json.loads((ROOT / "output/asset-improvement-20261030/riverside-sandbags/review.json").read_text())
group = K.game_object(M.ids, "Sandbags", "sandbags", children=M.sandbag_objects())
assert len(group["Children"]) == 54
for child, bag in zip(group["Children"], approved["bags"]):
    assert all(abs(float(a) - b) < .002 for a, b in zip(child["Position"].split(','), bag["position"]))
    assert child["Components"][0]["Model"].endswith("sandbag_" + str(bag["variant"]) + ".vmdl")
(OUT / "placements.json").write_text(json.dumps(dict(group=group, bags=approved["bags"], walls=approved["walls"]), indent=2))
prepared, report = [], []
for name in zones:
    path = ROOT / "Assets/models/maps/riverside" / (name + ".obj")
    original = path.read_bytes()
    lines = original.decode("utf-8").splitlines(keepends=True)
    paint, dropped, kept = None, 0, []
    for line in lines:
        if line.startswith("usemtl "):
            paint = line.split()[1]
            if paint == "rs_sandbag":
                continue
        if paint == "rs_sandbag" and line.startswith("f "):
            dropped += 1
        else:
            kept.append(line)
    count = sum(b["zone"] == name for b in approved["bags"])
    assert dropped == count * 64, (name, count, dropped)
    vmdl = path.with_suffix(".vmdl")
    report.append(dict(zone=name, bags=count, removed_triangles=dropped, collision_model_sha256=hashlib.sha256(vmdl.read_bytes()).hexdigest()))
    prepared.append((path, original, ''.join(kept).encode("utf-8")))
    print(report[-1], flush=True)
if "--apply" in sys.argv:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path, before, after in prepared:
        assert path.read_bytes() == before, str(path) + " changed during preparation"
        backup = BACKUP / path.name
        if not backup.exists(): shutil.copy2(path, backup)
        incoming = path.with_suffix(".sandbags-incoming")
        incoming.write_bytes(after)
        incoming.replace(path)
    if not (BACKUP / "riverside.scene").exists(): shutil.copy2(scene_path, BACKUP / "riverside.scene")
(OUT / "mesh-cuts.json").write_text(json.dumps(report, indent=2))
print("Applied old mesh cuts" if "--apply" in sys.argv else "Dry run only")
