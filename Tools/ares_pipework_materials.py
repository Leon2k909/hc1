"""Restrained pipe-specific satin steel, copper, cast hardware and contact metal."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

PREFIX='materials/ares/pipework-v1'
FINISHES={
    'pipe':((106,115,119),.30,.55),
    'copper':((151,82,46),.76,.50),
    'cast':((61,68,71),.58,.56),
    'metal':((172,178,180),.86,.34),
    'rubber':((30,32,30),0.,.84),
}


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(73026);size=1024
    raw=rng.standard_normal((size,size)).astype(np.float32)
    def field(sigma):
        value=gaussian_filter(raw,sigma,mode='wrap');return value/max(value.std(),1e-8)
    fine=field(.8);broad=field(22);grain=field((.7,10));scuff=field((1.2,35))
    # Subtle tangent-space microtexture, never the deep relief of stone or rust.
    height=.0015*fine+.0005*grain
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.6
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.6
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/'micro_normal.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    for name,(color,metal,rough) in FINISHES.items():
        variation=.003*fine+.004*broad+.002*grain
        if name=='copper':variation+=.004*np.tanh(broad)
        if name=='rubber':variation*=.5
        rgb=np.asarray(color)[None,None,:]*(1+variation[...,None])
        # Fine rubbed streaks affect reflection more than the base colour.
        scratches=np.clip(scuff-1.6,0,1.5)*.009
        rgb+=scratches[...,None]*22
        r=np.clip(rough+.005*fine+.009*broad-scratches,.16,.94)
        Image.fromarray(np.uint8(np.clip(rgb,0,255))).save(out/f'{name}_color.png')
        Image.fromarray(np.uint8(r*255)).save(out/f'{name}_rough.png')
        normal='micro_normal.png' if name=='cast' else 'flat_normal.png'
        text=('// Tools/ares_pipework_materials.py\n"Layer0"\n{\n'
            '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
            f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
            f'    TextureColor "{PREFIX}/{name}_color.png"\n'
            f'    TextureNormal "{PREFIX}/{normal}"\n'
            f'    TextureRoughness "{PREFIX}/{name}_rough.png"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            '    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n}\n')
        (out/f'{name}.vmat').write_text(text)
