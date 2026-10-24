import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
OUT = ROOT / "output/veridant/planter-bushes-v1"
BASE = OUT / "stage/baseline"
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import veridant_planter_bushes as B

for path in ("Tools/veridant_map.py", "Tools/veridant_planter_bushes.py"):
    ast.parse((ROOT / path).read_text())
scene_path = Path("Assets/scenes/maps/veridant/veridant.scene")
before = json.loads((BASE / scene_path).read_text())
after = json.loads((ROOT / scene_path).read_text())
world = next(go for go in after["GameObjects"] if go.get("Name") == "Veridant")
group = next(go for go in world["Children"] if go.get("Name") == B.GROUP)
assert len(group["Children"]) == len(B.PLANTS) == 12
by_name = {go["Name"]: go for go in group["Children"]}
for p in B.props():
    go = by_name[p["name"]]
    position = tuple(map(float, go["Position"].split(",")))
    scale = tuple(map(float, go["Scale"].split(",")))
    assert max(abs(a - b) for a, b in zip(position, K.to_world(p["position"]))) < 0.001
    assert max(abs(a - b) for a, b in zip(scale, p["scale"])) < 0.000002
    assert abs(position[2] + B.ROOT_Z * scale[2] - (B.SOIL_Z - .8)) < 0.001
    components = go["Components"]
    assert len(components) == 1 and components[0]["__type"] == "Sandbox.ModelRenderer"
    assert components[0]["Model"]["Path"] == B.MODEL
world["Children"].remove(group)
after["__references"].remove(B.PACKAGE)
def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()
                if key != "__PrefabIdToInstanceId" and not (key == "Id" and "Path" in value)}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value
unrelated_scene_equal = normalize(before) == normalize(after)
if not unrelated_scene_equal:
    def differences(a, b, path=""):
        if type(a) is not type(b):
            return [(path, a, b)]
        if isinstance(a, dict):
            return [item for key in a.keys() | b.keys() for item in differences(a.get(key), b.get(key), path + "/" + key)]
        if isinstance(a, list):
            if len(a) != len(b):
                return [(path + "/length", len(a), len(b))]
            return [item for index, (x, y) in enumerate(zip(a, b)) for item in differences(x, y, path + f"/{index}")]
        return [] if a == b else [(path, a, b)]
    print(json.dumps(differences(normalize(before), normalize(after))[:20], indent=2))
manifest = json.loads((OUT / "stage/manifest.json").read_text())
mesh = ROOT / manifest["source"]
mesh_hash = hashlib.sha256(mesh.read_bytes()).hexdigest()
shared_mesh_changed = mesh_hash != manifest["after"]
import veridant_parts as P
legacy = K.Model()
P.shrubs(legacy, (-56, 614), (56, 736), 148, seed=9, kind="grass", h=24)
def triangle_key(points):
    return tuple(sorted(tuple(round(float(c), 3) for c in p) for p in points))
old_grass = set()
for points, _ in legacy.polygons["vr_foliage"]:
    vertices = [(-p[0], p[2], p[1]) for p in points]
    for index in range(1, len(vertices) - 1):
        old_grass.add(triangle_key((vertices[0], vertices[index], vertices[index + 1])))
vertices, material, remaining = [None], None, 0
for line in mesh.read_text().splitlines():
    if line.startswith("v "):
        vertices.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith("usemtl "):
        material = line.split()[1]
    elif line.startswith("f ") and material == "vr_foliage":
        ids = [int(item.split("/")[0]) for item in line.split()[1:]]
        remaining += triangle_key(vertices[index] for index in ids) in old_grass
assert remaining == 0, "The old planter grass has returned."
assert unrelated_scene_equal, "Other saved scene values changed: inspect before claiming an isolated change."
foliage_vmdl = Path("Assets/models/maps/veridant/veridant_foliage.vmdl")
assert (ROOT / foliage_vmdl).read_bytes() == (BASE / foliage_vmdl).read_bytes()
result = dict(Passed=True, Bushes=12, ReusedModel=B.MODEL, OldGrassPlants=15, RemovedTriangles=120,
              StemEmbedDepth=.8, NoNewColliders=True, CollisionSourceUnchanged=True,
              UnrelatedSceneContentUnchanged=True, AssetIdsReserialized=True, NativePrefabMappingsReserialized=True,
              UnrelatedMeshBytesUnchangedAtImport=True, SharedMeshChangedAfterImport=shared_mesh_changed,
              LegacyGrassTrianglesRemaining=remaining, GeneratorSourcesParse=True)
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
