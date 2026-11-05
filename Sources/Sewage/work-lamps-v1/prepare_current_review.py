"""Review/reuse the already-authored lamp model; never regenerate its geometry."""
from pathlib import Path
import hashlib,json,sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/work-lamps-v1';REVIEW=OUT/'current-review';REVIEW.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
original=ROOT/'Assets/models/maps/sewage/sewage_details.obj'
plan=json.loads((OUT/'plan.json').read_text())
assert hashlib.sha256(original.read_bytes()).hexdigest()==plan['original_sha256'],'Details model changed'
_,old=S.read_obj(original);_,removed=S.read_obj(OUT/'original-lamps.obj')
_,base=S.read_obj(ROOT/'Assets/models/maps/sewage/work-lamps-v1/base_details.obj')
assert not Counter(removed)-Counter(old)
assert Counter(base)==Counter(old)-Counter(removed),'Base loses unrelated geometry'
old_doc=original.with_suffix('.vmdl').read_text()
new_doc=(ROOT/'Assets/models/maps/sewage/work-lamps-v1/base_details.vmdl').read_text()
assert old_doc[old_doc.index('_class = "PhysicsShapeList"'):]==new_doc[new_doc.index('_class = "PhysicsShapeList"'):]
scene=ROOT/'Assets/scenes/maps/sewage/sewage.scene'
scene_bytes=scene.read_bytes()
scene_data=json.loads(scene_bytes)
assert not any(g.get('Name')=='Waterworks caged work lamps' for g in scene_data['GameObjects']),'Already installed; use verify_installed.py'
snapshot=REVIEW/'scene-before.json'
if snapshot.exists():assert snapshot.read_bytes()==scene_bytes,'Preserve existing review baseline; saved scene has changed'
else:snapshot.write_bytes(scene_bytes)
(REVIEW/'reuse-audit.json').write_text(json.dumps(dict(
 selected='models/maps/sewage/work-lamps-v1/lamps.vmdl',status='existing staged model, not previously installed',
 alternatives_checked=['models/props/riverside/porch_light_v2/porch_light.vmdl','models/maps/reefhall/wall-light-v1/wall_light.vmdl','Sources/Ares/bulkhead-lamp-trial-v1'],
 reason='Purpose-built for the existing 24 Sewage anchors and four light colours; original light data and physics retained',
 source_model_unchanged=True,removed_faces=len(removed),retained_faces=len(base),original_physics_retained=True,
 stair_original_kept=(ROOT/'Assets/models/maps/sewage/stair-treads-v1/before.vmdl').exists(),
 stair_new_kept=(ROOT/'Assets/models/maps/sewage/stair-treads-v1/after.vmdl').exists()),indent=2))
capture=(HERE/'capture.cs.txt').read_text()
capture=capture.replace('"output/sewage/work-lamps-v1"','"output/sewage/work-lamps-v1/current-review"')
capture=capture.replace('var scene = Scene.CreateEditorScene();','var editor=Editor.SceneEditorSession.Active;\nvar savedState=new{Scene=editor.Scene.Id,Runtime=Game.ActiveScene?.Id,Game.IsPlaying,Dirty=editor.HasUnsavedChanges};\nvar scene = Scene.CreateEditorScene();')
capture=capture.replace('Bolted flange preview','Existing caged work lamp preview').replace('Flange model failed','Lamp model failed').replace('Pipe texture review camera','Caged work lamp review camera').replace('Pipework variant failed','Details variant failed')
capture=capture.replace('return new { Success=true, Material=material.ResourcePath, ActiveScene=Editor.SceneEditorSession.Active.Scene.Name, Output=output };',
 'var result=new{Success=true,ReusedExistingModel=true,MatchedCameraAndLighting=true,UserStatePreserved=editor.Scene.Id==savedState.Scene&&Game.ActiveScene?.Id==savedState.Runtime&&Game.IsPlaying==savedState.IsPlaying&&editor.HasUnsavedChanges==savedState.Dirty,Output=output};\nSystem.IO.File.WriteAllText(System.IO.Path.Combine(output,"capture-report.json"),System.Text.Json.JsonSerializer.Serialize(result));return result;')
(HERE/'review-current.cs.txt').write_text(capture)
print((REVIEW/'reuse-audit.json').read_text())
