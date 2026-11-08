from pathlib import Path
import sys,json
root=Path.cwd();sys.path.insert(0,str(root/'Tools'))
import map_kit as K,veridant_map as V
out=root/'output/veridant/operations-window-backing-v1'
res='models/props/shared/operations_window_backing_original_v1'
m=K.Model();V.box(m,-70,70,0,1,0,86,'vr_window_dark');V.configure(m)
K.write_model(out/'stage'/res,res,'window_backing_original',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/operations-window-backing');ex.mkdir(parents=True,exist_ok=True)
p=ex/'retain-original.cs'
p.write_text('''var root=Sandbox.Project.Current.GetRootPath();var rel="models/props/shared/operations_window_backing_original_v1";var stage=System.IO.Path.Combine(root,"output/veridant/operations-window-backing-v1/stage",rel);foreach(var f in System.IO.Directory.GetFiles(stage)){var dst=System.IO.Path.Combine(root,"Assets",rel,System.IO.Path.GetFileName(f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}var model=Model.Load("models/maps/veridant/veridant_buildings.vmdl");return new {ModelError=model.IsError,Scene=Editor.SceneEditorSession.Active.Scene.Name};''')
(out/'retain-original.json').write_text(json.dumps({'path':str(p)}))
(out/'after.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.18.26.55.png').read_bytes())
note=root/'Sources/Veridant/operations-window-backing-v1/README.md';note.parent.mkdir(parents=True,exist_ok=True)
note.write_text('''# Operations lobby garden window

Removed one opaque glossy black placeholder backing from the occupied operations lobby south window (plan E450..590, N-683..-682, Z150..236). Existing steel frame, glazing, wall opening and all physics remain unchanged. Closed-room/upper-floor window backings remain.

Exactly 12 render triangles removed from the current Buildings model; guarded import and unchanged PhysicsShapeList check in output/veridant/operations-window-backing-v1. Original render sources and parent saved there under before/. Reusable original backing: models/props/shared/operations_window_backing_original_v1/window_backing_original.vmdl. Generator condition updated for repeatability.

Before/after are native ScreenshotService captures of the actual Veridant editor viewport, same camera (-475,-520,195), angles (0,180,0), FOV80. No temporary camera, render, scene or lighting changes. Images: output/veridant/operations-window-backing-v1/before.png and after.png.
''')
with (root/'CLAUDE.md').open('a') as f:f.write('\n- [Veridant operations lobby garden window — removed opaque backing, retained original; 2026-11-06](Sources/Veridant/operations-window-backing-v1/README.md)\n')
