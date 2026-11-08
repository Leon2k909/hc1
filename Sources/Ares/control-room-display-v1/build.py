"""Reuse the approved Collider display construction for one plain Ares wall screen."""
from pathlib import Path
import sys,json,re,hashlib,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K
OUT=ROOT/'output/ares/control-room-display-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/control_room_display_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
docpath=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc)
matches=[]
for rel in imports:
 raw=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);v=[];uv=[];n=[];paint='';cut=[];saved=[]
 for i,l in enumerate(raw):
  s=l.split()
  if not s:continue
  if s[0]=='v':a,z,north=map(float,s[1:]);v.append(np.array((-a,north,z)))
  elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
  elif s[0]=='vn':a,z,north=map(float,s[1:]);n.append(np.array((-a,north,z)))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f' and paint=='ar_screens':
   ids=[[int(x)-1 for x in t.split('/')] for t in s[1:]];p=np.array([v[x] for x,t,z in ids])
   if np.all(p.min(0)>=(-1099.501,209.999,79.999)) and np.all(p.max(0)<=(-1099.499,270.001,130.001)):
    cut.append(i);saved.append((p,[uv[t] for x,t,z in ids],[n[z] for x,t,z in ids]))
 if cut:matches.append((rel,raw,cut,saved))
assert len(matches)==1 and len(matches[0][2])==2,[(p,len(c)) for p,r,c,s in matches]
rel,raw,cut,saved=matches[0]
(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(raw) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(raw),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
source=ROOT/'Assets/models/props/collider/monitor-trial-v1/after.obj';v=[];uv=[];n=[];paint='';m=K.Model();T=np.array(((0,-.20,0),(60/112,0,0),(0,0,50/66)));N=np.linalg.inv(T).T;offset=np.array((-1096,240,80-2.5*50/66))
for l in source.read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':a,z,north=map(float,s[1:]);v.append(T@np.array((-a,north,z))+offset)
 elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
 elif s[0]=='vn':a,z,north=map(float,s[1:]);q=N@np.array((-a,north,z));n.append(q/np.linalg.norm(q))
 elif s[0]=='usemtl':paint=s[1]
 elif s[0]=='f' and paint!='co_screens':
  ids=[[int(x)-1 for x in t.split('/')] for t in s[1:]];m.polygon(paint,[v[x] for x,t,z in ids],uv=[uv[t] for x,t,z in ids],normals=[n[z] for x,t,z in ids])
for p,tex,normals in saved:m.polygon('ar_screens',[q+np.array((3.474,0,0)) for q in p],uv=tex,normals=normals)
for paint in m.polygons:
 m.material_overrides[paint]='materials/ares/ar_screens.vmat' if paint=='ar_screens' else f'materials/collider/monitor-trial-v1/{paint}.vmat'
 m.tile_overrides[paint]=32
K.write_obj(DEST/'display.obj',m,'ares-control-room-display');K.write_vmdl(DEST/'display.vmdl',RES,'display',m)
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',ROOT/'Assets/models/maps/ares/ares_dressing.vmdl',source,*[ROOT/'Assets'/p for p in imports]]
protected.extend((ROOT/'Assets/materials/collider/monitor-trial-v1').glob('*.*'));protected.extend((ROOT/'Assets/materials/ares').glob('ar_screens*'))
manifest=dict(preview_only=True,reused_approved_collider_monitor=True,original_faces=2,triangles=m.triangle_count(),artwork_uv_unchanged=True,added_lights=0,added_collision=0,active_base=rel,cut=cut,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected if p.is_file()},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('protected','files','cut')}))
