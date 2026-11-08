from pathlib import Path
from collections import Counter
import sys,json,hashlib,re,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K
LEGACY=ROOT/'Sources/Ares/bulkhead-lamp-trial-v1';OUT=ROOT/'output/ares/bulkhead-lamp-native-v1';STAGE=OUT/'stage/Assets'
RES='models/props/ares/bulkhead_lamp_native_v1';MAT='materials/ares/bulkhead_lamp_native_v1';MODEL=STAGE/RES;MATS=STAGE/MAT
for d in (MODEL,MATS):d.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
materials={};name=None
for line in (LEGACY/'bulkhead_lamp_after.mtl').read_text().splitlines():
 p=line.split()
 if not p:continue
 if p[0]=='newmtl':name=p[1];materials[name]={}
 elif name:materials[name][p[0]]=p[1:]
bindings={}
for name,data in materials.items():
 paint=name.lower();bindings[name]=f'{MAT}/{paint}.vmat'
 def texture(key,default):
  if key not in data:return default
  src=LEGACY/data[key][-1];shutil.copyfile(src,MATS/src.name);return f'{MAT}/{src.name}'
 color=texture('map_Kd','['+' '.join(data.get('Kd',['.5','.5','.5']))+' 1]')
 rough=texture('map_Ns','[0.45 0.45 0.45 0]');normal=texture('map_Bump','materials/default/default_normal.tga')
 if 'Internal_sealed' in name:
  text=(ROOT/'Assets/materials/ares/ar_led_warm.vmat').read_text()
 elif name=='Warm_internal_diffuser':
  text=(ROOT/'Assets/materials/ares/ar_led_warm.vmat').read_text().replace('"5.000"','"0.6"')
 elif 'borosilicate' in name.lower():
  text=(ROOT/'Assets/materials/ares/ar_glass.vmat').read_text().replace('0.030000','0.105000').replace('0.120','0.025').replace('1.006','1.01')
 else:
  metal=.96 if 'stainless' in name.lower() or 'alloy' in name.lower() else 0
  text=f'Layer0\n{{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n TextureColor "{color}"\n TextureNormal "{normal}"\n TextureRoughness "{rough}"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_flMetalness "{metal}"\n g_flRoughnessScaleFactor "1"\n'
  emission=list(map(float,data.get('Ke',['0','0','0'])))
  if max(emission)>0:text+=' F_SELF_ILLUM "1"\n TextureSelfIllumMask "[1 1 1 0]"\n g_flSelfIllumBrightness "1"\n g_flSelfIllumAlbedoFactor "0"\n g_vSelfIllumTint "['+' '.join(map(str,emission))+' 0]"\n'
  text+='}\n'
 (MATS/f'{paint}.vmat').write_text(text)
lines=[];triangles=0;verts=[]
for line in (LEGACY/'bulkhead_lamp_after.obj').read_text().splitlines():
 if line.startswith('v '):
  x,y,z=map(float,line.split()[1:]);x=-x;y=-y;verts.append((x/.0254,y/.0254,z/.0254));line=f'v {y/.0254:.7f} {z/.0254:.7f} {x/.0254:.7f}'
 elif line.startswith('vn '):
  x,y,z=map(float,line.split()[1:]);x=-x;y=-y;line=f'vn {y:.7f} {z:.7f} {x:.7f}'
 elif line.startswith('mtllib '):line='mtllib lamp.mtl'
 elif line.startswith('f '):triangles+=1;assert len(line.split())==4
 lines.append(line)
(MODEL/'lamp.obj').write_text('\n'.join(lines)+'\n');(MODEL/'lamp.mtl').write_text('\n'.join(f'newmtl {n}\nKd 1 1 1\nd 1' for n in materials)+'\n')
m=K.Model();m.polygons={n:[] for n in materials};m.material_overrides.update(bindings);K.write_vmdl(MODEL/'lamp.vmdl',RES,'lamp',m)
# Identify the exact original 24 faces in the CURRENT dressing imports.
before=json.loads((LEGACY/'before.json').read_text());wanted=Counter()
for paint,faces in before.items():
 for face in faces:
  obj=[(p[1]+1100,p[2]+120,p[0]-300) for p in face['vertices']]
  wanted[(paint,tuple(sorted(tuple(round(float(x),3) for x in p) for p in obj)))]+=1
assert sum(wanted.values())==24
docpath=ROOT/'Assets/models/maps/ares/ares_dressing.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for relative in imports:
 src=ROOT/'Assets'/relative;raw=src.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in raw if l.startswith('v ')];paint='';cut=set();remaining=wanted.copy()
 for i,line in enumerate(raw):
  if line.startswith('usemtl '):paint=line.split()[1]
  elif line.startswith('f '):
   key=(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:])))
   if remaining[key]:remaining[key]-=1;cut.add(i)
 if len(cut)==24 and not +remaining:matches.append((relative,raw,cut))
if len(matches)!=1:
 for relative in imports:
  v=[];paint='';near=[]
  for line in (ROOT/'Assets'/relative).read_text().splitlines():
   if line.startswith('v '):v.append(tuple(map(float,line.split()[1:])))
   elif line.startswith('usemtl '):paint=line.split()[1]
   elif line.startswith('f '):
    points=np.array([v[int(t.split('/')[0])-1] for t in line.split()[1:]])
    if np.all(points.min(0)>=(-306,116,-1101)) and np.all(points.max(0)<=(-294,124,-1094)):near.append((paint,points.tolist()))
  print(relative,'near',len(near),near[:3])
assert len(matches)==1,[(x[0],len(x[2])) for x in matches]
relative,raw,cut=matches[0];(MODEL/'preview.obj').write_text(''.join(line for i,line in enumerate(raw) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(raw),re.M):shutil.copyfile((ROOT/'Assets'/relative).parent/name.strip(),MODEL/name.strip())
(MODEL/'preview.vmdl').write_text(doc.replace(relative,f'{RES}/preview.obj'))
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',*[ROOT/'Assets'/p for p in imports],LEGACY/'bulkhead_lamp_after.obj',LEGACY/'bulkhead_lamp_after.mtl']
manifest=dict(preview_only=True,reused_existing_candidate=True,triangles=triangles,original_faces=24,active_base=relative,cut=sorted(cut),world_position=[-300,1100,120],local_bounds=[np.min(verts,0).tolist(),np.max(verts,0).tolist()],protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','protected','cut')}))
