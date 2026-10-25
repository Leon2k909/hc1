import sys,json,collections
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
out=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/floor-overlap-fix-20261021")
models=F.build(visual_chunks=['ground'])
triangles=K.write_obj(out/'ground.obj',models['ground'],'ground')
K.write_vmdl(out/'ground.vmdl',F.RES,'ground',models['ground'])
for suffix in ('.vmdl','.mtl'):
    assert (out/('ground'+suffix)).read_bytes()==(root/'Assets/models/maps/forestbase'/('ground'+suffix)).read_bytes(),suffix+' changed'
def faces(path):
    v=[];vt=[];vn=[];paint='';counter=collections.Counter();flat=[]
    for line in path.read_text().splitlines():
        a=line.split()
        if not a:continue
        if a[0]=='v':v.append(tuple(a[1:]))
        elif a[0]=='vt':vt.append(tuple(a[1:]))
        elif a[0]=='vn':vn.append(tuple(a[1:]))
        elif a[0]=='usemtl':paint=a[1]
        elif a[0]=='f':
            face=[]
            for item in a[1:]:
                i,j,k=map(int,item.split('/'));face.append((v[i-1],vt[j-1],vn[k-1]))
            counter[(paint,tuple(face))]+=1
            pts=[(-float(p[0][0]),float(p[0][2]),float(p[0][1])) for p in face]
            if all(abs(p[2])<1e-6 for p in pts) and float(face[0][2][1])>.99:flat.append((paint,pts))
    return counter,flat
old,oldflat=faces(root/'Assets/models/maps/forestbase/ground.obj');new,newflat=faces(out/'ground.obj')
removed=old-new;added=new-old
assert sum(removed.values())==2
assert all(k[0]=='asphalt' and all(float(p[0][1])==0 for p in k[1]) for k in removed)
assert all(k[0]=='asphalt' and all(float(p[0][1])==0 for p in k[1]) for k in added)
def hits(flat,point):
    result=[];x,y=point
    for paint,pts in flat:
        cross=[(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]) for a,b in zip(pts,pts[1:]+pts[:1])]
        if min(cross)>=-1e-6:result.append(paint)
    return result
checks=[]
for name,p,chunk in [('Motor Pool',(-1100.25,-760.5),'motor'),('Workshop',(1200.25,400.5),'workshop'),('Logistics',(-50.25,180.5),'logistics')]:
    _,slab=faces(root/'Assets/models/maps/forestbase'/(chunk+'.obj'))
    before=hits(oldflat,p)+hits(slab,p);after=hits(newflat,p)+hits(slab,p)
    assert sorted(before)==['asphalt','concrete'],(name,before)
    assert after==['concrete'],(name,after)
    checks.append(dict(name=name,point=p,before=before,after=after))
assert hits(newflat,(10.25,-800.5))==['asphalt']
report=dict(trianglesBefore=sum(old.values()),trianglesAfter=triangles,removedTriangles=sum(removed.values()),addedTriangles=sum(added.values()),changedOnlyAsphaltTop=True,physicsAndImportUnchanged=True,materialSlotsUnchanged=True,boxes=len(models['ground'].boxes),hulls=len(models['ground'].hulls),overlapChecks=checks)
(out/'audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
