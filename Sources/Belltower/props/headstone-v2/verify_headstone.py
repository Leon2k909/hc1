"""Check the stones from their files: python verify_headstone.py <project root> <export dir> <old stones json>

Each one's parts must face outward, it must fit its old stone, its collision must be the old box for its kind, its textures must exist, and the old merged model must
be unchanged with all its stones measured. Compiling and seeing them in s&box is not covered.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, EXPORT, OLD = sys.argv[1], sys.argv[2], sys.argv[3]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(EXPORT, "models/props/belltower/headstone_v2")
MATS = "materials/belltower/headstone_v2"
OLD_OBJ = "models/maps/belltower/compiler-safe/west/west_001_ashlar_grey.obj"
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def read_obj(path):
    v, f = [], 0
    for line in open(path, encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    return np.array(v, float)[:, [2, 0, 1]], f  # OBJ (a, b, c) is engine (c, a, b).


stones = json.load(open(OLD))
report["old_stones"] = dict(slabs=sum(s["kind"] == "slab" for s in stones), crosses=sum(s["kind"] == "cross" for s in stones))
check(report["old_stones"] == dict(slabs=14, crosses=5), f"expected 14 slabs and 5 crosses in the west half: {report['old_stones']}")
slab_heights = [s["height"] for s in stones if s["kind"] == "slab"]
report["old_slab_heights"] = [round(min(slab_heights), 1), round(max(slab_heights), 1)]
SIZES = dict(arched=(6.0, 22.0, 32.0), shouldered=(6.0, 22.0, 29.0), low=(6.0, 22.0, 26.0), cross=(6.0, 6.0, 40.0))
for kind, (dx, dy, dz) in SIZES.items():
    name = f"headstone_{kind}"
    report[name] = {}
    for lod in range(4):
        v, f = read_obj(os.path.join(NEW, f"{name}_lod{lod}.obj"))
        lo, hi = v.min(0), v.max(0)
        report[name][f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
        if lod:
            check(f < report[name][f"lod{lod - 1}"]["triangles"], f"{name} lod{lod} isn't lighter")
    v, _ = read_obj(os.path.join(NEW, f"{name}_lod0.obj"))
    lo, hi = v.min(0), v.max(0)
    # They go 2 in into the ground, so a lean or a sloping path shows no gap. Footings and the cross's base stand a little past the old box at ankle height.
    check(abs(lo[2] + 2.0) < 0.2 and abs(hi[2] - dz) < 0.5, f"{name}: height doesn't fit: {lo} {hi}")
    width = 24.5 if kind != "cross" else 24.5
    check(hi[1] - lo[1] <= width + 0.5 and np.abs(hi[0]) <= 5.9 and np.abs(lo[0]) <= 5.9, f"{name}: too wide: {lo} {hi}")
    above = v[v[:, 2] > 6.0]
    check(np.abs(above[:, 0]).max() <= 3.05, f"{name}: thicker than the old box above the footing: {np.abs(above[:, 0]).max()}")
    outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{name}_lod0.obj"), "headstone"], capture_output=True, text=True)
    report[name]["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{name}: {report[name]['outward']}")
    vmdl = open(os.path.join(NEW, f"{name}.vmdl"), encoding="utf-8").read()
    check(f"dimensions = [ {dx:.4f}, {dy:.4f}, {dz:.4f} ]" in vmdl and f"origin = [ 0.0000, 0.0000, {dz / 2:.4f} ]" in vmdl, f"{name}: collision box isn't the old kind's")
    check(f'to = "{MATS}/headstone.vmat"' in vmdl, f"{name}: vmdl doesn't remap to its material")
    for ref in re.findall(r'filename = "([^"]+)"', vmdl):
        check(os.path.exists(os.path.join(EXPORT, ref)), f"{name}: vmdl names missing {ref}")
vmat = open(os.path.join(EXPORT, MATS, "headstone.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 5, "expected five textures")
for tex in textures:
    check(os.path.exists(os.path.join(EXPORT, tex)), f"missing {tex}")
changed = subprocess.run(["git", "status", "--porcelain", "--", f"Assets/{OLD_OBJ}"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
report["old_model_status"] = changed
check(changed == "", f"the old model changed: {changed}")
report["in_assets"] = [p for p in ("models/props/belltower/headstone_v2", MATS) if os.path.exists(os.path.join(ASSETS, p))]
report["compiled_files"] = [f for d in (NEW, os.path.join(EXPORT, MATS)) for f in os.listdir(d) if f.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
