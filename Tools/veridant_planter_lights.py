"""Recessed louvred face housings for the two courtyard planter lights."""
import numpy as np

def build_one(m,n):
    def p(u,d,z):return np.array((316+d,n+u,12+z))
    def quad(coords,normal):
        pts=[p(*x) for x in coords];no=np.array(normal,float)
        if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),no)<0:pts.reverse()
        m.polygon('vr_steel',pts,normal=no)
    outer=[(-4.7,-2.7),(4.7,-2.7),(4.7,2.7),(-4.7,2.7)]
    bevel=[(-4.45,-2.45),(4.45,-2.45),(4.45,2.45),(-4.45,2.45)]
    inner=[(-3.4,-1.3),(3.4,-1.3),(3.4,1.3),(-3.4,1.3)]
    for i,a in enumerate(outer):
        j=(i+1)%4;b=outer[j];fa,fb=bevel[i],bevel[j];ia,ib=inner[i],inner[j]
        # Normal components here are plan E,N,Z; local u runs north.
        normal=np.array((0,b[1]-a[1],a[0]-b[0]),float);normal/=np.linalg.norm(normal)
        quad([(a[0],.15,a[1]),(b[0],.15,b[1]),(b[0],1.05,b[1]),(a[0],1.05,a[1])],normal)
        bn=normal+np.array((1,0,0));bn/=np.linalg.norm(bn)
        quad([(a[0],1.05,a[1]),(b[0],1.05,b[1]),(fb[0],1.3,fb[1]),(fa[0],1.3,fa[1])],bn)
        quad([(fa[0],1.3,fa[1]),(fb[0],1.3,fb[1]),(ib[0],1.3,ib[1]),(ia[0],1.3,ia[1])],(1,0,0))
        quad([(ia[0],1.3,ia[1]),(ib[0],1.3,ib[1]),(ib[0],.36,ib[1]),(ia[0],.36,ia[1])],-normal)
    # Two projecting blades: sloped tops shade the lens from above.
    for z in (-.45,.45):
        profile=[(.4,z+.18),(1.35,z-.12),(1.35,z-.27),(.4,z+.03)]
        for i,(d0,z0) in enumerate(profile):
            d1,z1=profile[(i+1)%4];normal=np.array((z1-z0,0,d0-d1));normal/=np.linalg.norm(normal)
            quad([(-3.4,d0,z0),(3.4,d0,z0),(3.4,d1,z1),(-3.4,d1,z1)],normal)

def build_into(m):
    for n in (220,258):build_one(m,n)
