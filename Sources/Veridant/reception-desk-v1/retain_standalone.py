"""Restore Veridant's original desk and retain the replacement as a reusable prop."""
from pathlib import Path
import sys,re,json
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_reception_desk as D
OUT=ROOT/'output/veridant/reception-desk-v1/retained'
RESOURCE='models/props/shared/reception_desk_walnut_v1'
OUT.mkdir(parents=True,exist_ok=True)
stage=OUT/'stage';dest=stage/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
m=K.Model();m.uv_source_name='veridant_buildings';D.build_into(m,True)
P.led(m,(32,419.7,39),(168,419.7,39),P.v(0,-1,0),1)
V.configure(m)
K.write_obj(dest/'reception_desk.obj',m,'veridant_buildings')
# Translate only positions, preserving all original UVs, normals and materials.
lines=[]
for line in (dest/'reception_desk.obj').read_text().splitlines():
    if line.startswith('v '):
        x,y,z=map(float,line.split()[1:]);line=f'v {x+100:.3f} {y:.3f} {z-435:.3f}'
    lines.append(line)
(dest/'reception_desk.obj').write_text('\n'.join(lines)+'\n')
shift=np.array((100,435,0.))
m.boxes=[(np.array(c)-shift,axes,size,surface) for c,axes,size,surface in m.boxes]
m.collision_box((-72,-17,40),(72,17,42),'default')
K.write_vmdl(dest/'reception_desk.vmdl',RESOURCE,'reception_desk',m)
live=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl';text=live.read_text()
matches=[x for x in re.finditer(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S) if 'name = "reception_desk_v1"' in x.group()]
assert len(matches)==1
match=matches[0];reverted=text[:match.start()]+text[match.end():]
assert reverted.count('models/maps/veridant/reception-desk-v1/buildings_without_desk.obj')==1
reverted=reverted.replace('models/maps/veridant/reception-desk-v1/buildings_without_desk.obj','models/maps/veridant/lounger-v2/veridant_buildings-base.obj')
(OUT/'pre-revert.vmdl').write_bytes(live.read_bytes());(OUT/'restored.vmdl').write_text(reverted)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/0730b014a5c64da1897eba920d0ecd2e');ex.mkdir(parents=True,exist_ok=True)
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/reception-desk-v1/retained");var live=System.IO.Path.Combine(root,"Assets/models/maps/veridant/veridant_buildings.vmdl");
if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"pre-revert.vmdl")))throw new Exception("Parent changed since preparation");
var stage=System.IO.Path.Combine(o,"stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}
var temp=live+".restore-desk";System.IO.File.Copy(System.IO.Path.Combine(o,"restored.vmdl"),temp,true);System.IO.File.Move(temp,live,true);Editor.AssetSystem.RegisterFile(live);return new{OriginalRestored=true,RetainedModel="models/props/shared/reception_desk_walnut_v1/reception_desk.vmdl"};'''
p=ex/'retain-desk.cs';p.write_text(script);(OUT/'import.json').write_text(json.dumps({'path':str(p)}))
(OUT/'compile.json').write_text(json.dumps({'path':RESOURCE+'/reception_desk.vmdl','full':True}))
print(json.dumps({'triangles':m.triangle_count(),'origin':'floor centre','collision_boxes':len(m.boxes),'model':RESOURCE+'/reception_desk.vmdl'}))
