import sys,json,collections,re,hashlib
from pathlib import Path
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');sys.path.insert(0,str(r/'Tools'))
import forestbase_map as F
import forestbase_truck as T
import map_kit as K
out=Path(__file__).parent
if '--geometry' not in sys.argv:T.materials(out/'materials')
print('Truck PBR materials prepared',flush=True)
placements={'motor':[(-1261.6,-555,90),(-901.6,-555,90)],'workshop':[(1020,560,90)],'yard':[(-1360,-840,-20)]}
def parse(path):
    verts=[];uv=[];norm=[];group=None;records=[];counts=collections.Counter()
    for line in path.read_text().splitlines():
        if line.startswith('v '):verts.append(tuple(round(float(x),5) for x in line.split()[1:]))
        elif line.startswith('vt '):uv.append(tuple(round(float(x),5) for x in line.split()[1:]))
        elif line.startswith('vn '):norm.append(tuple(round(float(x),5) for x in line.split()[1:]))
        elif line.startswith('usemtl '):group=line.split()[1]
        if line.startswith('f '):
            points=[]
            for v in line.split()[1:]:
                a,b,c=map(int,v.split('/'));points.append((verts[a-1],uv[b-1],norm[c-1]))
            key=(group,tuple(sorted(points)));counts[key]+=1;records.append((line,key))
        else:records.append((line,None))
    return records,counts,(len(verts),len(uv),len(norm))
report={}
for name,positions in placements.items():
    old=F.model();refine=T.refine;T.refine=lambda *args:None
    try:
        for e,n,a in positions:F.truck(old,e,n,a)
    finally:T.refine=refine
    K.write_obj(out/(name+'-old-trucks.obj'),old,name)
    new=F.model()
    for e,n,a in positions:F.truck(new,e,n,a)
    count=K.write_obj(out/(name+'-new-trucks.obj'),new,name)
    _,remove,_=parse(out/(name+'-old-trucks.obj'))
    records,base,offsets=parse(out/(name+'.before.obj'))
    assert not (remove-base),f'{name}: old geometry does not match installed model'
    original_remove=remove.copy();lines=[];removed=0
    for line,key in records:
        if key and remove[key]>0:remove[key]-=1;removed+=1
        else:lines.append(line)
    assert not +remove
    lines.append('o reference_transport_trucks')
    for line in (out/(name+'-new-trucks.obj')).read_text().splitlines():
        if line.startswith(('mtllib ','o ','#')):continue
        if line.startswith('f '):
            refs=[]
            for v in line.split()[1:]:refs.append('/'.join(str(int(x)+o) for x,o in zip(v.split('/'),offsets)))
            line='f '+' '.join(refs)
        lines.append(line)
    target=out/(name+'.obj');target.write_text('\n'.join(lines)+'\n')
    _,result,_=parse(target);_,added,_=parse(out/(name+'-new-trucks.obj'))
    assert result==base-original_remove+added,'Non-truck geometry changed'
    source=(out/(name+'.before.vmdl')).read_text();match=re.search(r'(remaps\s*=\s*\[)(.*?)(\]\s*use_global_default)',source,re.S)
    entries=',\n'.join('                            { from = "'+p+'.vmat" to = "'+new.material_overrides[p]+'" }' for p in sorted(new.polygons))
    updated=source[:match.start(2)]+match.group(2).rstrip()+',\n'+entries+'\n                        '+source[match.end(2):]
    marker='_class = "PhysicsShapeList"';assert updated[updated.index(marker):]==source[source.index(marker):]
    (out/(name+'.vmdl')).write_text(updated)
    mtl=(out/(name+'.before.mtl')).read_text()
    for p in sorted(new.polygons):mtl+=f'newmtl {p}\nKd 1 1 1\nd 1\n'
    (out/(name+'.mtl')).write_text(mtl)
    report[name]={'trucks':len(positions),'trianglesBefore':sum(base.values()),'removedTruckTriangles':removed,'newTruckTriangles':count,
                  'trianglesAfter':sum(result.values()),'allOtherFacesUnchanged':True,'physicsUnchanged':True,
                  'inputHash':hashlib.sha256((out/(name+'.before.obj')).read_bytes()).hexdigest()}
    print(name,report[name],flush=True)
m=F.model();F.truck(m,0,0)
K.write_obj(out/'truck.obj',m,'truck')
(out/'material-map.json').write_text(json.dumps(m.material_overrides,indent=2))
(out/'audit.json').write_text(json.dumps(report,indent=2));print('STAGE COMPLETE',flush=True)
