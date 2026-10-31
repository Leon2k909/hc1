"""Check the thermite grenade from its files: python verify_thermite.py <project root> <work dir>

Its parts must face outward, it must stay close to the old model's bounds in each body group, the vmdl must keep the old
body groups in order, every texture the vmat names must exist, and the old files and prefabs must be as they were.
Compiling it and seeing it in s&box is not covered by this.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(WORK, "export")
OLD = os.path.join(WORK, "old")
TOOLS = os.path.join(ROOT, "Sources/Gameplay/capture-flag-v2/check_outward.py")
OLD_OF = {"grenade": (0, 1, 2), "spoon": (3, 4, 5), "pin": (6, 7)}
LIMIT = 0.05  # Inches a group may stand past the old one's bounds.
failures = []
report = {}


def check(ok, text):
    if not ok:
        failures.append(text)


def read_obj(path, swap):
    v, f = [], 0
    for line in open(path, encoding="utf-8"):
        if line.startswith("v "):
            v.append(line[2:].split())
        elif line.startswith("f "):
            f += 1
    v = np.array(v, float)
    return (v[:, [2, 0, 1]] if swap else v), f


total = {}
for group, old_ids in OLD_OF.items():
    report[group] = {}
    old_v, old_f = read_obj(os.path.join(OLD, f"old_mesh_{old_ids[0]}.obj"), False)
    lo_old, hi_old = old_v.min(0), old_v.max(0)
    report[group]["old"] = dict(triangles_by_lod=[read_obj(os.path.join(OLD, f"old_mesh_{k}.obj"), False)[1] for k in old_ids], min=lo_old.round(3).tolist(), max=hi_old.round(3).tolist())
    for lod in range(len(old_ids)):
        v, f = read_obj(os.path.join(NEW, f"thermite_grenade_{group}_lod{lod}.obj"), True)
        lo, hi = v.min(0), v.max(0)
        total[lod] = total.get(lod, 0) + f
        report[group][f"lod{lod}"] = dict(triangles=f, min=lo.round(3).tolist(), max=hi.round(3).tolist())
        over = max(float((lo_old - lo).max()), float((hi - hi_old).max()))
        check(over < LIMIT, f"{group} lod{lod} stands {over:.3f} in past the old bounds")
    outward = subprocess.run([sys.executable, TOOLS, os.path.join(NEW, f"thermite_grenade_{group}_lod0.obj"), "thermite_grenade"], capture_output=True, text=True)
    report[group]["outward"] = outward.stdout.splitlines()[0] if outward.stdout else outward.stderr
    check(outward.returncode == 0, f"{group}: {report[group]['outward']}")
report["triangles_by_lod"] = total

vmdl = open(os.path.join(NEW, "thermite_grenade.vmdl"), encoding="utf-8").read()
order = re.findall(r'_class = "BodyGroup" name = "(\w+)"', vmdl)
check(order == ["grenade", "spoon", "pin"], f"body groups are {order}")
check(vmdl.count('name = "none"') == 2, "spoon and pin need an empty second choice, as the old model has")
files = re.findall(r'filename = "([^"]+)"', vmdl)
for rel in files:
    check(os.path.exists(os.path.join(NEW, os.path.basename(rel))), f"missing {rel}")
vmat_rel = re.search(r'to = "([^"]+\.vmat)"', vmdl).group(1)
vmat = open(os.path.join(NEW, os.path.basename(vmat_rel)), encoding="utf-8").read()
textures = re.findall(r'"([^"]+\.png)"', vmat)
for rel in textures:
    check(os.path.exists(os.path.join(NEW, os.path.basename(rel))), f"missing {rel}")
report["textures"] = len(textures)
# The early skin must differ from the main model in its material alone, and that material in its colour map alone.
early = open(os.path.join(NEW, "thermite_grenade_early.vmdl"), encoding="utf-8").read()
check(early.replace("thermite_grenade_early.vmat", "thermite_grenade.vmat") == vmdl, "the early skin's vmdl differs from the main one in more than its material")
early_vmat = open(os.path.join(NEW, "thermite_grenade_early.vmat"), encoding="utf-8").read()
check(early_vmat.replace("thermite_grenade_early_color.png", "thermite_grenade_color.png") == vmat, "the early skin's vmat differs in more than its colour map")
check(os.path.exists(os.path.join(NEW, "thermite_grenade_early_color.png")), "missing the early skin's colour map")
report["compiled_files"] = sorted(f for f in os.listdir(NEW) if f.endswith("_c"))

status = subprocess.run(["git", "status", "--porcelain", "--", "Assets/Weapons/Throwable/Molotov_Cocktail/molotov_grenade.prefab", "Assets/Weapons/Throwable/Molotov_Cocktail/vm_molotov_grenade.prefab", "Assets/Weapons/Throwable/Molotov_Cocktail/wm_molotov_grenade.prefab", "Assets/Weapons/Throwable/Molotov_Cocktail/molotov_grenade.equip", "Assets/Weapons/Throwable/HE_Grenade/mounted/mounted_molotov.prefab"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(status == "", f"the grenade's prefabs changed: {status}")
for name in ("Molotov_Cocktail/molotov_grenade.prefab", "Molotov_Cocktail/vm_molotov_grenade.prefab", "Molotov_Cocktail/wm_molotov_grenade.prefab", "Molotov_Cocktail/molotov_grenade.equip", "HE_Grenade/mounted/mounted_molotov.prefab"):
    text = open(os.path.join(ASSETS, "Weapons/Throwable", name), encoding="utf-8").read()
    check("thermite_grenade_v2" not in text, f"{name} already points at v2")
report["failures"] = failures
print(json.dumps(report, indent=1))
sys.exit(1 if failures else 0)
