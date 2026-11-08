"""Fitted timber slats and a dark plinth for the north terrace bar."""
import numpy as np
from riverdale_parts import box

def build_into(m):
    # Backing and plinth fit under the existing countertop overhang.
    box(m,60,260,711.8,712.05,134,165,'vr_steel')
    box(m,59.5,260.5,711.5,712.1,128.15,134,'vr_steel')
    def slat(e,n,w,side=False):
        # Chamfered front corners keep each piece distinct at grazing angles.
        profile=[(-w/2,0),(-w/2,.85),(-w/2+.22,1.15),(w/2-.22,1.15),(w/2,.85),(w/2,0)]
        def point(u,d,z):return np.array((e-d,n+u,z) if side else (e+u,n-d,z))
        low=[point(u,d,134.3) for u,d in profile];high=[point(u,d,164.8) for u,d in profile]
        for i in range(len(profile)):
            j=(i+1)%len(profile)
            pts=[low[i],low[j],high[j],high[i]]
            # Determine outward normals from each side's edge.
            if side:pts.reverse()
            edge=low[j]-low[i];no=np.cross(edge,np.array((0,0,1.)));no*= -1 if side else 1;no/=np.linalg.norm(no)
            m.polygon('vr_timber_dark',pts,normal=no,uv=[(0,0),(w/24,0),(w/24,30.5/24),(0,30.5/24)])
        m.polygon('vr_timber_dark',high[::-1] if side else high,normal=np.array((0,0,1.)))
        m.polygon('vr_timber_dark',low if side else low[::-1],normal=np.array((0,0,-1.)))
    for e in np.linspace(62.7,257.3,36):slat(e,711.8,4.65)
    # Return cladding on the exposed west end.
    box(m,59.8,60.05,712,740,134,165,'vr_steel')
    box(m,59.5,60.1,712,740,128.15,134,'vr_steel')
    for n in np.linspace(714.7,737.3,5):slat(59.8,n,4.65,True)
