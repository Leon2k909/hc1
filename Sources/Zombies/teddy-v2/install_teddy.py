"""Swap Riverside's teddy for teddy_v2 without regenerating the map: python install_teddy.py <project root>

As install_cooler.py does for the cooler, and for the same reason: rerunning Tools/riverside_map.py rewrites far more than one prop. This cuts every rs_teddy and rs_teddy_dark face out of
the checked-in riverside_pad.obj, which only the old teddy used, and adds the same object to the scene that riverside_map.py's write_scene makes. It stops before writing anything if the
faces aren't the old teddy's. Safe to rerun.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import riverside_map as M  # noqa: E402

K, P = M.K, M.P
EXPECTED = {"rs_teddy": 480, "rs_teddy_dark": 240}

P.reset()
M.trailers(K.Model(), K.Model(), K.Model())
M.store(K.Model())
M.pad(K.Model())
M.dressing(K.Model())
if len(P.TEDDIES) != 1:
    raise SystemExit(f"{len(P.TEDDIES)} teddies, not 1. Nothing written.")

path = os.path.join(ROOT, "Assets", "models", "maps", "riverside", "riverside_pad.obj")
with open(path, encoding="utf-8", newline="") as h:
    lines = h.readlines()
current = None
drop = set()
counts = {}
for n, line in enumerate(lines):
    if line.startswith("usemtl"):
        current = line.split()[1]
        if current in EXPECTED:
            drop.add(n)
    elif line.startswith("f ") and current in EXPECTED:
        drop.add(n)
        counts[current] = counts.get(current, 0) + len(line.split()) - 3
print("triangles to cut:", counts, flush=True)
if counts and counts != EXPECTED:
    raise SystemExit(f"Those aren't the old teddy's faces (expected {EXPECTED}). Nothing written.")
if drop:
    with open(path, "w", encoding="utf-8", newline="") as h:
        h.writelines(line for n, line in enumerate(lines) if n not in drop)

scene = json.loads(open(M.SCENE_FILE, encoding="utf-8").read())
objects = scene["GameObjects"]
placed = M.teddy_objects()[0]
names = [o.get("Name") for o in objects]
if "Teddy" in names:
    objects[names.index("Teddy")] = placed
else:
    objects.insert(names.index("Cooler") + 1, placed)
K.write_text(M.SCENE_FILE, json.dumps(scene, indent=2), newline=None)
print("triangles cut:", sum(counts.values()), "scene: Teddy at", placed["Position"], "rotation", placed["Rotation"], flush=True)
