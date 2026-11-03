"""Make a review-only pad model with the old supply crate hidden, for a like-for-like engine comparison.

Only the new crate's asset directory is written. The live pad OBJ and scene remain unchanged.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import numpy as np

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "Assets/models/props/riverside/crate_v2/review"
OUT.mkdir(parents=True, exist_ok=True)
PAD = ROOT / "Assets/models/maps/riverside/riverside_pad.obj"
original = PAD.read_bytes()
lines = original.decode("utf-8").splitlines(keepends=True)
vertices = np.array([(float(p[2]), float(p[0]), float(p[1])) for line in lines if line.startswith("v ") for p in [line.split()[1:4]]])
position = np.array((-80, -140, 96))
yaw = math.atan2(-1, .3)
drop = set()
material = None
for i, line in enumerate(lines):
    if line.startswith("usemtl "):
        material = line.split()[1]
    elif line.startswith("f ") and material in ("rs_crate", "rs_wood", "rs_signs"):
        delta = vertices[[int(t.split("/")[0]) - 1 for t in line.split()[1:]]] - position
        u = delta[:, 0] * math.cos(yaw) + delta[:, 1] * math.sin(yaw)
        v = -delta[:, 0] * math.sin(yaw) + delta[:, 1] * math.cos(yaw)
        if abs(u).max() < 16.5 and abs(v).max() < 13.2 and delta[:, 2].min() > -.01 and delta[:, 2].max() < 22.01:
            drop.add(i)
assert len(drop) == 86, (len(drop), {lines[i] for i in drop})
(OUT / "pad_without_crate.obj").write_text("".join(line for i, line in enumerate(lines) if i not in drop), newline="\n")
(OUT / "riverside_pad.mtl").write_bytes(PAD.with_suffix(".mtl").read_bytes())
# Keep the original material remaps and import settings; remove collision only in this visual review copy.
vmdl = PAD.with_suffix(".vmdl").read_text()
vmdl = vmdl.replace("models/maps/riverside/riverside_pad.obj", "models/props/riverside/crate_v2/review/pad_without_crate.obj")
# Existing VMDL also references collision source files via absolute asset paths, which remain valid.
(OUT / "pad_without_crate.vmdl").write_text(vmdl)
report = dict(pad_sha256=hashlib.sha256(original).hexdigest(), scene_sha256=hashlib.sha256((ROOT / "Assets/scenes/maps/Riverside/riverside.scene").read_bytes()).hexdigest(), removed_old_crate_triangles=len(drop), position=position.tolist(), yaw=math.degrees(yaw))
(ROOT / "output/asset-improvement-20261030/riverside-crate/review-config.json").write_text(json.dumps(report, indent=2))
assert PAD.read_bytes() == original
print(json.dumps(report, indent=2))
