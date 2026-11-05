from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/orion/yard-lamp-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,orion_map as R,riverdale_splice as S,riverdale_parts as P
import lamp
assert not (ROOT/'Tools/orion_yard_lamp.py').exists(),'Already installed; retain historical comparison'
folder=STAGE/'Assets/materials/orion/yard-lamp-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(84142);grain=rng.normal(0,1,(1024,1024))
Image.fromarray(np.clip(np.array((139.,145.,136.))+grain[:,:,None]*1.5,0,255).astype('uint8')).save(folder/'coat_color.png')
Image.new('RGB',(8,8),(238,238,238)).save(folder/'hardware_color.png')
Image.fromarray(np.clip(167+grain*3,0,255).astype('uint8')).save(folder/'rough.png')
dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.012;dy=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.012
n=np.stack((dx,dy,np.ones_like(grain)),2);n/=np.linalg.norm(n,axis=2)[:,:,None]
Image.fromarray(np.clip((n*.5+.5)*255,0,255).astype('uint8')).save(folder/'normal.png')
for name,tint,metal,rough,color in (('coat',(1,1,1),.12,.95,'coat_color.png'),('seal',(.035,.041,.034),0,1.3,'hardware_color.png'),('alloy',(.53,.57,.53),.82,.64,'hardware_color.png')):
 (folder/(name+'.vmat')).write_text(f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/orion/yard-lamp-v1/{color}"
 TextureNormal "materials/orion/yard-lamp-v1/normal.png"
 TextureRoughness "materials/orion/yard-lamp-v1/rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
}}
''')
modeldir=STAGE/'Assets/models/maps/orion/yard-lamp-v1';modeldir.mkdir(parents=True,exist_ok=True)
old=lamp.original(K.Model());R.configure(old);K.write_obj(OUT/'sample-original.obj',old,'orion_props')
_,faces=S.read_obj(OUT/'sample-original.obj');_,published=S.read_obj(ROOT/'Assets/models/maps/orion/orion_props.obj')
assert not Counter(faces)-Counter(published),'Original lamp does not match public model'
stub=K.Model();P.cylinder(stub,(0,5),2.4,-12,0,'oa_steel',8);R.configure(stub)
K.write_obj(OUT/'review-stub.obj',stub,'orion_props');stubfaces=S.read_obj(OUT/'review-stub.obj')[1]
preview=lamp.original(K.Model(),(0,0,0));preview.extend(stub);R.configure(preview)
K.write_obj(modeldir/'before.obj',preview,'orion_props');K.write_vmdl(modeldir/'before.vmdl','models/maps/orion/yard-lamp-v1','before',preview)
e,n,z=lamp.CENTRE;translated=[]
for mat,corners in faces:
 q=[]
 for p,uv,nrm in corners:
  a,b,c=map(float,p.split());q.append((f'{a+e:.3f} {b-z:.3f} {c-n:.3f}',uv,nrm))
 translated.append((mat,tuple(q)))
S.write_obj(modeldir/'before.obj',['mtllib before.mtl\n','o before\n'],translated+stubfaces)
new=lamp.local();new.extend(stub);R.configure(new)
count=K.write_obj(modeldir/'lamp.obj',new,'orion_props');K.write_vmdl(modeldir/'lamp.vmdl','models/maps/orion/yard-lamp-v1','lamp',new)
plan=dict(triangles=count,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print({'Triangles':count})
for name in ('native.py','import_preview.cs.txt','compile.py','capture.cs.txt'):
 text=(ROOT/'Sources/Spillway/trench-grates-v1'/name).read_text().replace('spillway/trench-grates-v1','orion/yard-lamp-v1')
 if name=='compile.py':text=text.replace("('before','grate')","('before','lamp')")
 if name=='capture.cs.txt':
  text=text.replace('"before","grate"','"before","lamp"').replace('Trench grate comparison','Yard lamp head comparison')
  text=text.replace('new Vector3(0,0,0)','new Vector3(0,0,-12.2f)').replace('W(110,-160,165)','W(18,-32,-8)').replace('W(0,0,0)','W(0,0,-3)').replace('FieldOfView=46','FieldOfView=34')
 (HERE/name).write_text(text)
