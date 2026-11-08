from pathlib import Path
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/control-room-display-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
for p,h in m['files'].items():assert sha(ROOT/'Assets'/p)==h,p
folder=ROOT/'Assets/models/props/ares/control_room_display_v1';raw=(ROOT/'Assets'/m['active_base']).read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==2
assert (folder/'preview.obj').read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
def parse(path):
 v=[];uv=[];n=[];f=[];paints=[];paint=''
 for l in path.read_text().splitlines():
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(list(map(float,s[1:])))
  elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
  elif s[0]=='vn':n.append(list(map(float,s[1:])))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':f.append([[int(k)-1 for k in t.split('/')] for t in s[1:]]);paints.append(paint)
 return np.array(v),np.array(uv),np.array(n),np.array(f),paints
v,uv,n,f,paints=parse(folder/'display.obj');t=v[f[:,:,0]];c=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(n).all() and (np.linalg.norm(c,axis=1)>1e-10).all()
agreement=float(((c*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.999
source_uv=[]
# Original saved screen UV corners are copied without remapping or atlas edits.
original=(ROOT/'Assets'/m['active_base']).read_text().splitlines();all_uv=[tuple(map(float,l.split()[1:])) for l in original if l.startswith('vt ')]
for i in m['cut']:source_uv.append([all_uv[int(t.split('/')[1])-1] for t in original[i].split()[1:]])
after_uv=[uv[face[:,1]].tolist() for face,p in zip(f,paints) if p=='ar_screens'];assert np.allclose(np.array(source_uv),np.array(after_uv),rtol=0,atol=1e-5)
native=json.loads((OUT/'native/validation.json').read_text());assert native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['AddedColliders']==0
doc=(folder/'display.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
report=dict(preview_only=True,protected_sources_unchanged=True,exact_original_faces=2,triangles=len(f),finite_nondegenerate=True,normal_agreement=agreement,original_artwork_uv_preserved=True,no_added_collision_or_lights=True,native=native)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
