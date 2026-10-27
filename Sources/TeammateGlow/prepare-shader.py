"""Derive a scoped highlight shader from the installed engine's implementation."""
import hashlib
import json
import os
from pathlib import Path
import winreg

root=Path(__file__).resolve().parents[2]
engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
        engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
source=Path(engine)/'core/shaders/postprocess/objecthighlight/objecthighlight.shader'
text=source.read_text(encoding='utf8')
start=text.index('\t\tfloat objectDepth = i.vPositionSs.z;')
end=text.index('\n\t\t// Add pattern to alpha',start)
replacement='''        // The private highlight target uses projection Z already. Normalize
        // only the sampled scene depth, which includes the scene's layer range.
        float2 pixelPosition = i.vPositionSs.xy - g_vViewportOffset;
        float2 screenUv = CalculateViewportUv( i.vPositionSs.xy );
        float objectDepth = i.vPositionSs.z;
        float worldDepth = Depth::GetNormalized( pixelPosition );
        float objectDistance = Depth::Linearize( objectDepth, pixelPosition );
        float worldDistance = Depth::Linearize( worldDepth, pixelPosition );
        // A tiny world-space tolerance prevents the character's own surface
        // being mistaken for cover, including flat arm/armour triangles.
        float tolerance = max( 0.12f, fwidth( objectDistance ) * 0.25f );
        bool hidden = objectDistance > worldDistance + tolerance;
        float4 vColor = hidden ? _ColorOccluded : _ColorMain;
'''
text='// Scoped teammate variant of the engine object-highlight shader.\n'+text[:start]+replacement+text[end:]
text=text.replace('RenderState( CullMode, NONE );','RenderState( CullMode, BACK );')
dest=Path(__file__).with_name('hc1_teammate_occlusion.shader')
dest.write_text(text,encoding='utf8')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
target=root/'Assets/shaders/hc1_teammate_occlusion.shader'
record={'engine_source_sha256':sha(source),'shader_sha256':sha(dest),
        'before_sha256':sha(target) if target.exists() else None}
Path(__file__).with_name('shader-import.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
