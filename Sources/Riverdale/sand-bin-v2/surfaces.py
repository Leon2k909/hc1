"""Object-specific PBR maps for weathered moulded plastic, no baked lighting."""
from PIL import Image,ImageFilter,ImageDraw
import numpy as np
def write_surfaces(folder,res):
 size=1024;rng=np.random.default_rng(7314)
 def noise(n):
  a=rng.random((n,n));return np.asarray(Image.fromarray((a*255).astype('uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
 yy,xx=np.mgrid[0:size,0:size]/(size-1)
 for kind in ('body','lid'):
  broad=noise(12);cloud=noise(56);fine=noise(256);grain=rng.random((size,size))
  # V zero is the foot on upright faces. Restrained grime is ingrained in the plastic.
  bottom=np.exp(-yy*13)*(0.35+0.65*cloud) if kind=='body' else np.zeros_like(xx)
  bands=noise(70);streak=np.asarray(Image.fromarray((bands*255).astype('uint8')).filter(ImageFilter.GaussianBlur(2)),float)/255
  streak=np.roll(streak,170,axis=0)*(0.25+0.75*noise(14))
  dirt=np.clip(bottom*.55+(cloud-.48).clip(0)*.035+(streak-.53).clip(0)*.04,0,.65)
  fade=(broad-.5)*.025+(fine-.5)*.008
  base=np.array([176.,135.,43.]);rgb=np.ones((size,size,3))*base
  rgb*=1+fade[:,:,None];rgb=rgb*(1-dirt[:,:,None])+np.array([68.,60.,42.])*dirt[:,:,None]
  # Thin shallow scuffs, clustered lightly rather than a uniformly distressed coat.
  scratches=Image.new('L',(size,size));draw=ImageDraw.Draw(scratches)
  for k in range(95):
   x=int(rng.integers(15,size-15));y=int(rng.integers(10,size-10));length=int(rng.integers(4,45));dy=int(rng.integers(-15,16))
   draw.line((x,y,x+length,y+dy),fill=int(rng.integers(35,105)),width=1)
  scuff=np.asarray(scratches,float)/255
  rgb+=scuff[:,:,None]*np.array([35.,30.,18.]);rgb+=(grain-.5)[:,:,None]*2.
  rough=np.clip(.59+dirt*.35+(cloud-.5)*.025+scuff*.13,.44,.91)
  height=(fine-.5)*.035+(grain-.5)*.07-scuff*.08
  dx=np.roll(height,-1,1)-np.roll(height,1,1);dy=np.roll(height,-1,0)-np.roll(height,1,0)
  normal=np.stack((-dx*.12,dy*.12,np.ones_like(dx)),axis=2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
  maps=dict(color=np.uint8(np.clip(rgb,0,255)),rough=np.uint8(rough*255),normal=np.uint8((normal*.5+.5)*255),ao=np.uint8(np.ones_like(xx)*255))
  name='sb_'+kind
  for suffix,data in maps.items():Image.fromarray(data).save(folder/f'{name}_{suffix}.png',compress_level=1)
  (folder/f'{name}.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
 g_flModelTintAmount "1"
'''+''.join(f' Texture{field} "{res}/{name}_{suffix}.png"\n' for field,suffix in [('Color','color'),('Normal','normal'),('Roughness','rough'),('AmbientOcclusion','ao')])+'}\n')
