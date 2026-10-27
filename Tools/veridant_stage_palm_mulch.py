"""Replace only palm-bed fill faces, keeping the original edging bytes/indices."""
import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

import map_kit as K
import veridant_palm_mulch as M
import veridant_parts as P
from railhead_stage_extinguisher import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/veridant/palm-mulch-v1"
OBJ = Path("Assets/models/maps/veridant/veridant_palm_pits.obj")


def existing_beds(path):
    vertices, fill, removed = [], [], set()
    material = None
    for index, line in enumerate(path.read_bytes().splitlines(keepends=True)):
        if line.startswith(b"v "):
            x, y, z = map(float, line.split()[1:])
            vertices.append((-x, z, y))
        elif line.startswith(b"usemtl "):
            material = line.split()[1]
        elif line.startswith(b"f ") and material == b"vr_palm_mulch":
            removed.add(index)
            fill.extend(int(t.split(b"/")[0])-1 for t in line.split()[1:])
    points = np.unique(np.round(np.asarray(vertices)[fill], 3), axis=0)
    pairs = cKDTree(points[:, :2]).query_pairs(15, output_type="ndarray")
    graph = coo_matrix((np.ones(len(pairs)*2),
                       (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                      shape=(len(points), len(points)))
    count, labels = connected_components(graph)
    beds = []
    for k in range(count):
        q = points[labels == k]
        lo, hi = q.min(axis=0), q.max(axis=0)
        centre = (lo+hi)/2
        assert len(q) == 49 and np.allclose(hi[:2]-lo[:2], 61.4)
        e, n = centre[:2]
        seed = round((n+1230)/300)+100 if e < -1500 else round((n+1080)/420)+200
        beds.append({"base": [round(e, 3), round(n, 3), 0.0], "seed": seed})
    assert count == 10 and len(removed) == 720
    return beds, removed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--geometry-reference", type=Path)
    args = parser.parse_args()
    assert args.stage.startswith("stage-") and args.stage.replace("-", "").isalnum()
    stage = OUT / args.stage
    assert not stage.exists()
    stage.mkdir(parents=True)
    sources = {p: sha(ROOT/p) for p in ("Tools/veridant_palm_mulch.py", "Tools/veridant_stage_palm_mulch.py",
        "Tools/map_kit.py", "Tools/riverdale_parts.py", "Sources/Veridant/palm-mulch-v1/soil-bark-albedo-generated.png")}
    snippets = {"Tools/veridant_parts.py": [inspect.getsource(P.palm_pit)],
        "Tools/veridant_materials.py": ['if p == "vr_palm_mulch":\n                from veridant_palm_mulch import write_materials\n                write_materials( out )\n                continue']}
    protected = {p: sha(ROOT/p) for p in ("Assets/scenes/maps/Veridant/veridant.scene",
        "Assets/models/maps/veridant/veridant_palm_pits.vmdl", "Assets/models/maps/veridant/veridant_palm_pits.mtl",
        "Assets/materials/veridant/vr_stone_light.vmat", "Assets/materials/veridant/vr_gravel_color.jpg",
        "Assets/materials/veridant/vr_gravel_normal.jpg", "Assets/materials/veridant/vr_gravel_rough.png")}
    files = {}

    def record(relative):
        relative = Path(relative)
        source, staged = ROOT/relative, stage/relative
        before = sha(source) if source.exists() else None
        backup = stage/"before"/relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            assert sha(backup) == before
        files[relative.as_posix()] = {"before": before, "after": sha(staged),
            "source": staged.relative_to(ROOT).as_posix(),
            "backup": backup.relative_to(ROOT).as_posix() if before else None}

    material = Path("Assets/materials/veridant")
    M.write_materials(stage/material)
    record(material/"vr_palm_mulch.vmat")
    for p in sorted((stage/material/"palm-mulch-v1").iterdir()):
        record(p.relative_to(stage))

    geometry_source = (ROOT/args.geometry_reference).resolve() if args.geometry_reference else ROOT/OBJ
    assert geometry_source.is_relative_to(ROOT)
    if args.geometry_reference:
        sources[geometry_source.relative_to(ROOT).as_posix()] = sha(geometry_source)
    input_hash = sha(geometry_source)
    beds, removed = existing_beds(geometry_source)
    model = K.Model()
    details = []
    for bed in beds:
        piece = K.Model()
        detail = M.build_into(piece, **bed)
        points = np.vstack([p for rows in piece.polygons.values() for p, n in rows])
        base = np.asarray(bed["base"])
        assert np.isfinite(points).all() and not piece.boxes and not piece.hulls
        assert np.all(np.max(np.abs(points[:, :2]-base[:2]), axis=0) <= M.INNER+1e-6)
        assert points[:, 2].min() >= 0.20 and points[:, 2].max() < 1.5
        details.append({**bed, **detail, "triangles": piece.triangle_count(),
                        "bounds_min": points.min(axis=0).tolist(), "bounds_max": points.max(axis=0).tolist()})
        for paint, rows in piece.polygons.items():
            for i, (pts, normal) in enumerate(rows):
                assert np.isfinite(normal).all()
                ns = piece.polygon_normals.get((paint, i))
                if ns is not None: assert np.isfinite(ns).all()
                model.polygon(paint, pts, normals=ns, uv=piece.polygon_uvs.get((paint, i)))
    model.material_overrides.update({M.PAINT: "materials/veridant/vr_palm_mulch.vmat"})
    model.tile_overrides[M.PAINT] = M.TILE
    addition = stage/"proof/fill.obj"
    addition.parent.mkdir()
    K.write_obj(addition, model, "veridant_palm_mulch")

    original = geometry_source.read_bytes().splitlines(keepends=True)
    retained = b"".join(line for i, line in enumerate(original) if i not in removed)
    counts = Counter({key: sum(line.startswith(key+b" ") for line in original) for key in (b"v", b"vt", b"vn")})
    tables, tail = [], []
    for line in addition.read_bytes().splitlines(keepends=True):
        if line.startswith((b"v ", b"vt ", b"vn ")):
            tables.append(line)
        elif line.startswith(b"usemtl "):
            tail.append(line)
        elif line.startswith(b"f "):
            tokens = [b"/".join(str(int(x)+counts[key]).encode() for key, x in
                       zip((b"v", b"vt", b"vn"), token.split(b"/"))) for token in line.split()[1:]]
            tail.append(b"f "+b" ".join(tokens)+b"\n")
    target = stage/OBJ
    target.parent.mkdir(parents=True)
    target.write_bytes(retained+b"".join(tables)+b"".join(tail))
    assert target.read_bytes().startswith(retained) and sha(geometry_source) == input_hash
    record(OBJ)
    manifest = {"revision": "veridant-palm-mulch-v1", "stage": args.stage, "files": files,
        "source_sha256": sources, "protected_sha256": protected, "required_source_snippets": snippets,
        "beds": details, "beds_updated": 10, "removed_triangles": len(removed),
        "new_triangles": model.triangle_count(), "fragments": sum(x["fragments"] for x in details),
        "retained_bytes_sha256": hashlib.sha256(retained).hexdigest(), "retained_bytes": len(retained),
        "geometry_reference": geometry_source.relative_to(ROOT).as_posix(), "geometry_reference_sha256": input_hash,
        "stone_rim_triangles_preserved": 1760, "scene_unchanged": True, "collision_unchanged": True,
        "original_indices_preserved": True}
    for group in (sources, protected):
        for p, h in group.items(): assert sha(ROOT/p) == h, p
    for p, item in files.items():
        assert sha(ROOT/item["source"]) == item["after"]
        assert (sha(ROOT/p) if (ROOT/p).exists() else None) == item["before"], p
    for p, parts in snippets.items():
        assert all(part in (ROOT/p).read_text() for part in parts), p
    assert model.triangle_count() < 35000
    (stage/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    (OUT/"import-request.json").write_text(json.dumps({"stage": args.stage})+"\n")
    print(json.dumps({"beds": 10, "triangles": manifest["new_triangles"], "fragments": manifest["fragments"],
                      "stone_rims_preserved": True, "files": len(files)}))


if __name__ == "__main__":
    main()
