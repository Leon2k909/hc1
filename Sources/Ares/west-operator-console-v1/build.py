"""Offline review: reuse the installed detailed console for one crude control-room desk."""
from pathlib import Path
from collections import Counter
import sys,json,re,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,ares_map as A
OUT=ROOT/'output/ares/west-operator-console-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/west_operator_console_v1';DEST=STAGE/RES;DEST.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
raw_model=K.Model();A.console(raw_model,-1074,240,180.,screen=0);A.configure(raw_model);K.write_obj(OUT/'expected.obj',raw_model,'expected')
def sigs(lines):
 v=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(round(float(x),3) for x in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':result.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in s[1:])))))
 return result
wanted=Counter(k for i,k in sigs((OUT/'expected.obj').read_text().splitlines()));assert sum(wanted.values())==40
docpath=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for rel in imports:
 lines=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);remaining=wanted.copy();cut=[]
 for i,k in sigs(lines):
  if remaining[k]:cut.append(i);remaining[k]-=1
 if len(cut)==40 and not +remaining:matches.append((rel,lines,cut))
assert len(matches)==1,'Actual saved desk differs from the baseline'
rel,lines,cut=matches[0];v=[];uv=[];n=[];paint='';before=K.Model();screen_uv=[]
T=np.array(((0,1,0),(-1,0,0),(0,0,1)));origin=np.array((-1074.,240.,0.))
for i,l in enumerate(lines):
 s=l.split()
 if not s:continue
 if s[0]=='v':a,z,north=map(float,s[1:]);v.append(T@(np.array((-a,north,z))-origin))
 elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
 elif s[0]=='vn':a,z,north=map(float,s[1:]);n.append(T@np.array((-a,north,z)))
 elif s[0]=='usemtl':paint=s[1]
 elif s[0]=='f' and i in cut:
  ids=[[int(k)-1 for k in t.split('/')] for t in s[1:]];tex=[uv[t] for x,t,z in ids]
  before.polygon(paint,[v[x] for x,t,z in ids],uv=tex,normals=[n[z] for x,t,z in ids])
  if paint=='ar_screens':screen_uv.extend(tex)
bindings=dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}',doc));A.configure(before);before.material_overrides.update({p:bindings.get(p,before.material_overrides[p]) for p in before.polygons})
K.write_obj(DEST/'before.obj',before,'before');K.write_vmdl(DEST/'before.vmdl',RES,'before',before)
source_dir=ROOT/'Assets/models/props/ares/control_console_native_v1';source_doc=(source_dir/'console.vmdl').read_text();bindings=dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}',source_doc))
screen_paint='Original_approved_Ares_display_atlas';target=np.array(screen_uv);target_min=target.min(0);target_max=target.max(0)
def parse(path):
 v=[];uv=[];n=[];f=[];paint=''
 for l in path.read_text().splitlines():
  s=l.split()
  if not s:continue
  if s[0]=='v':a,z,north=map(float,s[1:]);v.append(np.array((-a,north,z)))
  elif s[0]=='vt':uv.append(np.array(list(map(float,s[1:]))))
  elif s[0]=='vn':a,z,north=map(float,s[1:]);n.append(np.array((-a,north,z)))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':f.append((paint,[[int(k)-1 for k in t.split('/')] for t in s[1:]]))
 return v,uv,n,f
source=parse(source_dir/'console.obj');source_uv=np.array([source[1][t] for p,face in source[3] if p==screen_paint for x,t,z in face]);lo=source_uv.min(0);hi=source_uv.max(0);assert np.all(hi>lo)
counts=[];normal_repairs=[]
for lod,name in enumerate(('console.obj','console_lod1.obj','console_lod2.obj')):
 v,uv,n,faces=parse(source_dir/name);model=K.Model();outname='after' if lod==0 else f'after_lod{lod}'
 # Retain source positions at full precision; only display UV references change.
 # Distance meshes contain a few zero/opposing split normals; replace those
 # face references with a finite geometric normal, leaving source assets intact.
 attributes=[l for l in (source_dir/name).read_text().splitlines() if l.startswith(('v ','vt ','vn '))]
 additions=[];face_lines=[];uv_count=len(uv);normal_count=len(n);repairs=0
 for paint,face in faces:
  points=np.array([v[x] for x,t,z in face]);c=np.cross(points[1]-points[0],points[2]-points[0]);assert np.linalg.norm(c)>1e-12
  # parse() expresses OBJ normals in a rotated, right-handed coordinate system.
  ns=np.array([n[z] for x,t,z in face]);bad=not np.isfinite(ns).all() or np.any(np.linalg.norm(ns,axis=1)<1e-8) or np.dot(c,ns.mean(0))<=0
  newnormal=None
  if bad:
   c/=np.linalg.norm(c);normal_count+=1;newnormal=normal_count;additions.append(f'vn {-c[0]:.9f} {c[2]:.9f} {c[1]:.9f}');repairs+=1
  tokens=[]
  for x,t,z in face:
   ti=t+1
   if paint==screen_paint:
    tex=target_min+(uv[t]-lo)/(hi-lo)*(target_max-target_min);uv_count+=1;ti=uv_count;additions.append(f'vt {tex[0]:.9f} {tex[1]:.9f}')
   tokens.append(f'{x+1}/{ti}/{newnormal if bad else z+1}')
  face_lines.extend(['usemtl '+paint,'f '+' '.join(tokens)])
 model.polygons={p:[] for p,face in faces}
 model.material_overrides.update(bindings);model.tile_overrides.update({p:32 for p in model.polygons})
 (DEST/(outname+'.obj')).write_text('\n'.join(['mtllib '+outname+'.mtl',*attributes,*additions,*face_lines])+'\n');(DEST/(outname+'.mtl')).write_bytes((source_dir/'console.mtl').read_bytes());K.write_vmdl(DEST/(outname+'.vmdl'),RES,outname,model);counts.append(len(faces));normal_repairs.append(repairs)
(DEST/'after.vmdl').write_text(source_doc.replace('models/props/ares/control_console_native_v1/console.obj',RES+'/after.obj').replace('models/props/ares/control_console_native_v1/console_lod1.obj',RES+'/after_lod1.obj').replace('models/props/ares/control_console_native_v1/console_lod2.obj',RES+'/after_lod2.obj'))
preview=DEST/'preview.obj';preview.write_text(''.join(l for i,l in enumerate(lines) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):
 (DEST/name.strip()).write_bytes((ROOT/'Assets'/rel).parent.joinpath(name.strip()).read_bytes())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',ROOT/'Tools/ares_map.py',*[ROOT/'Assets'/p for p in imports],*source_dir.glob('console*')]
for path in set(before.material_overrides.values())|set(bindings.values()):
 p=ROOT/'Assets'/path;protected.append(p)
 for t in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/t
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,native_engine_compilation='pending native import',reused_approved_console=True,actual_original_faces=40,triangles=counts,active_base=rel,cut=cut,world_position=[240,1074,0],world_yaw=90,screen_uv_bounds=[target_min.tolist(),target_max.tolist()],original_screen_material_unchanged=True,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected if p.is_file()},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
manifest['distance_normal_repairs']=normal_repairs
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','protected','cut')}))
