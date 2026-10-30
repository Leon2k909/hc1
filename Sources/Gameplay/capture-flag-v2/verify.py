"""Check the installed capture flag from its files, and that the game uses it and nothing still asks for the old model.

python verify.py <project root>
Exit code 1 and a list of failures if anything's wrong. Compiling and seeing it in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
MODEL = os.path.join(ASSETS, "models/gameplay/capture_flag_v2")
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


def read_obj(path):
    v, vt, vn, faces = [], [], [], []
    current = None
    used = set()
    for line in open(path, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            v.append(line[2:].split())
        elif tag == "vt":
            vt.append(line[3:].split())
        elif tag == "vn":
            vn.append(line[3:].split())
        elif line.startswith("usemtl"):
            current = line.split()[1]
            used.add(current)
        elif tag == "f ":
            faces.append([tuple(int(i) - 1 for i in tok.split("/")) for tok in line.split()[1:]])
    return (np.array(v, float), np.array(vt, float), np.array(vn, float), np.array(faces, int), used)


lowest = None
for lod in range(4):
    v, vt, vn, f, used = read_obj(os.path.join(MODEL, f"capture_flag_lod{lod}.obj"))
    check(f.shape[1:] == (3, 3), f"lod{lod}: not all triangles")
    tri = v[f[:, :, 0]]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(cross, axis=1) * 0.5
    degenerate = int((area < 1e-7).sum())
    check(np.isfinite(v).all() and np.isfinite(vt).all() and np.isfinite(vn).all(), f"lod{lod}: non-finite values")
    check(np.allclose(np.linalg.norm(vn, axis=1), 1, atol=0.01), f"lod{lod}: normals not unit")
    check(vt.min() >= -1e-4 or lod >= 0, f"lod{lod}: uv")
    # Corner normals should agree with their face: otherwise the winding is backwards. Thin cloth and rope ends excepted.
    face_n = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
    corner = vn[f[:, :, 2]].mean(1)
    agree = float(((corner * face_n).sum(1) > 0).mean())
    check(agree > 0.985, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    # OBJ (a, b, c) is the engine's (c, a, b).
    engine = v[:, [2, 0, 1]]
    report["lods"][lod] = dict(
        triangles=len(f),
        degenerate=degenerate,
        normals_agree=round(agree, 4),
        bounds_min=[round(float(x), 2) for x in engine.min(0)],
        bounds_max=[round(float(x), 2) for x in engine.max(0)],
        materials=sorted(used),
    )
    check(abs(engine[:, 2].max() - 102.6) < 0.2, f"lod{lod}: not the old model's 102.6 tall")
    check(abs(engine[:, 2].min()) < 0.2, f"lod{lod}: not standing on the origin")
    check(engine[:, 0].max() > 30, f"lod{lod}: flag no longer flies along +X")
    if lowest is not None:
        check(len(f) < lowest, f"lod{lod}: not fewer triangles than the last")
    lowest = len(f)

outward = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_outward.py"), os.path.join(MODEL, "capture_flag_lod0.obj"), "cf_hardware"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, "solid parts are inside out: " + report["outward"])

doc = open(os.path.join(MODEL, "capture_flag.vmdl"), encoding="utf-8").read()
remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', doc))
for lod in range(4):
    check(f"capture_flag_lod{lod}.obj" in doc, f"vmdl lacks lod{lod}")
for name, rel in remaps.items():
    path = os.path.join(ASSETS, rel)
    check(os.path.exists(path), f"missing {rel}")
    text = open(path, encoding="utf-8").read()
    for tex in re.findall(r'"(materials/[^"]+\.(?:png|tga))"', text):
        if tex.startswith("materials/default/"):
            continue
        p = os.path.join(ASSETS, tex)
        check(os.path.exists(p), f"{rel}: missing {tex}")
        if os.path.exists(p):
            with Image.open(p) as im:
                w, h = im.size
            check(w & (w - 1) == 0 and h & (h - 1) == 0, f"{tex}: {w}x{h} is not a power of two")
    tint = float(re.search(r'g_flModelTintAmount "([\d.]+)"', text).group(1))
    check((tint > 0) == (name == "cf_cloth"), f"{name}: only the cloth should take the team tint")

# The game asks for the new model in its three places, and for the old one nowhere.
NEW = "models/gameplay/capture_flag_v2/capture_flag.vmdl"
for rel in ("Code/GameLoop/Rules/Domination/DominationManager.cs", "Code/GameLoop/Rules/Hardpoint/HardpointManager.cs", "Assets/prefabs/gamemode_prefabs/capture_point.prefab"):
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    check(NEW in text, f"{rel} doesn't use the new model")
    check("flag_pole_base" not in text, f"{rel} still names the old model")
check(not os.path.exists(os.path.join(ASSETS, "models/gameplay/flag_pole_base")), "the old model is still in Assets")
keep = os.path.join(ROOT, "output/asset-improvement-20261030/capture-flag/retired-flag_pole_base")
check(os.path.exists(os.path.join(keep, "flag_pole_base.fbx")), "the rollback copy is missing")

report["texture_bytes_png"] = sum(os.path.getsize(os.path.join(ASSETS, "materials/gameplay/capture_flag_v2", f)) for f in os.listdir(os.path.join(ASSETS, "materials/gameplay/capture_flag_v2")) if f.endswith(".png"))
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
