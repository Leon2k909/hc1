"""Check the sofas from their files: python verify_sofa.py <project root> <export dir>

Each length's parts must face outward, its bounds must fit the old sofa's numbers, its collision box must be the old one, its
textures must exist, and the old sofa's reception copy must be as committed. Compiling and seeing it in s&box is not covered.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, EXPORT = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(EXPORT, "models/props/veridant/sofa_v2")
MATS = "materials/veridant/sofa_v2"
OLD_OBJ = "models/maps/veridant/veridant_buildings.obj"
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


def old_reception(lines):
    """The 84 in sofa at reception, as text: the one copy on the ground floor at engine (270, -60)."""
    v, current, out = [], None, []
    for line in lines:
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in ("vr_sofa", "vr_cushion", "vr_black"):
            corners = [v[int(t.split("/")[0]) - 1] for t in line.split()[1:]]
            if all(abs(float(c[2]) - 270) < 18.5 and abs(float(c[0]) + 60) < 42.5 and -0.5 < float(c[1]) < 33.5 for c in corners):
                out.append(tuple(tuple(c) for c in corners))
    return out


for length in (84, 96, 120):
    name = f"sofa_{length}"
    report[name] = {}
    # From the map script: x +-18, y +-length / 2, z up to 33 at the back's top.
    want_lo, want_hi = np.array((-18.0, -length / 2, 0.0)), np.array((18.0, length / 2, 33.0))
    for lod in range(4):
        v, f = read_obj(os.path.join(NEW, f"{name}_lod{lod}.obj"))
        lo, hi = v.min(0), v.max(0)
        report[name][f"lod{lod}"] = dict(triangles=f, min=lo.round(2).tolist(), max=hi.round(2).tolist())
        if lod == 0:
            # The scatter pillows stand 0.9 in above the old top: nothing goes over a sofa, and the collision is unchanged.
            check((lo >= want_lo - 0.6).all() and (hi <= want_hi + np.array((0.6, 0.6, 1.0))).all(), f"{name} lod0 goes beyond the old sofa: {lo} {hi}")
            check((np.abs(hi - want_hi)[:2] < 1.5).all() and (np.abs(lo - want_lo)[:2] < 1.5).all(), f"{name} lod0 doesn't fill the old footprint: {lo} {hi}")
        if lod:
            check(f < report[name][f"lod{lod - 1}"]["triangles"], f"{name} lod{lod} isn't lighter")
    outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{name}_lod0.obj"), name], capture_output=True, text=True)
    report[name]["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{name}: {report[name]['outward']}")
    vmdl = open(os.path.join(NEW, f"{name}.vmdl"), encoding="utf-8").read()
    check(f"dimensions = [ 36.0000, {length:.4f}, 30.0000 ]" in vmdl and "origin = [ 0.0000, 0.0000, 15.0000 ]" in vmdl and 'surface_prop = "fabric"' in vmdl, f"{name}: collision box isn't the old one")
    for ref in re.findall(r'filename = "([^"]+)"', vmdl):
        check(os.path.exists(os.path.join(EXPORT, ref)), f"{name}: vmdl names missing {ref}")
    check(f'to = "{MATS}/{name}.vmat"' in vmdl, f"{name}: vmdl doesn't remap to its material")
    vmat = open(os.path.join(EXPORT, MATS, f"{name}.vmat"), encoding="utf-8").read()
    textures = re.findall(r'"(materials/[^"]+\.png)"', vmat)
    check(len(textures) == 5, f"{name}: expected five textures")
    for tex in textures:
        check(os.path.exists(os.path.join(EXPORT, tex)), f"{name}: missing {tex}")

now = old_reception(open(os.path.join(ASSETS, OLD_OBJ), encoding="utf-8"))
committed = subprocess.run(["git", "show", f"HEAD:Assets/{OLD_OBJ}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
was = old_reception(committed.splitlines())
report["old_sofa_faces"] = dict(now=len(now), committed=len(was))
check(len(now) > 0, "the old reception sofa wasn't found")
check(now == was, "the old reception sofa's geometry changed")
report["in_assets"] = [p for p in ("models/props/veridant/sofa_v2", MATS) if os.path.exists(os.path.join(ASSETS, p))]
report["compiled_files"] = [f for d in (NEW, os.path.join(EXPORT, MATS)) for f in os.listdir(d) if f.endswith("_c")]
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
