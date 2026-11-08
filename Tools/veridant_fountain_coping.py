"""Fitted stone coping for the forecourt fountain's open basin wall."""
import math
import numpy as np

def build_into(m):
    profile=[(83.8,14),(83.8,20.6),(84.6,22),(90.6,22),(92,20.6),(92,18.8),(90,18.8),(90,20),(83.8,14)]
    # Separate masonry pieces leave narrow radial joints rather than a seamless torus.
    for sector in range(32):
        a=sector*math.tau/32+.0015
        b=(sector+1)*math.tau/32-.0015
        def point(r,z,t): return np.array((1600+r*math.cos(t),150+r*math.sin(t),z))
        for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
            for t0,t1 in zip(np.linspace(a,b,5),np.linspace(a,b,5)[1:]):
                pts=[point(r,z,t) for r,z,t in ((r0,z0,t0),(r0,z0,t1),(r1,z1,t1),(r1,z1,t0))]
                n=np.array((-(z1-z0)*math.cos((t0+t1)/2),-(z1-z0)*math.sin((t0+t1)/2),r1-r0));n/=np.linalg.norm(n)
                m.polygon('vr_stone_dark',pts[::-1],normal=n)
        for t,sign in ((a,-1),(b,1)):
            # End faces are triangulated in profile order by map_kit.
            m.polygon('vr_stone_dark',[point(r,z,t) for r,z in profile[:-1]],normal=np.array((-math.sin(t)*sign,math.cos(t)*sign,0)))
