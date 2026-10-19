"""Patch Lowtide's existing dressing OBJs without discarding independently edited meshes.

The full Lowtide generator can omit detail subsequently added to the live OBJs.
Replace only the old street bollard faces and their matching physics-box origins.
"""
import re
import shutil
from pathlib import Path

import map_kit as K
import railhead_props as P
import railhead_map as R

ROOT = K.ROOT
LIVE = ROOT / "Assets/models/maps/lowtide"
BACKUP = ROOT / "output/lowtide/bollards-20261017/before"
STREET_E = tuple(range(1050, 2200, 160))
MARKER = "# Lowtide street bollards: sealed smooth caps, pavement contact"


def replace(side):
    name = f"lowtide_dress_{side}"
    target = LIVE / f"{name}.obj"
    physics = LIVE / f"{name}.vmdl"
    source = target.read_text(encoding="utf-8")
    if MARKER in source:
        raise RuntimeError(f"{name}: retrofit already installed")

    backup = BACKUP / target.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    shutil.copy2(physics, BACKUP / physics.name)

    # Work in world coordinates: plan (e,n,z) becomes (n,-e,z).
    old_positions = {(round(float(x), 3), round(float(z), 3))
                     for e in STREET_E for x, _, z in
                     (map(float, K.obj_vector(K.to_world((e if side == 'east' else -e, 1205, 5))).split()),)}
    old_vertices = set()
    vertex_count = uv_count = normal_count = 0
    for line in source.splitlines():
        if line.startswith("v "):
            vertex_count += 1
            _, x, y, z = line.split()
            if any(abs(float(x)-cx) <= 2.05 and abs(float(z)-cz) <= 2.05
                   for cx, cz in old_positions) and 4.9 <= float(y) <= 44.41:
                old_vertices.add(vertex_count)
        elif line.startswith("vt "):
            uv_count += 1
        elif line.startswith("vn "):
            normal_count += 1

    m = K.Model()
    for e in STREET_E:
        P.bollard(m, e if side == 'east' else -e, 1193, 5, illuminated=True)
    R.configure(m)
    # Shared production material mapping is unchanged.
    temp = BACKUP.parent / f"{name}_new_posts.obj"
    K.write_obj(temp, m, name)
    added = {"v": [], "vt": [], "vn": [], "f": []}
    paint = None
    for line in temp.read_text(encoding="utf-8").splitlines():
        if line.startswith("usemtl "):
            paint = line
        elif line.startswith(("v ", "vt ", "vn ")):
            added[line.split(" ", 1)[0]].append(line)
        elif line.startswith("f "):
            refs = []
            for item in line.split()[1:]:
                v, t, n = map(int, item.split("/"))
                refs.append(f"{v+vertex_count}/{t+uv_count}/{n+normal_count}")
            added["f"].append((paint, "f " + " ".join(refs)))

    removed = 0
    expected_removed = sum(
        line.startswith("f ") and all(int(ref.split("/")[0]) in old_vertices for ref in line.split()[1:])
        for line in source.splitlines()
    )
    if not 600 <= expected_removed <= 900:
        raise RuntimeError(f"{name}: unexpected bollard face count {expected_removed}")
    with target.open("w", encoding="utf-8", newline="\n") as out:
        for line in source.splitlines():
            if line.startswith("f ") and all(int(ref.split("/")[0]) in old_vertices for ref in line.split()[1:]):
                removed += 1
                continue
            out.write(line + "\n")
        out.write(MARKER + "\n")
        for key in ("v", "vt", "vn"):
            for line in added[key]:
                out.write(line + "\n")
        last_paint = None
        for material, line in added["f"]:
            if material != last_paint:
                out.write(material + "\n")
                last_paint = material
            out.write(line + "\n")
    assert removed == expected_removed, (name, removed, expected_removed)

    # Keep every pre-existing physics shape, update only eight matching street posts.
    contents = physics.read_text(encoding="utf-8")
    changed = 0
    for e in STREET_E:
        world = K.to_world((e if side == 'east' else -e, 1205, 5))
        old = f"origin = [ {world[0]:.4f}, {world[1]:.4f}, 24.7000 ]"
        new = f"origin = [ 1193.0000, {world[1]:.4f}, 24.7000 ]"
        if contents.count(old) != 1:
            raise RuntimeError(f"{name}: expected exactly one collision box {old}")
        contents = contents.replace(old, new)
        changed += 1
    physics.write_text(contents, encoding="utf-8")
    print(f"{name}: removed {removed} old triangles, added {len(added['f'])} new triangles, moved {changed} collision boxes")


if __name__ == "__main__":
    for side in ("east", "west"):
        replace(side)
