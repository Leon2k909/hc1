"""Constructed wall fixture for the reception entrance; light settings stay in P.wall_washer."""
import numpy as np
import map_kit as K

def point(u,d,z):return np.array((170+u,200-d,108+z),float)

def quad(m,paint,coords,normal):
    q=[point(*p) for p in coords];n=np.array(normal,float)
    if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),n)<0:q.reverse()
    m.polygon(paint,q,normal=n)

def outline(w,h,r):
    return [(-w/2+r,-h/2),(w/2-r,-h/2),(w/2,-h/2+r),(w/2,h/2-r),(w/2-r,h/2),(-w/2+r,h/2),(-w/2,h/2-r),(-w/2,-h/2+r)]

def build_into(m):
    outer=outline(11,6.5,.35);front=outline(10.6,6.1,.3);inner=outline(9,4.5,.14)
    for i,a in enumerate(outer):
        j=(i+1)%8;b=outer[j];fa,fb=front[i],front[j];ia,ib=inner[i],inner[j]
        normal=np.array((b[1]-a[1],0,a[0]-b[0]));normal/=np.linalg.norm(normal)
        quad(m,'vr_steel',[(a[0],.12,a[1]),(b[0],.12,b[1]),(b[0],1.5,b[1]),(a[0],1.5,a[1])],normal)
        bevel=normal+np.array((0,-1,0));bevel/=np.linalg.norm(bevel)
        quad(m,'vr_steel',[(a[0],1.5,a[1]),(b[0],1.5,b[1]),(fb[0],1.72,fb[1]),(fa[0],1.72,fa[1])],bevel)
        quad(m,'vr_steel',[(fa[0],1.72,fa[1]),(fb[0],1.72,fb[1]),(ib[0],1.72,ib[1]),(ia[0],1.72,ia[1])],(0,-1,0))
        quad(m,'vr_dark',[(ia[0],1.72,ia[1]),(ib[0],1.72,ib[1]),(ib[0],.72,ib[1]),(ia[0],.72,ia[1])],-normal)
    # Existing emissive material, recessed behind the front rim.
    m.polygon('vr_lamp',[point(u,.73,z) for u,z in inner],normal=np.array((0,-1,0)))
    # Slim weather lip and a separate gasket against the masonry.
    m.box((164.6,198.05,110.97),(175.4,199.85,111.22),'vr_steel')
    for u in (-5.02,5.02):
        for z in (-2.5,2.5):
            # Hexagonal captive fasteners, dark centres rather than decorative bright dots.
            ring=[(u+.14*np.cos(t),z+.14*np.sin(t)) for t in np.linspace(0,2*np.pi,6,endpoint=False)]
            m.polygon('vr_brass',[point(a,1.74,b) for a,b in ring],normal=np.array((0,-1,0)))
            quad(m,'vr_dark',[(u-.075,1.75,z-.018),(u+.075,1.75,z-.018),(u+.075,1.75,z+.018),(u-.075,1.75,z+.018)],(0,-1,0))
