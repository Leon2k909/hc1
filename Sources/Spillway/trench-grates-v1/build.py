from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/spillway/trench-grates-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,spillway_map as R,riverdale_splice as S
import grate
folder=STAGE/'Assets/materials/spillway/trench-grates-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(58833);grain=rng.normal(0,1,(1024,1024));y,x=np.mgrid[:1024,:1024]
fleck=(np.sin(x*.11+np.sin(y*.07)*3)+np.cos(y*.13+np.sin(x*.08)*2))*1.6
col=np.array((155.,160.,157.))+(grain*2+fleck)[:,:,None]
Image.fromarray(np.clip(col,0,255).astype('uint8')).save(folder/'steel_color.png')
Image.fromarray(np.clip(145+grain*3+fleck,0,255).astype('uint8')).save(folder/'steel_rough.png')
dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.012;dy=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.012
n=np.stack((dx,dy,np.ones_like(grain)),2);n/=np.linalg.norm(n,axis=2)[:,:,None]
Image.fromarray(np.clip((n*.5+.5)*255,0,255).astype('uint8')).save(folder/'steel_normal.png')
for name,tint,metal,rough in (('steel',(1,1,1),.8,.83),('frame',(.48,.55,.54),.65,1.1),('dark',(.032,.028,.022),0,1.5),('bolt',(.43,.45,.43),.82,.65)):
 (folder/(name+'.vmat')).write_text(f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/spillway/trench-grates-v1/steel_color.png"
 TextureNormal "materials/spillway/trench-grates-v1/steel_normal.png"
 TextureRoughness "materials/spillway/trench-grates-v1/steel_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
}}
''')
modeldir=STAGE/'Assets/models/maps/spillway/trench-grates-v1';modeldir.mkdir(parents=True,exist_ok=True)
old=K.Model();P.quad(old,'rv_grating',(330,-460,.35),(1,0,0),(0,1,0),150,55);R.configure(old)
OUT.mkdir(parents=True,exist_ok=True);K.write_obj(OUT/'sample-original.obj',old,'spillway_cargo')
_,faces=S.read_obj(OUT/'sample-original.obj');_,published=S.read_obj(ROOT/'Assets/models/maps/spillway/spillway_cargo.obj')
assert not Counter(faces)-Counter(published),'Original grate does not match'
preview=K.Model();P.quad(preview,'rv_grating',(0,0,.35),(1,0,0),(0,1,0),150,55);R.configure(preview)
K.write_obj(modeldir/'before.obj',preview,'spillway_cargo');K.write_vmdl(modeldir/'before.vmdl','models/maps/spillway/trench-grates-v1','before',preview)
translated=[]
for mat,corners in faces:
 q=[]
 for p,uv,n in corners:
  a,b,c=map(float,p.split());q.append((f'{a+330:.3f} {b:.3f} {c+460:.3f}',uv,n))
 translated.append((mat,tuple(q)))
S.write_obj(modeldir/'before.obj',['mtllib before.mtl\n','o before\n'],translated)
new=grate.grate(K.Model(),(0,0,0),150,55);R.configure(new)
triangles=K.write_obj(modeldir/'grate.obj',new,'spillway_cargo');K.write_vmdl(modeldir/'grate.vmdl','models/maps/spillway/trench-grates-v1','grate',new)
plan=dict(triangles=triangles,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({'Triangles':triangles})
for name in ('native.py','import_preview.cs.txt','compile.py','capture.cs.txt'):
 text=(ROOT/'Sources/Riverside/searchlight-v1'/name).read_text().replace('riverside/searchlight-v1','spillway/trench-grates-v1')
 if name=='compile.py':text=text.replace("('before','searchlight')","('before','grate')")
 if name=='capture.cs.txt':
  text=text.replace('"before","searchlight"','"before","grate"').replace('Searchlight comparison','Trench grate comparison')
  text=text.replace('new Vector3(0,0,-16)','new Vector3(0,0,0)').replace('W(60,-82,36)','W(110,-160,165)').replace('W(0,0,-1)','W(0,0,0)').replace('FieldOfView=29','FieldOfView=46')
 (HERE/name).write_text(text)
