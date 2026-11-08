from pathlib import Path
import json,hashlib,sys,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/pump-isolation-valve-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Ares/ares.scene'):assert sha(ROOT/p)==h,p
assert (ROOT/'Assets'/m['active_base']).read_bytes()==(OUT/'install-stage/reactor_with_valve_gap.obj').read_bytes()
before=json.loads((OUT/'install-before/ares.scene').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Northeast Pump Isolation Valve'];assert len(nodes)==1
assert nodes[0]==json.loads((OUT/'install-stage/node.json').read_text());scene['GameObjects'].remove(nodes[0]);assert scene==before,'Unrelated scene change'
sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A,ares_interior as I,map_kit as K,ares_pump_isolation_valve as V
legacy=K.Model();I.pump_unit(legacy,270,270,135);new=K.Model();A.pump_unit(new,270,270,135)
assert new.triangle_count()==legacy.triangle_count()+64 and len(new.boxes)==len(legacy.boxes)==1 and len(new.hulls)==len(legacy.hulls)==0
for old_box,new_box in zip(legacy.boxes,new.boxes):
 assert old_box[3]==new_box[3] and all(np.allclose(a,b) for a,b in zip(old_box[:3],new_box[:3]))
assert len(V.patch()['faces'])==96 and V.scene_object(None)==nodes[0]
native=json.loads((OUT/'installed/validation.json').read_text());assert native['Installed'] and native['ModelsValid'] and native['Triangles']==20164 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(installed=True,exact_reviewed_pipe_migration=True,original_32_pipe_faces_removed=True,retained_pipe_triangles=96,shared_valve_geometry_and_materials_unchanged=True,all_other_scene_data_and_physics_unchanged=True,generator_pipe_gap_and_stable_valve_node_verified=True,native=native)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
