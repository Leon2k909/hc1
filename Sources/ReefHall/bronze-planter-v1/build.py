from pathlib import Path
from collections import Counter
import sys,json,hashlib,shutil,time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=HERE/'review';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,reefhall_map as R,riverdale_splice as S
import planter as G
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
 p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='')
OUT.mkdir(parents=True,exist_ok=True)
base='Assets/models/maps/reefhall/reefhall_lobby'
inputs=['Tools/reefhall_map.py',*[base+'.'+e for e in ('obj','mtl','vmdl')],
 'Assets/scenes/maps/ReefHall/reefhall.scene']
inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/reefhall').glob('reefhall_lobby*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
header,published=S.read_obj(ROOT/(base+'.obj'))
old=K.Model();new=K.Model()
for centre in G.CENTRES:G.original(old,centre);G.shell(new,centre)
R.configure(old);R.configure(new)
K.write_obj(OUT/'removed.obj',old,'reefhall_lobby');removed=Counter(S.read_obj(OUT/'removed.obj')[1])
assert not removed-Counter(published),'Original planters do not match public lobby'
K.write_obj(OUT/'added.obj',new,'reefhall_lobby');added=S.read_obj(OUT/'added.obj')[1]
remaining=list((Counter(published)-removed).elements())
assert not new.boxes and not new.hulls
assert sum(removed.values())==52
folder=STAGE/'Assets/materials/reefhall/bronze-planter-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(79329);n=1024
grain=rng.normal(0,1,(n,n));bands=rng.normal(0,1,(1,n));bands=np.repeat(bands,n,axis=0)
colour=np.clip(np.array((147.,106.,64.))+bands[:,:,None]*1.1+grain[:,:,None]*.6,0,255).astype('uint8')
Image.fromarray(colour).save(folder/'bronze_color.png')
Image.fromarray(np.clip(112+bands*3+grain*2,0,255).astype('uint8')).save(folder/'rough.png')
dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.003
normal=np.stack((dx,np.zeros_like(dx),np.ones_like(dx)),2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(folder/'normal.png')
for name,tint,metal,rough in (('bronze',(1,1,1),.85,1),('edge',(1.08,1.08,1.08),.88,.8),('toe',(.23,.25,.26),.55,1.35)):
 put(f'Assets/materials/reefhall/bronze-planter-v1/{name}.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/reefhall/bronze-planter-v1/bronze_color.png"
 TextureNormal "materials/reefhall/bronze-planter-v1/normal.png"
 TextureRoughness "materials/reefhall/bronze-planter-v1/rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
}}
''')
modeldir=STAGE/'Assets/models/maps/reefhall/bronze-planter-v1';modeldir.mkdir(parents=True,exist_ok=True)
# Matched closeups carry the exact published soil and leaves, rather than regenerated foliage.
e,n,z=G.CENTRES[0]
foliage=[]
for mat,corners in published:
 if mat not in ('rh_leaf','rh_soil'):continue
 p=np.array([list(map(float,c[0].split())) for c in corners])
 if abs(p[:,0].mean()+e)<38 and abs(p[:,2].mean()-n)<38 and p[:,1].min()>40 and p[:,1].max()<100:
  foliage.append((mat,corners))
assert sum(x[0]=='rh_leaf' for x in foliage)==1800
def localise(faces):
 result=[]
 for mat,corners in faces:
  q=[]
  for p,uv,nrm in corners:
   a,b,c=map(float,p.split());q.append((f'{a+e:.3f} {b-z:.3f} {c-n:.3f}',uv,nrm))
  result.append((mat,tuple(q)))
 return result
oldone=G.original(K.Model(),G.CENTRES[0]);newone=G.shell(K.Model(),G.CENTRES[0])
for name,m in [('before',oldone),('planter',newone)]:
 R.configure(m);K.write_obj(OUT/(name+'-world.obj'),m,'reefhall_lobby')
 faces=localise(S.read_obj(OUT/(name+'-world.obj'))[1]+foliage)
 m.polygons['rh_soil'];m.polygons['rh_leaf'] # remaps for unchanged published details
 K.write_obj(modeldir/(name+'.obj'),m,'reefhall_lobby')
 K.write_vmdl(modeldir/(name+'.vmdl'),'models/maps/reefhall/bronze-planter-v1',name,m)
 S.write_obj(modeldir/(name+'.obj'),['mtllib '+name+'.mtl\n','o '+name+'\n'],faces)
# Full lobby candidate is a render-only review asset. The public map remains untouched.
materials=K.Model()
for paint in set(mat for mat,_ in published)|set(G.MATS):materials.polygons[paint]
materials.material_overrides.update(new.material_overrides);R.configure(materials)
K.write_obj(modeldir/'lobby_preview.obj',materials,'reefhall_lobby')
K.write_vmdl(modeldir/'lobby_preview.vmdl','models/maps/reefhall/bronze-planter-v1','lobby_preview',materials)
S.write_obj(modeldir/'lobby_preview.obj',['mtllib lobby_preview.mtl\n','o lobby_preview\n'],remaining+added)
# Installation is prepared separately for the user's next acceptance.
install=OUT/'install-stage';p=install/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True)
S.write_obj(p,header,remaining+added)
text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in G.MATS.items())
(install/(base+'.vmdl')).write_bytes(text.replace(anchor,remaps+eol+anchor,1).encode())
(install/(base+'.mtl')).write_bytes((ROOT/(base+'.mtl')).read_bytes()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in G.MATS).encode())
text=(ROOT/'Tools/reefhall_map.py').read_text();start=text.index('    for k in range( 4 ):',text.index('def bronze_planter('));end=text.index('    soil = ',start)
text=text[:start]+'    from reefhall_bronze_planter import shell as draw_planter_shell\n    draw_planter_shell(model, centre, z, width, height, foot)\n'+text[end:]
start=text.index('    for k in range( 4 ):',text.index('def bronze_planter('));end=text.index('    model.hull(',start)
text=text[:start]+text[end:]
p=install/'Tools/reefhall_map.py';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
(install/'Tools/reefhall_bronze_planter.py').write_text((HERE/'planter.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(install).as_posix():sha(p) for p in install.rglob('*') if p.is_file()},
 planters=2,removed_triangles=sum(removed.values()),added_triangles=len(added),preserved_faces=len(remaining),foliage_triangles=len(foliage))
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
(OUT/'preview-plan.json').write_text(json.dumps(dict(files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}),indent=2))
for name in ('native.py','import_preview.cs.txt'):
 (HERE/name).write_text((ROOT/'Sources/Orion/yard-lamp-v1'/name).read_text().replace('output/orion/yard-lamp-v1','Sources/ReefHall/bronze-planter-v1/review').replace('orion/yard-lamp-v1','reefhall/bronze-planter-v1'))
print(json.dumps({k:v for k,v in plan.items() if k not in ('guards','files')},indent=2))
