"""Low stone coffee table with an eased slab and recessed pedestal."""
import math
import numpy as np
from riverdale_parts import lathe,card,v,UP

def build_into(m,c=(0,0)):
    # Keep the original 32-inch diameter and 16-inch height.
    lathe(m,c,[(0,0),(10.5,0),(11,.4),(11,1),(10.6,1.4),(9.5,2),(9.5,11.6),(9.8,12),(0,12)],'vr_stone_dark',64)
    lathe(m,c,[(0,12),(9.2,12),(9.2,13.6),(0,13.6)],'vr_steel',64)
    profile=[(0,13.5),(15.4,13.5),(15.8,13.65),(16,14),(16,15.5),(15.85,15.85),(15.5,16)]
    lathe(m,c,profile,'vr_table_honed',96)
    pts=[v(c[0]+15.5*math.cos(a),c[1]+15.5*math.sin(a),16) for a in np.linspace(0,math.tau,96,endpoint=False)]
    card(m,'vr_table_honed',pts,UP,uv=[(.5+(p[0]-c[0])/96,.75+(p[1]-c[1])/96) for p in pts])
    m.material_overrides['vr_table_honed']='materials/veridant/table-v2/honed.vmat'
    m.tile_overrides['vr_table_honed']=96
