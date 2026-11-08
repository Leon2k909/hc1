"""Pedestal bar stools for the north terrace; original positions and 12-inch diameter retained."""
import math
import numpy as np
import veridant_parts as P

def build_one(m,centre,z0=128):
    e,n=centre
    def polygon(paint,points,normals):
        pts=[];ns=[]
        for p,no in zip(points,normals):
            if not pts or np.linalg.norm(p-pts[-1])>1e-7:pts.append(p);ns.append(no)
        if len(pts)>2 and np.linalg.norm(pts[0]-pts[-1])<1e-7:pts.pop();ns.pop()
        if len(pts)<3:return
        uv=[((p[0]-e)/24+.35,(p[1]-n)/24+.35) for p in pts] if paint=='vr_timber_dark' else None
        no=sum(ns);no/=np.linalg.norm(no)
        m.polygon(paint,pts,normal=no,normals=ns,uv=uv)
    def lathe(profile,paint,sides):
        rings=[]
        for i,(r,z) in enumerate(profile):
            a=np.array(profile[max(0,i-1)]);b=np.array(profile[min(len(profile)-1,i+1)]);dr,dz=b-a
            local=np.array((dz,-dr));local/=np.linalg.norm(local)
            row=[]
            for angle in np.linspace(0,2*math.pi,sides,endpoint=False):
                p=np.array((e+r*math.cos(angle),n+r*math.sin(angle),z0+z));no=np.array((local[0]*math.cos(angle),local[0]*math.sin(angle),local[1]))
                row.append((p,no))
            rings.append(row)
        for a,b in zip(rings,rings[1:]):
            for i in range(sides):
                j=(i+1)%sides;items=[a[i],a[j],b[j],b[i]];polygon(paint,[x[0] for x in items],[x[1] for x in items])
    lathe([(0,0),(5.55,0),(5.9,.28),(6,.6),(5.8,1.2),(3.5,2.5),(1.15,3.25),(1.05,4),(1.05,26.6),(3.4,26.6),(3.6,26.9),(0,26.9)],'vr_steel',48)
    lathe([(0,26.8),(4.8,26.8),(5.65,26.95),(5.95,27.2),(6,27.5),(5.95,27.85),(5.7,28),(4.9,27.95),(3,27.8),(0,27.72)],'vr_timber_dark',64)
    # A continuous footrest ring with smooth section normals.
    aa=np.linspace(0,2*math.pi,49);bb=np.linspace(0,2*math.pi,9)
    def torus(a,b):
        p=np.array((e+(4.65+.32*math.cos(b))*math.cos(a),n+(4.65+.32*math.cos(b))*math.sin(a),z0+10.5+.32*math.sin(b)))
        no=np.array((math.cos(a)*math.cos(b),math.sin(a)*math.cos(b),math.sin(b)));return p,no
    for a0,a1 in zip(aa,aa[1:]):
        for b0,b1 in zip(bb,bb[1:]):
            items=[torus(a,b) for a,b in ((a0,b0),(a1,b0),(a1,b1),(a0,b1))];polygon('vr_steel',[x[0] for x in items],[x[1] for x in items])
    for a in np.linspace(0,2*math.pi,3,endpoint=False):
        d=np.array((math.cos(a),math.sin(a),0.));c=np.array((e,n,z0+10.5));P.tube(m,[c+d,c+d*4.65],[.25,.25],'vr_steel',sides=12,cap=True)

def build_into(m):
    for e in (90.,140.,190.,240.):build_one(m,(e,690.),128.)
