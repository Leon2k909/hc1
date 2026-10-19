"""Stage native scripts and preserve the pre-revision evidence (no live edits)."""
from pathlib import Path
import shutil,json
ROOT=Path(__file__).resolve().parent.parent
S=ROOT/"Sources/Spillway"
O=ROOT/"output/spillway"
before=O/"realism-v1-before"
before.mkdir(exist_ok=True)
for name in ("reference.png","cargo.png"):
    dest=before/name
    if not dest.exists():shutil.copy2(O/"captures"/name,dest)
scene=ROOT/"Assets/scenes/maps/spillway/spillway.scene"
if not (before/"spillway.scene").exists():shutil.copy2(scene,before/"spillway.scene")
# Adopt only art roots from regeneration. Preserve the saved native gameplay serialization.
saved=json.loads(scene.read_text())
staged=json.loads((O/"scene-import.json").read_text())
art={g.get("Name"):g for g in staged["GameObjects"] if g.get("Name") in ("Sun","Sky","Sky Fill","Fog","Look","Spillway")}
saved["GameObjects"]=[art.get(g.get("Name"),g) for g in saved["GameObjects"]]
(O/"scene-import.json").write_text(json.dumps(saved,indent=2))
importer=(S/"editor/import-assets.cs.txt").read_text()
importer=importer.replace('var shaders=', '''var backup=System.IO.Path.Combine(root,"output/spillway/realism-v1-before/assets");
void Backup(string relative,string destination)
{
    var path=System.IO.Path.Combine(backup,relative);
    if(System.IO.File.Exists(destination) && !System.IO.File.Exists(path))
    {
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
        System.IO.File.Copy(destination,path,false);
    }
}
var shaders=''')
importer=importer.replace('    var pending=destination+', '    Backup(relative,destination);\n    var pending=destination+')
if not (S/"editor/import-realism.cs.txt").exists():(S/"editor/import-realism.cs.txt").write_text(importer)
bake=(ROOT/"Sources/Collider/editor/bake-lighting.cs.txt").read_text().replace('collider','spillway').replace('Collider','Spillway')
bake=bake.replace('reflections.Length != 4','reflections.Length != 5')
bake=bake.replace('var reflections = scene.GetAllComponents<EnvmapProbe>().ToArray();','var reflections = scene.GetAllComponents<EnvmapProbe>().ToArray();\nvar mirrors=scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Select(c=>(Component:c,Enabled:c.Enabled)).ToArray();')
bake=bake.replace('    var type = typeof(IndirectLightVolume);','    foreach(var mirror in mirrors)mirror.Component.Enabled=false;\n    var type = typeof(IndirectLightVolume);')
bake=bake.replace('    typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);','    foreach(var mirror in mirrors)mirror.Component.Enabled=mirror.Enabled;\n    typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);')
bake=bake.replace('finally\n{','finally\n{\n    foreach(var mirror in mirrors)if(mirror.Component.IsValid())mirror.Component.Enabled=mirror.Enabled;')
if not (S/"editor/bake-lighting.cs.txt").exists():(S/"editor/bake-lighting.cs.txt").write_text(bake)
if not (O/"bake-config.json").exists():(O/"bake-config.json").write_text(json.dumps({"directory":"lighting-v1","timeout_seconds":600},indent=2))
if not (O/"realism-capture.json").exists():(O/"realism-capture.json").write_text(json.dumps({"directory":"realism-v1","width":1600,"height":1066,"views":[
    {"name":"reference","eye":[1100,-3100,700],"target":[-100,850,620],"fov":78},
    {"name":"art","eye":[650,-2700,660],"target":[-200,850,430],"fov":87},
    {"name":"cargo","eye":[-420,-1020,70],"target":[120,800,215],"fov":86},
    {"name":"water","eye":[-1000,-1750,140],"target":[-600,-600,-210],"fov":76},
    {"name":"west-bank","eye":[-2000,-2450,680],"target":[300,1050,450],"fov":88}
]},indent=2))
print("Prepared realism import, native capture and lighting scripts.")
