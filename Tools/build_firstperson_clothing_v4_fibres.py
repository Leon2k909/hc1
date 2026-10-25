"""Stage an analytic cotton height map and stable, model-space textile sampling."""
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/firstperson-clothing-v4-20261021"
STAGE = OUT / "fibre-stage"
SOURCE = ROOT / "Sources/Clothing/firstperson-v4"
assert not (STAGE / "manifest.json").exists()
STAGE.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


previous = json.loads((OUT / "native-import-clean.json").read_text())
published = {p["Path"].replace("\\", "/"): p["Sha256"] for p in previous["Published"]}
for name in ["Assets/shaders/viewmodel_fabric_v4.shader", "Assets/materials/operators/first_person/v4/shirt.vmat"]:
    assert sha(ROOT / name) == published[name]
    shutil.copy2(ROOT / name, STAGE / (Path(name).name + ".before"))

# Technical PBR data, not painted colour: 32 periodic yarn cycles per tile,
# with a shallow 2/2 diagonal modulation of the crossing threads.
y, x = np.mgrid[0:256, 0:256].astype(np.float64) / 8
warp, weft = np.cos(2 * np.pi * x), np.cos(2 * np.pi * y)
height = .5 + .17 * warp + .14 * weft + .05 * np.cos(np.pi * (x + y) / 2) * warp * weft
data = np.dstack((height, np.full_like(height, .5), np.full_like(height, .5)))
height_path = STAGE / "cotton-height.png"
Image.fromarray(np.rint(np.clip(data, 0, 1) * 255).astype(np.uint8)).save(height_path)

shader_path = SOURCE / "viewmodel_fabric_v4.shader"
shader = shader_path.read_text()
assert sha(shader_path) == published["Assets/shaders/viewmodel_fabric_v4.shader"]
shader = shader.replace('    #include "common/pixelinput.hlsl"\n',
                        '    #include "common/pixelinput.hlsl"\n    float3 vFabricRestPosition : TEXCOORD14;\n')
old_vs = '    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }'
new_vs = '''    PixelInput MainVs( VertexInput i )
    {
        float3 fabricPosition = i.vPositionOs;
        PixelInput result = ProcessVertex( i );
        result.vFabricRestPosition = fabricPosition;
        return FinalizeVertex( result );
    }'''
assert old_vs in shader
shader = shader.replace(old_vs, new_vs)
anchor = '    // Each image is authored over just this UV rectangle'
extra = '''    CreateInputTexture2D( TextureFabricHeight, Linear, 8, "", "_cotton_height", "Cotton,25/10", Default3( 0.5, 0.5, 0.5 ) );
    Texture2D g_tFabricHeight < Channel( RGB, Box( TextureFabricHeight ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    float g_flFabricTiling < Default( 3.0 ); Range( 0.5, 8.0 ); UiGroup( "Cotton,25/20" ); >;
    float g_flFabricRelief < Default( 0.0008 ); Range( 0.0, 0.003 ); UiGroup( "Cotton,25/30" ); >;

    // Binding the fine textile to unprocessed model positions makes its scale
    // independent of the narrow, stretched cuff UV islands. Three projections
    // blend around the rounded arm and remain continuous across UV seams.
    float CottonHeight( float3 restPosition )
    {
        float3 restNormal = cross( ddx( restPosition ), ddy( restPosition ) );
        restNormal *= rsqrt( max( dot( restNormal, restNormal ), 0.00000000000000000001 ) );
        float3 weights = pow( abs( restNormal ) + 0.000001, 4.0 );
        weights /= max( dot( weights, float3( 1, 1, 1 ) ), 0.00000001 );
        float3 p = restPosition * g_flFabricTiling;
        return dot( weights, float3(
            g_tFabricHeight.Sample( TextureFiltering, p.yz ).r,
            g_tFabricHeight.Sample( TextureFiltering, p.xz ).r,
            g_tFabricHeight.Sample( TextureFiltering, p.xy ).r ) );
    }

    float3 CottonNormal( float3 normalWs, float3 positionWs, float height )
    {
        // Surface-gradient bump mapping: use actual deformed geometry to orient
        // the tiny thread relief, rather than treating triplanar normals as UV normals.
        float3 dx = ddx( positionWs );
        float3 dy = ddy( positionWs );
        float3 r1 = cross( dy, normalWs );
        float3 r2 = cross( normalWs, dx );
        float determinant = dot( dx, r1 );
        float3 gradient = sign( determinant ) * (ddx( height ) * r1 + ddy( height ) * r2) * g_flFabricRelief;
        if ( abs( determinant ) < 0.0000000001 ) return normalWs;
        return normalize( abs( determinant ) * normalWs - gradient );
    }

'''
assert shader.count(anchor) == 1
shader = shader.replace(anchor, extra + anchor)
old = '        m.Normal = TransformNormal( combined, i.vNormalWs, i.vTangentUWs, i.vTangentVWs );'
new = old + '''
        float cotton = CottonHeight( i.vFabricRestPosition );
        m.Normal = CottonNormal( m.Normal, i.vPositionWithOffsetWs, cotton );
        m.Albedo *= 1.0 + (cotton - 0.5) * 0.025;'''
assert shader.count(old) == 1
shader = shader.replace(old, new)
shader_path.write_text(shader, encoding="utf-8")

material = (ROOT / "Assets/materials/operators/first_person/v4/shirt.vmat").read_text()
material = material.replace('g_flFineNormalStrength "0.22"', 'g_flFineNormalStrength "0.06"')
material = material.replace('\n}', '\n    TextureFabricHeight "materials/operators/first_person/v4/cotton-height.png"\n    g_flFabricTiling "3"\n    g_flFabricRelief "0.0008"\n}')
material_path = STAGE / "shirt.vmat"
material_path.write_text(material, encoding="utf-8")
files = {}
for target, source in [("Assets/shaders/viewmodel_fabric_v4.shader", shader_path),
                       ("Assets/materials/operators/first_person/v4/shirt.vmat", material_path),
                       ("Assets/materials/operators/first_person/v4/cotton-height.png", height_path)]:
    files[target] = {"source": source.relative_to(ROOT).as_posix(), "sha256": sha(source),
                     "before": sha(ROOT / target) if (ROOT / target).exists() else None}
(STAGE / "manifest.json").write_text(json.dumps({"files": files, "tile_yarn_cycles": 32,
    "tiles_per_model_unit": 3, "relief_model_units": .0008, "data_map": "Analytic periodic height, linear RGB"}, indent=2), encoding="utf-8")
print(json.dumps({"assets": len(files), "data_map": "256 square analytic cotton height", "geometry_changed": False}))
