"""Stage only Veridant's old lantern roof triangles from the installed meshes.

The generator records placements without writing a scene or regenerating models.
All other OBJ lines remain byte-for-byte; editor import checks the source hashes.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import map_kit as K
import veridant_map as M

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/veridant/lantern-roof-v1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def triangles(model):
    for material, faces in model.polygons.items():
        for points, _ in faces:
            for k in range(1, len(points) - 1):
                yield material, [K.to_world(points[i])[[1, 2, 0]] for i in (0, k, k + 1)]


def key(material, points):
    return material, tuple(sorted(tuple(round(float(x), 3) + 0.0 for x in p) for p in points))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lamps = []
    original = M.P.lantern_post

    def record(model, name, base, h=132.0, **kwargs):
        lamps.append((model, {"name": name, "base": list(base), "h": h}))
        original(model, name, base, h, **kwargs)

    M.P.lantern_post = record
    try:
        models = M.build(backdrop=False)
    finally:
        M.P.lantern_post = original

    manifest = {"revision": "veridant-lantern-roof-v1", "files": {}, "protected": {}, "lamps": []}
    for model_name, source_model in models.items():
        selected = [item for model, item in lamps if model is source_model]
        if not selected:
            continue
        old_roofs, new_roofs = K.Model(), K.Model()
        for lamp in selected:
            top = M.P.v(*lamp["base"]) + M.P.UP * (lamp["h"] - 16)
            M.P.P.lathe(old_roofs, top, [(7.5, top[2] + 14), (6, top[2] + 16),
                                      (.5, top[2] + 19), (0, top[2] + 19.5)], "vr_steel", 4)
            M.P.lantern_roof(new_roofs, top)
        expected = Counter(key(material, points) for material, points in triangles(old_roofs))
        relative = f"Assets/models/maps/veridant/{model_name}.obj"
        data = (ROOT / relative).read_bytes()
        lines = data.decode("utf-8").splitlines(keepends=True)
        vertices, counts, removed = [], Counter(), Counter()
        retained, material = [], None
        for line in lines:
            parts = line.split()
            if parts and parts[0] in ("v", "vt", "vn"):
                counts[parts[0]] += 1
                if parts[0] == "v":
                    vertices.append(tuple(map(float, parts[1:4])))
            if parts and parts[0] == "usemtl":
                material = parts[1]
            if parts and parts[0] == "f":
                points = [vertices[int(part.split("/")[0]) - 1] for part in parts[1:]]
                signature = key(material, points)
                if signature in expected:
                    removed[signature] += 1
                    continue
            retained.append(line)
        if removed != expected:
            raise RuntimeError(f"{model_name}: expected {sum(expected.values())} roof triangles, matched {sum(removed.values())}")
        fragment = OUT / f"{model_name}-roof-fragment.obj"
        M.configure(new_roofs)
        new_count = K.write_obj(fragment, new_roofs, model_name)
        additions = []
        for line in fragment.read_text(encoding="utf-8").splitlines():
            if line.startswith(("#", "mtllib ", "o ")):
                continue
            if line.startswith("f "):
                references = []
                for part in line.split()[1:]:
                    v, vt, vn = map(int, part.split("/"))
                    references.append(f"{v + counts['v']}/{vt + counts['vt']}/{vn + counts['vn']}")
                line = "f " + " ".join(references)
            additions.append(line)
        retained_bytes = "".join(retained).encode("utf-8")
        patched = retained_bytes + ("# Aligned closed lantern canopies\n" + "\n".join(additions) + "\n").encode("utf-8")
        for material, points in triangles(new_roofs):
            a, b, c = points
            import numpy as np
            if np.linalg.norm(np.cross(b - a, c - a)) < 1e-7:
                raise RuntimeError("Degenerate replacement triangle")
        backup = OUT / "before" / f"{model_name}.obj"
        staged = OUT / "stage" / f"{model_name}.obj"
        backup.parent.mkdir(exist_ok=True)
        staged.parent.mkdir(exist_ok=True)
        if backup.exists() and backup.read_bytes() != data:
            raise RuntimeError("Existing backup differs; preserve it and review the shared file")
        backup.write_bytes(data)
        staged.write_bytes(patched)
        manifest["files"][relative] = {
            "before": sha(data), "after": sha(patched),
            "backup": backup.relative_to(ROOT).as_posix(), "stage": staged.relative_to(ROOT).as_posix(),
            "removed_triangles": sum(removed.values()), "added_triangles": new_count,
            "retained_lines_sha256": sha(retained_bytes), "lamps": len(selected),
        }
        manifest["lamps"].extend(dict(item, model=model_name) for item in selected)
        for protected in sorted((ROOT / "Assets/models/maps/veridant").glob(model_name + "*")):
            if protected.suffix in (".obj", ".vmdl", ".mtl") and protected != ROOT / relative:
                manifest["protected"][protected.relative_to(ROOT).as_posix()] = sha(protected.read_bytes())
    scene = ROOT / "Assets/scenes/maps/Veridant/veridant.scene"
    manifest["protected"][scene.relative_to(ROOT).as_posix()] = sha(scene.read_bytes())
    for source in ("Tools/veridant_parts.py", "Tools/veridant_map.py"):
        manifest["protected"][source] = sha((ROOT / source).read_bytes())
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"lamps": len(manifest["lamps"]), "files": manifest["files"]}, indent=2))


if __name__ == "__main__":
    main()
