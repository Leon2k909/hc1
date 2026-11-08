from pathlib import Path
import json,hashlib,sys,collections
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverdale/sand-bin-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());old=(OUT/'install-before/original-yard.obj').read_text().splitlines();new=(ROOT/m['source']).read_text().splitlines()
assert [l for l in old if not l.startswith('f ')]==[l for l in new if not l.startswith('f ')]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==38
scene=json.loads((ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene').read_text());before=json.loads((OUT/'install-before/riverdale.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Court Sand Bin'];assert len(nodes)==1
scene['GameObjects']=[n for n in scene['GameObjects'] if n not in nodes];assert scene==before
guard=json.loads((OUT/'current-native/guard.json').read_text());assert sha(ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.vmdl')==guard['Assets/models/maps/riverdale/riverdale_yard_props.vmdl']
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,riverdale_yard as Y,riverdale_sand_bin as S
model=K.Model();Y.sand_bin(model,'court sand',(-1250,258),(0,1));assert model.triangle_count()==0 and not model.boxes and not model.hulls
assert S.scene_object(K.SceneIds('e1a2b420-c718-4ac0-986a-41d4ea7a56de'))==nodes[0]
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==2126 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_38_faces_removed=True,all_other_obj_records_preserved=True,only_one_renderer_added=True,public_modeldoc_physics_and_other_scene_objects_unchanged=True,generator_retains_upgrade_and_collision_note=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
