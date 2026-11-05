"""Render-only axial extractor tops for Spillway's existing rooftop ventilation units."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P

MATS={'srf_shell':'materials/spillway/roof-fans-v1/shell.vmat',
      'srf_blade':'materials/spillway/roof-fans-v1/blade.vmat',
      'srf_guard':'materials/spillway/roof-fans-v1/guard.vmat',
      'srf_dark':'materials/spillway/roof-fans-v1/dark.vmat'}
PLACEMENTS={'spillway_west':[((e,440,711),43) for e in (-2190,-1940,-1690)],
            'spillway_east':[((e,n,1081),42) for e in (1820,2150) for n in (145,255)]}

def ring(m,c,major,minor,paint='srf_guard',axis=(0,0,1),segments=64):
    P.torus(m,c,axis,major,minor,paint,seg=segments,sides=6)

def bolt(m,c):
    ring(m,c,.85,.13,'srf_blade',segments=12)
    P.lathe_axis(m,c,(0,0,1),[(.58,0),(.64,.12),(.64,.57),(.49,.68)],'srf_blade',6,cap='srf_blade',turn=math.pi/6)

def blade(m,centre,radius,angle):
    e,n,z=centre;nr,nc=10,5
    points=np.zeros((nr+1,nc+1,3))
    for i in range(nr+1):
        t=i/nr;r=9+(radius-14)*t;a=angle+.42*t+.04*math.sin(math.pi*t)
        chord=4.5+6.2*math.sin(math.pi*(t*.72+.08))
        for j in range(nc+1):
            u=j/nc-.5
            points[i,j]=(e+r*math.cos(a)-u*chord*math.sin(a),n+r*math.sin(a)+u*chord*math.cos(a),z+4.6+u*(5.5-2.6*t)+.55*math.sin(math.pi*t))
    normals=np.zeros_like(points)
    for i in range(nr+1):
        for j in range(nc+1):
            normal=np.cross(points[min(i+1,nr),j]-points[max(i-1,0),j],points[i,min(j+1,nc)]-points[i,max(j-1,0)])
            normals[i,j]=normal/np.linalg.norm(normal)
    for i in range(nr):
        for j in range(nc):
            ids=((i,j),(i+1,j),(i+1,j+1),(i,j+1));p=[points[a,b] for a,b in ids];ns=[normals[a,b] for a,b in ids]
            P.card(m,'srf_blade',p,(0,0,1),normals=ns)
            P.card(m,'srf_blade',[v-(0,0,.3) for v in p],(0,0,-1),normals=[-v for v in ns])
    outline=[points[0,j] for j in range(nc+1)]+[points[i,nc] for i in range(1,nr+1)]+[points[nr,j] for j in range(nc-1,-1,-1)]+[points[i,0] for i in range(nr-1,0,-1)]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        P.card(m,'srf_blade',[a,b,b-(0,0,.3),a-(0,0,.3)],np.cross(b-a,(0,0,-1)))

def build(m,centre=(0,0,0),radius=43):
    e,n,z=centre;c=np.asarray(centre,float)
    # Folded mounting flange, short barrel, rolled throat, and dark interior.
    profile=[(radius+4,0),(radius+4,1.2),(radius+3.4,1.65),(radius+1.3,1.65),
      (radius+.7,2.1),(radius+.7,7.3),(radius+.45,8.25),(radius-.35,8.8),
      (radius-1.35,8.8),(radius-2.05,8.25),(radius-2.2,7.3),(radius-2.2,1.4)]
    P.lathe_axis(m,c,(0,0,1),profile,'srf_shell',64)
    P.cylinder(m,(e,n),radius-2.2,z+.12,z+.3,'srf_dark',64,top='srf_dark')
    # Seven separately pitched, swept, thick blades around a spun motor boss.
    for k in range(7):blade(m,centre,radius,k*2*math.pi/7)
    P.lathe_axis(m,c,(0,0,1),[(8.7,1),(8.7,5.8),(8.3,7.1),(7.4,8.3),(5.2,8.9),(2.1,9.1)],'srf_shell',48,cap='srf_shell')
    P.lathe_axis(m,c+(0,0,9.13),(0,0,1),[(1,0),(1,.45),(.8,.65)],'srf_blade',6,cap='srf_blade')
    for k in range(8):
        a=k*math.pi/4;bolt(m,(e+(radius+2.65)*math.cos(a),n+(radius+2.65)*math.sin(a),z+1.7))
    # A welded, shallow domed safety cage; actual open gaps reveal the rotor.
    guard_r=radius-1.5
    height=lambda r:z+9.8+4.8*(1-(r/guard_r)**2)
    for r in np.linspace(5,guard_r,10):ring(m,(e,n,height(r)),r,.22)
    for k in range(24):
        a=k*math.pi/12;rs=np.linspace(0,guard_r,8)
        points=[(e+r*math.cos(a),n+r*math.sin(a),height(r)) for r in rs]
        for p,q in zip(points,points[1:]):P.rod(m,p,q,.23,'srf_guard',6)
    ring(m,(e,n,z+9.8),guard_r,.44,segments=64)
    # Four cage attachment clamps, plus two lifting eyes on the barrel.
    for k in range(4):
        a=k*math.pi/2;x=np.array((math.cos(a),math.sin(a),0));y=np.array((-math.sin(a),math.cos(a),0));up=np.array((0,0,1))
        P.bevel_box(m,c+x*(radius-1.3)+(0,0,9.1),(x,y,up),(3.0,2.6,.5),'srf_shell',.18)
        bolt(m,c+x*(radius-.65)+(0,0,9.36))
    for s in (-1,1):
        P.bevel_box(m,c+(s*(radius+.9),0,4.7),((1,0,0),(0,1,0),(0,0,1)),(1.3,4.2,2.5),'srf_shell',.22)
        ring(m,c+(s*(radius+1.2),0,6),1.55,.38,'srf_shell',axis=(1,0,0),segments=20)
    m.material_overrides.update(MATS);m.tile_overrides.update({p:48. for p in MATS})
    return m

def original(m,centre=(0,0,0),radius=43):
    """Frozen original fan for exact comparisons, including after installation."""
    e,n,z=centre
    P.lathe(m,(e,n),[(radius+4,z),(radius+4,z+3),(radius,z+6),(radius-2,z+6)],'rv_steel',32)
    P.cylinder(m,(e,n),radius-2,z+.2,z+1,'rv_dark',32)
    for j in range(5):
        a=j*2*math.pi/5
        points=[P.v(e+math.cos(a+off)*r,n+math.sin(a+off)*r,z+2+dz) for r,off,dz in ((7,-.12,0),(radius-4,.15,1),(radius-5,.52,1),(10,.24,0))]
        P.card(m,'rv_steel',points,P.UP)
    P.cylinder(m,(e,n),8,z+1,z+6,'rv_steel',24)
    for rr in (radius*.35,radius*.65,radius*.90):
        points=[P.v(e+math.cos(a)*rr,n+math.sin(a)*rr,z+7) for a in np.linspace(0,2*math.pi,33)]
        for p,q in zip(points[:-1],points[1:]):P.rod(m,p,q,.45,'rv_frame',5)
    for j in range(8):
        a=j*math.pi/4
        P.rod(m,(e,n,z+7),(e+math.cos(a)*(radius-2),n+math.sin(a)*(radius-2),z+7),.5,'rv_frame',5)
    return m
