"""Record native publication, visual comparisons and actual live material verification."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v3-20261021"


def read(path):
    return json.loads((OUT / path).read_text(encoding="utf-8"))


def native_json(path):
    receipt = read(path)
    assert not receipt.get("isError"), path
    return json.loads(next(c["text"] for c in receipt["content"] if c["type"] == "text"))


manifest = read("stage/manifest.json")
published = read("native-import.json")
comparison = read("native-r1/proof.json")
live = read("live-proof.json")
compilation = native_json("code-compile-settled/compile_status.json")
material = native_json("material-compile/asset_compile.json")
assert published["SharedEditorStatePreserved"]
assert comparison["SharedEditorStatePreserved"] and comparison["TemporarySceneDestroyed"]
assert len(comparison["Captures"]) == 6
assert material["Success"]
assert not compilation["IsBuilding"]
assert all(c["Success"] and c["Errors"] == 0 for c in compilation["Compilers"])
assert live["LiveProductionBindingVerified"] and live["SharedEditorStatePreserved"]
assert (OUT / "live-after/camera_screenshot.png").exists()
for c in comparison["Captures"]:
    assert Path(c["Captured"]).exists()
    if c["Version"] == "v3":
        assert all(t["Valid"] and not t["Error"] for t in c["Textures"])
for p in published["Published"]:
    target = ROOT / p["Path"]
    assert hashlib.sha256(target.read_bytes()).hexdigest() == p["Sha256"]
shader = ROOT / "Assets/shaders/viewmodel_fabric_v3.shader"
compiled = Path(str(shader) + "_c")
assert compiled.exists() and compiled.stat().st_mtime >= shader.stat().st_mtime
for path in [__file__, ROOT / "Tools/build_firstperson_clothing_v3.py"]:
    ast.parse(Path(path).read_text(encoding="utf-8"))
source_files = [ROOT / "Code/Weapons/ViewModelClothing.Materials.cs"]
source_files += sorted((ROOT / "Sources/Clothing/firstperson-v3").iterdir())
report = {
    "result": "Higher-density first-person sleeve and cuff textures applied and verified live",
    "density": manifest["density"],
    "published": published["Published"],
    "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source_files if p.is_file()},
    "prompts": json.loads((ROOT / "Sources/Clothing/firstperson-v3/imagegen-prompts.json").read_text()),
    "live": live,
    "native_comparisons": comparison,
    "compilation": {"all_successful": True, "errors": 0,
                    "warnings": {c["Name"]: c["Warnings"] for c in compilation["Compilers"] if c["Warnings"]}},
    "limits": [
        "Native generated pixel counts, rather than compiler-resized dimensions, determine the reported density gain.",
        "Live before and after cameras differ because the existing game remained interactive; use the fixed-camera native captures for direct comparisons.",
        "Original body garment geometry, animation rig and coverage remain; this revision changes only the first-person shirt material and its streaming bindings.",
    ],
}
(OUT / "applied-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"live_verified": True, "published_assets": len(published["Published"]),
                  "fixed_camera_images": len(comparison["Captures"]), "compile_errors": 0,
                  "report": str(OUT / "applied-report.json")}, indent=2))
