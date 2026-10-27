import sys,json,hashlib
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
out=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/light-stability-20261021")
models=F.build(visual_chunks=['ground','barracks','command'])
report={}
for name in ('ground','barracks','command'):
    triangles=K.write_obj(out/(name+'.obj'),models[name],name)
    K.write_vmdl(out/(name+'.vmdl'),F.RES,name,models[name])
    assert (out/(name+'.vmdl')).read_bytes()==(root/'Assets/models/maps/forestbase'/(name+'.vmdl')).read_bytes(),name+' physics/import changed'
    assert (out/(name+'.mtl')).read_bytes()==(root/'Assets/models/maps/forestbase'/(name+'.mtl')).read_bytes()
    before=sum(l.startswith('f ') for l in (root/'Assets/models/maps/forestbase'/(name+'.obj')).read_text().splitlines())
    assert triangles==before
    report[name]={'triangles':triangles,'physicsAndImportUnchanged':True,'materialsUnchanged':True}
(out/'model-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
