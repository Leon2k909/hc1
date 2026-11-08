from pathlib import Path
import json,hashlib,re,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/main-airlock-sign-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
folder=ROOT/'Assets/models/props/ares/main_airlock_sign_v1';raw=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==14 and all(raw[i].startswith('f ') for i in cut)
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
v=[];uv=[];n=[];f=[]
for l in (folder/'sign.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);uv=np.array(uv);n=np.array(n);f=np.array(f);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all() and (np.linalg.norm(cross,axis=1)>1e-12).all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement==1
plan=np.column_stack((-v[:,0],v[:,2],v[:,1]));assert np.isclose(plan[:,0].ptp() if hasattr(plan[:,0],'ptp') else np.ptp(plan[:,0]),130,atol=.002) and np.isclose(np.ptp(plan[:,2]),34,atol=.002)
assert plan[:,2].max()<=267.001 and plan[:,2].min()>=232.999,'Suspension hardware remains'
doc=(folder/'sign.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for p in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/p).exists(),p
for name in ('face_color.png','face_illum.png'):assert Image.open(ROOT/'Assets/materials/ares/main_airlock_sign_v1'/name).size==(2048,512)
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==460 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(review_only=True,approved_enclosure_reused=True,original_14_faces_removed_only_in_private_preview=True,all_other_original_obj_lines_preserved=True,geometry_finite_nondegenerate=True,normal_agreement=agreement,original_outer_width_and_height_preserved=True,suspension_hardware_removed=True,public_scene_physics_and_materials_unchanged=True,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
