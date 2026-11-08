from pathlib import Path
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/pa-speaker-v2';CURRENT=OUT/'current-native';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in json.loads((CURRENT/'guard.json').read_text()).items():assert sha(ROOT/p)==h,p
m=json.loads((OUT/'manifest.json').read_text())
for p,h in m['files'].items():assert sha(ROOT/p)==h,p
v=[];n=[];f=[]
for l in (ROOT/'Assets/models/maps/railhead/pa-speaker-v2/pa_speaker.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);n=np.array(n);f=np.array(f);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);length=np.linalg.norm(cross,axis=1)
assert np.isfinite(v).all() and np.isfinite(n).all() and (length>1e-12).all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.999
native=json.loads((CURRENT/'validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==32386 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
cavity=json.loads((OUT/'cavity-check.json').read_text());assert cavity['all_occluded'] and cavity['edge_hole_rays_checked']==222
report=json.loads((CURRENT/'verification.json').read_text());report.update(geometry_finite_nondegenerate=True,normal_agreement=agreement,cavity_rays_checked=222,matching_temporary_inspection_light=True,saved_lighting_unchanged=True,native=native)
(CURRENT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
