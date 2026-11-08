"""Keep the original flat wall fixture as a reusable model, without changing the active upgrade."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
OUT=ROOT/'output/veridant/reception-wall-light-v1/original-retained'
RESOURCE='models/props/shared/wall_light_original_v1'
dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
m=K.Model();m.uv_source_name='veridant_buildings'
P.wall_washer(m,'Original fixture reusable asset',(170,200,108),(0,-1),130,light=False)
V.configure(m);K.write_obj(dest/'wall_light_original.obj',m,'veridant_buildings')
lines=[]
for l in (dest/'wall_light_original.obj').read_text().splitlines():
    if l.startswith('v '):
        x,y,z=map(float,l.split()[1:]);l=f'v {x+170:.3f} {y-108:.3f} {z-200:.3f}'
    lines.append(l)
(dest/'wall_light_original.obj').write_text('\n'.join(lines)+'\n')
K.write_vmdl(dest/'wall_light_original.vmdl',RESOURCE,'wall_light_original',m)
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/ff392d2b5eaa45e592699f19b6b8b84b');EX.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/reception-wall-light-v1/original-retained/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return new{OriginalRetained=true};'''
p=EX/'retain-original-wall-light.cs';p.write_text(script)
(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile.json').write_text(json.dumps({'path':RESOURCE+'/wall_light_original.vmdl','full':True}))
(OUT/'check.json').write_text(json.dumps({'code':'var m=Model.Load("'+RESOURCE+'/wall_light_original.vmdl");return new {m.ResourcePath,m.IsError,m.Bounds};'}))
print(json.dumps({'triangles':m.triangle_count(),'origin':'wall mounting centre','faces':'-X','model':RESOURCE+'/wall_light_original.vmdl'}))
