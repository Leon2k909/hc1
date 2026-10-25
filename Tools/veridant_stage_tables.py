"""Patch only the published bistro tops, including active partitioned render imports."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

import numpy as np

import map_kit as K
from belltower_safe_imports import span
from railhead_stage_extinguisher import coverage, lookup_polygons, point, replace_obj, sha
import veridant_table as T

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/veridant/table-v2"
ROWS = [(-520., -100., 0.), (-520., 40., 0.), (-400., -120., 0.),
        (-400., 20., 0.), (-400., 140., 0.), (-520., 150., 0.),
        (-520., 800., 128.), (-330., 820., 128.), (110., 380., 128.),
        (220., -1060., 0.), (-460., -1240., 0.)]


def replace_preserving_vertex_order(source, output, retained, lookup, piece):
    # Published imports can already contain vertices AFTER earlier face groups.
    # New tables must follow ALL retained bytes, otherwise those later original
    # vertices change index and both old and replacement faces address bad data.
    stats, found = replace_obj(source, output, retained, lookup, piece)
    counts = Counter()
    for line in source.open("rb"):
        for kind in (b"v", b"vt", b"vn"):
            if line.startswith(kind + b" "):
                counts[kind] += 1
    tables, tail = [], []
    for line in piece.open("rb"):
        if line.startswith((b"v ", b"vt ", b"vn ")):
            tables.append(line)
        elif line.startswith(b"usemtl "):
            tail.append(line)
        elif line.startswith(b"f "):
            tokens = [b"/".join(str(int(value) + counts[kind]).encode()
                      for kind, value in zip((b"v", b"vt", b"vn"), token.split(b"/")))
                      for token in line.split()[1:]]
            tail.append(b"f " + b" ".join(tokens) + b"\n")
    original = retained.read_bytes()
    output.write_bytes(original + b"\n" + b"".join(tables) + b"".join(tail))
    assert output.read_bytes()[:len(original)] == original
    stats["original_vertex_order_exact"] = True
    return stats, found


def legacy_lookup():
    combined, owner = {}, {}
    for i, (e, n, z) in enumerate(ROWS):
        model = K.Model()
        T.legacy_top(model, (e, n), z)
        lookup, _ = lookup_polygons(model)
        for key in lookup:
            assert key not in combined
            combined[key] = True
            owner[key] = i
    return combined, owner


def audit(path, wanted, owner):
    positions = {p for _, points in wanted for p in points}
    paints = {p for p, _ in wanted}
    vertices, found, counts, paint = {}, Counter(), 0, None
    for line in path.open("rb"):
        if line.startswith(b"v "):
            counts += 1
            q = point(line[2:].decode())
            if q in positions:
                vertices[counts] = q
        elif line.startswith(b"usemtl "):
            paint = line.split()[1]
        elif line.startswith(b"f ") and paint in paints:
            indices = [int(t.split(b"/")[0]) for t in line.split()[1:]]
            if all(k in vertices for k in indices):
                key = paint, frozenset(vertices[k] for k in indices)
                if key in wanted:
                    found[owner[key]] += 1
    assert all(n == 60 for n in found.values()), (str(path), found)
    return sorted(found)


def check_top():
    model = K.Model()
    T.build_top_into(model, (0, 0))
    edges = Counter()
    for paint, faces in model.polygons.items():
        for i, (pts, normal) in enumerate(faces):
            assert np.isfinite(pts).all()
            normals = model.polygon_normals.get((paint, i))
            if normals is not None:
                assert np.isfinite(normals).all()
            for k in range(1, len(pts) - 1):
                tri = [pts[0], pts[k], pts[k + 1]]
                geom = np.cross(tri[1] - tri[0], tri[2] - tri[0])
                assert np.linalg.norm(geom) > 1e-8
                shaded = sum(normals[j] for j in (0, k, k + 1)) if normals is not None else normal
                assert np.dot(geom, shaded) > 0
                q = [tuple(np.round(p, 6)) for p in tri]
                for a, b in zip(q, q[1:] + q[:1]):
                    edges[frozenset((a, b))] += 1
    assert set(edges.values()) == {2}, Counter(edges.values())
    assert not model.boxes and not model.hulls
    vertices = np.array([p for faces in model.polygons.values() for pts, _ in faces for p in pts])
    assert np.allclose(vertices.min(axis=0), (-15, -15, 28))
    assert np.allclose(vertices.max(axis=0), (15, 15, 29.5))
    return {"triangles": model.triangle_count(), "closed_manifold": True, "outward_normals": True,
            "diameter_inches": 30, "top_height_inches": 29.5, "thickness_inches": 1.5,
            "edge_ease_mm": T.EASE * 25.4, "rim_segments": T.SIDES,
            "maximum_circle_error_mm": T.RADIUS * (1 - math.cos(math.pi / T.SIDES)) * 25.4}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--stage", default="stage-v1")
    parser.add_argument("--repair-from", help="Rebuild this task's OBJ replacements from its preserved pre-import sources.")
    parser.add_argument("--repair-model", choices=("buildings", "dress"), help="Repair only the specified model, preserving independently updated imports.")
    args = parser.parse_args()
    assert re.fullmatch("[a-z0-9-]+", args.stage)
    wanted, owner = legacy_lookup()
    checked = check_top()
    if args.repair_from:
        assert re.fullmatch("[a-z0-9-]+", args.repair_from)
        previous = json.loads((OUT / args.repair_from / "manifest.json").read_text())
        stage = OUT / args.stage
        assert not stage.exists()
        stage.mkdir(parents=True)
        files, replacements = {}, {}
        for relative, indices_rows in previous["placements"].items():
            if args.repair_model and ("veridant_" + args.repair_model) not in relative:
                continue
            assert sha(ROOT / relative) == previous["files"][relative]["after"], "Shared OBJ changed; inspect before repair."
            before_source = ROOT / previous["files"][relative]["backup"]
            assert sha(before_source) == previous["files"][relative]["before"]
            old, new = K.Model(), K.Model()
            for e, n, z in indices_rows:
                T.legacy_top(old, (e, n), z)
                T.build_top_into(new, (e, n), z)
            lookup, polygons = lookup_polygons(old)
            piece = stage / "pieces" / (relative.replace("/", "--") + ".obj")
            piece.parent.mkdir(parents=True, exist_ok=True)
            K.write_obj(piece, new, "veridant_tables_v2")
            output = stage / relative
            retained = stage / "retained" / relative
            stats, found = replace_preserving_vertex_order(before_source, output, retained, lookup, piece)
            coverage(found, lookup, polygons)
            backup = stage / "before" / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, backup)
            files[relative] = {"before": sha(backup), "after": sha(output),
                               "source": output.relative_to(ROOT).as_posix(), "backup": backup.relative_to(ROOT).as_posix()}
            replacements[relative] = {**stats, "instances": len(indices_rows), "new_triangles": new.triangle_count()}
        protected = dict(previous["protected_sha256"])
        protected.update({p: sha(ROOT / p) for p, data in previous["files"].items() if p not in files})
        report = {**previous, "files": files, "replacement": replacements,
                  "source_sha256": {p: sha(ROOT / p) for p in previous["source_sha256"]}, "protected_sha256": protected,
                  "geometry": checked, "corrects_interleaved_vertex_indices": True}
        for group in (report["source_sha256"], protected):
            for relative, digest in group.items():
                assert sha(ROOT / relative) == digest
        (stage / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"files": len(files), "active_instances": report["active_instances"], "repaired_vertex_order": True}))
        return
    candidates, parents = {}, {}
    for stem in ("veridant_buildings", "veridant_dress"):
        canonical = Path("Assets/models/maps/veridant") / (stem + ".obj")
        vmdl = canonical.with_suffix(".vmdl")
        raw = (ROOT / vmdl).read_text()
        a, b = span(raw, '_class = "RenderMeshList"')
        imports = [Path("Assets") / p for p in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', raw[a:b])]
        parents[vmdl.as_posix()] = {"imports": [p.as_posix() for p in imports], "raw": raw}
        for path in dict.fromkeys([canonical, *imports]):
            found = audit(ROOT / path, wanted, owner)
            if found:
                candidates[path.as_posix()] = found
    report = {"revision": "veridant-table-v2", "geometry": checked,
              "placements": {p: [ROWS[i] for i in indices] for p, indices in candidates.items()}}
    if args.audit_only:
        print(json.dumps(report))
        return
    stage = OUT / args.stage
    assert not stage.exists(), "Use a fresh stage name."
    stage.mkdir(parents=True)
    files, protected, replacement = {}, {}, {}

    def record(relative, path):
        relative = Path(relative).as_posix()
        target = ROOT / relative
        before = sha(target) if target.exists() else None
        backup = stage / "before" / relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, backup)
            assert sha(backup) == before
        files[relative] = {"before": before, "after": sha(path), "source": path.relative_to(ROOT).as_posix(),
                           "backup": backup.relative_to(ROOT).as_posix() if before else None}

    for relative, indices in candidates.items():
        old, new = K.Model(), K.Model()
        for i in indices:
            e, n, z = ROWS[i]
            T.legacy_top(old, (e, n), z)
            T.build_top_into(new, (e, n), z)
        piece = stage / "pieces" / (relative.replace("/", "--") + ".obj")
        piece.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(piece, new, "veridant_tables_v2")
        lookup, polygons = lookup_polygons(old)
        output = stage / relative
        retained = stage / "retained" / relative
        stats, found = replace_preserving_vertex_order(ROOT / relative, output, retained, lookup, piece)
        coverage(found, lookup, polygons)
        assert stats["removed_triangles"] == len(indices) * 60
        record(relative, output)
        # Preserve and extend the exact MTL named by this source's mtllib.
        header = (ROOT / relative).read_bytes().split(b"\n", 8)
        name = next(line.split(maxsplit=1)[1].decode() for line in header if line.startswith(b"mtllib "))
        mtl = Path(relative).parent / name
        path = stage / mtl
        if mtl.as_posix() not in files:
            assert b"newmtl vr_table_honed" not in (ROOT / mtl).read_bytes()
            path.write_bytes((ROOT / mtl).read_bytes() + b"\nnewmtl vr_table_honed\nKd 1 1 1\nd 1\n")
            record(mtl, path)
        replacement[relative] = {**stats, "instances": len(indices), "new_triangles": new.triangle_count()}
    for relative, data in parents.items():
        raw = data["raw"]
        if not any(p in candidates for p in data["imports"]):
            continue
        remap = '{ from = "vr_table_honed.vmat" to = "materials/veridant/table-v2/honed.vmat" },\n'
        assert "vr_table_honed" not in raw
        pos = raw.index("[", raw.index("remaps =")) + 1
        updated = raw[:pos] + "\n" + remap + raw[pos:]
        a, b = span(raw, '_class = "PhysicsShapeList"')
        c, d = span(updated, '_class = "PhysicsShapeList"')
        assert raw[a:b] == updated[c:d]
        path = stage / relative
        path.write_text(updated)
        record(relative, path)
    relative = Path("Assets/materials/veridant/table-v2/honed.vmat")
    path = stage / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    material = (ROOT / "Assets/materials/veridant/vr_stone_light.vmat").read_text()
    material = material.replace("// Tools/veridant_materials.py", "// Tools/veridant_stage_tables.py: honed slab, restrained surface relief")
    material = material.replace('TextureNormal "materials/veridant/vr_stone_light_normal.jpg"',
                                'TextureNormal "materials/default/default_normal.tga"')
    path.write_text(material)
    record(relative, path)
    scene = "Assets/scenes/maps/Veridant/veridant.scene"
    protect = [scene, "Assets/materials/veridant/vr_stone_light.vmat",
               *[p.relative_to(ROOT).as_posix() for p in (ROOT / "Assets/models/maps/veridant").glob("*_hulls_*.obj")]]
    protected = {p: sha(ROOT / p) for p in protect}
    inputs = ["Tools/veridant_table.py", "Tools/veridant_parts.py", "Tools/veridant_map.py",
              "Tools/veridant_stage_tables.py", "Tools/map_kit.py", "Tools/riverdale_parts.py"]
    report.update(files=files, source_sha256={p: sha(ROOT / p) for p in inputs},
                  protected_sha256=protected, replacement=replacement,
                  collision_unchanged=True, scene_unchanged=True,
                  active_instances=sum(len(candidates[p]) for d in parents.values() for p in d["imports"] if p in candidates))
    for group in (report["source_sha256"], protected):
        for relative, digest in group.items():
            assert sha(ROOT / relative) == digest
    for relative, item in files.items():
        assert (sha(ROOT / relative) if (ROOT / relative).exists() else None) == item["before"]
    (stage / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"files": len(files), "active_instances": report["active_instances"],
                      "replacement": replacement, "geometry": checked}))


if __name__ == "__main__":
    main()
