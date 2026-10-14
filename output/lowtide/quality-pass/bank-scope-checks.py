"""Check the staged bank meshes against their actual pre-pass assets and routes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_banks as B
import lowtide_marine as M
import lowtide_finish as F

FOLDER = Path(__file__).parent
STAGE = FOLDER / "banks-stage"
STONE = {"lt_tidal_granite", "lt_tidal_brick"}


def signature(model, paint):
    digest = hashlib.sha256()
    for index, (points, normal) in enumerate(model.polygons.get(paint, [])):
        for value in (points, normal, model.polygon_uvs.get((paint, index), []),
                      model.polygon_normals.get((paint, index), [])):
            array = np.asarray(value, dtype=np.float64)
            digest.update(str(array.shape).encode())
            digest.update(array.tobytes())
    return digest.hexdigest()


def old_module(name):
    spec = importlib.util.spec_from_file_location(name + "_before_banks", FOLDER / "banks-before/Tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


placements = []
original_cobble = B.cobble


def record_cobble(model, e, n, ground, radius, height, seed, brick=False, terrain=None):
    paint = "lt_tidal_brick" if brick else "lt_tidal_granite"
    start = len(model.polygons[paint])
    original_cobble(model, e, n, ground, radius, height, seed, brick, terrain)
    points = np.asarray([p for face, _ in model.polygons[paint][start:] for p in face])
    distance = float(np.min(np.abs(points[:, 1, None] - np.asarray(B.LANDINGS))))
    exposed = points[:, 2] - L.mud_z(points[:, 0], points[:, 1])
    placements.append({"landing_distance": distance, "height_above_ground": float(exposed.max())})


B.cobble = record_cobble
report = {}
for module in (M, F):
    name = module.__name__
    old = old_module(name)
    before = old.build(L)
    model = module.build(L)
    assert not model.boxes and not model.hulls and not model.props
    if module is M:
        reference = K.Model()
        old.shell(reference, L)
        expected = set(reference.polygons)
        assert set(model.polygons) - STONE == expected
    else:
        reference = before
        expected = set(before.polygons) - {"lt_bank_stone"}
        assert set(model.polygons) - STONE == expected
    for paint in expected:
        assert signature(reference, paint) == signature(model, paint), (name, paint)
    triangles = 0
    minimum_normal_dot = 1.0
    for paint in STONE & set(model.polygons):
        points = np.asarray([p for p, _ in model.polygons[paint]])
        normals = np.asarray([model.polygon_normals[(paint, i)] for i in range(len(points))])
        uv = np.asarray([model.polygon_uvs[(paint, i)] for i in range(len(points))])
        face = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        area = np.linalg.norm(face, axis=1)
        assert np.min(area) > 1e-8
        face /= area[:, None]
        alignment = np.sum(face[:, None, :] * normals, axis=-1)
        assert np.all(np.isfinite(points)) and np.all(np.isfinite(uv))
        assert np.allclose(np.linalg.norm(normals, axis=-1), 1, atol=1e-7)
        assert alignment.min() > 0, "Inverted stone winding or shading normal"
        minimum_normal_dot = min(minimum_normal_dot, float(alignment.min()))
        triangles += len(points)
    verify = STAGE / "verified-generator"
    verify.mkdir(exist_ok=True)
    K.write_obj(verify / (name + ".obj"), model, name)
    assert (verify / (name + ".obj")).read_bytes() == (STAGE / (name + ".obj")).read_bytes()
    assert "Physics" not in (STAGE / (name + ".vmdl")).read_text()
    report[name] = {"preserved_material_groups": sorted(expected), "triangles": model.triangle_count(),
                    "bank_triangles": triangles, "minimum_normal_alignment": minimum_normal_dot,
                    "staged_obj_matches_generator": True, "physics_added": False}

materials = json.loads((STAGE / "materials.json").read_text())
for path, source in materials.items():
    for reference in re.findall(r'"((?:materials|shaders)/[^\"]+)"', source):
        assert (K.ASSETS / reference).exists() or reference.startswith("materials/default/"), reference
    assert "TextureColor" in source and "TextureNormal" in source
report["placements"] = {"stones": len(placements),
    "minimum_landing_clearance_inches": min(p["landing_distance"] for p in placements),
    "maximum_height_above_bank_inches": max(p["height_above_ground"] for p in placements)}
assert report["placements"]["minimum_landing_clearance_inches"] >= 45
report["materials"] = list(materials)
report["engine_validation"] = "Geometry checks only; engine evidence is recorded separately in bank-render-checks.json"
(FOLDER / "bank-scope-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
