from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
R=Path('C:/sbox-projects/hc1/forked-shooter-main');dest=R/'output/cerroblanco/queue-posts-metal-v2/stage/models/props/cerroblanco/queue_posts_metal_v2';dest.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(531);grain=gaussian_filter(rng.normal(size=(512,512)),(24,.65),mode='wrap');grain/=grain.std()
rough=np.clip(.15+grain*.018,.10,.21);Image.fromarray((rough*255).astype('uint8')).save(dest/'brushed_rough.png')
for name,tint,roughness in [('queue_shaft',.90,'models/props/cerroblanco/queue_posts_metal_v2/brushed_rough.png'),('queue_metal',.86,'[0.18 0.18 0.18 0]')]:
    (dest/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n g_flMetalness "1"\n g_flRoughnessScaleFactor "1"\n TextureColor "materials/default/default_color.tga"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "'+roughness+'"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_vColorTint "['+str(tint)+' '+str(tint)+' '+str(tint)+' 1]"\n g_flModelTintAmount "1"\n}\n')
