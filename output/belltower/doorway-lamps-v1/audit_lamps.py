import sys,json
from pathlib import Path
import numpy as np
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'Tools'))
import belltower_map as B
import map_kit as K
lamps=[]
original=B.wall_lantern
def record(model,wall,r,z_top,**kw):
    result=original(model,wall,r,z_top,**kw)
    if result:
        d,sign,out=B.wall_out(wall)
        lamps.append([float(x) for x in wall.point(r,d+sign*13,z_top-10)])
    return result
B.wall_lantern=record
m=K.Model()
B.west_houses(m,np.random.default_rng(2024))
posts=[(-1450,1122),(-760,1122),(-330,1122),(-1600,-80),(-940,-80),(-1450,330),(-850,330),(-420,520),(-420,-150),*[(-1870,n) for n in (-800,-350,450,1000,1550)]]
rows=[]
for p in posts:
    nearby=sorted(lamps,key=lambda v:np.linalg.norm(np.array(v[:2])-p))[:2]
    rows.append({'post':p,'nearby_wall_lanterns':nearby,'distance_inches':[round(float(np.linalg.norm(np.array(v[:2])-p)),1) for v in nearby]})
print(json.dumps(rows,indent=2))
