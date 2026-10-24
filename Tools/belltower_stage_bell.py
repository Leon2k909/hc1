"""Stage a bell-only replacement; publish through the running editor."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import map_kit as K
import belltower_bell as Bell

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/bell-v2"
STAGE = OUT / "stage"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def keys(model):
    result = Counter()
    for paint, faces in model.polygons.items():
        for points, _ in faces:
            values = [K.obj_vector(K.to_world(p)) for p in points]
            for i in range(1, len(values)-1):
                tri = [values[j] for j in (0, i, i+1)]
                a, b, c = np.array([list(map(float, p.split())) for p in tri])
                if np.linalg.norm(np.cross(b-a, c-a)) > 1e-7:
                    result[(paint, frozenset(tri))] += 1
    return result


def record(path, staged):
    rel = path.relative_to(ROOT)
    backup = OUT / "before" / rel
    before = sha(path) if path.exists() else None
    if before:
        backup.parent.mkdir(parents=True, exist_ok=True)
        assert not backup.exists() or sha(backup) == before
        backup.write_bytes(path.read_bytes())
    return {"before": before, "after": sha(staged), "source": staged.relative_to(ROOT).as_posix(),
            "backup": backup.relative_to(ROOT).as_posix() if before else None}


def main():
    assert not (STAGE / "manifest.json").exists(), "Preserve the existing import receipt."
    STAGE.mkdir(parents=True, exist_ok=True)
    old, new = K.Model(), K.Model()
    Bell.legacy(old, (0, 130))
    Bell.build(new, (0, 130))
    assert not new.boxes and not new.hulls and not new.props
    for paint, faces in new.polygons.items():
        for i, (points, normal) in enumerate(faces):
            ns = new.polygon_normals.get((paint, i))
            for j in range(1, len(points)-1):
                cross = np.cross(points[j]-points[0], points[j+1]-points[0])
                if np.linalg.norm(cross) < 1e-7:
                    continue  # Existing sphere helper's pole fan is harmless.
                assert np.dot(cross, normal) > 0
                if ns:
                    assert np.dot(cross, ns[0]+ns[j]+ns[j+1]) > 0, (paint, i, j)
    piece = STAGE / "bell-only.obj"
    K.write_obj(piece, new, "belltower_centre")
    Bell.materials(STAGE / "Assets" / Bell.RESOURCE)
    source = ROOT / "Assets/models/maps/belltower/belltower_centre.obj"
    initial = sha(source)
    wanted = keys(old)
    wanted_positions = {v for _, tri in wanted for v in tri}
    sparse, counts, found, drop = {}, dict(v=0, vt=0, vn=0), Counter(), set()
    paint = None
    with source.open("rb") as stream:
        for line_no, line in enumerate(stream):
            kind = line.split(b" ", 1)[0].decode()
            if kind in counts:
                counts[kind] += 1
                if kind == "v":
                    value = line[2:].strip().decode()
                    if value in wanted_positions:
                        sparse[counts[kind]] = value
            elif kind == "usemtl":
                paint = line.split()[1].decode()
            elif kind == "f":
                indices = [int(t.split(b"/")[0]) for t in line.split()[1:]]
                if all(i in sparse for i in indices):
                    key = (paint, frozenset(sparse[i] for i in indices))
                    if key in wanted:
                        found[key] += 1
                        drop.add(line_no)
    assert found == wanted, ("Bell matching failed", sum((wanted-found).values()), sum((found-wanted).values()))
    tables, tail = [], []
    for line in piece.open("rb"):
        kind = line.split(b" ", 1)[0].decode()
        if kind in counts:
            tables.append(line)
        elif kind == "usemtl":
            tail.append(line)
        elif kind == "f":
            shifted = []
            for token in line.split()[1:]:
                a, b, c = map(int, token.split(b"/"))
                shifted.append(f'{a+counts["v"]}/{b+counts["vt"]}/{c+counts["vn"]}')
            tail.append(("f " + " ".join(shifted) + "\n").encode())
    kept = b"".join(line for i, line in enumerate(source.read_bytes().splitlines(keepends=True)) if i not in drop)
    insertion = kept.index(b"usemtl ")
    target = STAGE / source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(kept[:insertion]+b"".join(tables)+kept[insertion:]+b"".join(tail))
    assert sha(source) == initial
    manifest = {"revision": "bell-v2", "files": {}, "removed_bell_triangles": len(drop),
                "new_bell_triangles": new.triangle_count(), "all_other_obj_bytes_preserved": True,
                "collision_unchanged": True, "scene_unchanged": True, "yoke_unchanged": True,
                "source_sha256": {p: sha(ROOT/p) for p in ("Tools/belltower_bell.py", "Tools/belltower_stage_bell.py", "Tools/map_kit.py")}}
    manifest["files"][source.relative_to(ROOT).as_posix()] = record(source, target)
    mtl = source.with_suffix(".mtl")
    raw = mtl.read_bytes()
    extra = b"".join(f"newmtl {paint}\nKd 1 1 1\nd 1\n".encode() for paint in Bell.MATERIALS)
    assert all(f"newmtl {paint}\n".encode() not in raw for paint in Bell.MATERIALS)
    staged = target.with_suffix(".mtl")
    staged.write_bytes(raw+extra)
    manifest["files"][mtl.relative_to(ROOT).as_posix()] = record(mtl, staged)
    vmdl = source.with_suffix(".vmdl")
    raw = vmdl.read_bytes()
    anchor = next(line for line in raw.splitlines(keepends=True) if b'from = "fountain_bronze.vmat"' in line)
    indent = anchor[:len(anchor)-len(anchor.lstrip())]
    extra = b"".join(indent + f'{{ from = "{paint}.vmat" to = "{path}" }},\n'.encode() for paint, path in Bell.MATERIALS.items())
    assert raw.count(anchor) == 1
    staged = target.with_suffix(".vmdl")
    staged.write_bytes(raw.replace(anchor, extra+anchor))
    assert staged.read_bytes().replace(extra, b"", 1) == raw
    manifest["files"][vmdl.relative_to(ROOT).as_posix()] = record(vmdl, staged)
    for staged in (STAGE / "Assets" / Bell.RESOURCE).iterdir():
        path = ROOT / staged.relative_to(STAGE)
        manifest["files"][path.relative_to(ROOT).as_posix()] = record(path, staged)
    manifest["protected_sha256"] = {p: sha(ROOT/p) for p in (
        "Assets/materials/belltower/fountain_bronze.vmat",
        "Assets/materials/belltower/fountain_bronze_color.png",
        "Assets/materials/belltower/fountain_bronze_normal.png",
        "Assets/materials/belltower/fountain_bronze_rough.png")}
    (STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("files", "source_sha256", "protected_sha256")}))


if __name__ == "__main__":
    main()
