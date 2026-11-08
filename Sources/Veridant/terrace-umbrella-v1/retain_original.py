"""Preserve the original closed umbrella as a floor-centred reusable prop."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
OUT=ROOT/'output/veridant/terrace-umbrella-v1/original-retained';RESOURCE='models/props/shared/terrace_umbrella_original_v1'
dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
m=K.Model();m.uv_source_name='veridant_buildings'
# A local origin avoids the scoped map-only upgrade hook and emits the old design.
P.umbrella_closed(m,(0,0),182,z0=0);V.configure(m);K.write_model(dest,RESOURCE,'umbrella_original',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/a23fad6d011b4b4ab10394bbe805dc35');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/terrace-umbrella-v1/original-retained/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var target=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));System.IO.File.Copy(f,target,true);Editor.AssetSystem.RegisterFile(target);}return new{OriginalRetained=true};'''
p=ex/'retain-original-umbrella.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile.json').write_text(json.dumps({'path':RESOURCE+'/umbrella_original.vmdl','full':True}));(OUT/'check.json').write_text(json.dumps({'code':'var m=Model.Load("'+RESOURCE+'/umbrella_original.vmdl");return new{m.ResourcePath,m.IsError,m.Bounds};'}))
print(json.dumps({'triangles':m.triangle_count(),'boxes':len(m.boxes),'hulls':len(m.hulls),'model':RESOURCE+'/umbrella_original.vmdl'}))
