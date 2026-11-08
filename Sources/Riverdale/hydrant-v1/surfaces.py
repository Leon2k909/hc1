"""Deterministic, tileable painted-cast-iron PBR maps. No shared material is changed."""
from pathlib import Path
import numpy as np,io
from PIL import Image
def build(folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);N=512;rng=np.random.default_rng(5071)
 fy=np.fft.fftfreq(N)[:,None];fx=np.fft.fftfreq(N)[None,:];freq=fx*fx+fy*fy
 def noise(sigma):
  a=np.fft.ifft2(np.fft.fft2(rng.standard_normal((N,N)))*np.exp(-2*np.pi*np.pi*sigma*sigma*freq)).real
  return ((a-a.mean())/(a.std()+1e-8)).astype(np.float32)
 fine=noise(.65);grain=noise(1.5);patch=noise(9);large=noise(28)
 u,v=np.meshgrid(np.arange(N)/N,np.arange(N)/N)
 edge=np.exp(-np.minimum(v,1-v)*45);lower=np.exp(-v*9)
 chips=(patch+fine*.28+edge*2.4+lower*.30>2.2).astype(np.float32)
 # Pits and old paint loss cluster at flange rims; broad color shifts stay subtle.
 pits=np.maximum(0,-fine-1.7)*.10;streak=np.maximum(0,large-.6)*(.2+.8*v)
 for name,base,metal in [('cast_red',(137,32,24),.18),('cap_iron',(58,61,62),.55)]:
  col=np.array(base)[None,None,:]*(1+large[...,None]*.025+grain[...,None]*.016-streak[...,None]*.028)
  rust=np.array((76,48,31)) if name=='cast_red' else np.array((67,52,38))
  col=col*(1-chips[...,None])+rust*chips[...,None]
  height=grain*.018+fine*.006-pits-chips*.035
  dx=(np.roll(height,-1,1)-np.roll(height,1,1))*3;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*3
  normal=np.dstack((-dx,-dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2,keepdims=True)
  rough=np.clip(.64+grain*.018+chips*.14+streak*.02,.48,.88)
  arrays={'color':np.clip(col,0,255).astype(np.uint8),'normal':np.clip((normal*.5+.5)*255,0,255).astype(np.uint8),'rough':(rough*255).astype(np.uint8)}
  for suffix,a in arrays.items():
   b=io.BytesIO();Image.fromarray(a).save(b,format='PNG');(folder/f'{name}_{suffix}.png').write_bytes(b.getvalue())
  resource='materials/riverdale/hydrant_v1/'+name
  (folder/f'{name}.vmat').write_text('"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n g_flMetalness "'+str(metal)+'"\n g_flRoughnessScaleFactor "1"\n TextureColor "'+resource+'_color.png"\n TextureNormal "'+resource+'_normal.png"\n TextureRoughness "'+resource+'_rough.png"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n}\n')
