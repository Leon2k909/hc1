import numpy as np
import map_kit as K
import riverdale_camera as C
import riverdale_parts as P
def build():
    m=K.Model();fine=K.Model();at=np.array((-1126.,-160.,200.));out=P.unit((-1,-1,0))
    class Face:
        def __init__(self):self.out=out;self.a=np.cross((0,0,1),out)
        def p(self,s,z,depth=0):return at+self.a*s+np.array((0,0,z))+out*depth
    end=at+out*10;target=end+P.unit(out*.85-np.array((0,0,.5)))*100
    C.camera(m,fine,Face(),0,0,target);m.extend(fine);return m
