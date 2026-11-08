from pathlib import Path
import hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A
OUT=ROOT/'output/ares/control-console-native-v1';plan=json.loads((OUT/'install-plan.json').read_text());old=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for f,h in plan['protected'].items():
 if f not in ('Assets/scenes/maps/Ares/ares.scene','Assets/'+plan['active_base']):assert sha(ROOT/f)==h,f
assert (ROOT/'Assets'/plan['active_base']).read_bytes()==(OUT/'install-stage/dressing_without_console.obj').read_bytes()
folder=ROOT/'Assets/models/props/ares/control_console_native_v1';lods=json.loads((OUT/'lods.json').read_text())['triangles'];reports=[]
for lod,name in enumerate(('console.obj','console_lod1.obj','console_lod2.obj')):
 v=[];n=[];uv=[];faces=[]
 for line in (folder/name).read_text().splitlines():
  s=line.split()
  if not s:continue
  if s[0]=='v':v.append(list(map(float,s[1:])))
  elif s[0]=='vn':n.append(list(map(float,s[1:])))
  elif s[0]=='vt':uv.append(list(map(float,s[1:])))
  elif s[0]=='f':faces.append([[int(x)-1 for x in t.split('/')] for t in s[1:]])
 v=np.array(v);n=np.array(n);uv=np.array(uv);f=np.array(faces);assert len(f)==lods[lod] and np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
 t=v[f[:,:,0]];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert (np.linalg.norm(cross,axis=1)>1e-10).all()
 agreement=float(((cross*n[f[:,:,2]].mean(1)).sum(1)>0).mean());assert agreement>.99,(lod,agreement)
 assert np.all(v.min(0)>=np.array((-30.,0.,-16.))) and np.all(v.max(0)<=np.array((30.,64.,18.)))
 reports.append(dict(lod=lod,triangles=len(f),normal_agreement=agreement))
 assert sha(folder/name)==sha(OUT/'stage/Assets/models/props/ares/control_console_native_v1'/name)
assert sha(folder/'console.obj')==old['files']['models/props/ares/control_console_native_v1/console.obj'],'Approved base changed'
doc=(folder/'console.vmdl').read_text();assert 'PhysicsShape' not in doc and 'PhysicsHull' not in doc
for path in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc):assert (ROOT/'Assets'/path).exists(),path
scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Core Process Console'];assert len(nodes)==1 and len(nodes[0]['Components'])==1
m=A.Model();A.console(m,230,-440,90.,2,0.);assert m.triangle_count()==0 and len(m.boxes)==1
native=json.loads((OUT/'installed/validation.json').read_text());assert native['LodTriangles']==lods and native['ModelsValid'] and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(installed=True,old_faces_removed=40,modeldoc_and_physics_unchanged=True,approved_base_unchanged=True,source_hook_verified=True,lods=reports,native=native);(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
