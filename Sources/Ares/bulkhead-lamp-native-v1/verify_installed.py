from pathlib import Path
import json,hashlib,sys,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/bulkhead-lamp-native-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Ares/ares.scene'):assert sha(ROOT/p)==h,p
raw=(OUT/'install-before/original-dressing.obj').read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==24
assert (ROOT/'Assets'/m['active_base']).read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
before=json.loads((OUT/'install-before/ares.scene').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Lower Hall Bulkhead Lamp'];assert len(nodes)==1
scene['GameObjects'].remove(nodes[0]);assert scene==before,'Unexpected scene changes'
folder=ROOT/'Assets/models/props/ares/bulkhead_lamp_native_v1';counts=[]
for name in ('lamp.obj','lamp_lod1.obj','lamp_lod2.obj'):
 v=[];n=[];f=[]
 for l in (folder/name).read_text().splitlines():
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(list(map(float,s[1:])))
  elif s[0]=='vn':n.append(list(map(float,s[1:])))
  elif s[0]=='f':f.append([[int(i)-1 for i in t.split('/')] for t in s[1:]])
 v=np.array(v);n=np.array(n);f=np.array(f);t=v[f[:,:,0]];c=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);assert np.isfinite(v).all() and np.isfinite(n).all() and (np.linalg.norm(c,axis=1)>1e-10).all()
 agreement=float(((c*n[f[:,:,2]].mean(1)).sum(1)>0).mean());print(name,'normal agreement',agreement)
 assert agreement>.99
 counts.append(len(f))
assert counts==[32482,6496,1460]
native=json.loads((OUT/'installed/validation.json').read_text());assert native['Lods']==3 and native['LodTriangles']==counts and native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged']
sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A
model=A.Model();A.wall_lamp(model,-1100,-300,120,(1,0));assert model.triangle_count()==0
other=A.Model();A.wall_lamp(other,-1100,-540,120,(1,0));assert other.triangle_count()==24
report=dict(installed=True,old_triangles_deleted=24,unrelated_faces_preserved=True,one_scene_node_added=True,all_other_scene_data_unchanged=True,collision_and_materials_unchanged=True,lods=counts,generator_verified=True,native=native)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
