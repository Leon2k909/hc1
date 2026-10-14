"""Replace only the four discarded tyres; retain every other authored Fleet face."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_tyres as T

folder = Path(__file__).parent
before, stage = folder / "tyres-before", folder / "tyres-stage"
stage.mkdir(exist_ok=True)
manifest = json.loads((before / "manifest.json").read_text())
for relative, expected in manifest.items():
    if relative.startswith("Assets/"):
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
spec = importlib.util.spec_from_file_location("lowtide_before_tyres", before / "Tools/lowtide_map.py")
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
previous, replacement = K.Model(), K.Model()
for e,n,r in ((168,-460,14), (176,-440,13), (-190,120,14), (-150,1240,13)):
    old.tyre(previous, e,n,float(old.mud_z(e,n))-1.5,r)
for e,n,r in T.POSITIONS:
    L.tyre(replacement, e,n,float(L.mud_z(e,n))-1.5,r)
assert not previous.boxes and not replacement.boxes and not previous.hulls and not replacement.hulls
old.configure(previous)
L.configure(replacement)
K.write_obj(stage / "original-tyres.obj", previous, "original-tyres")
K.write_obj(stage / "replacement-tyres.obj", replacement, "replacement-tyres")


def face_keys(rows):
    vertices, result, paint = [], {}, None
    for i,row in enumerate(rows):
        if row.startswith("v "):
            vertices.append(tuple(row.split()[1:]))
        elif row.startswith("usemtl "):
            paint = row.split()[1]
        elif row.startswith("f "):
            points = tuple(sorted(vertices[int(t.split("/")[0])-1] for t in row.split()[1:]))
            result[i] = (paint,points)
    return result


original = (before / "Assets/models/maps/lowtide/lowtide_fleet.obj").read_text().splitlines()
expected = Counter(face_keys((stage / "original-tyres.obj").read_text().splitlines()).values())
remaining, removed = expected.copy(), set()
for index,key in face_keys(original).items():
    if remaining[key] > 0:
        removed.add(index)
        remaining[key] -= 1
assert not +remaining, +remaining
counts = [sum(row.startswith(prefix) for row in original) for prefix in ("v ","vt ","vn ")]
updated = [row for i,row in enumerate(original) if i not in removed]
updated.append("# Hollow discarded tyres; unrelated authored geometry retained")
for row in (stage / "replacement-tyres.obj").read_text().splitlines():
    if row.startswith(("mtllib ","o ","#")):
        continue
    if row.startswith("f "):
        row = "f " + " ".join("/".join(str(int(v)+counts[k]) for k,v in enumerate(t.split("/"))) for t in row.split()[1:])
    updated.append(row)
K.write_text(stage / "lowtide_fleet.obj", "\n".join(updated)+"\n")
mtl = (before / "Assets/models/maps/lowtide/lowtide_fleet.mtl").read_text()
assert f"newmtl {T.PAINT}\n" not in mtl
K.write_text(stage / "lowtide_fleet.mtl", mtl + (stage / "replacement-tyres.mtl").read_text())
vmdl = (before / "Assets/models/maps/lowtide/lowtide_fleet.vmdl").read_text()
anchor = "\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n"
assert vmdl.count(anchor) == 1
remap = f'\t\t\t\t\t\t\t{{ from = "{T.PAINT}.vmat" to = "{T.RESOURCE}" }},\n'
K.write_text(stage / "lowtide_fleet.vmdl", vmdl.replace(anchor,anchor+remap))
material = stage / "Assets" / T.RESOURCE
material.parent.mkdir(parents=True, exist_ok=True)
K.write_text(material,T.material_source())
K.write_text(Path(str(material)+".meta"),json.dumps({"guid":str(uuid.uuid5(uuid.NAMESPACE_URL,T.RESOURCE))},indent=2)+"\n")
report = {"removed_triangles":len(removed), "replacement_triangles":replacement.triangle_count(),
    "net_added_triangles":replacement.triangle_count()-len(removed), "tyres":4,
    "collision_unchanged":True, "unrelated_faces_retained":True, "original_sha256":manifest}
(stage / "manifest.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="original_sha256"},indent=2))
