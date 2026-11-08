"""Slim removable drain covers using the existing Spillway grate material set."""
import math
import numpy as np
import riverdale_parts as P

MATERIALS={f'vr_drain_{n}':f'materials/spillway/trench-grates-v1/{n}.vmat' for n in ('steel','frame','dark','bolt')}
PLACEMENTS=(((380,-150),(700,150)),((300,-60),(520,140)),((-180,130),(60,140)),((560,-300),(740,-120)))

def build_one(m,a,b,z=0,w=5):
    a=np.array((*a,z),float);b=np.array((*b,z),float);d=(b-a)/np.linalg.norm(b-a);length=np.linalg.norm(b-a);side=np.cross(np.array((0.,0.,1.)),d);centre=(a+b)/2
    def pt(u,v,h):return centre+d*u+side*v+np.array((0,0,h))
    def face(paint,coords,normal):
        q=[pt(*p) for p in coords];n=d*normal[0]+side*normal[1]+np.array((0.,0.,normal[2]));n/=np.linalg.norm(n)
        if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),n)<0:q.reverse()
        m.polygon(paint,q,normal=n)
    def bar(u0,u1,v0,v1,z0,z1,paint,bevel=.035):
        bb=min(bevel,(u1-u0)/3,(v1-v0)/3,(z1-z0)/3);lo=z1-bb
        face(paint,[(u0,v0,z0),(u1,v0,z0),(u1,v0,lo),(u0,v0,lo)],(0,-1,0))
        face(paint,[(u0,v1,z0),(u0,v1,lo),(u1,v1,lo),(u1,v1,z0)],(0,1,0))
        face(paint,[(u0,v0,z0),(u0,v0,lo),(u0,v1,lo),(u0,v1,z0)],(-1,0,0))
        face(paint,[(u1,v0,z0),(u1,v1,z0),(u1,v1,lo),(u1,v0,lo)],(1,0,0))
        lower=[(u0,v0,lo),(u1,v0,lo),(u1,v1,lo),(u0,v1,lo)]
        upper=[(u0+bb,v0+bb,z1),(u1-bb,v0+bb,z1),(u1-bb,v1-bb,z1),(u0+bb,v1-bb,z1)]
        for i,n in enumerate(((0,-1,1),(1,0,1),(0,1,1),(-1,0,1))):
            j=(i+1)%4;face(paint,[lower[i],lower[j],upper[j],upper[i]],n)
        face(paint,upper,(0,0,1))
    half=w*.59 # Original steel side strips extend to 1.18 times the central grating width.
    face('vr_drain_dark',[(-length/2,-half,.025),(length/2,-half,.025),(length/2,half,.025),(-length/2,half,.025)],(0,0,1))
    for v0,v1 in ((-half,-half+.5),(half-.5,half)):
        bar(-length/2,length/2,v0,v1,.035,.22,'vr_drain_frame')
    for u0,u1 in ((-length/2,-length/2+.45),(length/2-.45,length/2)):
        bar(u0,u1,-half+.5,half-.5,.035,.22,'vr_drain_frame')
    # A lower central tie is visible through the open slots.
    bar(-length/2+.5,length/2-.5,-.10,.10,.035,.09,'vr_drain_frame',.015)
    count=max(1,math.ceil(length/24));span=(length-1)/count
    for i in range(count):
        lo=-length/2+.5+i*span+.06;hi=-length/2+.5+(i+1)*span-.06
        for u0,u1 in ((lo,lo+.24),(hi-.24,hi)):
            bar(u0,u1,-half+.5,half-.5,.045,.22,'vr_drain_steel')
        slots=max(3,round((hi-lo-.6)/1.3))
        for j in range(slots):
            u=lo+.3+(hi-lo-.6)*(j+.5)/slots
            bar(u-.115,u+.115,-half+.54,half-.54,.045,.22,'vr_drain_steel')
        for u in (lo+.3,hi-.3):
            for vv in (-half+.25,half-.25):
                c=pt(u,vv,.22);P.cylinder(m,(c[0],c[1]),.12,z+.22,z+.245,'vr_drain_bolt',6,top='vr_drain_bolt')
    m.material_overrides.update(MATERIALS)
    for name in MATERIALS:m.tile_overrides[name]=18

def build_into(m):
    for a,b in PLACEMENTS:build_one(m,a,b)
