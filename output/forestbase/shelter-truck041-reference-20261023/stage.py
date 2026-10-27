import sys,json,types,hashlib,re,collections,shutil
from pathlib import Path
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');sys.path.insert(0,str(r/'Tools'))
import forestbase_map as F
import forestbase_truck as T
import map_kit as K
out=Path(__file__).parent
legacy=types.ModuleType('truck_legacy');exec(compile((out/'forestbase_truck.before.py').read_text(),str(out/'forestbase_truck.before.py'),'exec'),legacy.__dict__)
old=F.model();current=T.refine;current_config=T.configure
T.refine=lambda m,api,**kw:legacy.refine(m,api)
T.configure=lambda m,**kw:legacy.configure(m)
try:F.truck(old,-901.6,-555,90)
finally:T.refine=current;T.configure=current_config
new=F.model();F.truck(new,-901.6,-555,90)
K.write_obj(out/'old-truck.obj',old,'motor');count=K.write_obj(out/'new-truck.obj',new,'motor')
reader=(r/'output/forestbase/truck-reference-20261023/stage.py').read_text();exec(reader[reader.index('def parse(path):'):reader.index('report={}')])
_,remove,_=parse(out/'old-truck.obj');records,base,offsets=parse(out/'motor.before.obj')
assert not remove-base,'Existing shelter truck does not match baseline'
original=remove.copy();lines=[]
for line,key in records:
    if key and remove[key]>0:remove[key]-=1
    else:lines.append(line)
assert not +remove
lines.append('o reference_shelter_FB041')
for line in (out/'new-truck.obj').read_text().splitlines():
    if line.startswith(('mtllib ','o ','#')):continue
    if line.startswith('f '):line='f '+' '.join('/'.join(str(int(v)+o) for v,o in zip(token.split('/'),offsets)) for token in line.split()[1:])
    lines.append(line)
(out/'motor.obj').write_text('\n'.join(lines)+'\n')
_,result,_=parse(out/'motor.obj');_,added,_=parse(out/'new-truck.obj')
assert result==base-original+added,'Unrelated faces changed'
source=(out/'motor.before.vmdl').read_text();match=re.search(r'(remaps\s*=\s*\[)(.*?)(\]\s*use_global_default)',source,re.S)
entries=',\n'.join('                            { from = "'+p+'.vmat" to = "'+new.material_overrides[p]+'" }' for p in sorted(new.polygons))
updated=source[:match.start(2)]+match.group(2).rstrip()+',\n'+entries+'\n                        '+source[match.end(2):]
marker='_class = "PhysicsShapeList"';assert updated[updated.index(marker):]==source[source.index(marker):]
(out/'motor.vmdl').write_text(updated)
mtl=(out/'motor.before.mtl').read_text()
for p in sorted(new.polygons):mtl+=f'newmtl {p}\nKd 1 1 1\nd 1\n'
(out/'motor.mtl').write_text(mtl)
unit=F.model();T.refine(unit,F.__dict__,reference=True,shelter=True);K.write_obj(out/'truck.obj',unit,'truck')
(out/'materials').mkdir(exist_ok=True)
for p in (r/'Assets/materials/forestbase/truck041').glob('*.png'):shutil.copy2(p,out/'materials'/p.name)
# Compare all other profile outputs to the previous source, including UVs/normals.
for reference in (False,True):
    a=F.model();T.refine(a,F.__dict__,reference=reference);b=F.model();legacy.refine(b,F.__dict__,reference=reference)
    K.write_obj(out/'current.obj',a,'parity');K.write_obj(out/'before.obj',b,'parity')
    assert parse(out/'current.obj')[1]==parse(out/'before.obj')[1],'Unrelated truck profile changed'
norms=[]
for paint,polys in unit.polygons.items():
    for i,(pts,n) in enumerate(polys):
        for nn in unit.polygon_normals.get((paint,i),[]):norms.append(float(K.np.dot(n,nn)))
assert min(norms)>0
report={'trianglesBefore':sum(base.values()),'trianglesAfter':sum(result.values()),'oldTruckTriangles':sum(original.values()),'newTruckTriangles':count,
        'allOtherFacesUnchanged':True,'allPhysicsUnchanged':True,'otherTruckProfilesUnchanged':True,'privateMaterialSlots':len(new.polygons),
        'minimumSmoothNormalAgreement':min(norms),'position':[-901.6,-555,0],'yaw':90,
        'inputHash':hashlib.sha256((out/'motor.before.obj').read_bytes()).hexdigest()}
(out/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
