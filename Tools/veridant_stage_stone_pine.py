"""Stage a replacement of the north-terrace pine only; retain every other OBJ face."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import map_kit as K
import veridant_map as M
import veridant_parts as P

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "output/veridant/stone-pine-v2"
MODEL_DIR = ROOT / "Assets/models/maps/veridant"
STAGE = WORK / "stage"
ARGS = ((0.0, 676.0, 148.0), 360)
KWARGS = dict(crown_r=240, seed=8, lean=(30.0, -40.0))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parsed(text):
    lines = text.splitlines(keepends=True)
    vertices = [tuple(map(float, l.split()[1:])) for l in lines if l.startswith("v ")]
    counts = [sum(l.startswith(prefix) for l in lines) for prefix in ("v ", "vt ", "vn ")]
    return lines, vertices, counts


def face_keys(lines, vertices):
    material = None
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f "):
            pts = tuple(vertices[int(t.split("/")[0])-1] for t in line.split()[1:])
            cyclic = min(pts[k:] + pts[:k] for k in range(len(pts)))
            yield i, (material, cyclic)


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    original = (MODEL_DIR / "veridant_foliage.obj").read_bytes()
    original_mtl = (MODEL_DIR / "veridant_foliage.mtl").read_bytes()
    original_vmdl = (MODEL_DIR / "veridant_foliage.vmdl").read_bytes()
    legacy_namespace = dict(vars(P))
    exec((ROOT / "Sources/Veridant/stone-pine-v2/legacy-stone-pine.py.txt").read_text(encoding="utf-8"), legacy_namespace)
    old = K.Model()
    legacy_namespace["stone_pine"](old, *ARGS, **KWARGS)
    M.configure(old)
    old_count = K.write_obj(STAGE / "old-tree.obj", old, "veridant_foliage")
    old_lines, old_vertices, _ = parsed((STAGE / "old-tree.obj").read_text(encoding="utf-8"))
    wanted = Counter(key for _, key in face_keys(old_lines, old_vertices))
    lines, vertices, counts = parsed(original.decode("utf-8"))
    remove = set()
    for index, key in face_keys(lines, vertices):
        if wanted[key] > 0:
            wanted[key] -= 1
            remove.add(index)
    if sum(wanted.values()) or len(remove) != old_count:
        raise RuntimeError(f"Legacy tree did not match exactly: {len(remove)}/{old_count}, missing {sum(wanted.values())}")

    new = K.Model()
    P.stone_pine(new, *ARGS, **KWARGS)
    M.configure(new)
    assert not new.boxes and not new.hulls and not new.props
    new_count = K.write_obj(STAGE / "new-tree.obj", new, "veridant_foliage")
    new_lines, _, _ = parsed((STAGE / "new-tree.obj").read_text(encoding="utf-8"))
    extra = []
    for line in new_lines:
        if line.startswith(("v ", "vt ", "vn ", "usemtl ")):
            extra.append(line)
        elif line.startswith("f "):
            refs = []
            for token in line.split()[1:]:
                refs.append("/".join(str(int(t)+count) for t, count in zip(token.split("/"), counts)))
            extra.append("f " + " ".join(refs) + "\n")
    kept = [line for i, line in enumerate(lines) if i not in remove]
    merged = ("".join(kept) + "\n# North terrace stone pine v2\n" + "".join(extra)).encode("utf-8")
    retained_before = Counter(key for i, key in face_keys(lines, vertices) if i not in remove)
    merged_lines, merged_vertices, _ = parsed(merged.decode("utf-8"))
    assert Counter(key for _, key in face_keys(merged_lines, merged_vertices)) == retained_before + Counter(key for _, key in face_keys(new_lines, parsed("".join(new_lines))[1]))
    material = "vr_stone_pine_needles"
    remap = b'\t\t\t\t\t\t\t{ from = "vr_stone_pine_needles.vmat" to = "models/sbox_props/shrubs/pine/mountain_pine.vmat" },\n'
    anchor = b'\t\t\t\t\t\t\t{ from = "vr_bark.vmat"'
    assert original_vmdl.count(anchor) == 1
    new_vmdl = original_vmdl.replace(anchor, remap + anchor)
    new_mtl = original_mtl + b'\nnewmtl vr_stone_pine_needles\nKd 1 1 1\nd 1\n'
    files = {"veridant_foliage.obj": merged, "veridant_foliage.mtl": new_mtl, "veridant_foliage.vmdl": new_vmdl}
    before = WORK / "before"
    before.mkdir(exist_ok=True)
    for name, data in (("veridant_foliage.obj", original), ("veridant_foliage.mtl", original_mtl), ("veridant_foliage.vmdl", original_vmdl)):
        saved = before / name
        if saved.exists() and saved.read_bytes() != data:
            raise RuntimeError(f"Existing backup differs: {saved}")
        saved.write_bytes(data)
    for name, data in files.items():
        (STAGE / name).write_bytes(data)
    # A separate native preview lets us review the replacement without changing the active map.
    preview_dir = "models/maps/veridant/stone-pine-v2"
    preview_vmdl = new_vmdl.decode("utf-8").replace("models/maps/veridant/veridant_foliage.obj", f"{preview_dir}/veridant_foliage_preview.obj")
    (STAGE / "veridant_foliage_preview.obj").write_bytes(merged.replace(b"mtllib veridant_foliage.mtl", b"mtllib veridant_foliage_preview.mtl", 1))
    (STAGE / "veridant_foliage_preview.mtl").write_bytes(new_mtl)
    (STAGE / "veridant_foliage_preview.vmdl").write_text(preview_vmdl, encoding="utf-8")
    plan = {"OldTreeTriangles":old_count,"NewTreeTriangles":new_count,"RetainedTriangles":sum(retained_before.values()),
            "OnlyOneTreeChanged":True,"CollisionChanged":False,"CloudMaterial":"models/sbox_props/shrubs/pine/mountain_pine.vmat",
            "Files":[{"Path":f"Assets/models/maps/veridant/{name}","Before":digest((before/name).read_bytes()),"After":digest(data),"Staged":str((STAGE/name).relative_to(ROOT)).replace("\\","/")} for name,data in files.items()]}
    (STAGE / "manifest.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in plan.items() if k!="Files"}))


if __name__ == "__main__":
    main()
