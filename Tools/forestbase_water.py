"""Deterministic flow and impact masks for Forest Base's backdrop waterfall."""
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
import map_kit as K

OUT = K.ASSETS / 'materials/forestbase'
RESOURCE = 'materials/forestbase'


def normalized(values):
    return (values - values.mean()) / max(values.std(), 1e-6)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(39171)
    shape = (2048, 512)
    # Connected turbulent sheets; texture controls froth, not missing water.
    streak = normalized(gaussian_filter(rng.normal(size=shape), (18, 2.2), mode='wrap'))
    swell = normalized(gaussian_filter(rng.normal(size=shape), (48, 24), mode='wrap'))
    detail = normalized(gaussian_filter(rng.normal(size=shape), (4, .8), mode='wrap'))
    density = np.clip(.65 + streak*.12 + swell*.10 + detail*.035, 0, 1)
    flow = np.stack((density, np.clip(.5+detail*.14, 0, 1), np.clip(.5+swell*.16, 0, 1)), axis=-1)
    Image.fromarray((flow*255).astype('uint8')).save(OUT/'waterfall_flow.png')
    y, x = np.mgrid[-1:1:1024j, -1:1:1024j]
    noise = normalized(gaussian_filter(rng.normal(size=x.shape), 9, mode='wrap'))
    fine = normalized(gaussian_filter(rng.normal(size=x.shape), 2, mode='wrap'))
    radius = np.sqrt(x*x+y*y)
    # Impact foam trails away from the cliff: several connected, torn plumes
    # with a dense turbulent origin and sparse downstream strings. Keeping
    # the boundary anchored avoids a drifting rectangular texture footprint.
    trail = normalized(gaussian_filter(rng.normal(size=x.shape), (26, 4), mode='wrap'))
    width = .18 + .40*(1-y)/2
    centers = (x + .12*np.sin(y*5) + .075*noise)
    envelope = np.exp(-(centers/width)**2*1.7)
    end = np.clip((1-np.abs(y)+noise*.06)*6,0,1)
    veins = np.clip((trail*.20 + noise*.12 + fine*.07 - .035)*3,0,1)
    impact = np.exp(-((x/.35)**2+((y-.34)/.40)**2)*1.5)
    foam = (veins*envelope*.75 + impact*np.clip(.35+noise*.16+fine*.14,0,.75))*end
    # River foam is long narrow streaks separated by exposed water, rather
    # than circular rafts. The two phases in the shader advect this pattern.
    current = np.clip((trail*.23+noise*.08+fine*.045-.12)*4,0,1)
    current *= np.clip((1-np.abs(x)+noise*.08)*4,0,1)*np.clip((1-np.abs(y))*5,0,1)*.63
    edge = np.clip((1-radius+noise*.075)*5, 0, 1)
    broken = np.clip(.57+noise*.18+fine*.09, 0, 1)
    for name, values in [('waterfall_foam', foam),
                         ('waterfall_current', current),
                         ('waterfall_spray', edge*broken*.35*np.exp(-radius*radius*1.3))]:
        Image.fromarray((np.clip(values,0,1)*255).astype('uint8')).save(OUT/f'{name}_mask.png')
        shader=('forestbase_mist' if name=='waterfall_spray' else
                'forestbase_current' if name=='waterfall_current' else 'forestbase_foam')
        footprint=' EllipticalFootprint "1"\n' if name=='waterfall_foam' else ''
        basin=' ConstrainPlungeBasin "1"\n' if name in ('waterfall_spray','waterfall_foam') else ''
        mist_strength=' MistStrength "1.8"\n' if name=='waterfall_spray' else ''
        K.write_text(OUT/f'{name}.vmat', f'''"Layer0"
{{
 shader "shaders/{shader}.shader"
 SplashMask "{RESOURCE}/{name}_mask.png"
{footprint}
{basin}
{mist_strength}
}}
''')
    K.write_text(OUT/'waterfall.vmat', f'''"Layer0"
{{
 shader "shaders/forestbase_waterfall.shader"
 FlowMask "{RESOURCE}/waterfall_froth_v2.png"
}}
''')
    K.write_text(OUT/'river.vmat', '"Layer0"\n{\n shader "shaders/forestbase_river.shader"\n}\n')
    K.write_text(OUT/'waterfall_plunge.vmat', f'''"Layer0"
{{
 shader "shaders/forestbase_foam.shader"
 SplashMask "{RESOURCE}/waterfall_froth_v2.png"
 EllipticalFootprint "1"
 ConstrainPlungeBasin "1"
}}
''')
    K.write_text(OUT/'waterfall_impact.vmat', f'''"Layer0"
{{
 shader "shaders/forestbase_mist.shader"
 SplashMask "{RESOURCE}/waterfall_spray_mask.png"
 MistStrength "3.2"
 ConstrainPlungeBasin "1"
}}
''')
    K.write_text(OUT/'cascade_rock.vmat','''"Layer0"
{
 shader "shaders/forestbase_cliff_infill.shader"
 F_SPECULAR "1"
 RockMappingScale "106"
 TextureColor "materials/forestbase/scans/rock_face_03_diff.jpg"
 TextureNormal "materials/forestbase/scans/rock_face_03_nor_gl.jpg"
 TextureRoughness "materials/forestbase/scans/rock_face_03_rough.jpg"
 TextureAmbientOcclusion "materials/forestbase/scans/rock_face_03_ao.jpg"
}
''')
    print('Forest Base connected cascade sheets, impact froth, wet rock and spray masks written.')


if __name__ == '__main__':
    main()
