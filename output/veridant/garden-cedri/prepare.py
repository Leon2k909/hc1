from pathlib import Path
from collections import Counter
import sys,json,numpy as np
sys.path.insert(0,'Tools')
import veridant_map as V
import map_kit as K
import veridant_parts as P

out=Path('output/veridant/garden-cedri');root=Path.cwd()
old='models/maps/veridant/cedri_olive_trial';new='models/maps/veridant/garden_cedri'
dest=out/'stage'/new;dest.mkdir(parents=True,exist_ok=True)
def parse(lines):
    vertices=[];material='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('v '):vertices.append(tuple(round(float(a),3) for a in line.split()[1:]))
        if line.startswith('usemtl '):material=line.split()[1]
        if line.startswith('f '):faces.append((i,(material,tuple(sorted(vertices[int(a.split('/')[0])-1] for a in line.split()[1:])))))
    return faces

src=Path('Assets',old,'garden_foliage.obj');lines=src.read_text().splitlines(keepends=True)
faces=parse(lines);available=Counter(k for _,k in faces);remove=Counter();placements=[]
g0,g1,n0,n1=V.GARDEN_S;rng=np.random.default_rng(31)
for k in range(28):
    e=rng.uniform(g0+60,g1-60);n=rng.uniform(n0+60,n1-60)
    if -900<n<-800 or -1240<n<-1150 or any(a-20<e<b+20 for a,b in ((-40,20),(560,620),(1240,1300))):continue
    h=rng.uniform(150,230)
    m=K.Model();P.olive(m,(e,n,0),h,seed=300+k,spread=1.2);V.configure(m)
    obj=out/'match.obj';K.write_obj(obj,m,'veridant_foliage')
    target=Counter(key for _,key in parse(obj.read_text().splitlines()))
    matched=target & available
    if not matched and abs(e+555.862305)<.01 and abs(n+785.236206)<.01:continue
    assert matched==target,(k,e,n,sum(matched.values()),sum(target.values()))
    remove+=target;available-=target
    scale=h/(10.876063*39.3700787)
    placements.append((float(n),float(-e),float(scale),float((k*137.508)%360)))
removed=set()
for i,k in faces:
    if remove[k]:removed.add(i);remove[k]-=1
assert not +remove
kept=[l for i,l in enumerate(lines) if i not in removed]
(dest/'garden_foliage.obj').write_text(''.join(kept))
mtl=next(l.split()[1] for l in kept if l.startswith('mtllib '));(dest/mtl).write_bytes((src.parent/mtl).read_bytes())
(dest/'garden_foliage.vmdl').write_text(Path('Assets',old,'garden_foliage.vmdl').read_text().replace(old+'/garden_foliage.obj',new+'/garden_foliage.obj'))
previous=Path('output/veridant/bermuda/import.json');source=Path(json.loads(previous.read_text())['path']);exchange=source.with_name('import-garden-cedri.cs')
exchange.write_text(source.read_text().replace('bermuda/stage','garden-cedri/stage'));(out/'import.json').write_text(json.dumps({'path':str(exchange)}))
(out/'compile.json').write_text(json.dumps({'path':new+'/garden_foliage.vmdl','full':False}))
(out/'placements.json').write_text(json.dumps(placements));print(len(placements),len(removed))
