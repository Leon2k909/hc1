"""Stage architectural shed shading outside live assets."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

folder=Path(__file__).resolve().parent
root=folder.parents[2]
sys.path.insert(0,str(root/'Tools'))
import map_kit as K
import lowtide_map as L
import lowtide_shed_weathering as W
stage=folder/'shed-weathering-stage'
live=root/'Assets'
K.ASSETS=stage
layout=W.bake(L, folder)
materials={
    'materials/lowtide/lt_brick.vmat':.9,
    'materials/lowtide/lt_brick_soot.vmat':.9,
    'materials/lowtide/finish/lt_quay_stone.vmat':.7,
    'materials/lowtide/masonry/lt_granite_trim.vmat':.7,
}
for name,strength in materials.items():
    text=(live/name).read_text()
    assert 'TextureShedWear' not in text,name
    head,tail=text.rsplit('}',1)
    path=stage/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(head+W.material_inputs(strength)+'}'+tail)
shader=(live/'shaders/hc1_brick.shader').read_text()
anchor='    #include "common/pixel.hlsl"\n'
assert shader.count(anchor)==1
shader=shader.replace(anchor,anchor+'    #include "common/lowtide_shed_wear.hlsl"\n')
anchor='        #endif\n        return ShadingModelStandard::Shade( input, material );'
assert shader.count(anchor)==1
shader=shader.replace(anchor,'''        if ( g_flShedWear > 0 )
        {
            float3 deposits = ShedWear( world, normalize( input.vNormalWs ) ) * g_flShedWear;
            material.AmbientOcclusion *= 1 - saturate( deposits.r * .65 );
            material.Albedo *= 1 - saturate( deposits.g * .62 + deposits.r * .10 );
            material.Albedo = lerp( material.Albedo, float3( .31, .29, .25 ), deposits.b * .35 );
            material.Roughness = saturate( material.Roughness + deposits.g * .07 );
        }
'''+anchor)
(stage/'shaders/hc1_brick.shader').write_text(shader)
files=[*materials,'shaders/hc1_brick.shader','shaders/common/lowtide_shed_wear.hlsl',W.RESOURCE,W.RESOURCE+'.meta']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changes={}
for name in files:
    path=live/name
    if path.exists():
        backup=folder/'shed-weathering-before'/name
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(path,backup)
    changes[name]={'before':digest(path) if path.exists() else None,'after':digest(stage/name)}
protected={}
for path in (live/'models/maps/lowtide').iterdir():
    if path.suffix in ('.obj','.mtl','.vmdl'):protected[str(path.relative_to(root))]=digest(path)
for name in ('Assets/scenes/maps/lowtide/lowtide.scene','Assets/shaders/hc1_slate.shader',
             'Assets/materials/lowtide/roofs/lt_slate.vmat','Assets/materials/lowtide/lt_brick_v2_color.png',
             'Assets/materials/lowtide/masonry/facade_wear.png'):
    protected[name]=digest(root/name)
(folder/'shed-weathering-manifest.json').write_text(json.dumps({'changes':changes,'protected':protected},indent=2)+'\n')
print(json.dumps({'staged':len(changes),'protected':len(protected),'windows':layout['window_count'],'elevations':len(layout['records'])*2}))
