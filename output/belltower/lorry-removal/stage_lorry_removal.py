"""Belltower: stage the town halves without the Market Street lorries (the user: "remove this truck from belltower").

Takes find_lorry.py's report: drops exactly the lorries' triangles from the installed OBJs (their vertices stay, unused,
so every other face keeps its indices) and the lorries' six PhysicsShapeBox entries from each vmdl, matched by origin and
dimensions as map_kit writes them. Writes the staged files and a manifest of hashes to stage/; the installed files are
untouched (Sources: the native import, import-lorry-removal.cs.txt, publishes them)."""
import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import belltower_map as BM

report = json.loads((HERE / "find-report.json").read_text(encoding="utf-8"))
stage = HERE / "stage"; stage.mkdir(exist_ok=True)
assets = ROOT / "Assets/models/maps/belltower"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = {"files": {}}
for name, east in (("belltower_west", False), ("belltower_east", True)):
    entry = report[name]
    assert entry["Matched"] == entry["LorryTriangles"] == 330 and entry["BoxesMatched"] == entry["Boxes"] == 6
    drop = set(entry["FaceLines"])
    source = assets / f"{name}.obj"
    raw = source.read_bytes()
    lines = raw.split(b"\n")
    kept = [line for number, line in enumerate(lines) if number not in drop]
    assert len(lines) - len(kept) == 330 and all(lines[n].startswith(b"f ") for n in drop)
    (stage / f"{name}.obj").write_bytes(b"\n".join(kept))

    m = K.Model(); BM.lorry(m, (-900, 1290), 8)
    if east: m = m.mirrored(BM.EAST_PAINTS)
    vmdl = (assets / f"{name}.vmdl").read_bytes().decode("utf-8")
    removed = 0
    for centre, axes, size, surface in m.boxes:
        block = re.compile(r"\t\t\t\t\t\{\r?\n\t\t\t\t\t\t_class = \"PhysicsShapeBox\"\r?\n(?:\t\t\t\t\t\t[^\n]*\n){2}"
                           r"\t\t\t\t\t\tcollision_tags = \"solid\"\r?\n"
                           + re.escape(f"\t\t\t\t\t\torigin = {K.vec3(K.to_world(centre))}") + r"\r?\n"
                           r"\t\t\t\t\t\tangles = [^\n]*\n"
                           + re.escape(f"\t\t\t\t\t\tdimensions = {K.vec3(size)}") + r"\r?\n\t\t\t\t\t\},\r?\n")
        vmdl, n = block.subn("", vmdl, count=1)
        assert n == 1, (name, centre)
        removed += n
    (stage / f"{name}.vmdl").write_bytes(vmdl.encode("utf-8"))
    for ext in ("obj", "vmdl"):
        manifest["files"][f"{name}.{ext}"] = {"before": sha(assets / f"{name}.{ext}"), "after": sha(stage / f"{name}.{ext}")}
    print(name, "triangles removed 330, boxes removed", removed)
manifest.update({"triangles_removed_per_half": 330, "boxes_removed_per_half": 6,
                 "retakes_sightlines_through_lorries": 0, "spots_on_lorries": 0})
(stage / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
