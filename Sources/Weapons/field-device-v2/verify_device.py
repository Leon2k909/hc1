"""Check field device v2 from its files: python verify_device.py <project root>

LOD 0 must be the right way out, every LOD must fit the old model's bounds and agree with its normals, every key must be
where the old model's is, every texture a vmat names must exist, and everything that shows the device must ask for v2.
Compiling and seeing it in s&box is not covered by this. OBJ (a, b, c) is engine (c, a, b).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
ASSETS = os.path.join(ROOT, "Assets")
C4 = os.path.join(ASSETS, "Weapons", "C4")
NEW = os.path.join(C4, "field_device_v2")
failures = []
report = {"lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


def positions(path):
    return np.array([line[2:].split() for line in open(path, encoding="utf-8") if line[:2] == "v "], float)[:, [2, 0, 1]]


old = positions(os.path.join(C4, "field_device", "field_device.obj"))
old_min, old_max = old.min(0), old.max(0)
report["old_bounds"] = dict(min=old_min.round(3).tolist(), max=old_max.round(3).tolist())

for lod in range(4):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"field_device_lod{lod}.obj"), encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            v.append(line[2:].split())
        elif tag == "vt":
            vt.append(line[3:].split())
        elif tag == "vn":
            vn.append(line[3:].split())
        elif tag == "f ":
            f.append([tuple(int(i) - 1 for i in tok.split("/")) for tok in line.split()[1:]])
    v, vt, vn, f = np.array(v, float), np.array(vt, float), np.array(vn, float), np.array(f, int)
    tri = v[f[:, :, 0]]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    face_n = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
    agree = float(((vn[f[:, :, 2]].mean(1) * face_n).sum(1) > 0).mean())
    engine = v[:, [2, 0, 1]]
    check(agree > 0.985, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    check(np.isfinite(v).all() and np.isfinite(vt).all(), f"lod{lod}: non-finite values")
    check((vt >= 0).all() and (vt <= 1).all(), f"lod{lod}: UVs outside the atlas")
    if lod == 0:
        check((np.abs(engine.min(0) - old_min) < 0.06).all(), f"lod0: minimum {engine.min(0)} differs from the old {old_min}")
        check((np.abs(engine.max(0) - old_max) < 0.06).all(), f"lod0: maximum {engine.max(0)} differs from the old {old_max}")
    else:
        check((engine.min(0) > old_min - 0.06).all() and (engine.max(0) < old_max + 0.06).all(), f"lod{lod}: outside the old bounds")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds_min=engine.min(0).round(3).tolist(), bounds_max=engine.max(0).round(3).tolist())
    if lod == 0:
        # The old keys' centres, worked out as Tools/build_field_device.py does, against the new key tops.
        worst = 0.0
        for row in range(4):
            for col in range(3):
                ua = 0.123 + col * 0.091
                va = 0.674 + row * 0.066
                cy = (0.25 - (ua + ua + 0.069) / 2) / 0.494 * 7.25
                cx = (0.75 - (va + va + 0.05) / 2) / 0.494 * 8.9
                tops = engine[(engine[:, 2] > 4.1) & (np.abs(engine[:, 0] - cx) < 0.6) & (np.abs(engine[:, 1] - cy) < 0.66)]
                check(len(tops) > 0, f"no key top near the old key at {cx:.2f}, {cy:.2f}")
                if len(tops):
                    centre = (tops.min(0) + tops.max(0)) / 2
                    worst = max(worst, float(np.hypot(centre[0] - cx, centre[1] - cy)))
        report["worst_key_offset"] = round(worst, 3)
        check(worst < 0.03, f"a key is {worst:.3f} from the old key's centre")

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "field_device_lod0.obj"), "fd_device"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines() if outward.stdout else outward.stderr
check(outward.returncode == 0, "parts are inside out: " + str(report["outward"]))

vmat = open(os.path.join(NEW, "fd_device.vmat"), encoding="utf-8").read()
textures = re.findall(r'"(weapons/c4/field_device_v2/[^"]+\.png)"', vmat)
report["textures"] = textures
check(len(textures) == 6, "the vmat should name six textures")
for tex in textures:
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
vmdl = open(os.path.join(NEW, "field_device.vmdl"), encoding="utf-8").read()
for path in re.findall(r'"(weapons/c4/field_device_v2/[^"]+)"', vmdl):
    check(os.path.exists(os.path.join(ASSETS, path)), f"the vmdl names {path}, which is missing")
check(vmdl.count('_class = "LODGroup"') == 4, "the vmdl should have four LOD groups")

# Everything that shows the device uses v2, and the scripts that write those files wouldn't bring the old one back.
OLD_PATH = "weapons/c4/field_device/field_device.vmdl"
NEW_PATH = "weapons/c4/field_device_v2/field_device.vmdl"
users = [os.path.join(C4, name) for name in ("vm_c4.prefab", "wm_c4.prefab", "planted_c4.prefab", "mount_c4.prefab", "weapon_c4.prefab", "c4.equip")]
users += [os.path.join(ROOT, "Tools", name) for name in ("configure_defuse.py", "configure_defuse_world.py")]
for path in users:
    text = open(path, encoding="utf-8").read()
    check(NEW_PATH in text, f"{os.path.basename(path)} doesn't use v2")
    check(OLD_PATH not in text, f"{os.path.basename(path)} still names the old model")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
