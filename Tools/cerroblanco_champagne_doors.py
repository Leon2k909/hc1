"""Contemporary satin aluminium and frosted glass gallery door."""
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_parts as P
ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/cerroblanco/champagne_doors_v1'
def build():
    m=K.Model()
    def box(c,s,mat,b=.1):P.bevel_box(m,c,np.eye(3),s,mat,bevel=b)
    w=46.65
    for e in (1.4,w-1.4):box((e,0,61.5),(2.8,2.6,121),'metal')
    for z,h in ((2,3),(120,3),(28,2)):
        box((w/2,0,z),(w-5.6,2.6,h),'metal')
    box((w/2,0,15),(w-5.6,1.6,24),'metal')
    box((w/2,0,74),(w-5.6,.5,90),'glass',.02)
    for side in (-1,1):
        for z in (49,69):box((w-5,side*2,z),(1,2,1),'dark')
        box((w-5,side*3.2,59),(1.2,1.2,23),'dark',.3)
    for z in (12,61,110):box((.5,0,z),(1,3.4,4),'metal')
    m.material_overrides.update(metal='materials/cerroblanco/champagne-doors-v1/metal.vmat',glass='materials/cerroblanco/champagne-doors-v1/frosted.vmat',dark='materials/veridant/vr_steel.vmat')
    m.tile_overrides.update({k:96 for k in m.polygons})
    print(K.write_model(ROOT/'output/cerroblanco/champagne-doors-v1/stage'/RESOURCE,RESOURCE,'leaf',m))
if __name__=='__main__':build()
