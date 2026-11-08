from pathlib import Path
import sys, re, collections
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K, veridant_map as V, veridant_parts as P
OUT=Path(__file__).parent
m=K.Model();P.stone_stair(m,(-134,260),(-134,447),100,0,128,sides=(True,False),name='reception stair');V.configure(m);K.write_obj(OUT/'expected.obj',m,'veridant_buildings')
def keys(path):
    vs=[];mat='';result=[]
    for l in path.read_text().splitlines():
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):result.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return result
parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl'
source=re.search(r'filename = "([^"]+)"',parent.read_text().split('RenderMeshList',1)[1]).group(1)
live=collections.Counter(keys(ROOT/'Assets'/source));expected=collections.Counter(keys(OUT/'expected.obj'))
print({'source':source,'expected':sum(expected.values()),'missing':list((expected-live).elements())[:8],'missing_count':sum((expected-live).values())})
