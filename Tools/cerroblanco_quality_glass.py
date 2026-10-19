"""Stage a coated-glass comparison without touching the running editor's Assets.

Adapt the installed engine glass shader and its standard lighting function. The
only lighting change is the dielectric coating's normal-incidence reflectance,
used consistently for reflected light, transmission and the depth pass.
"""
from pathlib import Path
import argparse
import hashlib
import json
import textwrap

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Sources/CerroBlanco/glass-v1"
STAGE = ROOT / "output/cerroblanco/glass-stage"


def publish_accepted():
    """Called only by the base asset generator; unaccepted trials stay staged."""
    approval = SOURCE / "accepted.json"
    if not approval.exists():
        return
    import map_kit as K
    manifest = json.loads(approval.read_text())
    allowed = {"shaders/cerroblanco_glass.shader", "materials/cerroblanco/cb_glass.vmat"}
    assert {entry["path"] for entry in manifest["files"]} == allowed
    pending = []
    for entry in manifest["files"]:
        data = (SOURCE / entry["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], "Accepted glass source changed; repeat its native comparison"
        pending.append((K.ASSETS / entry["path"], data.decode("utf-8")))
    for path, content in pending:
        K.write_text(path, content)


def function_body(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return textwrap.dedent(source[start:end])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--reflectance", type=float, default=.10)
    args = parser.parse_args()
    assert .04 <= args.reflectance <= .2
    shader_root = args.engine / "core/shaders"
    glass = (shader_root / "glass.shader").read_text()
    standard = (shader_root / "common/shadingmodel.hlsl").read_text()
    original_hash = hashlib.sha256(glass.encode()).hexdigest()
    assert glass.count("0.04") == 2, "Review the updated engine glass shader before adapting it"
    shade = function_body(standard, "static float4 Shade( Material m )")
    shade = shade.replace("static float4 Shade( Material m )", "float4 ShadeCoatedGlass( Material m )", 1)
    shade = shade.replace("MaterialToCombinerInput( m );", "ShadingModelStandard::MaterialToCombinerInput( m );\n        combinerInput.vSpecularColor = g_flCoatingReflection.xxx;", 1)
    shade = shade.replace("return DoToolsVis( color, m, lightingTerms );", "return ShadingModelStandard::DoToolsVis( color, m, lightingTerms );", 1)
    assert "combinerInput.vSpecularColor" in shade
    glass = glass.replace("0.04", "g_flCoatingReflection")
    anchor = "    float g_flBlurAmount"
    assert glass.count(anchor) == 1
    glass = glass.replace(anchor, "    // Low-e coating: use the same Fresnel response for reflection and transmission.\n"
                          "    float g_flCoatingReflection < Default(0.10); Range(0.04, 0.20); UiGroup(\"Glass,10/5\"); >;\n\n" + anchor, 1)
    main_anchor = "    float4 MainPs(PixelInput i)  : SV_Target0"
    assert glass.count(main_anchor) == 1
    glass = glass.replace(main_anchor, textwrap.indent(shade, "    ") + "\n\n" + main_anchor, 1)
    glass = glass.replace("float4 output = ShadingModelStandard::Shade( m );", "float4 output = ShadeCoatedGlass( m );", 1)
    glass = "// Cerro Blanco coated glass; adapted from the installed engine glass shader.\n" + glass
    material = (ROOT / "Assets/materials/cerroblanco/cb_glass.vmat").read_text()
    material = material.replace('shader "shaders/glass.shader"', 'shader "shaders/cerroblanco_glass.shader"')
    material = material.replace('    F_GLASS_QUALITY "2"', f'    F_GLASS_QUALITY "2"\n    g_flCoatingReflection "{args.reflectance:.6f}"')
    material = material.replace("// Tools/cerroblanco_map.py, from materials/railhead/rw_glass.vmat", "// Tools/cerroblanco_quality_glass.py; low-e coated museum glazing")
    files = {"shaders/cerroblanco_glass.shader": glass,
             "materials/cerroblanco/cb_glass.vmat": material}
    manifest = {"candidate": "coating-v1", "reflectance": args.reflectance,
                "engine_glass_sha256": original_hash, "files": []}
    for relative, value in files.items():
        for base in (SOURCE, STAGE):
            path = base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8", newline="\n")
        data = (STAGE / relative).read_bytes()
        manifest["files"].append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    (ROOT / "output/cerroblanco/glass-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"files": len(files), "reflectance": args.reflectance, "published": False}))


if __name__ == "__main__":
    main()
