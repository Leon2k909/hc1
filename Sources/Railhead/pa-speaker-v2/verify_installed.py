from pathlib import Path
import json,hashlib,sys,collections
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/pa-speaker-v2';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());old=(OUT/'install-before/original-centre.obj').read_text().splitlines();new=(ROOT/m['source']).read_text().splitlines()
assert [l for l in old if not l.startswith('f ')]==[l for l in new if not l.startswith('f ')]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==36
scene=json.loads((ROOT/'Assets/scenes/maps/Railhead/railhead.scene').read_text());before=json.loads((OUT/'install-before/railhead.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Central Platform PA Speaker'];assert len(nodes)==1
scene['GameObjects']=[n for n in scene['GameObjects'] if n not in nodes];assert scene==before
guard=json.loads((OUT/'current-native/guard.json').read_text());assert sha(ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl')==guard['Assets/models/maps/railhead/railhead_dress_centre.vmdl']
for p,h in m['files'].items():
 if 'centre_without_speaker' not in p:assert sha(ROOT/p)==h,p
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_dress_detail as D,railhead_pa_speaker as S
model=K.Model();D.loudspeaker(model,7.7,820.,214.,'+e');assert model.triangle_count()==0 and not model.boxes and not model.hulls
assert S.scene_object(K.SceneIds('ec4c5b49-72b4-48e5-969f-bb9248a73ed1'))==nodes[0]
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==32386 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_36_faces_removed=True,all_other_obj_records_preserved=True,only_one_renderer_added=True,public_modeldoc_physics_and_other_scene_objects_unchanged=True,generator_retains_upgrade=True,approved_model_and_materials_unchanged=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
