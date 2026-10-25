"""Audit final garment sources against native publication, renders and production dressing."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v4-20261021"


def read(path):
    return json.loads((OUT / path).read_text(encoding="utf-8"))


def native_json(path):
    receipt = read(path)
    assert not receipt.get("isError"), path
    return json.loads(next(c["text"] for c in receipt["content"] if c["type"] == "text"))


published = {}
for filename in ["native-import-clean.json", "native-import-fibres.json", "native-import-final-shader.json"]:
    result = read(filename)
    assert result["SharedEditorStatePreserved"], filename
    for entry in result["Published"]:
        published[entry["Path"].replace("\\", "/")] = entry
for path, entry in published.items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == entry["Sha256"], path
assert len(published) == 8
shader = ROOT / "Assets/shaders/viewmodel_fabric_v4.shader"
compiled = Path(str(shader) + "_c")
assert compiled.exists() and compiled.stat().st_mtime >= shader.stat().st_mtime
assert shader.read_bytes() == (ROOT / "Sources/Clothing/firstperson-v4/viewmodel_fabric_v4.shader").read_bytes()
assert "g_flFabricClean" not in shader.read_text(), "Rejected filter is present."

comparison = read("native-final-settled/proof.json")
assert comparison["SharedEditorStatePreserved"] and comparison["TemporarySceneDestroyed"]
assert not comparison["LiveMatchCapture"] and len(comparison["Captures"]) == 4
for capture in comparison["Captures"]:
    assert Path(capture["Captured"]).exists()
    if capture["Version"] == "v4":
        assert capture["Frames"] == 40
        assert all(t["Valid"] and not t["Error"] for t in capture["Textures"])
        assert len(capture["Textures"]) == 10
        assert next(t for t in capture["Textures"] if t["Key"] == "g_tFabricHeight")["Width"] == 256

dress = read("dressing-proof.json")
assert dress["EditorStatePreserved"] and dress["TemporarySceneDestroyed"]
assert dress["Dressing"]["ProductionDressVerified"]
assert dress["Dressing"]["BodyOutfitTintPreserved"]
assert dress["Dressing"]["ArmsBodygroupHidden"]
paths = {g["Name"]: g["Material"] for g in dress["Dressing"]["Garments"]}
assert paths == {"shirt": "materials/operators/first_person/v4/shirt.vmat",
                 "gloves": "materials/operators/first_person/v2/gloves.vmat"}
compilation = native_json("code-compile-final/compile_status.json")
assert not compilation["IsBuilding"]
assert all(c["Success"] and c["Errors"] == 0 for c in compilation["Compilers"])
material = native_json("material-compile-final/asset_compile.json")
assert material["Success"]
for path in ROOT.glob("Tools/*firstperson_clothing_v4*.py"):
    ast.parse(path.read_text(encoding="utf-8"))

source_files = list((ROOT / "Sources/Clothing/firstperson-v4").iterdir())
source_files += list(ROOT.glob("Tools/*firstperson_clothing_v4*.py"))
source_files += [ROOT / "Code/Weapons/ViewModelClothing.Materials.cs"]
report = {
    "result": "Clean camouflage colour with independent fine cotton relief applied to first-person shirt",
    "published": published,
    "dressing": dress,
    "comparison": comparison,
    "compilation": {"all_successful": True, "errors": 0,
                    "warnings": {c["Name"]: c["Warnings"] for c in compilation["Compilers"] if c["Warnings"]}},
    "source_hashes": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source_files if p.is_file()},
    "imagegen": json.loads((ROOT / "Sources/Clothing/firstperson-v4/imagegen-prompts.json").read_text()),
    "cotton_data": read("fibre-stage/manifest.json"),
    "limits": [
        "Previewed in private native scenes with the production dressing routine; shared play mode stayed stopped.",
        "Live-match appearance and animated textile stability have not been verified for this revision.",
        "Existing garment geometry, rig, world clothing, original coverage/tint maps and v2 glove profile are unchanged.",
        "Compiler resampling of generated artwork does not add source detail.",
    ],
}
(OUT / "applied-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"published_assets": len(published), "production_dress_verified": True,
                  "native_final_images": 4, "compile_errors": 0, "live_match_verified": False,
                  "report": str(OUT / "applied-report.json")}, indent=2))
