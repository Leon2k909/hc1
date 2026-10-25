import sys,json,types,hashlib,re,collections,shutil
from pathlib import Path
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');sys.path.insert(0,str(r/'Tools'))
import forestbase_map as F
import forestbase_truck as T
import forestbase_truck041 as R
import map_kit as K
out=Path(__file__).parent
if '--geometry' not in sys.argv:R.materials(out/'materials',out/'canvas-source.png')
legacy=types.ModuleType('truck_legacy');exec(compile((out/'forestbase_truck.before.py').read_text(),str(out/'forestbase_truck.before.py'),'exec'),legacy.__dict__)
old=F.model();current=T.refine;T.refine=lambda m,api,**kw:legacy.refine(m,api)
try:F.truck(old,-1360,-840,-20)
finally:T.refine=current
new=F.model();F.truck(new,-1360,-840,-20)
K.write_obj(out/'old-truck.obj',old,'yard');count=K.write_obj(out/'new-truck.obj',new,'yard')
reader=(r/'output/forestbase/truck-reference-20261023/stage.py').read_text();exec(reader[reader.index('def parse(path):'):reader.index('report={}')])
_,remove,_=parse(out/'old-truck.obj');records,base,offsets=parse(out/'yard.before.obj')
assert not remove-base,'Existing rear-yard truck does not match baseline'
original=remove.copy();lines=[]
for line,key in records:
    if key and remove[key]>0:remove[key]-=1
    else:lines.append(line)
assert not +remove
lines.append('o reference_rear_yard_FB041')
for line in (out/'new-truck.obj').read_text().splitlines():
    if line.startswith(('mtllib ','o ','#')):continue
    if line.startswith('f '):line='f '+' '.join('/'.join(str(int(v)+o) for v,o in zip(token.split('/'),offsets)) for token in line.split()[1:])
    lines.append(line)
(out/'yard.obj').write_text('\n'.join(lines)+'\n')
_,result,_=parse(out/'yard.obj');_,added,_=parse(out/'new-truck.obj')
assert result==base-original+added,'Unrelated faces changed'
source=(out/'yard.before.vmdl').read_text();updated=source
for paint,path in new.material_overrides.items():
    if not paint.startswith('truck_'):continue
    expression=r'(from\s*=\s*"'+re.escape(paint)+r'\.vmat"\s+to\s*=\s*")[^\"]+("\s*})'
    updated,n=re.subn(expression,lambda m:m.group(1)+path+m.group(2),updated)
    assert n==1,(paint,n)
marker='_class = "PhysicsShapeList"';assert updated[updated.index(marker):]==source[source.index(marker):]
(out/'yard.vmdl').write_text(updated);shutil.copy2(out/'yard.before.mtl',out/'yard.mtl')
unit=F.model();T.refine(unit,F.__dict__,reference=True);K.write_obj(out/'truck.obj',unit,'truck')
# The three FB/027 trucks still use precisely the previous module geometry.
standard=F.model();T.refine(standard,F.__dict__);before=F.model();legacy.refine(before,F.__dict__)
K.write_obj(out/'standard-current.obj',standard,'standard');K.write_obj(out/'standard-before.obj',before,'standard')
_,current_standard,_=parse(out/'standard-current.obj');_,old_standard,_=parse(out/'standard-before.obj')
assert current_standard==old_standard,'Standard truck surfaces changed'
norms=[]
for paint,polys in unit.polygons.items():
    for i,(pts,n) in enumerate(polys):
        for nn in unit.polygon_normals.get((paint,i),[]):norms.append(float(K.np.dot(n,nn)))
assert min(norms)>0,'Reversed smooth normal'
report={'trianglesBefore':sum(base.values()),'trianglesAfter':sum(result.values()),'oldTruckTriangles':sum(original.values()),'newTruckTriangles':count,
        'allOtherFacesUnchanged':True,'allPhysicsUnchanged':True,'standardTrucksGeneratorUnchanged':True,
        'minimumSmoothNormalAgreement':min(norms),'position':[-1360,-840,0],'yaw':-20,
        'inputHash':hashlib.sha256((out/'yard.before.obj').read_bytes()).hexdigest()}
(out/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
