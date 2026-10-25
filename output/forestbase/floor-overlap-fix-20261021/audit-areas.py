import json,collections
from pathlib import Path
out=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/floor-overlap-fix-20261021")
reader=(out/'stage.py').read_text();reader=reader[reader.index('def faces(path):'):reader.index("old,oldflat=faces(")]
exec(reader)
_,flat=faces(out/'ground.obj')
triangles=[p for paint,p in flat if paint=='asphalt']
def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>2 else 0
def clipped(poly,axis,bound,above):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=(a[axis]>=bound) if above else (a[axis]<=bound);ib=(b[axis]>=bound) if above else (b[axis]<=bound)
        if ia:result.append(a)
        if ia!=ib:
            t=(bound-a[axis])/(b[axis]-a[axis]);result.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
    return result
rects=[('Motor Pool',(-1440,-778,-680,-340)),('Workshop',(750,212,1450,820)),('Logistics',(-375,-15,335,370))]
results=[]
for name,(x0,y0,x1,y1) in rects:
    overlap=0
    for tri in triangles:
        poly=[p[:2] for p in tri]
        for axis,bound,above in [(0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)]:
            if poly:poly=clipped(poly,axis,bound,above)
        overlap+=area(poly)
    assert overlap<1e-6,(name,overlap)
    results.append(dict(name=name,overlapAreaAfter=overlap,overlapAreaBefore=(x1-x0)*(y1-y0)))
visible=sum(area([p[:2] for p in tri]) for tri in triangles)
covered=sum(r['overlapAreaBefore'] for r in results)
assert abs(visible+covered-3100*2900)<1e-6
report=dict(footprints=results,visibleAsphaltArea=visible,concreteArea=covered,totalGroundArea=3100*2900,coverageComplete=True)
(out/'area-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
