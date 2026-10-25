import sys,json,hashlib
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
folder=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/stair-landings-before-20261021")
models=F.build(visual_chunks=['barracks','command'])
result={}
for name in ('barracks','command'):
    out=folder/'generated'/name;out.mkdir(parents=True,exist_ok=True)
    K.write_obj(out/(name+'.obj'),models[name],name)
    K.write_vmdl(out/(name+'.vmdl'),F.RES,name,models[name])
    for suffix in ('.obj','.mtl','.vmdl'):
        a=(out/(name+suffix)).read_bytes();b=(root/'Assets/models/maps/forestbase'/(name+suffix)).read_bytes()
        assert a==b,(name,suffix,'baseline generator mismatch')
    result[name]={'boxes':len(models[name].boxes),'hulls':len(models[name].hulls)}
(folder/'baseline-audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
