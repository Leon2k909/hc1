"""Forest Base boulder wrapper and wet, cool mineral/moss surface profile.

Original scan assets remain unchanged. Only the map's rock renderers use this
wrapper. Rim rocks keep their footprint and lose excessive vertical scaling.
"""
import math
from pathlib import Path
import map_kit as K

MODEL='models/maps/forestbase/forest_boulder.vmdl'
MATERIAL='materials/forestbase/forest_rock.vmat'
SHADER='shaders/forestbase_rock.shader'
PROFILE=dict(RockDesaturation=.82,RockWetness=.55,MossAmount=.80,
             RockTint=(.78,.84,.86),MossTint=(.035,.065,.025))


def rim(seed):
    return 80<=seed<118 and seed!=87


def height_scale(seed,scale):
    return min(scale[2]*.62,math.sqrt(scale[0]*scale[1])) if rim(seed) else scale[2]*(1 if seed==87 else .62)


def write(output=None):
    output=K.ASSETS if output is None else Path(output)
    template=(K.ASSETS/'models/maps/forestbase/boulder/cliff.vmdl').read_text()
    old='models/maps/forestbase/boulder/cliff.vmat'
    assert template.count(old)==1
    model=output/MODEL;model.parent.mkdir(parents=True,exist_ok=True)
    K.write_text(model,template.replace(old,MATERIAL))
    material=output/MATERIAL;material.parent.mkdir(parents=True,exist_ok=True)
    lines=['"Layer0"','{',f' shader "{SHADER}"',' F_SPECULAR "1"']
    for key,value in PROFILE.items():
        value='['+' '.join(map(str,value))+']' if isinstance(value,tuple) else str(value)
        lines.append(f' {key} "{value}"')
    for channel,file in (('Color','diff.jpg'),('Normal','nor_gl.jpg'),('Roughness','rough.png'),('AmbientOcclusion','ao.png')):
        lines.append(f' Texture{channel} "models/maps/forestbase/boulder/{file}"')
    lines+=[' TextureMetalness "[0 0 0 0]"','}']
    K.write_text(material,'\n'.join(lines)+'\n')
