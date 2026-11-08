from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/control-room-display-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Ares/ares.scene'):assert sha(ROOT/p)==h,p
raw=(OUT/'install-before/original-hall.obj').read_text().splitlines(keepends=True);cut=set(m['cut']);assert len(cut)==2
assert (ROOT/'Assets'/m['active_base']).read_text()==''.join(l for i,l in enumerate(raw) if i not in cut)
before=json.loads((OUT/'install-before/ares.scene').read_text());scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='West Control Room Display'];assert len(nodes)==1
scene['GameObjects'].remove(nodes[0]);assert scene==before,'Unrelated scene change'
model=ROOT/'Assets/models/props/ares/control_room_display_v1/display.obj';assert sha(model)==m['files']['models/props/ares/control_room_display_v1/display.obj']
native=json.loads((OUT/'installed/validation.json').read_text());assert native['ModelsValid'] and native['SceneUnchanged'] and native['PlayStateUnchanged'] and native['AddedColliders']==0
report=dict(installed=True,old_flat_geometry_deleted=True,exact_original_faces_removed=2,one_renderer_added=True,unrelated_geometry_scene_collision_materials_unchanged=True,approved_model_unchanged=True,native=native)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
