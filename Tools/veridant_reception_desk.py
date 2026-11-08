"""Reception counter with rounded limestone top and vertical walnut flutes."""
import math
import numpy as np
import map_kit as K

def face(m,paint,points,normal):
    pts=[np.array(p,float) for p in points]
    normal=np.array(normal,float)
    if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0: pts.reverse()
    m.polygon(paint,pts,normal=normal)

def outline(e0,e1,n0,n1,r,segments=12):
    pts=[]
    for e,n,start in ((e1-r,n1-r,0),(e0+r,n1-r,90),(e0+r,n0+r,180),(e1-r,n0+r,270)):
        for a in np.linspace(start,start+90,segments+1):
            t=math.radians(a);pts.append((e+r*math.cos(t),n+r*math.sin(t)))
    return pts

def slab(m,paint,bounds,z0,z1,r=4,bevel=.25):
    e0,e1,n0,n1=bounds
    outer=outline(e0,e1,n0,n1,r)
    inset=outline(e0+bevel,e1-bevel,n0+bevel,n1-bevel,r-bevel)
    for i,a in enumerate(outer):
        j=(i+1)%len(outer);b=outer[j]
        normal=np.array((b[1]-a[1],a[0]-b[0],0));normal/=np.linalg.norm(normal)
        face(m,paint,[(a[0],a[1],z0+bevel),(b[0],b[1],z0+bevel),(b[0],b[1],z1-bevel),(a[0],a[1],z1-bevel)],normal)
        for z,zz,sg in ((z0,z0+bevel,-1),(z1,z1-bevel,1)):
            ai,bi=inset[i],inset[j]
            norm=np.array((normal[0],normal[1],sg),float);norm/=np.linalg.norm(norm)
            face(m,paint,[(a[0],a[1],zz),(b[0],b[1],zz),(bi[0],bi[1],z),(ai[0],ai[1],z)],norm)
    for z,sg in ((z0,-1),(z1,1)):
        centre=((e0+e1)/2,(n0+n1)/2,z)
        for i,a in enumerate(inset):
            b=inset[(i+1)%len(inset)]
            face(m,paint,[centre,(a[0],a[1],z),(b[0],b[1],z)],(0,0,sg))

def build_into(m,collide=True):
    m.material_overrides['vr_table_honed']='materials/veridant/table-v2/honed.vmat'
    m.tile_overrides['vr_table_honed']=192
    # Same countertop footprint and 42-inch height as the original desk.
    slab(m,'vr_table_honed',(28,172,418,452),40,42,4,.28)
    slab(m,'vr_timber_dark',(30,170,420,450),5,39.5,3,.18)
    m.box((34,424,0),(166,446,5),'vr_dark')
    # Individual half-round hardwood battens, with physically open shadow grooves.
    for e in np.linspace(34,166,61):
        q=[(e+.82*math.cos(a),420+.82*math.sin(a)) for a in np.linspace(math.pi,2*math.pi,9)]
        for a,b in zip(q,q[1:]):
            normal=np.array(((a[0]+b[0])/2-e,(a[1]+b[1])/2-420,0));normal/=np.linalg.norm(normal)
            face(m,'vr_timber',[(a[0],a[1],6),(b[0],b[1],6),(b[0],b[1],38.5),(a[0],a[1],38.5)],normal)
        for z,sg in ((6,-1),(38.5,1)):
            face(m,'vr_timber',[(a,b,z) for a,b in q],(0,0,sg))
    # Rear working face: real drawer/door reveals and restrained metal pulls.
    for e0,e1 in ((34,76.5),(78,120.5),(122,166)):
        m.box((e0,450,7),(e1,450.25,36),'vr_timber_dark')
        m.box((e1-4,450.25,25),(e1-2.8,450.8,29),'vr_brass')
    if collide:
        m.collision_box((30,420,0),(170,450,40),'default')
