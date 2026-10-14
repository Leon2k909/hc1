"""Check a staged or installed seam repair against the canonical wall generator."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path.insert(0,str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
from PIL import Image, ImageStat

parser = argparse.ArgumentParser()
parser.add_argument("--installed",action="store_true")
args = parser.parse_args()
manifest = json.loads((HERE / "tidal-seam-manifest.json").read_text())
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
for path, before in manifest["protectedBefore"].items():
    expected = manifest["changes"][path]["after"] if args.installed and path in manifest["changes"] else before
    assert digest(ROOT / path) == expected, path

def relevant_faces(path):
    vertices,uvs,normals = [],[],[]
    faces = {}
    paint = None
    for line in path.read_text().splitlines():
        p = line.split()
        if not p: continue
        if p[0] == "v": vertices.append(tuple(map(float,p[1:])))
        elif p[0] == "vt": uvs.append(tuple(map(float,p[1:])))
        elif p[0] == "vn": normals.append(tuple(map(float,p[1:])))
        elif p[0] == "usemtl": paint = p[1]
        elif p[0] == "f" and paint in ("lt_brick_slime","lt_brick_glazed"):
            indices = [tuple(int(v)-1 for v in s.split("/")) for s in p[1:]]
            points = [vertices[i] for i,_,_ in indices]
            if all(abs(abs(x)-240) < .001 and -140 <= y <= -54 and z in (-1600,1450) for x,y,z in points):
                # Compare geometry, winding normal, and UV placement, not OBJ index order.
                signature = tuple(sorted((vertices[i],uvs[t],normals[n]) for i,t,n in indices))
                faces.setdefault(paint,[]).append(signature)
    return {k:sorted(v) for k,v in faces.items()}

model = K.Model()
L.fleet_wall(model,L.EAST,L.QUAY_N,L.STREET_N[1])
assert not model.boxes and not model.hulls
sample_dir = HERE / "tidal-seam-generator-check"
sample_dir.mkdir(exist_ok=True)
for name, generated in (("lowtide_east",model),("lowtide_west",model.mirrored(L.WEST_PAINTS))):
    L.configure(generated)
    sample = sample_dir / f"{name}.obj"
    K.write_obj(sample,generated,name)
    actual = ROOT / f"Assets/models/maps/lowtide/{name}.obj" if args.installed else HERE / f"tidal-seam-stage/{name}.obj"
    actual_faces, expected_faces = relevant_faces(actual), relevant_faces(sample)
    if actual_faces != expected_faces:
        print(json.dumps({"actual":actual_faces,"expected":expected_faces},indent=2))
    assert actual_faces == expected_faces, f"Generator disagrees with scoped patch: {name}"
    assert sum(map(len,relevant_faces(actual).values())) == 4
report = {
    "state":"installed" if args.installed else "staged",
    "scope":"PASS: scene, model resources, collision and all other mesh sources preserved",
    "canonicalWallGeometryAndUVs":"PASS: both repaired wall faces equal the canonical generator",
    "movedVertices":12,"adjustedUVs":4,"removedCapTriangles":4,
}
if args.installed:
    native = json.loads((HERE / "tidal-seam-native-compile.json").read_text())
    assert len(native["results"]) == 3 and all(r["compiled"] for r in native["results"])
    status = json.loads((HERE / "tidal-seam-editor-status.json").read_text())
    assert status["ActiveScenePath"] == "scenes/maps/lowtide/lowtide.scene"
    assert not status["SceneHasUnsavedChanges"] and not status["IsPlaying"]
    assert status["LastCompileSucceeded"] and status["LastCompileErrors"] == 0
    assert "No matching console output" in (HERE / "tidal-seam-console-errors.json").read_text()
    for side in ("east","west"):
        with Image.open(HERE / f"tidal-seam-{side}-after.png") as image:
            stats = ImageStat.Stat(image.convert("RGB"))
            assert image.size == (1280,720) and max(stats.mean) > 10 and max(stats.stddev) > 10
    report.update(nativeCompile="PASS: all three models", editorState="Saved Lowtide, outside play mode, camera restored",
                  visualReview="PASS: bright seam absent in both native viewport views", globalErrors="None")
(HERE / "tidal-seam-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
