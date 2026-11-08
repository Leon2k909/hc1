from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/reception-desk-v1'
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/db605f643da247b3a5b2f1f27ae53518');EX.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var output=System.IO.Path.Combine(root,"output/veridant/reception-desk-v1");
var relative="models/maps/veridant/veridant_buildings.vmdl";var live=System.IO.Path.Combine(root,"Assets",relative);
var expected=System.IO.Path.Combine(output,"last-installed.vmdl");if(!System.IO.File.Exists(expected))expected=System.IO.Path.Combine(output,"before/veridant_buildings.vmdl");
if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(expected))throw new Exception("Parent changed since staging");
var original=System.IO.Path.Combine(root,"Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj");
if(System.IO.File.ReadAllText(original)!=System.IO.File.ReadAllText(System.IO.Path.Combine(output,"before/veridant_buildings-base.obj")))throw new Exception("Original mesh changed since staging");
var stage=System.IO.Path.Combine(output,"stage");var files=System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories);
foreach(var f in files.Where(f=>!f.EndsWith(".vmdl"))){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}
var temp=live+".desk-import";System.IO.File.Copy(System.IO.Path.Combine(stage,relative),temp,true);System.IO.File.Move(temp,live,true);Editor.AssetSystem.RegisterFile(live);return new{Imported=true,Files=files.Length};
'''
p=EX/'desk-import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
if not (OUT/'before.png').exists():
    (OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.05.22.10.52.png').read_bytes())
