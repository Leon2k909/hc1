"""Stage a material correction for baked fabric relief; existing artwork is unchanged."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v4-20261021"
STAGE = OUT / "stage"
SOURCE = ROOT / "Sources/Clothing/firstperson-v4"
assert not (STAGE / "manifest.json").exists(), "Preserve existing staging evidence."
STAGE.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)

shader = (ROOT / "Sources/Clothing/firstperson-v3/viewmodel_fabric_v3.shader").read_text()
shader = shader.replace('Description = "First-person sleeves with separately authored close-up UV regions";',
                        'Description = "First-person cotton: edge-preserving print filtering and restrained fabric relief";')
anchor = '    // Each image is authored over just this UV rectangle'
assert shader.count(anchor) == 1
shader = shader.replace(anchor, '''    float g_flFabricClean < Default( 0.9 ); Range( 0.0, 1.0 ); UiGroup( "Surface,20/60" ); >;
    float g_flFoldNormalStrength < Default( 0.45 ); Range( 0.0, 1.0 ); UiGroup( "Surface,20/70" ); >;
    float g_flFabricFilterTexels < Default( 6.0 ); Range( 1.0, 12.0 ); UiGroup( "Surface,20/80" ); >;

''' + anchor)
old = '''        float3 colour = image.SampleGrad( TextureFiltering, regionUv, ddx( uv ) / size, ddy( uv ) / size ).rgb;
        return lerp( previous, colour, weight );'''
new = '''        float2 dx = ddx( uv ) / size;
        float2 dy = ddy( uv ) / size;
        // The generated colour sources contain raised-looking coarse yarn.
        // Use a second mip footprint to suppress that low-contrast relief, while
        // retaining the centre sample at print boundaries and actual stitching.
        // Explicit gradients preserve anisotropic filtering at grazing angles.
        float3 colour = image.SampleGrad( TextureFiltering, regionUv, dx, dy ).rgb;
        uint width, height;
        image.GetDimensions( width, height );
        float2 dimensions = float2( width, height );
        float footprint = max( length( dx * dimensions ), length( dy * dimensions ) );
        float filterScale = max( 1.0, g_flFabricFilterTexels / max( footprint, 0.05 ) );
        float3 broad = image.SampleGrad( TextureFiltering, regionUv, dx * filterScale, dy * filterScale ).rgb;
        float keepEdge = smoothstep( 0.025, 0.10, length( broad - colour ) );
        colour = lerp( colour, broad, g_flFabricClean * (1.0 - keepEdge) );
        return lerp( previous, colour, weight );'''
assert shader.count(old) == 1
shader = shader.replace(old, new)
shader = shader.replace('g_tColor.SampleBias( TextureFiltering, uv, -0.65 )', 'g_tColor.Sample( TextureFiltering, uv )')
shader = shader.replace('g_tNormal.SampleBias( TextureFiltering, uv, -0.35 )', 'g_tNormal.Sample( TextureFiltering, uv )')
shader = shader.replace('float3( folds.xy + fine.xy * g_flFineNormalStrength, folds.z )',
                        'float3( folds.xy * g_flFoldNormalStrength + fine.xy * g_flFineNormalStrength, folds.z )')
shader = shader.replace('clamp( m.Roughness + data.x * 0.06, 0.55, 0.96 )',
                        'clamp( max( m.Roughness, 0.84 ) + data.x * 0.035, 0.80, 0.96 )')
shader_path = SOURCE / "viewmodel_fabric_v4.shader"
assert not shader_path.exists()
shader_path.write_text(shader, encoding="utf-8")

material = (ROOT / "Assets/materials/operators/first_person/v3/shirt.vmat").read_text()
material = material.replace("viewmodel_fabric_v3.shader", "viewmodel_fabric_v4.shader")
material = material.replace('g_flFineScale "12"', 'g_flFineScale "24"')
material = material.replace('g_flFineNormalStrength "0.4"', 'g_flFineNormalStrength "0.12"')
material = material.replace('g_flFineColourStrength "0.02"', 'g_flFineColourStrength "0.008"')
material = material.replace('\n}', '\n    g_flFabricClean "0.9"\n    g_flFoldNormalStrength "0.45"\n    g_flFabricFilterTexels "6"\n}')
material_path = STAGE / "shirt.vmat"
material_path.write_text(material, encoding="utf-8")
files = {}
for target, source in [("Assets/shaders/viewmodel_fabric_v4.shader", shader_path),
                       ("Assets/materials/operators/first_person/v4/shirt.vmat", material_path)]:
    files[target] = {"source": source.relative_to(ROOT).as_posix(),
                     "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
(STAGE / "manifest.json").write_text(json.dumps({"files": files, "artwork_changed": False}, indent=2), encoding="utf-8")
print(json.dumps({"staged_assets": len(files), "artwork_changed": False}))
