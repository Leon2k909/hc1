"""Replace only Cerro Blanco's faceted bollards in its active dressing render OBJ.

The scene draws quality-v1/cerroblanco_dressing_v2.vmdl for visuals and keeps the
original dressing vmdl for collisions. Updating the complete dressing model from
the map generator would also replace unrelated museum details. This script instead
removes exactly the ten old 12-sided posts' faces and inserts the updated geometry
from cerroblanco_parts.bollard_light, preserving every other face and both colliders.

    python Tools/cerroblanco_bollards_upgrade.py             # dry run
    python Tools/cerroblanco_bollards_upgrade.py --apply     # publish OBJ only
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import cerroblanco_parts as P
import cerroblanco_map as C
import map_kit as K

ROOT = Path(__file__).resolve().parent.parent
OBJ = ROOT / "Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj"
SCENE = ROOT / "Assets/scenes/maps/CerroBlanco/cerroblanco.scene"
WORK = ROOT / "output/cerroblanco/bollards"
STAGED = WORK / "new_bollards.obj"
BACKUP = WORK / "before" / OBJ.name
POSTS = [(-560.0, -170.0), (400.0, -170.0), (-560.0, 780.0), (430.0, 760.0)]
POSTS += [(float(e), -2470.0) for e in (-1000, -710, -420, -130, 160, 450)]
LEGACY_FACES = {P.FRAME: 34, P.LAMP: 24}


def split_obj(data):
    lines = data.splitlines()
    vertices = []
    uvs = []
    normals = []
    for line in lines:
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith("vt "):
            uvs.append(line)
        elif line.startswith("vn "):
            normals.append(line)
    return lines, vertices, uvs, normals


def old_post_for_face(line, vertices):
    """Use the face's actual XYZ coordinates, never a material-wide replacement."""
    ids = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
    points = [vertices[i] for i in ids]
    # OBJ axes: x=-e, y=z(height), z=n. The legacy band is radius 3.6.
    if not all(-0.01 <= p[1] <= 34.01 for p in points):
        return None
    for index, (e, n) in enumerate(POSTS):
        if all((x + e) ** 2 + (north - n) ** 2 <= 3.72 ** 2
               for x, _, north in points):
            return index
    return None


def remap_faces(lines, vc, tc, nc):
    out = []
    for line in lines:
        if line.startswith("usemtl "):
            out.append(line)
        if not line.startswith("f "):
            continue
        refs = []
        for token in line.split()[1:]:
            a, b, c = map(int, token.split("/"))
            refs.append(f"{a + vc}/{b + tc}/{c + nc}")
        out.append("f " + " ".join(refs))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    assert OBJ.exists()
    assert "models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.vmdl" in SCENE.read_text(encoding="utf-8")
    original = OBJ.read_bytes()
    lines, vertices, uvs, normals = split_obj(original.decode("utf-8"))
    current_material = None
    removed = Counter()
    skipped = Counter()
    updated_lines = []
    for line in lines:
        if line.startswith("usemtl "):
            current_material = line.partition(" ")[2]
        if line.startswith("f ") and current_material in LEGACY_FACES:
            target = old_post_for_face(line, vertices)
            if target is not None:
                removed[(target, current_material)] += 1
                continue
        if line.startswith("f "):
            skipped[current_material] += 1
        updated_lines.append(line)

    expected = {(i, material): count for i in range(len(POSTS))
                for material, count in LEGACY_FACES.items()}
    if dict(removed) != expected:
        raise RuntimeError(f"Unexpected bollard geometry; refusing to edit. Found {sorted(removed.items())}, expected {sorted(expected.items())}")

    model = K.Model()
    for e, n in POSTS:
        P.bollard_light(model, e, n)
    C.configure(model)
    assert len(model.hulls) == len(POSTS)
    WORK.mkdir(parents=True, exist_ok=True)
    fresh_tris = K.write_obj(STAGED, model, STAGED.stem)
    new_lines, new_vertices, new_uvs, new_normals = split_obj(STAGED.read_text(encoding="utf-8"))
    assert {line.split()[1] for line in new_lines if line.startswith("usemtl ")} <= set(LEGACY_FACES)
    assert fresh_tris == 910 * len(POSTS), fresh_tris

    # Put new vertices before the existing UVs, new UVs before normals, and
    # new normals before the first material. All original indices stay valid.
    merged = []
    inserted = set()
    for line in updated_lines:
        if line.startswith("vt ") and "v" not in inserted:
            merged.extend(line_ for line_ in new_lines if line_.startswith("v "))
            inserted.add("v")
        if line.startswith("vn ") and "vt" not in inserted:
            merged.extend(new_uvs)
            inserted.add("vt")
        if line.startswith("usemtl ") and "vn" not in inserted:
            merged.extend(new_normals)
            inserted.add("vn")
        merged.append(line)
    assert inserted == {"v", "vt", "vn"}
    merged.extend(remap_faces(new_lines, len(vertices), len(uvs), len(normals)))
    output = ("\n".join(merged) + "\n").encode("utf-8")
    new_face_count = sum(1 for line in merged if line.startswith("f "))
    old_face_count = sum(1 for line in lines if line.startswith("f "))
    assert new_face_count == old_face_count - sum(removed.values()) + fresh_tris
    result = {
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "new_sha256": hashlib.sha256(output).hexdigest(),
        "legacy_faces_removed": sum(removed.values()),
        "new_faces": fresh_tris,
        "untouched_faces": sum(skipped.values()),
        "old_total_faces": old_face_count,
        "new_total_faces": new_face_count,
        "posts": len(POSTS),
        "scene_or_collision_changed": False,
        "applied": args.apply,
    }
    if args.apply:
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        if BACKUP.exists() and BACKUP.read_bytes() != original:
            raise RuntimeError("Existing backup is from a different version; refusing to overwrite")
        if not BACKUP.exists():
            BACKUP.write_bytes(original)
        # Atomic replace: s&box's asset watcher only sees the complete file.
        K.write_text(OBJ, output.decode("utf-8"))
    (WORK / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
