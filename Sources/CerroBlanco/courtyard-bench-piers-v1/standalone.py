from pathlib import Path
import sys,numpy as np,json
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
from build import build
import map_kit as K
OUT=ROOT/'output/cerroblanco/courtyard-bench-piers-v1'
RESOURCE='models/props/shared/stone_pier_teak_bench_v1'
m=build()
for mat,faces in m.polygons.items():
    for i,(points,normal) in enumerate(faces):
        faces[i]=([p+np.array((250.,800.,0.)) for p in points],normal)
for x in (-29.,29.):m.box((x-6,-9.6,0),(x+6,9.6,17),{},'default')
m.box((-41,-8.8,17.2),(41,8.8,18.6),{},'wood')
triangles=K.write_model(OUT/'stage'/RESOURCE,RESOURCE,'bench',m)
print(json.dumps({'asset':RESOURCE+'/bench.vmdl','triangles':triangles,'origin':'ground centre','collision_boxes':len(m.boxes)}))
