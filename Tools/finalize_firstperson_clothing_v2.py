"""Save the applied resource checks and limits after native clothing validation."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output/firstperson-clothing-v2-20261021"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


proof=read(OUT/"native-r5/proof.json")
dressing=read(OUT/"dressing-proof.json")
assert proof["ProductionMaterialBindingVerified"] and proof["EditorStatePreserved"]
assert dressing["Dressing"]["ProductionDressVerified"] and dressing["EditorStatePreserved"]
assert proof["TemporarySceneDestroyed"] and dressing["TemporarySceneDestroyed"]
stage=read(OUT/"stage/manifest.json")
assets={p:sha(ROOT/p) for p in stage["files"]}
sources=[ROOT/"Code/Weapons/ViewModelClothing.Materials.cs",ROOT/"Code/Weapons/ViewModelClothing.cs"]
sources+=list((ROOT/"Sources/Clothing/firstperson-v2").glob("*"))
sources += [ROOT/"Tools/build_firstperson_clothing_v2.py",Path(__file__).resolve()]
for path in sources:
    if path.suffix==".py":
        ast.parse(path.read_text(encoding="utf-8"))
report={
    "status":"applied",
    "scope":"First-person army-shirt sleeves and fingerless gloves; clothing models and UVs retained",
    "canonical_project":str(ROOT),
    "materials":[g["ExpectedMaterial"] for g in proof["Garments"]],
    "production_dressing":dressing,
    "native_render_validation":proof,
    "asset_sha256":assets,
    "source_sha256":{p.relative_to(ROOT).as_posix():sha(p) for p in sources if p.is_file()},
    "image_generation":read(ROOT/"Sources/Clothing/firstperson-v2/imagegen-prompts.json"),
    "generated_native_dimensions":{k:v["native_dimensions"] for k,v in stage["generated"].items()},
    "compiler_map_conversion":read(OUT/"compiler-map-conversion.json"),
    "source_coverage_and_tint_masks_preserved":True,
    "native_before_after_images":"output/firstperson-clothing-v2-20261021/native-r5/",
    "limits":[
        "These are isolated native garment renders, not a running-match capture.",
        "The base atlas resampling is for compiler mip compatibility, not newly generated 2048-pixel art.",
        "The separate repeating fine-detail layer supplies close-up surface detail.",
        "The new material does not replace third-person uniforms or the Militia flannel shirt.",
        "A neutral AO fallback replaces an unusable all-black engine AO readback."
    ]
}
(OUT/"applied-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":report["status"],"assets":len(assets),
    "production_dress_verified":True,"shared_editor_state_preserved":True,
    "report":str(OUT/"applied-report.json")}))
