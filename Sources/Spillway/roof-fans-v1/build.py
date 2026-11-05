from pathlib import Path
from collections import Counter
import hashlib,json,sys,shutil,time
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=HERE/'review';STAGE=OUT/'stage';INSTALL=OUT/'install-stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_splice as S,spillway_map as R
import fan as G
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8',newline='')
OUT.mkdir(parents=True,exist_ok=True)
inputs=['Tools/spillway_map.py','Assets/scenes/maps/Spillway/spillway.scene']
for name in G.PLACEMENTS:
 inputs += [f'Assets/models/maps/spillway/{name}.{ext}' for ext in ('obj','mtl','vmdl')]
 inputs += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/spillway').glob(name+'*hulls*.obj')]
guards={rel:sha(ROOT/rel) for rel in inputs};baseline='before-'+str(time.time_ns())
for rel in inputs:
 p=OUT/baseline/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
# Subtle PBR grain: geometry carries the blades, ribs, guard and folded edges.
folder=STAGE/'Assets/materials/spillway/roof-fans-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(94711);noise=rng.normal(0,1,(1024,1024));bands=np.repeat(rng.normal(0,1,(1,1024)),1024,axis=0)
Image.fromarray(np.clip(150+noise*2+bands,0,255).astype('uint8')).save(folder/'rough.png')
Image.fromarray(np.clip(np.array((180.,185.,178.))+noise[:,:,None]*.9+bands[:,:,None]*1.2,0,255).astype('uint8')).save(folder/'alloy_color.png')
dx=(np.roll(noise,1,1)-np.roll(noise,-1,1))*.004
norm=np.stack((dx,np.zeros_like(noise),np.ones_like(noise)),2);norm/=np.linalg.norm(norm,axis=2)[:,:,None]
Image.fromarray(np.clip((norm*.5+.5)*255,0,255).astype('uint8')).save(folder/'normal.png')
for name,tint,metal,rough in [('shell',(.62,.70,.70),.65,1.05),('blade',(.93,.95,.92),.8,.74),('guard',(.15,.19,.19),.65,1),('dark',(.025,.032,.028),.1,1.5)]:
 write(folder/(name+'.vmat'),f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/spillway/roof-fans-v1/alloy_color.png"
 TextureNormal "materials/spillway/roof-fans-v1/normal.png"
 TextureRoughness "materials/spillway/roof-fans-v1/rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
}}
''')
modeldir=STAGE/'Assets/models/maps/spillway/roof-fans-v1';modeldir.mkdir(parents=True,exist_ok=True)
def preview_model(name,faces,paints):
 m=K.Model()
 for p in paints:m.polygons[p]
 m.material_overrides.update(G.MATS);m.tile_overrides.update({p:48 for p in G.MATS});R.configure(m)
 K.write_obj(modeldir/(name+'.obj'),m,name)
 K.write_vmdl(modeldir/(name+'.vmdl'),'models/maps/spillway/roof-fans-v1',name,m)
 S.write_obj(modeldir/(name+'.obj'),['mtllib '+name+'.mtl\n','o '+name+'\n'],faces)
stats={}
for name,placements in G.PLACEMENTS.items():
 old=K.Model();new=K.Model()
 for centre,radius in placements:G.original(old,centre,radius);G.build(new,centre,radius)
 R.configure(old);R.configure(new);assert not new.hulls and not new.boxes
 K.write_obj(OUT/(name+'-removed.obj'),old,name);removed=Counter(S.read_obj(OUT/(name+'-removed.obj'))[1])
 K.write_obj(OUT/(name+'-added.obj'),new,name);added=S.read_obj(OUT/(name+'-added.obj'))[1]
 base=f'Assets/models/maps/spillway/{name}';header,public=S.read_obj(ROOT/(base+'.obj'))
 assert not removed-Counter(public),'Original fans no longer match '+name
 remain=list((Counter(public)-removed).elements());after=remain+added
 p=INSTALL/(base+'.obj');p.parent.mkdir(parents=True,exist_ok=True);S.write_obj(p,header,after)
 text=(ROOT/(base+'.vmdl')).read_bytes().decode();eol='\r\n' if '\r\n' in text else '\n';anchor=next(l for l in text.splitlines() if 'from = ' in l)
 remaps=eol.join(f'\t\t\t\t\t\t\t{{ from = "{key}.vmat" to = "{path}" }},' for key,path in G.MATS.items())
 write(INSTALL/(base+'.vmdl'),text.replace(anchor,remaps+eol+anchor,1))
 write(INSTALL/(base+'.mtl'),(ROOT/(base+'.mtl')).read_bytes().decode()+''.join(f'\nnewmtl {k}\nKd 1 1 1\nd 1\n' for k in G.MATS))
 preview_model(name+'_preview',after,set(p for p,_ in after))
 stats[name]=dict(fans=len(placements),removed=sum(removed.values()),added=len(added),preserved=len(remain))
# Matched closeups translate the actual world-space face samples, keeping UVs/normals intact.
centre,radius=G.PLACEMENTS['spillway_west'][1];e,n,z=centre
for variant,draw in [('before',G.original),('fan',G.build)]:
 m=draw(K.Model(),centre,radius);R.configure(m);K.write_obj(OUT/(variant+'-sample.obj'),m,'spillway_west')
 faces=S.read_obj(OUT/(variant+'-sample.obj'))[1];local=[]
 for paint,corners in faces:
  q=[]
  for p,uv,nrm in corners:
   x,y,zz=map(float,p.split());q.append((f'{x+e:.3f} {y-z:.3f} {zz-n:.3f}',uv,nrm))
  local.append((paint,tuple(q)))
 preview_model(variant,local,set(p for p,_ in local))
# Ready for a later acceptance; the public map is untouched during review.
text=(ROOT/'Tools/spillway_map.py').read_text();a=text.index('    e,n,z=centre',text.index('def roof_fan('));b=text.index('\n\ndef equipment_cover',a)
text=text[:a]+'    from spillway_roof_fans import build as draw_roof_fan\n    draw_roof_fan(m,centre,radius)\n'+text[b:]
write(INSTALL/'Tools/spillway_map.py',text);write(INSTALL/'Tools/spillway_roof_fans.py',(HERE/'fan.py').read_text())
plan=dict(baseline=baseline,guards=guards,files={p.relative_to(INSTALL).as_posix():sha(p) for p in INSTALL.rglob('*') if p.is_file()},stats=stats)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
(OUT/'preview-plan.json').write_text(json.dumps(dict(files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}),indent=2))
for file in ('native.py','import_preview.cs.txt'):
 s=(ROOT/'Sources/ReefHall/bronze-planter-v1'/file).read_text().replace('Sources/ReefHall/bronze-planter-v1/review','Sources/Spillway/roof-fans-v1/review').replace('reefhall/bronze-planter-v1','spillway/roof-fans-v1')
 (HERE/file).write_text(s)
print(json.dumps(stats,indent=2))
