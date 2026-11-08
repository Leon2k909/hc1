from pathlib import Path
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
R=Path('C:/sbox-projects/hc1/forked-shooter-main');D=R/'output/cerroblanco/queue-posts-metal-v3/stage/models/props/cerroblanco/queue_posts_metal_v3';D.mkdir(parents=True,exist_ok=True)
backup=R/'output/cerroblanco/queue-posts-metal-v3/subtle-texture-draft';backup.mkdir(parents=True,exist_ok=True)
for name in ('shaft_color.png','shaft_rough.png','shaft_normal.png','queue_shaft.vmat'):
    if (D/name).exists() and not (backup/name).exists():shutil.copyfile(D/name,backup/name)
H,W=2048,512;rng=np.random.default_rng(1089)
def noise(sigma):
    a=gaussian_filter(rng.normal(size=(H,W)),sigma,mode='wrap');return a/max(a.std(),1e-8)
grain=noise((45,.55));fine=noise((4,.5));long=noise((220,8));cloud=noise((105,28))
tone=grain*3.2+fine*.8+long*12-cloud*4.0
colour=np.clip(np.array((210.,213.,215.))[None,None,:]+tone[...,None],0,255)
Image.fromarray(colour.astype('uint8')).save(D/'shaft_color.png')
rough=np.clip(.21+grain*.032+long*.05+cloud*.025,.10,.38)
Image.fromarray((rough*255).astype('uint8')).save(D/'shaft_rough.png')
height=grain*.0008+fine*.00015
dx=np.gradient(height,axis=1)/(6.91/W);dy=np.gradient(height,axis=0)/(33.15/H)
n=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1)[...,None]
Image.fromarray(np.clip((n*.5+.5)*255,0,255).astype('uint8')).save(D/'shaft_normal.png')
old=R/'Assets/models/props/cerroblanco/queue_posts_metal_v2/queue_metal.vmat';(D/'queue_metal.vmat').write_bytes(old.read_bytes())
prefix='models/props/cerroblanco/queue_posts_metal_v3/'
(D/'queue_shaft.vmat').write_text('"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n g_flMetalness "1"\n g_flRoughnessScaleFactor "1"\n TextureColor "'+prefix+'shaft_color.png"\n TextureNormal "'+prefix+'shaft_normal.png"\n TextureRoughness "'+prefix+'shaft_rough.png"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_vColorTint "[1 1 1 1]"\n g_flModelTintAmount "1"\n}\n')
