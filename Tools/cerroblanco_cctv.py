import numpy as np
import map_kit as K
import riverdale_camera as C
import riverdale_parts as P
def build_into(m,at,direction):
    out=P.unit((direction[0],direction[1],0));anchor=np.array(at,dtype=float)
    class Face:
        def __init__(self):self.out=out;self.a=np.cross((0,0,1),out)
        def p(self,s,z,depth=0):return anchor+self.a*s+np.array((0,0,z))+out*depth
    end=anchor+out*10;target=end+P.unit(out*.85-np.array((0,0,.5)))*100
    detail=K.Model();fine=K.Model();C.camera(detail,fine,Face(),0,0,target)
    m.extend(detail).extend(fine)
