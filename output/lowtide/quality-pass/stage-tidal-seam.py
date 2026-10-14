"""Stage only the obsolete raised tide strip and cap; preserve all other mesh data."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
STAGE = HERE / "tidal-seam-stage"
BEFORE = HERE / "tidal-seam-before"
STAGE.mkdir(exist_ok=True)
BEFORE.mkdir(exist_ok=True)

def digest(data):
    return hashlib.sha256(data).hexdigest()

report = {}
for name in ("lowtide_east", "lowtide_west", "lowtide_finish"):
    path = ROOT / f"Assets/models/maps/lowtide/{name}.obj"
    original = path.read_bytes()
    backup = BEFORE / path.name
    if backup.exists():
        assert backup.read_bytes() == original, "Already applied or modified since staging"
    else:
        backup.write_bytes(original)
    lines = original.decode().splitlines(keepends=True)
    vertices = []
    vertex_lines = []
    uv_lines = []
    uvs = []
    faces = []
    paint = None
    for i, line in enumerate(lines):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append(tuple(map(float, parts[1:4])))
            vertex_lines.append(i)
        elif parts[0] == "vt":
            uvs.append(tuple(map(float,parts[1:3])))
            uv_lines.append(i)
        elif parts[0] == "usemtl":
            paint = parts[1]
        elif parts[0] == "f":
            assert all(v.split("/")[0] == v.split("/")[1] for v in parts[1:]), "Expected matching vertex/UV indices"
            faces.append((i, paint, [int(v.split("/")[0])-1 for v in parts[1:]]))
    moved = {}
    moved_uvs = {}
    removed = []
    strip_faces = lower_faces = 0
    for line, paint, indices in faces:
        points = [vertices[i] for i in indices]
        # OBJ axes are (-east, height, north), before the engine import.
        if name == "lowtide_finish":
            cap = paint == "lt_brick_glazed" and all(
                abs(y+53.98) < .001 and 239.3 < abs(x) < 240.1 and z in (-1600, 1450)
                for x, y, z in points)
            if cap:
                removed.append(line)
        else:
            strip = paint == "lt_brick_glazed" and all(
                abs(abs(x)-239.4) < .001 and y in (-60, -54) and z in (-1600, 1450)
                for x, y, z in points)
            lower = paint == "lt_brick_slime" and all(
                abs(abs(x)-240) < .001 and y in (-140, -58) and z in (-1600, 1450)
                for x, y, z in points)
            if strip:
                strip_faces += 1
                for i in indices:
                    x,y,z = vertices[i]
                    moved[i] = (240 if x > 0 else -240, y, z)
            if lower:
                lower_faces += 1
                for i in indices:
                    x,y,z = vertices[i]
                    if y == -58:
                        moved[i] = (x,-60,z)
                        u,v = uvs[i]
                        # Existing lt_brick_slime uses 64-inch world-projected UVs.
                        # Keep mortar rows at the same height when shortening the card.
                        moved_uvs[i] = (u,v-2/64)
    if name == "lowtide_finish":
        assert len(removed) == 4 and not moved, (name, removed, moved)
    else:
        assert strip_faces == 2 and lower_faces == 2 and len(moved) == 6, (name,strip_faces,lower_faces,len(moved))
        assert not removed
    for i, values in moved.items():
        lines[vertex_lines[i]] = "v " + " ".join(f"{v:.3f}" for v in values) + "\n"
    for i, values in moved_uvs.items():
        lines[uv_lines[i]] = "vt " + " ".join(f"{v:.5f}" for v in values) + "\n"
    for line in removed:
        lines[line] = ""
    updated = "".join(lines).encode()
    # Only the two lower-card UVs per side follow their moved vertices.
    original_lines = original.decode().splitlines(keepends=True)
    changed_lines = {vertex_lines[i] for i in moved} | {uv_lines[i] for i in moved_uvs} | set(removed)
    assert all(a == b for i,(a,b) in enumerate(zip(original_lines,lines)) if i not in changed_lines)
    (STAGE / path.name).write_bytes(updated)
    report[str(path.relative_to(ROOT)).replace("\\","/")] = {
        "before":digest(original), "after":digest(updated),
        "movedVertices":len(moved), "removedTriangles":len(removed),
        "adjustedUVs":len(moved_uvs),
        "edits":[{"index":i+1,"before":vertices[i],"after":v} for i,v in sorted(moved.items())],
    }
protected = [ROOT / "Assets/scenes/maps/Lowtide/lowtide.scene"]
protected += list((ROOT / "Assets/models/maps/lowtide").glob("*"))
guards = {str(p.relative_to(ROOT)).replace("\\","/"): digest(p.read_bytes()) for p in protected
          if p.is_file() and (p.suffix in (".obj", ".vmdl", ".scene"))}
(HERE / "tidal-seam-manifest.json").write_text(json.dumps({"changes":report,"protectedBefore":guards},indent=2)+"\n")
print(json.dumps({k:{x:v for x,v in item.items() if x != "edits"} for k,item in report.items()},indent=2))
