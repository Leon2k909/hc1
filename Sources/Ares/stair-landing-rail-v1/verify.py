from pathlib import Path
import json,hashlib,re,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/stair-landing-rail-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
folder=ROOT/'Assets/models/props/ares/stair_landing_rail_v1';raw=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==84 and all(raw[i].startswith('f ') for i in cut)
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
v=[];uv=[];n=[];f=[]
for l in (folder/'rail.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='f':f.append([[int(i)-1 for i in t.split('/')] for t in s[1:]])
v=np.array(v);uv=np.array(uv);n=np.array(n);f=np.array(f);t=v[f[:,:,0]];c=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all()
assert (np.linalg.norm(c,axis=1)>1e-10).all();agreement=float(((c*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.999
doc=(folder/'rail.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/p).exists(),p
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['AddedColliders']==0
report=dict(preview_only=True,triangles=len(f),exact_original_faces_removed_in_private_copy=84,all_other_obj_lines_unchanged=True,public_assets_scene_and_physics_unchanged=True,geometry_finite_nondegenerate=True,normal_agreement=agreement,reused_closed_tee_design=True,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
