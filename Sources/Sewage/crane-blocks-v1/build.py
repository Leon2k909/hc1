from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/sewage/crane-blocks-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S
import crane
R.PAINTS.update(steel=96,yellow=64) # verified tile values in sewage_map.materials; no material regeneration
folder=STAGE/'Assets/materials/sewage/crane-blocks-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(84093);grain=rng.normal(0,1,(1024,1024))
col=np.array((175.,139.,49.))+grain[:,:,None]*1.5
Image.fromarray(np.clip(col,0,255).astype('uint8')).save(folder/'paint_color.png')
Image.new('RGB',(8,8),(235,235,235)).save(folder/'metal_color.png')
Image.fromarray(np.clip(171+grain*3,0,255).astype('uint8')).save(folder/'rough.png')
dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.016;dy=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.016
n=np.stack((dx,dy,np.ones_like(grain)),2);n/=np.linalg.norm(n,axis=2)[:,:,None]
Image.fromarray(np.clip((n*.5+.5)*255,0,255).astype('uint8')).save(folder/'normal.png')
label=Image.new('RGB',(1024,540),(212,191,122));draw=ImageDraw.Draw(label)
def font(s):return ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',s)
draw.rectangle((10,10,1013,529),outline=(48,47,35),width=7)
draw.text((45,32),'WATERWORKS  /  HOIST 02',font=font(57),fill=(39,44,36))
draw.line((42,116,982,116),fill=(57,59,41),width=4)
draw.text((44,132),'20 t',font=font(190),fill=(38,42,35));draw.text((44,347),'WORKING LOAD LIMIT',font=font(65),fill=(38,42,35))
draw.text((44,445),'INSPECT LATCH BEFORE USE',font=font(44),fill=(68,54,30));label.save(folder/'label_color.png')
y,x=np.mgrid[:256,:1024];stripe=((x+y*1.3)//120)%2
hazard=np.where(stripe[:,:,None]>0,np.array((43,45,37)),np.array((173,136,44)))
Image.fromarray(hazard.astype('uint8')).save(folder/'stripes_color.png')
for name,tint,metal,rough,color in (('paint',(1,1,1),.13,1,'paint_color.png'),('steel',(.35,.38,.34),.8,.85,'metal_color.png'),('dark',(.085,.095,.080),.45,1,'metal_color.png'),('label',(1,1,1),.08,1.2,'label_color.png'),('stripes',(1,1,1),.10,1,'stripes_color.png')):
 (folder/(name+'.vmat')).write_text(f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/sewage/crane-blocks-v1/{color}"
 TextureNormal "materials/sewage/crane-blocks-v1/normal.png"
 TextureRoughness "materials/sewage/crane-blocks-v1/rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
}}
''')
assert not (ROOT/'Tools/sewage_crane_blocks.py').exists(),'Already installed; do not overwrite historical review assets'
modeldir=STAGE/'Assets/models/maps/sewage/crane-blocks-v1';modeldir.mkdir(parents=True,exist_ok=True)
old=crane.original(R.model(),*crane.PLACEMENTS[0]);K.write_obj(OUT/'sample-original.obj',old,'sewage_details')
_,faces=S.read_obj(OUT/'sample-original.obj');_,published=S.read_obj(ROOT/'Assets/models/maps/sewage/sewage_details.obj')
assert not Counter(faces)-Counter(published),'Original crane block differs from installed geometry'
from riverside_parts import place
preview=place(old,-np.array(crane.PLACEMENTS[0]),0)
K.write_obj(modeldir/'before.obj',preview,'sewage_details');K.write_vmdl(modeldir/'before.vmdl','models/maps/sewage/crane-blocks-v1','before',preview)
translated=[]
e,n,z=crane.PLACEMENTS[0]
for mat,corners in faces:
 q=[]
 for p,uv,nrm in corners:
  a,b,c=map(float,p.split());q.append((f'{a+e:.3f} {b-z:.3f} {c-n:.3f}',uv,nrm))
 translated.append((mat,tuple(q)))
S.write_obj(modeldir/'before.obj',['mtllib before.mtl\n','o before\n'],translated)
new=crane.local();triangles=K.write_obj(modeldir/'crane.obj',new,'sewage_details');K.write_vmdl(modeldir/'crane.vmdl','models/maps/sewage/crane-blocks-v1','crane',new)
plan=dict(triangles=triangles,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({'Triangles':triangles})
for name in ('native.py','import_preview.cs.txt','compile.py','capture.cs.txt'):
 text=(ROOT/'Sources/Spillway/trench-grates-v1'/name).read_text().replace('spillway/trench-grates-v1','sewage/crane-blocks-v1')
 if name=='compile.py':text=text.replace("('before','grate')","('before','crane')")
 if name=='capture.cs.txt':
  text=text.replace('"before","grate"','"before","crane"').replace('Trench grate comparison','Crane lower block comparison')
  text=text.replace('new Vector3(0,0,0)','new Vector3(0,0,-56)').replace('W(110,-160,165)','W(105,-210,80)').replace('W(0,0,0)','W(0,0,20)').replace('FieldOfView=46','FieldOfView=39')
 (HERE/name).write_text(text)
