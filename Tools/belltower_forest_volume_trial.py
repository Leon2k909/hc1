"""Stage rounded canopy lighting on the existing silhouette study, without scene edits.

The vertex shader decodes the atlas rectangle once per vertex. A separate UV
interpolant describes the crown; world derivatives supply the actual card frame.
All original atlas pixels, alpha, vertex positions and triangle counts remain intact.
"""
import hashlib
import json
import os
from pathlib import Path
import winreg
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/quality/forest-volume-v1'
SHADER='shaders/belltower_forest_volume_trial.shader'
MATERIALS='materials/belltower/forest/volume-v1'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def engine_root():
    value=os.environ.get('FACEPUNCH_ENGINE')
    if not value:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
            value=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
    return Path(value).resolve()


def replace_once(source,old,new):
    assert source.count(old)==1,old[:80]
    return source.replace(old,new,1)


def main():
    if (OUT/'manifest.json').exists():raise FileExistsError('Preserve the recorded volume trial.')
    OUT.mkdir(parents=True,exist_ok=True)
    record_path=ROOT/'Sources/Belltower/generated/forest-trees-v2.json'
    record=json.loads(record_path.read_text())
    atlas=ROOT/'Sources/Belltower/generated/forest-trees-v2.png'
    assert sha(atlas)==record['selected_sha256']
    with Image.open(atlas) as image:alpha=np.asarray(image.getchannel('A'))
    rectangles=[];calibrations=[];statistics=[]
    for region in record['regions']:
        x0,y0,x1,y1=region['pixel_rect'];a=alpha[y0:y1,x0:x1]>=90
        widths=[]
        for row in a:
            x=np.flatnonzero(row);widths.append(int(x[-1]-x[0]+1) if len(x) else 0)
        widths=np.convolve(widths,np.ones(5)/5,mode='same')
        crown_rows=np.flatnonzero(widths>=max(widths)*.24)
        assert len(crown_rows)>20
        top,bottom=int(crown_rows[0]),int(crown_rows[-1])
        yy,xx=np.nonzero(a[top:bottom+1]);yy+=top
        left,right=int(xx.min()),int(xx.max())
        width,height=x1-x0,y1-y0
        centre=((left+right)/2/width,1-(top+bottom)/2/height)
        radius=((right-left+1)/width*.535,(bottom-top+1)/height*.535)
        assert all(np.isfinite((*centre,*radius))) and min(radius)>.1
        u0,v0,u1,v1=region['uv_rect_top_down']
        rectangles.append((u0,1-v1,u1,1-v0))
        calibrations.append((*centre,*radius))
        statistics.append({'variant':region['variant'],'species':region['species'],
                           'local_crown_centre':centre,'local_crown_radius':radius,
                           'alpha_threshold':90,'crown_rows':[top,bottom]})
    rectangles=np.array(rectangles);calibrations=np.array(calibrations)
    # The installed vertex format declares LowPrecisionUv. Check exact and
    # half-float vertex UVs against the same decoder tolerance used by the shader.
    maximum_error=0.
    for index,rect in enumerate(rectangles):
        for expected in ((0,0),(1,0),(1,1),(0,1)):
            point=rect[:2]+np.asarray(expected)*(rect[2:]-rect[:2])
            for uv in (point,point.astype(np.float16).astype(np.float32)):
                corner_x=np.minimum(abs(rectangles[:,0]-uv[0]),abs(rectangles[:,2]-uv[0]))
                corner_y=np.minimum(abs(rectangles[:,1]-uv[1]),abs(rectangles[:,3]-uv[1]))
                matches=np.flatnonzero((corner_x<.00035)&(corner_y<.00035))
                assert matches.tolist()==[index],(index,uv,matches)
                local=(uv-rect[:2])/(rect[2:]-rect[:2])
                maximum_error=max(maximum_error,float(np.max(abs(local-np.asarray(expected)))))
    assert maximum_error<.0025
    engine=engine_root()
    engine_inputs=['core/shaders/common/pixelinput.hlsl','core/shaders/common/vertexinput.hlsl']
    pixel=(engine/engine_inputs[0]).read_text()
    assert 'TEXCOORD8' not in pixel and 'LowPrecisionUv' in (engine/engine_inputs[1]).read_text()
    template_path=ROOT/'Assets/shaders/belltower_forest_coverage_trial.shader'
    shader=template_path.read_text()
    rows=lambda values:',\n'.join('        float4('+', '.join(f'{x:.9f}' for x in row)+')' for row in values)
    common='''
    // Calibrated from unchanged source alpha, not an edited normal-map bitmap.
    static const float4 CrownAtlasRect[16] = {
__RECTS__
    };
    static const float4 CrownShape[16] = {
__SHAPES__
    };
    float2 DecodeCrownShape( float2 uv )
    {
        [unroll] for ( int n = 0; n < 16; ++n )
        {
            float4 rect = CrownAtlasRect[n];
            float2 cornerDistance = min( abs( uv - rect.xy ), abs( uv - rect.zw ) );
            if ( all( cornerDistance < .00035 ) )
            {
                float2 local = saturate( ( uv - rect.xy ) / ( rect.zw - rect.xy ) );
                return ( local - CrownShape[n].xy ) / CrownShape[n].zw;
            }
        }
        return float2( 0, -10 ); // Unknown UVs retain the original terrain normal.
    }
'''.replace('__RECTS__',rows(rectangles)).replace('__SHAPES__',rows(calibrations))
    shader=replace_once(shader,'#include "common/shared.hlsl"','#include "common/shared.hlsl"\n'+common)
    shader=replace_once(shader,'#include "common/pixelinput.hlsl"',
                        '#include "common/pixelinput.hlsl"\n    float2 vCrownShape : TEXCOORD8;')
    shader=replace_once(shader,'PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }',
                        '''PixelInput MainVs( VertexInput i )
    {
        PixelInput result = FinalizeVertex( ProcessVertex( i ) );
        result.vCrownShape = DecodeCrownShape( result.vTextureCoords.xy );
        return result;
    }''')
    volume='''
    float g_flCrownVolumeStrength < Default( 0 ); Range( 0, .8 ); UiGroup( "Crown volume,30/10" ); >;
    float3 CrownLightingNormal( PixelInput i, float3 worldPosition, float3 original )
    {
        float crownWindow = smoothstep( -1.55, -.85, i.vCrownShape.y );
        float strength = g_flCrownVolumeStrength * crownWindow;
        // Uniform branch only: quad derivatives must precede the varying crown mask.
        [branch] if ( g_flCrownVolumeStrength <= .00001 ) return original;
        float3 px = ddx( worldPosition ), py = ddy( worldPosition );
        float2 ux = ddx( i.vCrownShape ), uy = ddy( i.vCrownShape );
        float determinant = ux.x * uy.y - ux.y * uy.x;
        [branch] if ( abs( determinant ) <= 1e-12 ) return original;
        float3 across = normalize( ( px * uy.y - py * ux.y ) / determinant );
        float3 up = normalize( ( py * ux.x - px * uy.x ) / determinant );
        float3 face = normalize( cross( across, up ) );
        if ( dot( face, g_vCameraPositionWs - worldPosition ) < 0 ) face = -face;
        float2 q = i.vCrownShape;
        float bulge = sqrt( saturate( 1.0 - dot( q, q ) ) );
        float3 rounded = normalize( across * q.x + up * q.y + face * bulge );
        return normalize( lerp( original, rounded, strength ) );
    }
'''
    shader=replace_once(shader,'float4 MainPs( PixelInput i ) : SV_Target0',volume+'\n    float4 MainPs( PixelInput i ) : SV_Target0')
    shader=replace_once(shader,'m.GeometricNormal = m.Normal;',
                        'm.Normal = CrownLightingNormal( i, m.WorldPosition, m.Normal );\n        m.GeometricNormal = m.Normal;')
    files=[]
    def stage(relative,content):
        path=OUT/'Assets'/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(content,encoding='utf8',newline='\n')
        assert not (ROOT/'Assets'/relative).exists(),'Use a fresh trial resource name.'
        files.append({'path':relative,'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
    stage(SHADER,shader)
    material_path=ROOT/'Assets/materials/belltower/forest/shapes-v1/forest_trees.vmat'
    material=replace_once(material_path.read_text(),'shaders/belltower_forest_coverage_trial.shader',SHADER)
    assert 'g_flCanopyMipCompensation "0"' in material
    for name,strength in [('control',0),('rounded',.42)]:
        text=replace_once(material,'\n}',f'\n    g_flCrownVolumeStrength "{strength}"\n}}')
        stage(f'{MATERIALS}/{name}.vmat',text)
    inputs=[Path(__file__),record_path,atlas,template_path,material_path,
            ROOT/'output/belltower/quality/forest-shapes-v1/manifest.json',
            ROOT/'Assets/scenes/maps/Belltower/belltower.scene']
    manifest={'revision':'forest-volume-v1','state':'staged; native compiler and appearance review pending',
              'files':files,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in inputs},
              'engine_source_sha256':{p:sha(engine/p) for p in engine_inputs},
              'calibration':statistics,'atlas_corner_decoding_verified':True,
              'maximum_half_float_local_uv_error':maximum_error,
              'unchanged_atlas_sha256':sha(atlas),'additional_texture_samples':0,
              'additional_texture_files':0,'additional_triangles':0,'additional_colliders':0,
              'control_strength':0,'candidate_strength':.42,'canopy_mip_compensation':0,
              'model_source_revision':'forest-shapes-v1','bounded_model_count':8,
              'candidate_material':f'{MATERIALS}/rounded.vmat','control_material':f'{MATERIALS}/control.vmat',
              'native_visual_review_verified':False,'runtime_performance_verified':False,
              'scope':'Eight existing west-sector silhouette meshes. New crown diffuse normals only; alpha, fade, palette and specular suppression remain unchanged. Unknown vertex UVs and trunks use the original normal. No scene or accepted asset edits.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'staged_assets':3,'additional_triangles':0,'additional_texture_samples':0,
                      'maximum_half_float_local_uv_error':maximum_error,'native_review_pending':True}))


if __name__=='__main__':main()
