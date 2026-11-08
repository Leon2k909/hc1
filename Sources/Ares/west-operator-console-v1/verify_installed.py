from pathlib import Path
import json,hashlib,sys,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/west-operator-console-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Ares/ares.scene','Tools/ares_map.py'):assert sha(ROOT/p)==h,p
raw=(OUT/'install-before/original-hall.obj').read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==40
assert (ROOT/'Assets'/m['active_base']).read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
before=json.loads((OUT/'install-before/ares.scene').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='West Control Room Operator Console'];assert len(nodes)==1
scene['GameObjects'].remove(nodes[0]);assert scene==before,'Unrelated scene data changed'
for name in ('after.obj','after_lod1.obj','after_lod2.obj','after.vmdl'):
 p='models/props/ares/west_operator_console_v1/'+name;assert sha(ROOT/'Assets'/p)==m['files'][p]
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,ares_map as A
model=K.Model();A.console(model,-1074,240,180.,screen=0);assert model.triangle_count()==0 and len(model.boxes)==1
other=K.Model();A.console(other,-1074,340,180.,screen=1);assert other.triangle_count()==40 and len(other.boxes)==1
native=json.loads((OUT/'installed/validation.json').read_text());assert native['Installed'] and native['ModelsValid'] and native['Lods']==3 and native['LodTriangles']==m['triangles'] and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(installed=True,old_triangles_deleted=40,approved_mesh_unchanged=True,unrelated_geometry_and_scene_unchanged=True,physics_and_materials_unchanged=True,generator_preserves_cover_hull=True,native=native)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
