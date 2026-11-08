from pathlib import Path
import json,hashlib,sys,collections
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/help-point-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());old=(OUT/'install-before/original-west.obj').read_text().splitlines(keepends=True);new=(ROOT/'Assets'/m['active_base']).read_text();cut=set(m['cut'])
assert new==''.join(l for i,l in enumerate(old) if i not in cut) and len(cut)==360
scene=json.loads((ROOT/'Assets/scenes/maps/Railhead/railhead.scene').read_text());before=json.loads((OUT/'install-before/railhead.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='West Platform Help Point'];assert len(nodes)==1
scene['GameObjects']=[n for n in scene['GameObjects'] if n not in nodes];assert scene==before
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Railhead/railhead.scene'):assert sha(ROOT/p)==h,p
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_props as P,railhead_help_point as H,railhead_furniture as FU
model=K.Model();P.sos_pillar(model,-1154.,378.,'+e');legacy=K.Model();FU.sos_pillar(legacy,P.frame_for(-1154.,378.,0.,'+e'))
assert model.triangle_count()==0 and len(model.boxes)==len(legacy.boxes)==1
for a,b in zip(model.boxes[0][:3],legacy.boxes[0][:3]):
 import numpy as np
 assert np.allclose(a,b)
assert model.boxes[0][3]==legacy.boxes[0][3]
assert H.scene_object(K.SceneIds('b2be9919-67d8-4c95-af73-c78223aa9c50'))==nodes[0]
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==3432 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_360_faces_removed=True,all_other_obj_records_preserved=True,only_one_renderer_added=True,unrelated_scene_and_materials_preserved=True,generator_retains_upgrade_and_original_collider=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
