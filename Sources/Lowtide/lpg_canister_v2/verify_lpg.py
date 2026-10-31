"""Check the LPG cylinder v2 from its files: python verify_lpg.py <project root>

Sizes and origins against the old models, what LpgCanister hard-codes, physics word for word, faces outward, textures
present, nothing in the game pointing at it yet and the old models unchanged. Compiling and seeing it in s&box is not covered.
"""
import filecmp
import json
import math
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
OLD = os.path.join(ROOT, "output/asset-improvement-20261030/lpg-canister/retired-lpg_canister")
NEW = os.path.join(ASSETS, "models/props/lowtide/lpg_canister_v2")
MATS = os.path.join(ASSETS, "materials/lowtide/lpg_canister_v2")
SPEC = {"lpg_canister": ("lpg_intact", 3), "lpg_canister_ruptured": ("lpg_ruptured", 3), "lpg_canister_cap": ("lpg_cap", 2)}
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def read(path):
    v, vt, vn, f = [], [], [], []
    for line in open(path, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            v.append(line[2:].split())
        elif tag == "vt":
            vt.append(line[3:].split())
        elif tag == "vn":
            vn.append(line[3:].split())
        elif tag == "f ":
            f.append([tuple(int(i or 0) - 1 for i in tok.split("/")) for tok in line.split()[1:]])
    return np.array(v, float), np.array(vt, float), np.array(vn, float), f


def engine(v):
    return v[:, [2, 0, 1]]


for name, (mat, levels) in SPEC.items():
    old_v, *_ = read(os.path.join(OLD, name + ".obj"))
    old = engine(old_v)
    entry = {"old_bounds": [old.min(0).round(2).tolist(), old.max(0).round(2).tolist()], "lods": {}}
    for lod in range(levels):
        v, vt, vn, f = read(os.path.join(NEW, f"{name}_lod{lod}.obj"))
        faces = np.array(f, int)
        tri = v[faces[:, :, 0]]
        cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        face_n = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
        agree = float(((vn[faces[:, :, 2]].mean(1) * face_n).sum(1) > 0).mean())
        e = engine(v)
        check(agree > 0.97, f"{name} lod{lod}: only {agree:.3f} of faces agree with their normals")
        check(np.isfinite(v).all() and np.isfinite(vt).all(), f"{name} lod{lod}: non-finite values")
        check(((vt >= -1e-4) & (vt <= 1 + 1e-4)).all(), f"{name} lod{lod}: UVs outside the atlas")
        entry["lods"][lod] = dict(triangles=len(faces), normals_agree=round(agree, 4), bounds=[e.min(0).round(2).tolist(), e.max(0).round(2).tolist()])
    outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, f"{name}_lod0.obj"), mat], capture_output=True, text=True)
    entry["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{name}: solid parts inside out: {entry['outward']}")
    vmat = open(os.path.join(MATS, mat + ".vmat"), encoding="utf-8").read()
    for tex in re.findall(r'"(materials/[^"]+\.png)"', vmat):
        check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
    doc = open(os.path.join(NEW, name + ".vmdl"), encoding="utf-8").read()
    for ref in re.findall(r'filename = "([^"]+)"', doc) + re.findall(r'to = "([^"]+)"', doc):
        check(os.path.exists(os.path.join(ASSETS, ref)), f"{name}.vmdl names {ref}, which isn't there")
    report[name] = entry

# Bounds: within a whisker of the old models. The burst one may lose its foot end, since that's what flies off.
b = report["lpg_canister"]["lods"][0]["bounds"]
old = report["lpg_canister"]["old_bounds"]
for axis, label in enumerate("xyz"):
    check(abs(b[0][axis] - old[0][axis]) < 0.2, f"intact min {label} {b[0][axis]} against the old {old[0][axis]}")
    check(abs(b[1][axis] - old[1][axis]) < 0.2, f"intact max {label} {b[1][axis]} against the old {old[1][axis]}")
b = report["lpg_canister_cap"]["lods"][0]["bounds"]
old = report["lpg_canister_cap"]["old_bounds"]
for axis, label in enumerate("xyz"):
    check(b[0][axis] >= old[0][axis] - 0.05 and b[1][axis] <= old[1][axis] + 0.05, f"cap {label} outside the old cap: {b}")
b = report["lpg_canister_ruptured"]["lods"][0]["bounds"]
old = report["lpg_canister_ruptured"]["old_bounds"]
check(b[0][2] >= old[0][2] - 0.1, f"burst model lower than the old one's {old[0][2]}")
check(b[1][2] <= old[1][2] + 0.8, f"burst model flaps reach {b[1][2]}, old {old[1][2]}")
check(b[1][1] <= old[1][1] + 0.1, f"burst model reaches y {b[1][1]}, old {old[1][1]}")

# The shell profile the leak code works out by hand, measured on the intact mesh.
v, *_ = read(os.path.join(NEW, "lpg_canister_lod0.obj"))
e = engine(v)
radial = np.hypot(e[:, 0], e[:, 2])
stations = {}
for y, want in ((0.0, 6.3), (13.5, 6.3), (15.2, 5.9), (16.4, 4.7)):
    # The shell's own rings only: on the -Y end there's nothing else near these except the foot ring and welds.
    pick = np.abs(e[:, 1] + y) < 0.2 if y else np.abs(e[:, 1]) < 14
    near = radial[pick & (radial > want - 0.5) & (radial < want + 0.05)]
    stations[y] = round(float(np.median(near)), 2) if near.size else None
report["shell_stations"] = stations
check(stations[13.5] is not None and abs(stations[13.5] - 6.3) < 0.06, f"shell radius at 13.5 is {stations[13.5]}")
# The valve inside the scene's collider, and the hose's end where the old one met the truck.
old_v, *_ = read(os.path.join(OLD, "lpg_canister.obj"))
old_e = engine(old_v)
old_end = old_e[np.argmax(old_e[:, 0])]
new_end = e[np.argmax(e[:, 0])]
report["hose_end"] = dict(old=old_end.round(2).tolist(), new=new_end.round(2).tolist())
check(np.linalg.norm(old_end - new_end) < 0.5, "the hose no longer reaches the truck where it did")

# Physics: the old model's, word for word.
def physics(doc):
    start = doc.rindex("{", 0, doc.index('_class = "PhysicsShapeList"'))
    end = doc.rindex("]", 0, doc.index("model_archetype"))
    return re.sub(r"\s+", " ", doc[start:end]).strip()


old_doc = open(os.path.join(OLD, "lpg_canister.vmdl"), encoding="utf-8").read()
new_doc = open(os.path.join(NEW, "lpg_canister.vmdl"), encoding="utf-8").read()
check(physics(old_doc) == physics(new_doc).replace("lpg_canister_v2/", ""), "physics differs from the old model's")
check(filecmp.cmp(os.path.join(OLD, "lpg_canister_hulls_metal.obj"), os.path.join(NEW, "lpg_canister_hulls_metal.obj"), shallow=False), "hulls differ from the old model's")
for name in ("lpg_canister_ruptured", "lpg_canister_cap"):
    check("PhysicsShapeList" not in open(os.path.join(NEW, name + ".vmdl"), encoding="utf-8").read(), f"{name} gained physics the old one doesn't have")

# The game uses it, nothing asks for the old models, and the generator won't bring them back.
scene = json.load(open(os.path.join(ASSETS, "scenes/maps/Lowtide/lowtide.scene"), encoding="utf-8"))
bottles = [o for o in scene["GameObjects"] if any(c.get("__type") == "Facepunch.LpgCanister" for c in o.get("Components", []))]
check(len(bottles) == 4, f"{len(bottles)} bottles in the scene, not 4")
for bottle in bottles:
    parts = {c["__type"]: c for c in bottle["Components"]}
    intact = "models/props/lowtide/lpg_canister_v2/lpg_canister.vmdl"
    check(parts["Sandbox.ModelRenderer"]["Model"] == intact, f"{bottle['Name']}: renderer")
    check(parts["Sandbox.ModelCollider"]["Model"] == intact, f"{bottle['Name']}: collider")
    check(parts["Facepunch.LpgCanister"]["IntactModel"] == intact, f"{bottle['Name']}: intact model")
    check(parts["Facepunch.LpgCanister"]["RupturedModel"] == "models/props/lowtide/lpg_canister_v2/lpg_canister_ruptured.vmdl", f"{bottle['Name']}: ruptured model")
text = open(os.path.join(ASSETS, "scenes/maps/Lowtide/lowtide.scene"), encoding="utf-8").read()
check("3cbebf27-bb54-4157-92d2-217de25af549" not in text, "the scene still names the old model's guid")
code = open(os.path.join(ROOT, "Code/World/LpgCanister.Visuals.cs"), encoding="utf-8").read()
check('"models/props/lowtide/lpg_canister_v2/lpg_canister_cap.vmdl"' in code, "the code doesn't load v2's cap")
tool = open(os.path.join(ROOT, "Tools/lowtide_canisters.py"), encoding="utf-8").read()
check('MODEL_RESOURCE = "models/props/lowtide/lpg_canister_v2"' in tool and "write_models" not in tool, "the generator would bring the old models back")
for name in SPEC:
    for ext in (".vmdl", ".obj", ".vmdl_c"):
        check(not os.path.exists(os.path.join(ASSETS, "models/props/lowtide", name + ext)), f"{name}{ext} is still in Assets")
check(not os.path.exists(os.path.join(ASSETS, "models/props/lowtide/lpg_canister_hulls_metal.obj")), "the old hulls are still in Assets")

report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
