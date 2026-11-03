"""Stage a checked, board-only splice of Riverdale's published hall models.

Run from the checkout, then install stage.json through install.cs.txt in the native editor.
The original published meshes are retained in output/riverdale/pool-rules-20261031/backup.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverdale_hall as H
import riverdale_pool_rules as RULES
import riverdale_materials as RM
from riverdale_splice import read_obj, write_obj
from PIL import Image

OUT = ROOT / "output/riverdale/pool-rules-20261031"
STAGE = OUT / "stage"
ASSETS = ROOT / "Assets"
entries, report = [], []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def entry(relative):
    src, dst = STAGE / relative, ASSETS / relative
    entries.append({"Source": str(src), "Target": str(dst), "ExpectedSHA256": digest(dst), "SHA256": digest(src)})


def boards(new):
    detail, fine = K.Model(), K.Model()
    sites = [(H.Face((0, 2000), (0, -1)), RULES.NORTH_CENTRE if new else -200, 40)]
    for sx in (-1, 1):
        f = -sx
        face = H.Face((f * H.E0, 0), (f, 0))
        sites.append((face, face.s_of(f * H.E0, 1880), H.UPPER + 40))
    for face, s, z in sites:
        if new:
            RULES.board(detail, fine, face, s, z)
        else:
            H.notice_board(detail, fine, face, s, z, 26, 28, "pool_rules")
    return detail, fine


old, new = boards(False), boards(True)
RM.load_extras()
for model in (*old, *new):
    model.tile_overrides.update({paint: RM.TILES.get(paint, 64.0) for paint in model.polygons})
for i, name in enumerate(("riverdale_hall_detail", "riverdale_hall_fine")):
    rel = Path("models/maps/riverdale") / (name + ".obj")
    baseline, current = OUT / "baseline" / rel, OUT / "current" / rel
    baseline.parent.mkdir(parents=True, exist_ok=True)
    current.parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(baseline, old[i], name)
    K.write_obj(current, new[i], name)
    header, published = read_obj(ASSETS / rel)
    _, removed = read_obj(baseline)
    _, added = read_obj(current)
    before = Counter(published)
    assert not Counter(removed) - before, f"{name}: legacy sign faces do not match; refusing splice"
    after = before - Counter(removed) + Counter(added)
    # No face outside the exact old/new sign geometry may change.
    assert before - after == Counter(removed) - Counter(added)
    assert after - before == Counter(added) - Counter(removed)
    target = STAGE / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    write_obj(target, header, list(after.elements()))
    entry(rel)
    if i == 1:
        mtl = rel.with_suffix(".mtl")
        (STAGE / mtl).write_text((ASSETS / mtl).read_text() + f"\nnewmtl {RULES.PAINT}\nKd 1 1 1\nd 1\n", encoding="utf-8")
        entry(mtl)
        vmdl = rel.with_suffix(".vmdl")
        text = (ASSETS / vmdl).read_text()
        marker = '\t\t\t\t\t\t\t{ from = "rv_hall_signs.vmat"'
        remap = f'\t\t\t\t\t\t\t{{ from = "{RULES.PAINT}.vmat" to = "materials/riverdale/{RULES.PAINT}.vmat" }},\n'
        assert text.count(marker) == 1
        (STAGE / vmdl).write_text(text.replace(marker, remap + marker), encoding="utf-8", newline="\n")
        entry(vmdl)
    report.append({"Model": name, "OriginalFaces": len(published), "Removed": len(removed), "Added": len(added), "ResultFaces": sum(after.values()), "UnrelatedFacesPreserved": True})

mat = Path("materials/riverdale")
(STAGE / mat).mkdir(parents=True, exist_ok=True)
RULES.artwork().save(STAGE / mat / (RULES.PAINT + "_color.png"))
Image.new("RGB", (64,64), (128,128,255)).save(STAGE / mat / (RULES.PAINT + "_normal.png"))
Image.new("L", (64,64), 138).save(STAGE / mat / (RULES.PAINT + "_rough.png"))
for suffix in ("color", "normal", "rough"):
    entry(mat / (RULES.PAINT + "_" + suffix + ".png"))
vmat = f'''// Tools/riverdale_pool_rules.py
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "materials/riverdale/{RULES.PAINT}_color.png"
    TextureNormal "materials/riverdale/{RULES.PAINT}_normal.png"
    TextureRoughness "materials/riverdale/{RULES.PAINT}_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}}
'''
(STAGE / mat / (RULES.PAINT + ".vmat")).write_text(vmat, encoding="utf-8")
entry(mat / (RULES.PAINT + ".vmat"))
manifest = {"Entries": entries, "Geometry": report,
            "NorthSignPlanBounds": {"East": [-241, -215], "North": [1998.725, 1999.70], "Height": [40,74]},
            "NorthPilasterNearestEdge": -191, "HorizontalClearanceInches": 24,
            "SceneFileChanged": False}
(OUT / "stage.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({k:v for k,v in manifest.items() if k != "Entries"}, indent=2))
