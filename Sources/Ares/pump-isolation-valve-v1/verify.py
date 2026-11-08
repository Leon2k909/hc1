from pathlib import Path
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/pump-isolation-valve-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
original=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==32 and all(original[i].startswith('f ') for i in cut)
preview=(ROOT/'Assets/models/props/ares/pump_isolation_valve_v1/preview.obj').read_text();prefix=''.join(l for i,l in enumerate(original) if i not in cut);assert preview.startswith(prefix)
v=[];uv=[];n=[];faces=[];added=False
for l in preview.splitlines():
 if l.startswith('# Fitted valve:'):added=True
 s=l.split()
 if not s:continue
 if s[0]=='v':a,z,north=map(float,s[1:]);v.append(np.array((-a,north,z)))
 elif s[0]=='vt':uv.append(np.array(list(map(float,s[1:]))))
 elif s[0]=='vn':a,z,north=map(float,s[1:]);n.append(np.array((-a,north,z)))
 elif s[0]=='f' and added:faces.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);uv=np.array(uv);n=np.array(n);f=np.array(faces);p=v[f[:,:,0]];normals=n[f[:,:,2]];tex=uv[f[:,:,1]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);assert len(f)==96 and np.isfinite(p).all() and np.isfinite(tex).all() and np.isfinite(normals).all() and (np.linalg.norm(cross,axis=1)>1e-12).all()
agreement=float(((cross*normals.mean(1)).sum(1)>0).mean());assert agreement==1
low,high=m['cut_interval'];assert np.all((p[:,:,2].max(1)<=low+1e-6)|(p[:,:,2].min(1)>=high-1e-6))
assert np.isclose(low,75.36) and np.isclose(high,108.64)
doc=(ROOT/'Assets/models/maps/ares/ares_reactor.vmdl').read_text();trial=(ROOT/'Assets/models/props/ares/pump_isolation_valve_v1/preview.vmdl').read_text();assert trial==doc.replace(m['active_base'],'models/props/ares/pump_isolation_valve_v1/preview.obj')
forward=np.array(m['world_forward']);up=np.array(m['world_up']);assert np.isclose(np.linalg.norm(forward),1) and np.isclose(np.linalg.norm(up),1) and abs(forward@up)<1e-9
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==20164 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['IdenticalTemporaryInspectionLight']
rejected=json.loads((ROOT/'output/ares/concourse-column-guard-v1/rejected.json').read_text());assert rejected['Rejected'] and rejected['OriginalPublicColumnRetained']
report=dict(review_only=True,rejected_guard_discarded=True,original_map_scene_and_shared_valve_unchanged=True,original_pipe_faces_clipped=32,retained_lower_upper_pipe_triangles=96,all_other_original_obj_lines_preserved=True,new_pipe_attributes_finite_nondegenerate=True,normal_agreement=agreement,only_33_28_inches_of_one_riser_replaced_in_preview=True,original_modeldoc_physics_preserved=True,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
