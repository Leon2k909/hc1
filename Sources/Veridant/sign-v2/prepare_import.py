from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/veridant/sign-v2'
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/e7ecc8304ab645a19ffb07dbf7a97ac6')
EX.mkdir(exist_ok=True,parents=True)
script='''var root=Sandbox.Project.Current.GetRootPath();
var output=System.IO.Path.Combine(root,"output/veridant/sign-v2");
var relative="models/maps/veridant/veridant_dress.vmdl";
var live=System.IO.Path.Combine(root,"Assets",relative);
var expected=System.IO.Path.Combine(output,"failed-parent.vmdl");
if(!System.IO.File.Exists(expected)) expected=System.IO.Path.Combine(output,"before/veridant_dress.vmdl");
if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(expected)) throw new Exception("Parent model changed since staging; refusing overwrite.");
var sourceObj=System.IO.Path.Combine(root,"Assets/models/maps/veridant/chair-v2/dress-base.obj");
if(System.IO.File.ReadAllText(sourceObj)!=System.IO.File.ReadAllText(System.IO.Path.Combine(output,"before/dress-base.obj"))) throw new Exception("Original mesh changed since staging; refusing overwrite.");
var stage=System.IO.Path.Combine(output,"stage");
var files=System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories);
foreach(var file in files.Where(f=>!f.EndsWith(".vmdl"))) {
var rel=System.IO.Path.GetRelativePath(stage,file);var target=System.IO.Path.Combine(root,"Assets",rel);
System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
System.IO.File.Copy(file,target,true);Editor.AssetSystem.RegisterFile(target);
}
var temp=live+".sign-v2-import";
System.IO.File.Copy(System.IO.Path.Combine(stage,relative),temp,true);
System.IO.File.Move(temp,live,true);Editor.AssetSystem.RegisterFile(live);
return new { Imported=true, Files=files.Length, Model=relative };
'''
p=EX/'veridant-sign-import.cs'; p.write_text(script)
(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
(OUT/'compile.json').write_text(json.dumps({'path':'models/maps/veridant/veridant_dress.vmdl','full':True}))

if __name__=='__main__':
    screenshot=Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.05.21.04.51.png')
    if not (OUT/'before.png').exists(): (OUT/'before.png').write_bytes(screenshot.read_bytes())
