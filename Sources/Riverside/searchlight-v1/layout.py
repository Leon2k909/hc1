import numpy as np
import riverdale_parts as P
import riverside_map as R

def placement():
    b=np.asarray(R.TOWER[0],float);f=P.unit((*R.TOWER[1],0))
    sl=b+P.UP*572+f*52;head=sl+P.UP*6
    axis=P.unit(np.asarray(R.SEARCH_TARGET,float)-head)
    return sl,head,axis

def original(m,sl,head,a,lens=True):
    P.cylinder(m,sl,2.5,sl[2]-10,sl[2],'rs_steel',8)
    P.rod(m,sl+P.UP*2,head,1.5,'rs_steel',6)
    P.rod(m,head-a*8,head+a*10,9,'rs_dark',12,caps=True)
    if lens:
        import math
        side,up=P.perp(a)
        P.card(m,'rs_lamp_search',[head+a*10.2+(side*math.cos(2*math.pi*k/12)+up*math.sin(2*math.pi*k/12))*8 for k in range(12)],a)
