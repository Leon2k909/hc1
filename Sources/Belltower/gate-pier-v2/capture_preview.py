"""Render through an ephemeral editor-scene camera while the game keeps playing."""
from pathlib import Path
import review
HERE=Path(__file__).parent
s=review.helper().read_text()
a=s.index('var camera = scene.GetAllComponents<CameraComponent>().Single(');b=s.index('var tone =',a)
s=s[:a]+'''var mainCamera=scene.Camera;
var cameraHolder=new GameObject(scene,false,"Temporary prop review camera");
cameraHolder.Flags|=GameObjectFlags.NotSaved|GameObjectFlags.EditorOnly;
var camera=cameraHolder.Components.Create<CameraComponent>();
cameraHolder.Enabled=true;
'''+s[b:]
s=s.replace('scene.GetAllComponents<CameraComponent>().Select(c => new {','scene.GetAllComponents<CameraComponent>().Where(c=>c!=camera).Select(c => new {')
s=s.replace('scene.GetAllObjects(true).Select(o => o.Id).ToHashSet();','scene.GetAllObjects(true).Where(o=>o!=cameraHolder).Select(o => o.Id).ToHashSet();',1)
s=s.replace('var mainRestored = ReferenceEquals(scene.Camera, mainCamera);','')
s=s.replace('    var objectsRestored =','    using(scene.Push()){cameraHolder.Destroy();scene.ProcessDeletes();}\n    var mainRestored=ReferenceEquals(scene.Camera,mainCamera);\n    var objectsRestored =')
s=s.replace('gate-pier-v2/capture.cs.txt','gate-pier-v2/capture-preview.cs.txt')
p=HERE/'capture-preview.cs.txt';p.write_text(s);review.helper=lambda:p
for name,candidate in [('warm-preview-before',False),('warm-preview-after',True),('before-preview',False),('after-preview',True)]:
    print(name,review.capture(name,candidate)['Restoration'],flush=True)
