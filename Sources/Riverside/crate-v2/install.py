"""Prepare precise cuts of the twelve old crates, retaining collision and every unrelated face.

python install.py <project-root> [--apply]
The scene group is applied and saved separately through the running editor.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverside_map as M
import riverside_parts as P

OUT = ROOT / "output/asset-improvement-20261030/riverside-crate/installed"
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / "before-install"
P.reset()
zones = {name: K.Model() for name in ("riverside_pad", "riverside_store", "riverside_dressing")}
M.pad(zones["riverside_pad"])
M.store(zones["riverside_store"])
M.dressing(zones["riverside_dressing"])
file_of = {id(model): name for name, model in zones.items()}
spots = [dict(zone=file_of[id(owner)], plan=list(position), position=list(K.to_world(position)), yaw=yaw, size=list(size))
         for owner, position, yaw, size in P.CRATES]
assert len(spots) == 12, spots
group = K.game_object(M.ids, "Supply Crates", "supply_crates", children=M.crate_objects())
(OUT / "placements.json").write_text(json.dumps(dict(spots=spots, group=group), indent=2))


def old_mesh(spot):
    """Archived reconstruction used only to recognise the old face positions, never for gameplay."""
    m = K.Model()
    c = spot["plan"]
    angle = math.radians(spot["yaw"])
    along = P.v(math.cos(angle), math.sin(angle), 0)
    side = np.cross(P.UP, along)
    L, W, H = spot["size"]
    centre = P.v(c[0], c[1], c[2] + H / 2)
    P.obox(m, centre, along, (L, W, H), "rs_crate")
    for sign in (-1, 1):
        for k in (-.48, .48):
            P.obox(m, centre + side * (W / 2 + .3) * sign + along * (L * k), along, (2.5, .8, H), "rs_wood")
        P.obox(m, centre + side * (W / 2 + .3) * sign, along, (L, .8, 2.2), "rs_wood")
    P.sign(m, "crate_label", centre + side * (W / 2 + .75), P.right_for(side), H * .45, off=0)
    return m


prepared = []
report = []
for name in zones:
    wanted = {}
    for spot in (s for s in spots if s["zone"] == name):
        for material, polygons in old_mesh(spot).polygons.items():
            for points, normal in polygons:
                world = [K.to_world(p) for p in points]
                wanted.setdefault(material, []).extend(world)
    trees = {material: cKDTree(points) for material, points in wanted.items()}
    if name == "riverside_pad":
        pad_trees = trees
    path = ROOT / "Assets/models/maps/riverside" / (name + ".obj")
    original = path.read_bytes()
    lines = original.decode("utf-8").splitlines(keepends=True)
    vertices = [(float(p[2]), float(p[0]), float(p[1])) for line in lines if line.startswith("v ") for p in [line.split()[1:4]]]
    drop = set()
    material = None
    by_material = Counter()
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f ") and material in ("rs_crate", "rs_wood", "rs_signs"):
            points = [vertices[int(v.split("/")[0]) - 1] for v in line.split()[1:]]
            # Shared-kit quad triangulation has changed since this map was made. Match the
            # actual authored vertices, so either diagonal is accepted; unrelated plank faces
            # cannot pass merely because they overlap the crate's bounding box.
            if trees[material].query(points)[0].max() < .002:
                drop.add(i)
                by_material[material] += 1
    count = sum(s["zone"] == name for s in spots)
    assert by_material["rs_crate"] == 12 * count, (name, dict(by_material), count)
    assert by_material["rs_wood"] == 72 * count, (name, dict(by_material), count)
    assert by_material["rs_signs"] % 2 == 0
    # No rs_crate faces are allowed to survive in a live model after its old crates are cut.
    remaining = "".join(line for i, line in enumerate(lines) if i not in drop)
    # Drop its now-empty OBJ material directive as well.
    remaining = "".join(line for line in remaining.splitlines(keepends=True) if line.strip() != "usemtl rs_crate")
    prepared.append((path, original, remaining.encode("utf-8")))
    report.append(dict(zone=name, crates=count, removed_triangles=len(drop), materials=dict(by_material), before_sha256=hashlib.sha256(original).hexdigest()))
    print(report[-1], flush=True)

# These two unpublished comparison backgrounds also contain old pad crates. Clean only those
# faces so the obsolete flat crate material has no remaining asset dependants.
for relative in ("Assets/models/props/riverside/crate_v2/review/pad_without_crate.obj",
                 "Assets/models/maps/riverside/lantern-v1/pad_without_lantern.obj"):
    path = ROOT / relative
    if not path.exists():
        continue
    original = path.read_bytes()
    lines = original.decode("utf-8").splitlines(keepends=True)
    vertices = [(float(p[2]), float(p[0]), float(p[1])) for line in lines if line.startswith("v ") for p in [line.split()[1:4]]]
    drop, material, counts = set(), None, Counter()
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f ") and material in pad_trees:
            points = [vertices[int(v.split("/")[0]) - 1] for v in line.split()[1:]]
            if pad_trees[material].query(points)[0].max() < .002:
                drop.add(i)
                counts[material] += 1
    assert counts["rs_crate"] in (12, 24), (relative, dict(counts))
    assert len(drop) in (86, 172), (relative, len(drop))
    replacement = "".join(line for i, line in enumerate(lines) if i not in drop and line.strip() != "usemtl rs_crate")
    prepared.append((path, original, replacement.encode("utf-8")))
    report.append(dict(preview=relative, removed_triangles=len(drop), materials=dict(counts)))
    print(report[-1], flush=True)

if "--apply" in sys.argv:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path, before, after in prepared:
        assert path.read_bytes() == before, "Source changed while preparing " + str(path)
        if not (BACKUP / path.name).exists():
            shutil.copy2(path, BACKUP / path.name)
        incoming = path.with_suffix(".crate-incoming")
        incoming.write_bytes(after)
        incoming.replace(path)
    scene = ROOT / "Assets/scenes/maps/Riverside/riverside.scene"
    if not (BACKUP / "riverside.scene").exists():
        shutil.copy2(scene, BACKUP / "riverside.scene")
(OUT / "mesh-cuts.json").write_text(json.dumps(report, indent=2))
print("Applied mesh cuts" if "--apply" in sys.argv else "Dry run; nothing in Assets was changed")
