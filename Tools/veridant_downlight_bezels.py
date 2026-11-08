"""Recessed metal trims around the four existing reception ceiling lenses."""
import math,numpy as np
def build_into(m):
    profile=[(3.25,-.6),(3.55,-1.1),(4.65,-1.1),(5,-.75),(5,-.1),(3.25,-.1),(3.25,-.6)]
    for e,n in ((0,300),(150,300),(150,480),(-40,500)):
        for (r0,z0),(r1,z1) in zip(profile,profile[1:]):
            for a,b in zip(np.linspace(0,2*math.pi,65),np.linspace(0,2*math.pi,65)[1:]):
                pts=[np.array((e+r*math.cos(t),n+r*math.sin(t),112+z)) for r,z,t in ((r0,z0,a),(r0,z0,b),(r1,z1,b),(r1,z1,a))]
                normal=np.array(((z1-z0)*math.cos((a+b)/2),(z1-z0)*math.sin((a+b)/2),r0-r1));normal/=np.linalg.norm(normal)
                m.polygon('vr_steel',pts,normal=normal)
