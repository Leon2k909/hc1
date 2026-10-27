import sys,json,collections,hashlib
from pathlib import Path
root=Path("C:/Users/mimi-/Documents/S&box Projects/hc1")
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import map_kit as K
stage=Path("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/corridor-lighting-stage-20261021")
models=F.build(visual_chunks=['barracks','command'])

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
report={}
for name in ('barracks','command'):
    out=stage/(name+'.obj')
    count=K.write_obj(out,models[name],name)
    before=triangles(root/'Assets/models/maps/forestbase'/(name+'.obj'));after=triangles(out)
    removed=before-after;added=after-before
    assert not removed,(name,'Removed existing triangles',sum(removed.values()))
    assert set(k[0] for k in added).issubset({'steel','lamp'})
    assert (root/'Assets/models/maps/forestbase'/(name+'.mtl')).read_bytes()==out.with_suffix('.mtl').read_bytes()
    report[name]={'trianglesBefore':sum(before.values()),'trianglesAfter':sum(after.values()),'removed':sum(removed.values()),'addedByMaterial':dict(collections.Counter({p:sum(v for k,v in added.items() if k[0]==p) for p in set(k[0] for k in added)})),'collisionBoxes':len(models[name].boxes),'collisionHulls':len(models[name].hulls)}
lights=[F.scene_light(i,*light) for i,light in enumerate(F.LIGHTS) if ' corridor ' in light[0]]
(stage/'lights.json').write_text(json.dumps(lights,indent=2))
report['lights']=lights
(stage/'geometry-audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
