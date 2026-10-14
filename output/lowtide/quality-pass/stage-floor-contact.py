import hashlib
import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STAGE = OUT / "floor-contact-stage/Assets"
BEFORE = OUT / "floor-contact-before"
files = ["Assets/shaders/hc1_lowtide_concrete.shader", "Assets/materials/lowtide/interior/lt_concrete.vmat", "Tools/lowtide_interior.py"]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if not BEFORE.exists():
    BEFORE.mkdir()
    sources = {}
    for rel in files:
        p = ROOT/rel
        target = BEFORE/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        sources[rel] = sha(p)
    geometry = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in (ROOT/"Assets/models/maps/lowtide").iterdir() if p.suffix in (".obj", ".mtl", ".vmdl")}
    scene = ROOT/"Assets/scenes/maps/Lowtide/lowtide.scene"
    geometry[str(scene.relative_to(ROOT)).replace("\\", "/")] = sha(scene)
    (BEFORE/"manifest.json").write_text(json.dumps({"sources": sources, "geometry_and_scene": geometry}, indent=2)+"\n")
manifest = json.loads((BEFORE/"manifest.json").read_text())
for rel, digest in manifest["sources"].items():
    assert sha(ROOT/rel) == digest, f"Source changed since snapshot: {rel}"

shader = (BEFORE/files[0]).read_text()
shader = shader.replace("    float g_flConcreteScale", '''    CreateInputTexture2D( TextureFloorContact, Linear, 8, "", "_ao", "Floor contact", Default3( 1, 1, 1 ) );
    Texture2D g_tFloorContact < Channel( RGB, Box( TextureFloorContact ), Linear ); OutputFormat( BC7 ); SrgbRead( false ); >;
    SamplerState FloorContactSampler < Filter( MIN_MAG_MIP_LINEAR ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    float g_flFloorContact < Default( 0 ); Range( 0, 1 ); >;
    float g_flConcreteScale''')
shader = shader.replace("        m.Metalness = 0;", '''        // Static diffuse occlusion for the two concrete warehouse floors only.
        // The bake is made from saved architecture/cargo, not a painted shadow.
        // Other concrete, vertical faces and elevated surfaces remain unmasked.
        float east = -m.WorldPosition.y;
        float north = m.WorldPosition.x;
        if ( g_flFloorContact > 0 && abs( m.WorldPosition.z ) < .1 && i.vNormalWs.z > .98
            && abs( east ) > 240 && abs( east ) < 1000 && north > -400 && north < 1150 )
        {
            float2 uv = float2( ( abs( east ) - 240 ) / 760, 1 - ( north + 400 ) / 1550 );
            // Each atlas cell is 384 x 768. Clamp to its own texel centres.
            uv = clamp( uv, float2( .5 / 384, .5 / 768 ), 1 - float2( .5 / 384, .5 / 768 ) );
            uv.x = uv.x * .5 + ( east < 0 ? .5 : 0 );
            float2 contact = g_tFloorContact.Sample( FloorContactSampler, uv ).rg;
            float visibility = lerp( 1, contact.r, .85 ) * lerp( 1, contact.g, .45 );
            m.AmbientOcclusion *= lerp( 1, visibility, g_flFloorContact );
        }
        m.Metalness = 0;''')
material = (BEFORE/files[1]).read_text().replace('    g_flConcreteScale', '    TextureFloorContact "materials/lowtide/interior/floor_contact.png"\n    g_flFloorContact "1"\n    g_flConcreteScale')
for rel, content in ((files[0][7:], shader), (files[1][7:], material)):
    path = STAGE/rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
texture = STAGE/"materials/lowtide/interior/floor_contact.png"
shutil.copy2(OUT/"floor-contact-stage/floor_contact.png", texture)
texture.with_suffix(".png.meta").write_text(json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, "hc1/"+str(texture.relative_to(STAGE)).replace("\\", "/")))}, indent=2)+"\n")
print("Staged static floor contact texture, shader and material; runtime assets untouched")
