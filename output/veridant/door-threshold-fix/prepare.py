from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/5d0428de1508495cb0c30e55c93bd71c')
EX.mkdir(parents=True,exist_ok=True)
capture='''var scene = Editor.SceneEditorSession.Active.Scene;
GameObject holder;
CameraComponent camera;
using(scene.Push()) {
 holder = new GameObject(true, "Door threshold QA camera");
 camera = holder.Components.Create<CameraComponent>();
 camera.WorldPosition = new Vector3(-405,-320,60);
 camera.WorldRotation = Rotation.LookAt(new Vector3(1,0,-0.20f));
 camera.FieldOfView = 70;
 camera.FovAxis = CameraComponent.Axis.Horizontal;
 camera.CustomSize = new Vector2(1000,900);
 camera.ZNear=1; camera.ZFar=120000;
}
try {
 using var bitmap = new Bitmap(1000,900);
 for(int i=0;i<10;i++){camera.RenderToBitmap(bitmap,false);await Task.Delay(33,cancellationToken);}
 var path = @"DEST";
 System.IO.File.WriteAllBytes(path,bitmap.ToPng());
 return path;
} finally {holder.Destroy();}
'''
for name in ('before','after'):
 p=EX/f'threshold-{name}.cs'
 p.write_text(capture.replace('DEST',str(OUT/f'{name}.png')))
 (OUT/f'{name}.json').write_text(json.dumps({'path':str(p)}))
project=Path('C:/sbox-projects/hc1/forked-shooter-main')
backup=OUT/'veridant.before.scene'
if not backup.exists(): backup.write_bytes((project/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes())
script='''var root=Sandbox.Project.Current.GetRootPath();
var source=System.IO.Path.Combine(root,"output/veridant/door-threshold-fix/stage/models/maps/veridant/door-threshold-fix");
var dest=System.IO.Path.Combine(root,"Assets/models/maps/veridant/door-threshold-fix");
System.IO.Directory.CreateDirectory(dest);
foreach(var file in System.IO.Directory.GetFiles(source)) {
var target=System.IO.Path.Combine(dest,System.IO.Path.GetFileName(file));
System.IO.File.Copy(file,target,true);
Editor.AssetSystem.RegisterFile(target);
}
return dest;
'''
p=EX/'threshold-import.cs'; p.write_text(script)
(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
(OUT/'compile.json').write_text(json.dumps({'path':'models/maps/veridant/door-threshold-fix/courtyard_threshold.vmdl','full':True}))
(OUT/'spawn.json').write_text(json.dumps({'model':'models/maps/veridant/door-threshold-fix/courtyard_threshold.vmdl','name':'Operations courtyard doorway threshold','position':'0,0,0'}))
