import sys,json,types,re,collections,shutil,hashlib
from pathlib import Path
from PIL import Image
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');sys.path.insert(0,str(r/'Tools'))
import forestbase_map as F
import forestbase_apc as A
import map_kit as K
out=Path(__file__).parent
if '--geometry' not in sys.argv:A.materials(out/'materials',r/'output/forestbase/apc-reference-20261021/armor-source.png')
legacy=types.ModuleType('apc_legacy');exec(compile((out/'forestbase_apc.before.py').read_text(),str(out/'forestbase_apc.before.py'),'exec'),legacy.__dict__)
old=F.model();current=A.refine;A.refine=legacy.refine
try:F.truck(old,-900,-995,0,True)
finally:A.refine=current
new=F.model();F.truck(new,-900,-995,0,True)
K.write_obj(out/'old-apc.obj',old,'yard');count=K.write_obj(out/'new-apc.obj',new,'yard')
reader=(r/'output/forestbase/truck-reference-20261023/stage.py').read_text();reader=reader[reader.index('def parse(path):'):reader.index('report={}')];exec(reader)
_,remove,_=parse(out/'old-apc.obj');records,base,offsets=parse(out/'yard.before.obj')
assert not remove-base,'Existing APC does not match baseline'
original=remove.copy();lines=[]
for line,key in records:
    if key and remove[key]>0:remove[key]-=1
    else:lines.append(line)
assert not +remove
lines.append('o reference_FB041_APC')
for line in (out/'new-apc.obj').read_text().splitlines():
    if line.startswith(('mtllib ','o ','#')):continue
    if line.startswith('f '):line='f '+' '.join('/'.join(str(int(v)+o) for v,o in zip(token.split('/'),offsets)) for token in line.split()[1:])
    lines.append(line)
(out/'yard.obj').write_text('\n'.join(lines)+'\n')
_,result,_=parse(out/'yard.obj');_,added,_=parse(out/'new-apc.obj')
assert result==base-original+added,'Non-APC geometry changed'
# All private and borrowed material slots already exist in this ModelDoc.
vmdl=(out/'yard.before.vmdl').read_text()
for p in new.polygons:assert f'from = "{p}.vmat"' in vmdl,p
for ext in ('.vmdl','.mtl'):shutil.copy2(out/('yard.before'+ext),out/('yard'+ext))
unit=F.model();F.truck(unit,0,0,0,True);K.write_obj(out/'apc.obj',unit,'apc')
mat=out/'materials'
for name,basecolor in [('vehicle_glass',(20,31,34)),('vehicle_canvas',(62,70,45)),('timber',(105,73,41))]:
    vm=r/'Assets'/unit.material_overrides[name];s=vm.read_text()
    for kind,suffix,default in [('Color','color',basecolor),('Normal','normal',(128,128,255)),('Roughness','rough',(190,190,190))]:
        m=re.search(r'Texture'+kind+r'\s+"([^\"]+)"',s);target=mat/(name+'_'+suffix+'.png')
        if m and (r/'Assets'/m.group(1)).exists():Image.open(r/'Assets'/m.group(1)).convert('RGB').save(target,compress_level=3)
        else:Image.new('RGB',(512,512),default).save(target)
report={'trianglesBefore':sum(base.values()),'trianglesAfter':sum(result.values()),'oldAPCTriangles':sum(original.values()),
        'newAPCTriangles':count,'allNonAPCFacesUnchanged':True,'modelDocAndPhysicsUnchanged':True,'position':[-900,-995,0],
        'inputHash':hashlib.sha256((out/'yard.before.obj').read_bytes()).hexdigest()}
(out/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
