"""Solid three-panel walnut gallery door, authored at its fitted size."""
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_parts as P
ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/cerroblanco/walnut_doors_v1'
def build():
    m=K.Model()
    def box(c,size,mat,b=.12): P.bevel_box(m,c,np.eye(3),size,mat,bevel=b)
    w=46.65
    for e in (2,w-2): box((e,0,61.5),(4,2.6,121),'wood')
    for z,h in ((3,5),(43,4),(83,4),(120,4)):
        box((w/2,0,z),(w-8,2.6,h),'wood')
    for z,h in ((23,35),(63,35),(101.5,32)):
        box((w/2,0,z),(w-8,1.4,h),'wood')
        for side in (-1,1):
            for e in (5.1,w-5.1): box((e,side*1.0,z),(1.4,.7,h),'wood')
            for zz in (z-h/2+.7,z+h/2-.7): box((w/2,side*1.0,zz),(w-10,.7,1.4),'wood')
    for side in (-1,1):
        box((w-6,side*1.7,57),(2.2,.6,9),'brass')
        box((w-9,side*3,59),(7,1,1.2),'brass',.25)
        box((w/2,side*1.4,5),(w-8,.3,7),'metal')
    for z in (12,61,110):box((.6,0,z),(1.2,3.4,4),'brass',.25)
    m.material_overrides.update(wood='materials/cerroblanco/walnut-doors-v2/walnut.vmat',brass='materials/veridant/vr_brass.vmat',metal='materials/veridant/vr_steel.vmat')
    m.tile_overrides.update({k:48 for k in m.polygons})
    stage=ROOT/'output/cerroblanco/walnut-doors-v1/stage'/RESOURCE
    print(K.write_model(stage,RESOURCE,'leaf',m))
if __name__=='__main__':build()
