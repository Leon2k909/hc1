"""A temporary copy of Belltower's west half with the old stones cut out, for an honest before and after in a match: python preview_model.py <project root>

The match swaps its West Half renderer to this model for the "after" shots. The map's own files are only read. The copy has no physics, since the match's collider stays on the real model.
Writes to Assets/models/compare_old/headstone-preview/, and refuses unless it finds exactly the 19 old stones' 288 triangles.
"""
import json
import os
import re
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
OUT_REL = "models/compare_old/headstone-preview"
OUT = os.path.join(ASSETS, OUT_REL)
SOURCE = "models/maps/belltower/compiler-safe/west/west_001_ashlar_grey.obj"
STONES = json.load(open(os.path.join(ROOT, "output/asset-improvement-20261030/headstone/old_stones.json")))
stone_xy = np.array([(s["x"], s["y"]) for s in STONES])
os.makedirs(OUT, exist_ok=True)

# The OBJ's first axis is engine Y, its second Z, its third X.
positions, kept, cut, paint = [], [], 0, None
for line in open(os.path.join(ASSETS, SOURCE), encoding="utf-8", newline=""):
    if line.startswith("v "):
        a, b, c = map(float, line[2:].split())
        positions.append((c, a, b))
    elif line.startswith("usemtl"):
        paint = line.split()[1]
    elif line.startswith("f ") and paint == "ashlar_grey":
        corners = np.array([positions[int(t.split("/")[0]) - 1] for t in line.split()[1:]])
        close = np.linalg.norm(corners[:, None, :2] - stone_xy[None], axis=2).min(1).max() < 13.5
        if close and corners[:, 2].max() <= 40.1:
            cut += 1
            continue
    kept.append(line)
if cut != 288:
    sys.exit(f"Expected the old stones' 288 triangles, found {cut}. Nothing written.")
name = os.path.basename(SOURCE).replace(".obj", "_nostones.obj")
with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as h:
    h.writelines(kept)

text = open(os.path.join(ASSETS, "models/maps/belltower/belltower_west.vmdl"), encoding="utf-8").read()
if text.count(f'filename = "{SOURCE}"') != 1:
    sys.exit("The vmdl doesn't name the stones' OBJ exactly once. Nothing written.")
text = text.replace(f'filename = "{SOURCE}"', f'filename = "{OUT_REL}/{name}"')
# Everything collision is the real model's job: take the physics list out, braces and all.
start = text.index('_class = "PhysicsShapeList"')
start = text.rindex("{", 0, start)
depth, end = 0, start
for end in range(start, len(text)):
    if text[end] == "{":
        depth += 1
    elif text[end] == "}":
        depth -= 1
        if depth == 0:
            break
text = text[:start] + text[end + 1 :].lstrip(",")
if "Physics" in text:
    sys.exit("Physics left in the preview vmdl. Nothing more written.")
with open(os.path.join(OUT, "belltower_west_nostones.vmdl"), "w", encoding="utf-8", newline="\n") as h:
    h.write(text)
print("cut", cut, "triangles;", "render meshes", len(re.findall(r'_class = "RenderMeshFile"', text)), "; wrote", OUT_REL, flush=True)
