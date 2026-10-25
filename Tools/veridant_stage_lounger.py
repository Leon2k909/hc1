"""Stage the eight lounger replacements without regenerating the map or scene.

Match every old triangle and prove that all other OBJ lines and existing model
physics survive unchanged. The native editor imports the reviewed manifest.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil

import numpy as np

import map_kit as K
import veridant_lounger as L
from belltower_safe_imports import span
from railhead_stage_extinguisher import sha, lookup_polygons, coverage, replace_obj

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/veridant/lounger-v2"


def placements():
    return ([((-560., n), (1., 0.), 128.) for n in (-150., -110.)]
            + [((-440., n), (-1., 0.), 128.) for n in (340., 400., 460.)]
            + [((1060., n), (-1., 0.), 192.) for n in (-100., 0., 100.)])


def bake_model(stage, name, specs, legacy, record):
    old, new = K.Model(), K.Model()
    for c, f, z in specs:
        legacy.lounger(old, c, f, z)
        L.build_into(new, c, f, z)
    assert old.triangle_count() == 96 * len(specs)
    assert len(new.boxes) == len(old.boxes) == len(specs)
    for a, b in zip(old.boxes, new.boxes):
        assert a[3] == b[3]
        assert all(np.array_equal(x, y) for x, y in zip(a[:3], b[:3]))
    assert not old.hulls and not new.hulls
    assert new.triangle_count() < 80000
    for paint, polygons in new.polygons.items():
        for index, (pts, normal) in enumerate(polygons):
            assert np.isfinite(pts).all() and np.isfinite(normal).all()
            assert (paint, index) in new.polygon_uvs or paint != "vr_lounger_cloth"
    piece = Path(f"Assets/models/maps/veridant/lounger-v2/{name}-replacements.obj")
    (stage / piece).parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(stage / piece, new, "veridant_loungers_v2")
    record(piece)
    record(piece.with_suffix(".mtl"))
    source = Path(f"Assets/models/maps/veridant/{name}.obj")
    base = Path(f"Assets/models/maps/veridant/lounger-v2/{name}-base.obj")
    lookup, polygons = lookup_polygons(old)
    result, found = replace_obj(ROOT / source, stage / source, stage / base, lookup, stage / piece)
    coverage(found, lookup, polygons)
    assert result["removed_triangles"] == 96 * len(specs)
    record(source)
    record(base)
    mtl = source.with_suffix(".mtl")
    (stage / mtl).write_bytes((ROOT / mtl).read_bytes() + b"\n" + (stage / piece.with_suffix(".mtl")).read_bytes())
    record(mtl)
    base_mtl = base.with_name(mtl.name)
    shutil.copyfile(ROOT / mtl, stage / base_mtl)
    record(base_mtl)
    # Retain a complete canonical OBJ for future source-driven map rebuilds.
    vmdl = source.with_suffix(".vmdl")
    raw = (ROOT / vmdl).read_text(encoding="utf-8")
    lo, hi = span(raw, '_class = "RenderMeshList"')
    render = raw[lo:hi]
    a, b = span(render, '_class = "RenderMeshFile"')
    template = render[a:b]
    resource = source.relative_to("Assets").as_posix()
    assert render.count(f'filename = "{resource}"') == 1
    render = render.replace(f'filename = "{resource}"', f'filename = "{base.relative_to("Assets").as_posix()}"', 1)
    node = re.sub(r'name = "[^"]+"', f'name = "{name}_loungers_v2"', template, count=1)
    node = re.sub(r'filename = "[^"]+"', f'filename = "{piece.relative_to("Assets").as_posix()}"', node, count=1)
    end = render.rfind("]")
    prefix = render[:end].rstrip()
    render = prefix + ("" if prefix.endswith(",") else ",") + "\n" + node + "\n" + render[end:]
    updated = raw[:lo] + render + raw[hi:]
    remaps = "".join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint, resource in L.MATERIALS.items())
    at = updated.index("[", updated.index("remaps =")) + 1
    updated = updated[:at] + "\n" + remaps + updated[at:]
    a, b = span(raw, '_class = "PhysicsShapeList"')
    c, d = span(updated, '_class = "PhysicsShapeList"')
    assert raw[a:b] == updated[c:d]
    (stage / vmdl).write_text(updated, encoding="utf-8")
    record(vmdl)
    return {"placements": len(specs), "new_triangles": new.triangle_count(),
            "physics_bytes_exact": True, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", default="stage-v1")
    args = parser.parse_args()
    assert re.fullmatch(r"stage-[a-z0-9-]+", args.stage)
    stage = OUT / args.stage
    assert not stage.exists(), "Keep previous staging revisions"
    stage.mkdir(parents=True)
    inputs = {p: sha(ROOT / p) for p in ("Tools/veridant_lounger.py", "Tools/veridant_parts.py",
              "Tools/veridant_map.py", "Tools/veridant_stage_lounger.py",
              "Sources/Veridant/lounger-v2/legacy-lounger.py")}
    protected = {p: sha(ROOT / p) for p in ("Assets/scenes/maps/Veridant/veridant.scene",)}
    files = {}

    def record(relative):
        path = stage / relative
        original = ROOT / relative
        before = sha(original) if original.exists() else None
        backup = stage / "before" / relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, backup)
            assert sha(backup) == before
        files[relative.as_posix()] = {"before": before, "after": sha(path),
            "source": path.relative_to(ROOT).as_posix(),
            "backup": backup.relative_to(ROOT).as_posix() if before else None}

    material_dir = Path("Assets/materials/veridant/lounger-v2")
    L.write_materials(stage / material_dir)
    for p in sorted((stage / material_dir).iterdir()):
        record(p.relative_to(stage))
    spec = importlib.util.spec_from_file_location("legacy_lounger", ROOT / "Sources/Veridant/lounger-v2/legacy-lounger.py")
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    specs = placements()
    models = {"veridant_dress": bake_model(stage, "veridant_dress", specs[:5], legacy, record),
              "veridant_buildings": bake_model(stage, "veridant_buildings", specs[5:], legacy, record)}
    reusable = K.Model()
    L.build_into(reusable, (0, 0), (1, 0))
    reusable_dir = Path("Assets/models/props/veridant/lounger-v2")
    K.write_model(stage / reusable_dir, reusable_dir.relative_to("Assets").as_posix(), "lounger", reusable)
    for p in sorted((stage / reusable_dir).iterdir()):
        record(p.relative_to(stage))
    manifest = {"revision": "veridant-lounger-v2", "files": files, "source_sha256": inputs,
                "protected_sha256": protected, "placements": placements(), "placements_replaced": 8,
                "triangles_per_instance": reusable.triangle_count(), "old_triangles_removed": 768,
                "new_triangles": sum(r["new_triangles"] for r in models.values()), "physics_bytes_exact": True,
                "unrelated_obj_bytes_exact": True, "models": models}
    for relative, digest in inputs.items():
        assert sha(ROOT / relative) == digest, ("Shared source changed", relative)
    for relative, item in files.items():
        assert sha(ROOT / item["source"]) == item["after"]
        assert (sha(ROOT / relative) if (ROOT / relative).exists() else None) == item["before"], relative
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / "import-request.json").write_text(json.dumps({"stage": args.stage}) + "\n", encoding="utf-8")
    print(json.dumps({"stage": args.stage, "files": len(files), "placements": 8,
                      "triangles_per_instance": reusable.triangle_count(), "models": models}))


if __name__ == "__main__":
    main()
