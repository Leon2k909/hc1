from pathlib import Path
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/bulkhead-lamp-native-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
raw=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);folder=ROOT/'Assets/models/props/ares/bulkhead_lamp_native_v1'
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
assert len(cut)==24 and all(raw[i].startswith('f ') for i in cut)
v=[];n=[];faces=[]
for l in (folder/'lamp.obj').read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(list(map(float,s[1:])))
 elif s[0]=='vn':n.append(list(map(float,s[1:])))
 elif s[0]=='f':faces.append([[int(i)-1 for i in t.split('/')] for t in s[1:]])
v=np.array(v);n=np.array(n);f=np.array(faces);t=v[f[:,:,0]];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);valid=np.linalg.norm(cross,axis=1)>1e-10
assert np.isfinite(v).all() and np.isfinite(n).all() and valid.all()
agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.99
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['AddedColliders']==0
report=dict(preview_only=True,protected_files_unchanged=True,exact_old_faces_removed=24,triangles=len(f),normal_agreement=agreement,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
