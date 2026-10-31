"""Check the cash bag v2 from its files: python verify_cash_bag.py <project root> [installed]

Size and origin against the old dev bag (as read from its compiled file by read_old.py), faces outward, normals, UVs, textures. Without
"installed" it also checks that nothing uses it yet. Seeing it in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT = sys.argv[1]
INSTALLED = "installed" in sys.argv[2:]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "Weapons/Special/Cash_Bag/cash_bag_v2")
OLD_MIN, OLD_MAX = np.array((-6.454, -14.506, -0.062)), np.array((6.454, 14.083, 12.055))
failures = []
report = {"old_bounds": [OLD_MIN.tolist(), OLD_MAX.tolist()], "lods": {}}


def check(ok, text):
    if not ok:
        failures.append(text)


for lod in range(3):
    v, vt, vn, f = [], [], [], []
    for line in open(os.path.join(NEW, f"cash_bag_lod{lod}.obj"), encoding="utf-8"):
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
    e = v[:, [2, 0, 1]]
    lo, hi = e.min(0), e.max(0)
    check(agree > 0.97, f"lod{lod}: only {agree:.3f} of faces agree with their normals")
    check(np.isfinite(v).all() and np.isfinite(vt).all(), f"lod{lod}: non-finite values")
    check(((vt >= -1e-4) & (vt <= 1 + 1e-4)).all(), f"lod{lod}: UVs outside the atlas")
    check((lo >= OLD_MIN - 0.25).all() and (hi <= OLD_MAX + 0.25).all(), f"lod{lod}: bounds {lo.round(2)} {hi.round(2)} outside the old bag's")
    check((hi - lo)[1] > 26.0 and (hi - lo)[0] > 11.0 and (hi - lo)[2] > 9.5, f"lod{lod}: much smaller than the old bag: {lo.round(2)} {hi.round(2)}")
    check(abs(lo[2]) < 0.2, f"lod{lod}: its underside moved to z {lo[2]}")
    report["lods"][lod] = dict(triangles=len(f), normals_agree=round(agree, 4), bounds=[lo.round(2).tolist(), hi.round(2).tolist()])

outward = subprocess.run([sys.executable, os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py"), os.path.join(NEW, "cash_bag_lod0.obj"), "cb_bag"], capture_output=True, text=True)
report["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
check(outward.returncode == 0, "solid parts are inside out: " + outward.stdout)

doc = open(os.path.join(NEW, "cash_bag.vmdl"), encoding="utf-8").read()
for ref in re.findall(r'filename = "([^"]+)"', doc) + re.findall(r'to = "([^"]+)"', doc):
    check(os.path.exists(os.path.join(ASSETS, ref)), f"the vmdl names {ref}, which isn't there")
vmat = open(os.path.join(NEW, "cb_bag.vmat"), encoding="utf-8").read()
for tex in re.findall(r'"(weapons/[^"]+\.png)"', vmat):
    check(os.path.exists(os.path.join(ASSETS, tex)), f"missing {tex}")
check(len(re.findall(r'\.png"', vmat)) == 5, "the vmat should name five textures")

users = ["cash_bag.equip", "mount_cash_bag.prefab", "vm_cash_grab.prefab", "w_cash_bag.prefab"]
for name in users:
    text = open(os.path.join(ASSETS, "Weapons/Special/Cash_Bag", name), encoding="utf-8").read()
    if INSTALLED:
        # The package reference may stay: `ZombiesPowerUp`'s Point Boost still loads the old model by name.
        check("cash_bag_v2/cash_bag.vmdl" in text and "models/dev/duffelbag/dufflebag_money.vmdl" not in text, f"{name} doesn't use v2")
    else:
        check("cash_bag_v2" not in text, f"{name} already uses v2")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
