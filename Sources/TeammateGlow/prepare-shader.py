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
replacement='''        // A pixel is hidden only where cover stands in front of the character across
        // its whole 3x3 neighbourhood. A single depth tap reads the nearer surface
        // at the character's own depth edges (a vest's hem over the shirt, belts,
        // pockets) and on sloped triangles, which lit visible teammates.
        float2 pixelPosition = i.vPositionSs.xy - g_vViewportOffset;
        float2 screenUv = CalculateViewportUv( i.vPositionSs.xy );
        float objectDistance = Depth::Linearize( i.vPositionSs.z, pixelPosition );
        float coverDistance = 0.0f;
        [unroll] for ( int y = -1; y <= 1; y++ )
            [unroll] for ( int x = -1; x <= 1; x++ )
                coverDistance = max( coverDistance, CoverDistance( pixelPosition + float2( x, y ) ) );
        // About a pixel and a half of world size at that distance, for LOD and
        // depth precision, and never under a quarter inch.
        float pixelSize = objectDistance * 2.0f * g_vInvViewportSize.y / g_matViewToProjection[1][1];
        bool hidden = objectDistance > coverDistance + max( 0.25f, pixelSize * 1.5f );
        float4 vColor = hidden ? _ColorOccluded : _ColorMain;
'''
helper='''
	// The scene's distance at a pixel. The private highlight target uses projection
	// Z already; only the sampled scene depth needs the scene's layer range.
	float CoverDistance( float2 pixel )
	{
		pixel = clamp( pixel, 0.0f, 1.0f / g_vInvViewportSize - 1.0f );
		float depth = Depth::Get( pixel );
		float layer = ( depth - g_flViewportMinZ ) / ( g_flViewportMaxZ - g_flViewportMinZ );
		return Depth::Linearize( saturate( layer ), pixel );
	}
'''
anchor='\t//\n\t// Main\n\t//\n\tfloat4 MainPs'
text='// Scoped teammate variant of the engine object-highlight shader.\n'+text[:start]+replacement+text[end:]
assert text.count(anchor)==1
text=text.replace(anchor,helper+anchor,1)
text=text.replace('RenderState( CullMode, NONE );','RenderState( CullMode, BACK );')
dest=Path(__file__).with_name('hc1_teammate_occlusion.shader')
dest.write_text(text,encoding='utf8')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
target=root/'Assets/shaders/hc1_teammate_occlusion.shader'
record={'engine_source_sha256':sha(source),'shader_sha256':sha(dest),
        'before_sha256':sha(target) if target.exists() else None}
Path(__file__).with_name('shader-import.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
