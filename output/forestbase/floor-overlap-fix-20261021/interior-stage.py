import sys,json,collections
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
out=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/floor-overlap-fix-20261021")
models=F.build(visual_chunks=['barracks','command'])
# Reuse the OBJ reader and checks from the ground audit without rebuilding it.
reader=(out/'stage.py').read_text();reader=reader[reader.index('def faces(path):'):reader.index("old,oldflat=faces(")]
exec(reader)
report={}
for name,x0,x1,y0,y1 in [('barracks',-1290,-610,635,1065),('command',-45,575,705,1135)]:
    count=K.write_obj(out/(name+'.obj'),models[name],name)
    K.write_vmdl(out/(name+'.vmdl'),F.RES,name,models[name])
    for ext in ('.vmdl','.mtl'):
        assert (out/(name+ext)).read_bytes()==(root/'Assets/models/maps/forestbase'/(name+ext)).read_bytes(),(name,ext)
    old,_=faces(root/'Assets/models/maps/forestbase'/(name+'.obj'));new,_=faces(out/(name+'.obj'))
    removed=old-new;added=new-old
    assert sum(removed.values())==12 and not added,(name,'Unexpected geometry diff')
    for (paint,face),times in removed.items():
        assert paint=='concrete'
        for p,uv,n in face:
            ox,oz,oy=map(float,p);e,nn,z=-ox,oy,oz
            assert x0<=e<=x1 and y0<=nn<=y1 and 88<=z<=96,(name,e,nn,z)
    report[name]=dict(trianglesBefore=sum(old.values()),trianglesAfter=count,removedHiddenTriangles=12,allOtherTrianglesUnchanged=True,physicsAndImportUnchanged=True,materialSlotsUnchanged=True)
(out/'interior-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
