"""Real leaf meshes for the north terrace's pine planter; no collision changes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import map_kit as K

MODEL = "models/sbox_props/shrubs/beech/beech_bush_small.vmdl"
PACKAGE = "facepunch.beech_bush_small#145429"
GROUP = "Pine planter beech bushes"
SOIL_Z = 148.0
ROOT_Z, TOP_Z = 0.845722, 55.370075
# Plan e, n, canopy radius, height above soil, world yaw. Leave room for the trunk.
PLANTS = (
    (-35, 635, 16, 23, 15), (-8, 633, 18, 20, 137), (25, 636, 17, 25, 259),
    (38, 662, 16, 22, 48), (36, 692, 17, 26, 182), (29, 717, 17, 23, 296),
    (0, 718, 17, 21, 67), (-32, 716, 18, 24, 221), (-38, 687, 16, 20, 331),
    (-36, 659, 16, 25, 109), (7, 655, 14, 18, 201), (-14, 698, 15, 19, 278),
)


def props():
    result = []
    for index, (e, n, radius, height, yaw) in enumerate(PLANTS):
        sz = (height + 0.8) / (TOP_Z - ROOT_Z)
        xy = radius * 2 / 144.2649
        result.append(dict(name=f"Pine planter beech {index + 1:02}", path=MODEL,
                           position=(e, n, SOIL_Z - 0.8 - ROOT_Z * sz),
                           scale=(xy, xy, sz), yaw=yaw))
    return result


def scene_group(ids):
    children = []
    for index, p in enumerate(props()):
        key = f"pine-planter-bushes/{index}"
        children.append(K.game_object(ids, p["name"], key, K.to_world(p["position"]),
                                      K.yaw_rotation(p["yaw"]), scale=K.vec(p["scale"]), tags="navskip",
                                      components=[K.component(ids, "Sandbox.ModelRenderer", key + "/renderer",
                                                              Model=p["path"], RenderType="On", Tint="1,1,1,1")]))
    return K.game_object(ids, GROUP, "pine-planter-bushes", children=children)


def stage(out):
    """Remove only the exact old planter grass triangles from the published mesh."""
    import veridant_parts as P
    out = Path(out).resolve()
    snapshot = out / "baseline"
    if snapshot.exists():
        raise RuntimeError("Baseline already exists; inspect it before another stage.")
    mesh = Path("Assets/models/maps/veridant/veridant_foliage.obj")
    protected = [p for p in mesh.parent.iterdir() if p.is_file() and p != mesh and not p.name.endswith("_c")]
    files = [mesh, Path("Assets/scenes/maps/veridant/veridant.scene"), Path("Tools/veridant_map.py"), *protected]
    hashes = {}
    for relative in files:
        dest = snapshot / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(K.ROOT / relative, dest)
        hashes[relative.as_posix()] = hashlib.sha256(dest.read_bytes()).hexdigest()
    old = K.Model()
    P.shrubs(old, (-56, 614), (56, 736), 148, seed=9, kind="grass", h=24)
    def key(points):
        return tuple(sorted(tuple(round(float(c), 3) for c in p) for p in points))
    expected = Counter()
    for points, _ in old.polygons["vr_foliage"]:
        vertices = [(-p[0], p[2], p[1]) for p in points]
        for index in range(1, len(vertices) - 1):
            expected[key((vertices[0], vertices[index], vertices[index + 1]))] += 1
    original = (K.ROOT / mesh).read_bytes()
    vertices = [None]
    material = None
    kept, removed = [], 0
    for line in original.splitlines(keepends=True):
        if line.startswith(b"v "):
            vertices.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith(b"usemtl "):
            material = line.split()[1]
        elif line.startswith(b"f ") and material == b"vr_foliage":
            ids = [int(item.split(b"/")[0]) for item in line.split()[1:]]
            signature = key(vertices[index] for index in ids)
            if expected[signature] > 0:
                expected[signature] -= 1
                removed += 1
                continue
        kept.append(line)
    assert removed == 120 and not any(expected.values()), (removed, +expected)
    updated = b"".join(kept)
    staged = out / "veridant_foliage.obj"
    staged.write_bytes(updated)
    manifest = dict(revision="veridant-pine-planter-bushes-v1", source=mesh.as_posix(),
                    before=hashes[mesh.as_posix()], after=hashlib.sha256(updated).hexdigest(),
                    baseline_sha256=hashes, removed_triangles=removed, legacy_plants=15,
                    replacement_plants=props(), unrelated_obj_bytes_unchanged=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"RemovedTriangles": removed, "Bushes": len(PLANTS), "Manifest": str(out / "manifest.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    stage(parser.parse_args().stage)
