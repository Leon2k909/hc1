from pathlib import Path
from collections import Counter
import sys,json,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import zoom,gaussian_filter
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/boxyard/pipe-stacks-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,boxyard_map as B,riverdale_parts as P,riverdale_splice as S
import pipes
folder=STAGE/'Assets/materials/boxyard/pipe-stacks-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(66310);h,w=512,2048;grain=rng.normal(0,1,(h,w))
field=zoom(rng.random((32,128)),(h/32,w/128),order=3);fine=zoom(rng.random((128,512)),(h/128,w/512),order=1)
rust=np.clip((field+fine*.38-.47)*2.4,0,1)
steel=np.array((91,72,52));oxide=np.array((99,70,47))
streak=gaussian_filter(rng.normal(0,1,(h,w)),(.7,38))*18
pits=gaussian_filter((rng.random((h,w))>.978).astype(float),.6)*20
col=steel*(1-rust[:,:,None])+oxide*rust[:,:,None]+(grain*2.0+streak-pits)[:,:,None]
image=Image.fromarray(np.clip(col,0,255).astype('uint8'))
font=ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',23)
stamp=Image.new('L',(2048,40),0);ImageDraw.Draw(stamp).text((280,5),'DN 200   /   SCH 40   /   CARBON STEEL   /   LOT 24-07',font=font,fill=255)
stamp=stamp.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
for yy in (15,268):image.paste((146,132,105),(0,yy,2048,yy+40),stamp)
image.save(folder/'pipe_color.png')
Image.fromarray(np.clip(200+rust*18+grain*3,0,255).astype('uint8')).save(folder/'pipe_rough.png')
height=gaussian_filter(grain,.55)*.08+rust*.03
dx=np.roll(height,1,1)-np.roll(height,-1,1);dy=np.roll(height,-1,0)-np.roll(height,1,0)
n=np.stack((dx,dy,np.ones_like(grain)),2);n/=np.linalg.norm(n,axis=2)[:,:,None]
Image.fromarray(np.clip((n*.5+.5)*255,0,255).astype('uint8')).save(folder/'pipe_normal.png')
for name,tint,metal,rough in (('outer',(1,1,1),.52,1),('inner',(.35,.31,.25),.32,1.3),('rim',(1.22,1.2,1.12),.68,.78),('band',(.73,.81,.83),.84,.65)):
 (folder/(name+'.vmat')).write_text(f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/boxyard/pipe-stacks-v1/pipe_color.png"
 TextureNormal "materials/boxyard/pipe-stacks-v1/pipe_normal.png"
 TextureRoughness "materials/boxyard/pipe-stacks-v1/pipe_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
}}
''')
if (ROOT/'Tools/boxyard_pipe_stacks.py').exists():
 plan=json.loads((OUT/'preview-plan.json').read_text())
 for p in folder.glob('*'):
  if p.is_file():plan['files'][p.relative_to(STAGE).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 (OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2))
 print('Updated texture stage only; installed comparison geometry retained');raise SystemExit(0)
modeldir=STAGE/'Assets/models/maps/boxyard/pipe-stacks-v1';modeldir.mkdir(parents=True,exist_ok=True)
old=K.Model();B.pipes(old,782.,-480.,90.);B.configure(old)
K.write_obj(OUT/'sample-original.obj',old,'boxyard_props');_,faces=S.read_obj(OUT/'sample-original.obj');_,published=S.read_obj(ROOT/'Assets/models/maps/boxyard/boxyard_props.obj')
assert not Counter(faces)-Counter(published),'Original pipes no longer match'
# Inverse placement, retaining the exact published texture coordinates and normals.
from riverside_parts import place
preview=place(old,(480,782,0),-90);preview.boxes=[]
K.write_obj(modeldir/'before.obj',preview,'boxyard_props');K.write_vmdl(modeldir/'before.vmdl','models/maps/boxyard/pipe-stacks-v1','before',preview)
# Transfer published UVs into the translated comparison mesh rather than reprojecting.
rot=np.array(((0,1,0),(-1,0,0),(0,0,1)))
translated=[]
for mat,corners in faces:
 q=[]
 for p,uv,n in corners:
  a,b,c=map(float,p.split());local=rot@(np.array((-a,c,b))-np.array((782,-480,0)))
  na,nb,nc=map(float,n.split());normal=rot@np.array((-na,nc,nb))
  q.append((f'{-local[0]:.3f} {local[2]:.3f} {local[1]:.3f}',uv,f'{-normal[0]:.3f} {normal[2]:.3f} {normal[1]:.3f}'))
 translated.append((mat,tuple(q)))
S.write_obj(modeldir/'before.obj',['mtllib before.mtl\n','o before\n'],translated)
new=pipes.local(782.,-480.);B.configure(new)
triangles=K.write_obj(modeldir/'pipes.obj',new,'boxyard_props');K.write_vmdl(modeldir/'pipes.vmdl','models/maps/boxyard/pipe-stacks-v1','pipes',new)
plan=dict(triangles=triangles,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({'Triangles':triangles})
for name in ('native.py','import_preview.cs.txt','compile.py','capture.cs.txt'):
 text=(ROOT/'Sources/Spillway/trench-grates-v1'/name).read_text().replace('spillway/trench-grates-v1','boxyard/pipe-stacks-v1')
 if name=='compile.py':text=text.replace("('before','grate')","('before','pipes')")
 if name=='capture.cs.txt':
  text=text.replace('"before","grate"','"before","pipes"').replace('Trench grate comparison','Pipe stack comparison')
  text=text.replace('W(110,-160,165)','W(165,-145,75)').replace('W(0,0,0)','W(0,0,12)').replace('FieldOfView=46','FieldOfView=44')
 (HERE/name).write_text(text)
