from pathlib import Path
import json,hashlib,re,collections,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/help-point-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
folder=ROOT/'Assets/models/props/railhead/help_point_v1';original=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==360 and all(original[i].startswith('f ') for i in cut)
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(original) if i not in cut)
public=(ROOT/'Assets/models/maps/railhead/railhead_dress_west.vmdl').read_text();preview=(folder/'preview.vmdl').read_text();assert preview.replace('models/props/railhead/help_point_v1/preview.obj',m['active_base'])==public
v=[];n=[];uv=[];faces=[]
for l in (folder/'help_point.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='f':faces.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);n=np.array(n);uv=np.array(uv);f=np.array(faces);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);length=np.linalg.norm(cross,axis=1)
assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all() and (length>1e-10).all()
normal_agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert normal_agreement==1,normal_agreement
doc=(folder/'help_point.vmdl').read_text();assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^\"]+)"',doc):assert (ROOT/'Assets'/p).exists(),p
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==m['triangles'] and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(review_only=True,original_faces=360,new_triangles=m['triangles'],all_unrelated_obj_records_preserved=True,public_scene_and_materials_unchanged=True,modeldoc_physics_preserved=True,geometry_finite_nondegenerate=True,normal_agreement=normal_agreement,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
