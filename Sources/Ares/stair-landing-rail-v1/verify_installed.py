from pathlib import Path
import json,hashlib,sys,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/stair-landing-rail-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Ares/ares.scene'):assert sha(ROOT/p)==h,p
raw=(OUT/'install-before/original-hall.obj').read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==84
assert (ROOT/'Assets'/m['active_base']).read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
before=json.loads((OUT/'install-before/ares.scene').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='West Stair Landing Rail'];assert len(nodes)==1
scene['GameObjects'].remove(nodes[0]);assert scene==before,'Unexpected unrelated scene change'
for f in ('rail.obj','rail.mtl','rail.vmdl'):
 rel='models/props/ares/stair_landing_rail_v1/'+f;assert sha(ROOT/'Assets'/rel)==m['files'][rel],f
sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A,map_kit as K
model=K.Model();A.railing(model,(-760,-158),(-760,-80),208);assert model.triangle_count()==0 and len(model.boxes)==2 and len(model.hulls)==0
for box,z,size in zip(model.boxes,(248,211),((78,3,8),(78,1,6))):
 center,axes,dims,surface=box;assert np.allclose(center,(-760,-119,z)) and np.allclose(dims,size) and surface==A.METAL
other=K.Model();A.railing(other,(760,-158),(760,-80),208);assert other.triangle_count()==84 and len(other.boxes)==2
report=dict(installed=True,approved_mesh_unchanged=True,old_triangles_removed=84,all_unrelated_obj_lines_preserved=True,one_renderer_added=True,all_other_scene_data_unchanged=True,modeldoc_and_collision_unchanged=True,generator_preserves_original_collision=True,receipt=json.loads((OUT/'installed.json').read_text()))
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
