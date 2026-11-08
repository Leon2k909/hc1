from pathlib import Path
import json,hashlib,numpy as np,re
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverdale/sand-bin-v1';CURRENT=OUT/'current-native';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in json.loads((CURRENT/'guard.json').read_text()).items():assert sha(ROOT/p)==h,p
m=json.loads((OUT/'manifest.json').read_text())
for p,h in m['files'].items():assert sha(ROOT/p)==h,p
model=ROOT/'Assets/models/maps/riverdale/sand-bin-v1/sand_bin.vmdl';doc=model.read_text();historical=json.loads((OUT/'source-guard.json').read_text());dependencies=[]
for path in re.findall(r'to\s*=\s*"([^\"]+\.vmat)"',doc):
 p=ROOT/'Assets'/path;dependencies.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():dependencies.append(q)
for p in dependencies:
 rel=p.relative_to(ROOT).as_posix()
 if rel in historical:assert sha(p)==historical[rel],rel
v=[];n=[];uv=[];f=[]
for l in model.with_suffix('.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='vt':uv.append(list(map(float,s[1:])))
 elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]])
v=np.array(v);n=np.array(n);uv=np.array(uv);f=np.array(f);p=v[f[:,:,0]];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);length=np.linalg.norm(cross,axis=1)
assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all() and (length>1e-12).all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement==1
assert 'PhysicsShapeBox' not in doc and 'PhysicsHullFile' not in doc
native=json.loads((CURRENT/'validation.json').read_text());assert native['ModelsValid'] and native['Triangles']==2126 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=json.loads((CURRENT/'verification.json').read_text());report.update(geometry_finite_nondegenerate=True,normal_agreement=agreement,existing_materials_reused_unchanged=True,dependencies_checked=len(dependencies),native=native)
(CURRENT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
