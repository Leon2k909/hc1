"""Correct the installed Lowtide lamp heads without rebuilding the dressing meshes.

The canonical placement is in lowtide_map.py / lowtide_lamps.py. This migration
rotates only the hood, diffuser and top collar in existing OBJ files. All other
render faces, collision sources, materials and scene objects are left alone.

    python Tools/lowtide_lamp_orientation.py           # inspect, no changes
    python Tools/lowtide_lamp_orientation.py --apply   # update installed OBJ files
"""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import lowtide_lamps as L
import map_kit as K


PAINTS = {L.COAT, L.TRIM, L.LENS, "rw_steel_grey"}
EXPECTED_HEAD_FACES = Counter({L.COAT: 1158, L.LENS: 668, L.TRIM: 380, "rw_steel_grey": 4})


def turn(x, n, facing):
    """Rotate OBJ plan axes: the builder's +north head to its road-facing axis."""
    if facing == "-n":
        return -x, -n
    if facing == "-e":  # OBJ x is the negative of the builder's east axis.
        return n, -x
    if facing == "+e":
        return -n, x
    raise ValueError(f"Unsupported facing {facing}")


def fix(path, side, apply):
    source = path.read_text(encoding="utf-8").splitlines(keepends=True)
    vertices, normals = [None], [None]  # OBJ indices begin at one.
    last_vertex_line = last_normal_line = -1
    for index, line in enumerate(source):
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:4])))
            last_vertex_line = index
        elif line.startswith("vn "):
            normals.append(tuple(map(float, line.split()[1:4])))
            last_normal_line = index

    poses = L.placements(side)
    poles = [(-e, n, height + z0, facing) for e, n, height, z0, facing in poses]
    candidates = defaultdict(list)
    lens_offset = defaultdict(lambda: [0.0, 0.0, 0])
    paint = None
    for line_number, line in enumerate(source):
        if line.startswith("usemtl "):
            paint = line.split()[1]
        if not line.startswith("f ") or paint not in PAINTS:
            continue
        refs = [item.split("/") for item in line.split()[1:]]
        if any(len(item) != 3 or not item[0].isdigit() or not item[2].isdigit() for item in refs):
            raise ValueError(f"Unexpected face reference at line {line_number + 1}")
        points = [vertices[int(item[0])] for item in refs]
        for pole_id, (cx, cn, top, facing) in enumerate(poles):
            # All heads fit inside 40 inches of their posts. Leave the full-height
            # shaft and its low access cover exactly where they were.
            if not all(abs(x - cx) < 40 and abs(n - cn) < 40 and
                       top - 7.02 <= z <= top + 5.52 for x, z, n in points):
                continue
            candidates[pole_id].append((line_number, paint, refs))
            if paint == L.LENS:
                offset = lens_offset[pole_id]
                for x, _z, n in points:
                    offset[0] += x - cx
                    offset[1] += n - cn
                    offset[2] += 1
            break

    old, correct = [], []
    for pole_id, (_cx, _cn, _top, facing) in enumerate(poles):
        dx, dn, count = lens_offset[pole_id]
        if count < 100 or len(candidates[pole_id]) < 100:
            raise ValueError(f"Lamp {pole_id}: cannot identify its head ({count} lens vertices)")
        dx, dn = dx / count, dn / count
        expected = turn(0, 13, facing)
        if dn > 5 and abs(dx) < 5:
            old.append(pole_id)
        elif dx * expected[0] + dn * expected[1] > 60:
            correct.append(pole_id)
        else:
            raise ValueError(f"Lamp {pole_id}: unexpected lens direction ({dx:.2f}, {dn:.2f})")
        materials = Counter(paint for _, paint, _ in candidates[pole_id])
        if materials != EXPECTED_HEAD_FACES:
            raise ValueError(f"Lamp {pole_id}: unexpected head topology {dict(materials)}")
        print(f"  {pole_id}: head ({dx:+.1f}, {dn:+.1f}) target {facing}; {dict(materials)}")
    if old and correct:
        raise ValueError(f"Mixed old and fixed heads in {path}: {old}, {correct}")
    if correct:
        print(f"{path.name}: all {len(correct)} heads already face the roads")
        return
    print(f"{path.name}: {len(old)} heads need turning")
    if not apply:
        return

    new_vertices, new_normals, replacements = [], [], {}
    vertex_ids, normal_ids = {}, {}
    for pole_id, (_cx, _cn, _top, facing) in enumerate(poles):
        cx, cn, top, facing = poles[pole_id]
        for line_number, _paint, refs in candidates[pole_id]:
            updated = []
            for v, vt, vn in refs:
                vi, ni = int(v), int(vn)
                vkey, nkey = (pole_id, vi), (pole_id, ni)
                if vkey not in vertex_ids:
                    x, z, n = vertices[vi]
                    xr, nr = turn(x - cx, n - cn, facing)
                    vertex_ids[vkey] = len(vertices) + len(new_vertices)
                    new_vertices.append(f"v {cx + xr:.3f} {z:.3f} {cn + nr:.3f}\n")
                if nkey not in normal_ids:
                    nx, nz, nn = normals[ni]
                    nxr, nnr = turn(nx, nn, facing)
                    normal_ids[nkey] = len(normals) + len(new_normals)
                    new_normals.append(f"vn {nxr:.6f} {nz:.6f} {nnr:.6f}\n")
                updated.append(f"{vertex_ids[vkey]}/{vt}/{normal_ids[nkey]}")
            replacements[line_number] = "f " + " ".join(updated) + "\n"

    # Create the finished content beside the existing file, then replace it
    # only after writing it completely. Existing references keep their indices.
    destination = path.with_name(path.name + ".lamp-turn.tmp")
    try:
        with destination.open("w", encoding="utf-8", newline="") as stream:
            for number, line in enumerate(source):
                stream.write(replacements.get(number, line))
                if number == last_vertex_line:
                    stream.writelines(new_vertices)
                if number == last_normal_line:
                    stream.writelines(new_normals)
        destination.replace(path)
    finally:
        if destination.exists():
            destination.unlink()
    print(f"{path.name}: rotated {len(replacements)} faces, added {len(new_vertices)} vertices / "
          f"{len(new_normals)} normals; no other faces modified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for side, name in ((1, "lowtide_dress_east"), (-1, "lowtide_dress_west")):
        fix(K.ASSETS / "models/maps/lowtide" / (name + ".obj"), side, args.apply)
