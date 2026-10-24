"""Record successful native resource checks without claiming an in-map visual review."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT = Path.cwd().resolve()
HERE = Path(__file__).resolve().parent
assert ROOT == Path(r"C:\sbox-projects\hc1\forked-shooter-main")

def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

def native_rows(path):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert not receipt.get("isError"), path
    return [json.loads(c["text"]) for c in receipt["content"] if c["type"] == "text"]

model = json.loads((HERE / "compiled-model.json").read_text(encoding="utf-8"))
asset = native_rows(HERE / "model-before/asset_info.json")[0]
material_rows = native_rows(HERE / "all-materials/call_tools.json")
materials = [r for r in material_rows if r.get("Type") == "Material"]
compilers = native_rows(HERE / "project-compile/compile_status.json")[0]
assert len(materials) == 14
assert all(r["IsCompiledAndUpToDate"] and not r["IsCompileFailed"] for r in [asset] + materials)
assert not compilers["IsBuilding"]
assert all(c["Success"] and c["Errors"] == 0 for c in compilers["Compilers"])
assert model["EditorStatePreserved"] and model["NativeMaterialGeometryMatches"]
assert model["Triangles"] == 402832 and not model["IsError"]
assert all(not m["IsError"] for m in model["Materials"])
assert digest("Assets/models/maps/belltower/shop-display-v2/shop_displays.obj") == model["SourceSha256"]
shader_paths = ["Assets/shaders/belltower_shop_display_v2.shader", "Sources/Belltower/shop-displays/shop_display_v2.shader"]
assert all(digest(p) == model["ShaderSha256"] for p in shader_paths)
pixels = "4d65d15a761f3802ef7a0a74a113c6779d6a26b08a4b86176b3a3a5b52644c50"
assert digest("Assets/materials/belltower/shop-display-v2/labels-v2.png") == pixels
assert digest("Sources/Belltower/shop-displays/labels-v2.png") == pixels

report = {
    "verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "native_compilation_verified": True,
    "native_map_visual_review_verified": False,
    "native_model": model,
    "model_is_compiled_and_up_to_date": True,
    "shop_materials_compiled_and_up_to_date": len(materials),
    "loaded_model_materials_without_errors": len(model["Materials"]),
    "all_material_geometry_matches_source": True,
    "project_compile_errors": 0,
    "active_scene_camera_and_play_state_preserved": True,
    "shader_fix": {
        "problem": "AlphaWeighted mip filtering rejected the original 1254x1254 label artwork.",
        "solution": "Use Box colour filtering inside CommonInputs for this fully opaque shader.",
        "paths": shader_paths,
        "before_sha256": "b4b9462d66881454639c3e7d21a52cab91a70c559fa805a829f46fa01b8eae52",
        "after_sha256": model["ShaderSha256"],
        "texture_pixels_changed": False,
        "label_pixels_sha256": pixels,
        "originals": str((HERE / "before").relative_to(ROOT)).replace("\\", "/")
    },
    "remaining": "Saved Belltower close-up review requires a shared-editor handoff; the main chat is running a scale test.",
    "thumbnail_scope": "Native overview thumbnail only; insufficient for close-up acceptance."
}
report_path = HERE / "native-verification.json"
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

manifest_path = ROOT / "Sources/Belltower/props/soft-shop-props-v1.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["model_sha256"] == model["SourceSha256"]
manifest["state"] = "native compilation verified; saved-map close-up review pending shared-editor handoff"
manifest["native_compilation_verified"] = True
manifest["native_map_visual_review_verified"] = False
manifest["native_verification"] = str(report_path.relative_to(ROOT)).replace("\\", "/")
manifest["shader_compile_compatibility_fix"] = report["shader_fix"]
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

verification_path = ROOT / "output/belltower/prop-edge-audit/verification.json"
verification = json.loads(verification_path.read_text(encoding="utf-8"))
verification.update(native_compilation_verified=True, native_map_visual_review_verified=False,
                    native_verification=str(report_path.relative_to(ROOT)).replace("\\", "/"))
verification_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"native_compilation_verified": True, "native_materials": len(materials),
                  "native_triangles": model["Triangles"], "native_map_visual_review_verified": False}))
