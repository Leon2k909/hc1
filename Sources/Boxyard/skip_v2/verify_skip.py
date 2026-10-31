"""Check the skip from its files: python verify_skip.py <project root> <export dir>

Its parts must face outward, its bounds must match the old skip's, its collision must be the old skip's, its textures must
exist, and the old skip's geometry must be as committed. Compiling and seeing it in s&box is not covered.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, EXPORT = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(EXPORT, "models/props/boxyard/skip_v2")
MATS = "materials/boxyard/skip_v2"
NAME = "skip"
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def read_obj(path, wanted=None):
    v, f, current = [], [], None
    for line in open(path, encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and (wanted is None or current == wanted):
            f.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.array(v, float)[:, [2, 0, 1]], f  # OBJ (a, b, c) is engine (c, a, b).


def to_local(p):
    """Boxyard's skip: local x = 555 - Y, local y = X - 675."""
    return np.column_stack((555.0 - p[:, 1], p[:, 0] - 675.0, p[:, 2]))


v, f = read_obj(os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj"), "bx_skip_green")
used = sorted({i for face in f for i in face})
old = to_local(v[used])
old = old[(np.abs(old[:, 0]) < 80) & (np.abs(old[:, 1]) < 45)]
lo0, hi0 = old.min(0), old.max(0)
report["old"] = dict(faces=len(f), min=lo0.round(2).tolist(), max=hi0.round(2).tolist())
for lod in range(4):
    v, faces = read_obj(os.path.join(NEW, f"{NAME}_lod{lod}.obj"))
    lo, hi = v.min(0), v.max(0)
    report[f"lod{lod}"] = dict(triangles=len(faces), min=lo.round(2).tolist(), max=hi.round(2).tolist())
    if lod == 0:
        check(np.abs(lo - lo0).max() < 0.5 and np.abs(hi - hi0).max() < 0.5, f"lod0 bounds differ from the old skip's by more than 0.5 in: {lo} {hi}")
    if lod:
        check(len(faces) < report[f"lod{lod - 1}"]["triangles"], f"lod{lod} isn't lighter than lod{lod - 1}")

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{NAME}_lod0.obj"), NAME], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, report["outward"])

# The new hulls' points must be the old hull file's points for this skip, moved into the model's frame.
old_hulls, _ = read_obj(os.path.join(ASSETS, "models/maps/boxyard/boxyard_props_hulls_metal.obj"))
old_hulls = to_local(old_hulls)
old_hulls = old_hulls[(np.abs(old_hulls[:, 0]) < 73) & (np.abs(old_hulls[:, 1]) < 34) & (old_hulls[:, 2] <= 48.001) & (old_hulls[:, 2] >= 3.999)]
new_hulls, hull_faces = read_obj(os.path.join(NEW, "skip_hulls_metal.obj"))
key = lambda a: sorted(tuple(np.round(p, 2)) for p in a)
check(key(old_hulls) == key(new_hulls), f"collision hulls differ: old {len(old_hulls)} points, new {len(new_hulls)}")
report["hull_points"] = dict(old=len(old_hulls), new=len(new_hulls), faces=len(hull_faces))
props = open(os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.vmdl"), encoding="utf-8").read()
check('origin = [ 675.0000, 555.0000, 2.0000 ]' in props and "dimensions = [ 108.0000, 66.0000, 4.0000 ]" in props, "the old floor box isn't what this model copies")
vmdl = open(os.path.join(NEW, f"{NAME}.vmdl"), encoding="utf-8").read()
check("dimensions = [ 108.0000, 66.0000, 4.0000 ]" in vmdl and "origin = [ 0.0000, 0.0000, 2.0000 ]" in vmdl, "floor box missing from the new model")

vmat = open(os.path.join(EXPORT, MATS, f"{NAME}.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 5, "expected five textures")
for tex in textures:
    check(os.path.exists(os.path.join(EXPORT, tex)), f"missing {tex}")
for name in re.findall(r'filename = "([^"]+)"', vmdl):
    check(os.path.exists(os.path.join(EXPORT, name)), f"vmdl names missing file {name}")
check(f'to = "{MATS}/{NAME}.vmat"' in vmdl, "vmdl doesn't remap to the new material")

report["in_assets"] = [p for p in ("models/props/boxyard/skip_v2", MATS) if os.path.exists(os.path.join(ASSETS, p))]
report["compiled_files"] = [f for d in (NEW, os.path.join(EXPORT, MATS)) for f in os.listdir(d) if f.endswith("_c")]
# Other sessions install their own props into this map, so only the skip's own geometry has to stay as committed.
committed = subprocess.run(["git", "show", "HEAD:Assets/models/maps/boxyard/boxyard_props.obj"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout


def skip_faces(lines):
    v, current, out = [], None, []
    for line in lines:
        if line.startswith("v "):
            v.append(line[2:].strip())
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current == "bx_skip_green":
            out.append(tuple(v[int(t.split("/")[0]) - 1] for t in line.split()[1:]))
    return out


now = skip_faces(open(os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj"), encoding="utf-8"))
check(now == skip_faces(committed.splitlines()), "the old skip's geometry changed")
report["old_skip_as_committed"] = len(now)
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
