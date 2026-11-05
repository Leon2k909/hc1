import numpy as np
import riverside_map as R
import riverdale_parts as P

def placements():
    out=[]
    for bases,height,facing,indices in ((R.POLES_WEST,430,(1,.1),(1,3)),(R.POLES_EAST,400,(-1,0),(0,))):
        f=P.unit((*facing,0));side=np.cross(P.UP,f)
        for i in indices:
            b=np.array(bases[i],float)
            if len(b)==2:b=np.r_[b,0.]
            centre=b+P.UP*(height-80)-f*12
            primary=b+P.UP*(height-6.7)+f*5-side*43.2
            out.append(dict(base=b,height=height,facing=f,centre=centre,primary=primary))
    return out
