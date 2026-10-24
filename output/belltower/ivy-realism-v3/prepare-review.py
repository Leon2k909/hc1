from pathlib import Path
import hashlib
import json

root=Path.cwd()
out=root/'output/belltower/ivy-realism-v3'
(out/'open-belltower.json').write_text(json.dumps({'path':'scenes/maps/Belltower/belltower.scene'}))
(out/'restore-menu.json').write_text(json.dumps({'scene':'scenes/menu.scene'}))
(out/'capture-config.json').write_text(json.dumps({
    'directory':'ivy-realism-v3-preview','name':'front','exposure':2,
    'width':1440,'height':1080,'fov':62,'settle_ms':3000,
    'position':'1480,2070,82','angles':'0,90,0',
    'expected_scene_sha256':hashlib.sha256((root/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest(),
    'trial_ivy_model':'models/maps/belltower/ivy-realism-v3/preview_west.vmdl'}))
source=(root/'Sources/Belltower/editor/import-ivy-3d-v2.cs.txt').read_text()
source=source.replace('output/belltower/ivy-3d-v1/refined','output/belltower/ivy-realism-v3/preview')
source=source.replace('relative.StartsWith("Assets/materials/belltower/ivy-3d-v1/",StringComparison.Ordinal)',
    'relative.StartsWith("Assets/materials/belltower/ivy-realism-v3/",StringComparison.Ordinal) || relative=="Assets/shaders/belltower_ivy_realism_v3.shader"')
source=source.replace('if (manifest["files"].AsObject().Count != 14)','if (manifest["files"].AsObject().Count < 8)')
source=source.replace('p.Target.EndsWith(".png") ? 0','p.Target.EndsWith(".shader") ? -1 : p.Target.EndsWith(".png") ? 0')
(root/'Sources/Belltower/editor/import-ivy-realism-v3-preview.cs.txt').write_text(source)
helper=(root/'Sources/Belltower/editor/capture-preview-consistent.cs.txt').read_text()
helper=helper.replace('output/belltower/quality/consistent-preview.json','output/belltower/ivy-realism-v3/capture-config.json')
helper=helper.replace('Sources/Belltower/editor/capture-preview-consistent.cs.txt','Sources/Belltower/editor/capture-ivy-realism-v3.cs.txt')
helper=helper.replace('var scene = session.Scene;', '''var scene = session.Scene;
var trialPath = config["trial_ivy_model"]?.GetValue<string>();
var trialSide = config["trial_ivy_side"]?.GetValue<string>() ?? "west";
var trialRenderer = trialPath is null ? null : scene.GetAllComponents<ModelRenderer>().Single(r =>
    r.Model?.ResourcePath == "models/maps/belltower/belltower_"+trialSide+".vmdl");
var originalModel = trialRenderer?.Model;
var originalRendererSnapshot = trialRenderer?.Serialize().ToJsonString();
var trialModel = trialPath is null ? null : Model.Load(trialPath);
if (trialModel?.IsError == true) throw new InvalidOperationException("Preview model failed to load.");''')
helper=helper.replace('foreach (var material in materials.Where',
    'if (trialModel is not null) foreach (var m in trialModel.Materials) materials.Add(m);\n    foreach (var material in materials.Where')
helper=helper.replace('pinAttempted = true;',
    'if (trialRenderer is not null) trialRenderer.Model = trialModel;\n        pinAttempted = true;')
helper=helper.replace('if (pinAttempted) cameraProperty.SetValue(scene, mainCamera);',
    'if (trialRenderer is not null) trialRenderer.Model = originalModel;\n        if (pinAttempted) cameraProperty.SetValue(scene, mainCamera);')
helper=helper.replace('var objectsRestored =',
    'var modelRestored = trialRenderer is null || (ReferenceEquals(trialRenderer.Model,originalModel) && trialRenderer.Serialize().ToJsonString()==originalRendererSnapshot);\n    var objectsRestored =')
helper=helper.replace('ObjectsRestored = objectsRestored, EditorStatePreserved',
    'ObjectsRestored = objectsRestored, ModelRestored = modelRestored, EditorStatePreserved')
helper=helper.replace('if (!mainRestored || !toneRestored || !camerasRestored || !objectsRestored || !statePreserved)',
    'if (!mainRestored || !toneRestored || !camerasRestored || !objectsRestored || !modelRestored || !statePreserved)')
(root/'Sources/Belltower/editor/capture-ivy-realism-v3.cs.txt').write_text(helper)
print('Prepared private model import, restored model-swap capture, and camera configuration.')
