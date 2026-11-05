"""Record the authored bag positions and make render-only comparison backgrounds.

Does not write any existing asset. python prepare_review.py <project-root>
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverside_map as M
import riverside_parts as P

OUT = ROOT / "output/asset-improvement-20261030/riverside-sandbags"
ASSET = ROOT / "Assets/models/props/riverside/sandbag_v2/review"
OUT.mkdir(parents=True, exist_ok=True)
ASSET.mkdir(parents=True, exist_ok=True)
P.reset()
zones = {name: K.Model() for name in ("riverside_pad", "riverside_store", "riverside_dressing")}
file_of = {id(m): name for name, m in zones.items()}
bags, walls = [], []
old_wall = P.sandbag_wall


def record_bag(m, p, along, size):
    bags.append(dict(zone=file_of[id(m)], position=list(K.to_world(p)), yaw=K.plan_yaw(along), size=list(size), variant=len(bags) % 3))


def record_wall(m, a, b, rows=4, z0=0, seed=0):
    start = len(bags)
    old_wall(m, a, b, rows, z0, seed)
    for bag in bags[start:]:
        row = round((bag["position"][2] - z0 - 2.6) / 5.2)
        bag["tint"] = (.74, .72, .65) if row == 0 else (.86, .84, .78) if row == 1 else (.96, .95, .91)
    walls.append(dict(zone=file_of[id(m)], a=list(K.to_world((a[0], a[1], z0))), b=list(K.to_world((b[0], b[1], z0))), rows=rows, seed=seed, bag_start=start, bags=len(bags) - start))


P.bag, P.sandbag_wall = record_bag, record_wall
M.pad(zones["riverside_pad"])
M.store(zones["riverside_store"])
M.dressing(zones["riverside_dressing"])
assert len(bags) == 54 and len(walls) == 4, (len(bags), walls)
manifest = dict(bags=bags, walls=walls, protected={}, backgrounds={})
for name in zones:
    path = ROOT / "Assets/models/maps/riverside" / (name + ".obj")
    original = path.read_bytes()
    manifest["protected"][str(path.relative_to(ROOT))] = hashlib.sha256(original).hexdigest()
    lines = original.decode("utf-8").splitlines(keepends=True)
    material, removed, kept = None, 0, []
    for line in lines:
        if line.startswith("usemtl "):
            material = line.split()[1]
        if material == "rs_sandbag" and line.startswith("f "):
            removed += 1
        else:
            kept.append(line)
    count = sum(b["zone"] == name for b in bags)
    assert removed == count * 64, (name, count, removed)
    target = ASSET / (name + "_without_bags.obj")
    target.write_bytes("".join(kept).encode("utf-8"))
    shutil.copyfile(path.with_suffix(".mtl"), ASSET / (name + ".mtl"))
    vmdl = path.with_suffix(".vmdl").read_text()
    remaps = re.findall(r'\{\s*from\s*=\s*"[^"]+"\s+to\s*=\s*"[^"]+"\s*\}', vmdl)
    assert remaps
    filename = "models/props/riverside/sandbag_v2/review/" + target.name
    (ASSET / (name + "_without_bags.vmdl")).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ %REMAPS% ] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" name = "background" filename = "%FILENAME%"
 import_translation = [0.0,0.0,0.0] import_rotation = [0.0,0.0,0.0] import_scale = 1.0
 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
 parent_bone = "" import_filter = { exclude_by_default = false exception_list = [] }
} ] }
] } }
'''.replace("%REMAPS%", ',\n'.join(remaps)).replace("%FILENAME%", filename))
    manifest["backgrounds"][name] = dict(bags=count, removed_old_triangles=removed, model="models/props/riverside/sandbag_v2/review/" + name + "_without_bags.vmdl")
    print(name, count, "bags,", removed, "old triangles hidden only in the review copy", flush=True)
scene = ROOT / "Assets/scenes/maps/Riverside/riverside.scene"
manifest["protected"][str(scene.relative_to(ROOT))] = hashlib.sha256(scene.read_bytes()).hexdigest()
(OUT / "review.json").write_text(json.dumps(manifest, indent=2))
print("Recorded", len(bags), "bags in", len(walls), "barricades")
