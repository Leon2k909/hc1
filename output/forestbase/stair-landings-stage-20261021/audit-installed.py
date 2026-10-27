import sys,json,collections
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
stage=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/stair-landings-stage-20261021")
before=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/stair-landings-before-20261021")
def triangles(path):
    vertices=[];uv=[];normals=[];paint='';result=collections.Counter()
    for line in path.read_text().splitlines():
        vals=line.split()
        if not vals:continue
        if vals[0]=='v':vertices.append(tuple(vals[1:]))
        elif vals[0]=='vt':uv.append(tuple(vals[1:]))
        elif vals[0]=='vn':normals.append(tuple(vals[1:]))
        elif vals[0]=='usemtl':paint=vals[1]
        elif vals[0]=='f':
            corners=[]
            for item in vals[1:]:
                a,b,c=map(int,item.split('/'));corners.append((vertices[a-1],uv[b-1],normals[c-1]))
            result[(paint,tuple(corners))]+=1
    return result
report=json.loads((stage/'geometry-audit.json').read_text())
for name,x1,y0,y1 in [('barracks',-610,635,1065),('command',575,705,1135)]:
    old=triangles(before/'Assets/models/maps/forestbase'/(name+'.obj'));new=triangles(root/'Assets/models/maps/forestbase'/(name+'.obj'))
    for delta in (old-new,new-old):
        for (paint,corners),count in delta.items():
            for position,uv,normal in corners:
                ox,oy,oz=map(float,position);e,n,z=-ox,oz,oy
                assert x1-138-58<=e<=x1+.01 and y0-2<=n<=y1+2 and 87<=z<=284,(name,paint,e,n,z)
    report[name].update(trianglesBefore=sum(old.values()),trianglesAfter=sum(new.values()),changedOnlyInsideStairwell=True)
(stage/'geometry-audit.json').write_text(json.dumps(report,indent=2))
layout=json.loads((stage/'layout.json').read_text())
for name in ('barracks','command'):
    layout['stats'][name]['triangles']=report[name]['trianglesAfter']
    layout['stats'][name]['boxes']=report[name]['boxesAfter']
(stage/'layout.json').write_text(json.dumps(layout,indent=2))
print(json.dumps(report,indent=2))
