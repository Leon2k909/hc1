from pathlib import Path
import sys,json
sys.path.insert(0,'Sources/Belltower/terracotta-pot-v2')
import native
root=Path.cwd();native.OUT=root/'output/veridant/megascans-gravel-trial-20261105'
if sys.argv[1]=='install':
    print(json.dumps(native.script(root/'Sources/Veridant/megascans-gravel-trial-20261105/install.cs.txt','install-native'),indent=2))
elif sys.argv[1]=='compile':
    print(json.dumps(native.call('asset_compile',{'path':'models/maps/veridant/veridant_ground.vmdl'},'installed-model-compile'),indent=2))
elif sys.argv[1]=='verify':
    print(json.dumps(native.call('run_csharp',{'code':'''var path="models/maps/veridant/veridant_ground.vmdl"; var model=Model.Load(path); return new { Valid=model is not null && !model.IsError, Materials=model.Materials.Select(m=>m.ResourcePath).ToArray(), Game.IsPlaying, EditorScene=Editor.SceneEditorSession.Active?.Scene?.Name, SavedSceneDirty=Editor.SceneEditorSession.Active?.HasUnsavedChanges, Renderers=Editor.SceneEditorSession.All.SelectMany(s=>s.Scene.GetAllComponents<ModelRenderer>()).Concat(Game.ActiveScene?.GetAllComponents<ModelRenderer>() ?? Enumerable.Empty<ModelRenderer>()).Where(r=>r.Model?.ResourcePath==path).Select(r=>new {r.GameObject.Name, Materials=r.Model.Materials.Select(m=>m.ResourcePath).ToArray()}).ToArray() };'''},'installed-live-verification'),indent=2))
