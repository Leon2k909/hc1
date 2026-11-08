from pathlib import Path
import json,hashlib,re,collections,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/city-light-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();folder=ROOT/'Assets/models/props/railhead/city_light_v1'
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
def signatures(lines,selection=None):
 v=[];uv=[];n=[];paint='';result=collections.Counter()
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(map(float,s[1:])))
  elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
  elif s[0]=='vn':n.append(tuple(map(float,s[1:])))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f' and paint in ('rw_posters','rw_glass','rw_lamp_cool') and (selection is None or i in selection):
   result[(paint,tuple(sorted((v[a-1],uv[b-1],n[c-1]) for a,b,c in (map(int,t.split('/')) for t in s[1:]))))]+=1
 return result
original_art=collections.Counter()
for part in m['parts']:
 original=(ROOT/'Assets'/part['active_base']).read_text().splitlines(keepends=True);cut=set(part['cut']);assert len(cut)==part['original_faces'] and all(original[i].startswith('f ') for i in cut)
 assert (folder/(part['preview']+'.obj')).read_text()==''.join(l for i,l in enumerate(original) if i not in cut)
 public=(ROOT/'Assets'/part['public_model']).read_text();preview=(folder/(part['preview']+'.vmdl')).read_text();assert preview.replace('models/props/railhead/city_light_v1/'+part['preview']+'.obj',part['active_base'])==public
 original_art.update(signatures(original,cut))
candidate_art=signatures((folder/'lightbox.obj').read_text().splitlines())
assert original_art==candidate_art,dict(missing=list((original_art-candidate_art).items())[:2],extra=list((candidate_art-original_art).items())[:2])
v=[];n=[];uv=[];faces=[]
for l in (folder/'lightbox.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='f':faces.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);n=np.array(n);uv=np.array(uv);f=np.array(faces);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all() and (np.linalg.norm(cross,axis=1)>1e-10).all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement==1
doc=(folder/'lightbox.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^\"]+)"',doc):assert (ROOT/'Assets'/p).exists(),p
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==m['triangles'] and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(review_only=True,original_faces=96,new_triangles=m['triangles'],original_art_glass_and_luminous_border_uvs_and_normals_preserved=True,all_other_obj_records_preserved=True,public_models_scene_physics_materials_unchanged=True,geometry_finite_nondegenerate=True,normal_agreement=agreement,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
