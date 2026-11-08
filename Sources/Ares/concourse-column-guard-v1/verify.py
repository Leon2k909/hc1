from pathlib import Path
import json,hashlib,numpy as np,re
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/concourse-column-guard-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
folder=ROOT/'Assets/models/props/ares/concourse_column_guard_v1';raw=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==24 and all(raw[i].startswith('f ') for i in cut)
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
v=[];uv=[];n=[];f=[]
for l in (folder/'guard.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);uv=np.array(uv);n=np.array(n);f=np.array(f);t=v[f[:,:,0]];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all() and (np.linalg.norm(cross,axis=1)>1e-12).all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.999
plan=np.column_stack((-v[:,0],v[:,2],v[:,1]));local=plan-np.array((-650,-1076,0));assert np.all(local.min(0)>=(-14.501,-14.501,-.001)) and np.all(local.max(0)<=(14.501,14.501,32.001)),(local.min(0),local.max(0))
doc=(folder/'guard.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/p).exists(),p
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['AddedColliders']==0 and native['IdenticalTemporaryInspectionLight']
report=dict(preview_only=True,original_column_and_all_unrelated_geometry_unchanged=True,exact_original_jacket_faces=24,triangles=len(f),finite_nondegenerate=True,normal_agreement=agreement,original_29_by_29_by_32_envelope_preserved=True,original_collision_and_shared_materials_unchanged=True,temporary_review_light_not_saved=True,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
