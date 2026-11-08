from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/operations-banner-v1'
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/0730b014a5c64da1897eba920d0ecd2e');EX.mkdir(exist_ok=True,parents=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/operations-banner-v1");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");
var expected=System.IO.Path.Combine(o,"last-installed.vmdl");if(!System.IO.File.Exists(expected))expected=System.IO.Path.Combine(o,"before/parent.vmdl");
if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(expected))throw new Exception("Parent changed since staging");var source=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"source-path.txt"));if(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Assets",source))!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before/base.obj")))throw new Exception("Base changed since staging");
var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).Where(x=>!x.EndsWith(".vmdl"))){var target=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));System.IO.File.Copy(f,target,true);Editor.AssetSystem.RegisterFile(target);}
var temp=live+".banner";System.IO.File.Copy(System.IO.Path.Combine(stage,"models/maps/veridant/veridant_buildings.vmdl"),temp,true);System.IO.File.Move(temp,live,true);Editor.AssetSystem.RegisterFile(live);return new{Imported=true};'''
p=EX/'operations-banner-import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
if not (OUT/'before.png').exists():(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.05.22.35.55.png').read_bytes())
