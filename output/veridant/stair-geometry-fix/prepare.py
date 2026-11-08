from pathlib import Path
import json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/veridant/stair-geometry-fix'
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/1d09b2f423ab4564983b1b6933715a6a');EX.mkdir(exist_ok=True,parents=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/stair-geometry-fix");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");
if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before/parent.vmdl")))throw new Exception("Parent changed since staging");
var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).Where(x=>!x.EndsWith(".vmdl"))){var target=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));System.IO.File.Copy(f,target,true);Editor.AssetSystem.RegisterFile(target);}
var temp=live+".stair-closure";System.IO.File.Copy(System.IO.Path.Combine(stage,"models/maps/veridant/veridant_buildings.vmdl"),temp,true);System.IO.File.Move(temp,live,true);Editor.AssetSystem.RegisterFile(live);return new{Imported=true};'''
p=EX/'veridant-stair-closure-import.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
(OUT/'asset-search.json').write_text(json.dumps({'query':'asset_compile'}))
