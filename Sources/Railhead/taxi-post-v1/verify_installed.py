from pathlib import Path
import json,hashlib,sys,collections
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/taxi-post-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());old=(OUT/'install-before/original-east.obj').read_text().splitlines();new=(ROOT/m['source']).read_text().splitlines()
assert [l for l in old if not l.startswith('f ')]==[l for l in new if not l.startswith('f ')]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==124
scene=json.loads((ROOT/'Assets/scenes/maps/Railhead/railhead.scene').read_text());before=json.loads((OUT/'install-before/railhead.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='East Taxi Rank Head Post'];assert len(nodes)==1
scene['GameObjects']=[n for n in scene['GameObjects'] if n not in nodes];assert scene==before
guard=json.loads((OUT/'current-native/guard.json').read_text());assert sha(ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl')==next(h for p,h in guard.items() if p.endswith('railhead_dress_east.vmdl'))
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_dress_detail as D,railhead_taxi_post as T
model=K.Model();D.taxi_post(model,1488.,1180.,'+n');assert model.triangle_count()==0 and len(model.boxes)==1
assert T.scene_object(K.SceneIds('29a58fab-920b-4cd8-a62c-2f917fb7b114'))==nodes[0]
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==4472 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_124_faces_removed=True,all_other_obj_records_preserved=True,only_one_renderer_added=True,public_modeldoc_and_physics_unchanged=True,generator_retains_upgrade_and_original_collider=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
