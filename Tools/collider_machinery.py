"""Layered accelerator hardware and workshop equipment, in Collider plan axes.

Machinery is behind the observation glass. Hall equipment uses the established
cover envelopes, keeping the authored multiplayer paths and sight blockers.
"""
import math
import numpy as np
import boxyard_map as B
import collider_detail_geometry as D
import collider_services as S

UP=np.array((0.,0.,1.))
X=np.array((1.,0.,0.))


def annulus(m,center,axis,inner,outer,width,paint="co_silver",sides=40):
    B.lathe(m,center,axis,[(inner,-width/2),(outer,-width/2),
        (outer,width/2),(inner,width/2),(inner,-width/2)],paint,sides=sides)


def tube(m,a,b,r,paint="co_silver",sides=12):
    a,b=np.asarray(a,float),np.asarray(b,float)
    B.lathe(m,a,b-a,[(r,0),(r,np.linalg.norm(b-a))],paint,sides=sides,cap=paint)


def gauge(m,center,axis,r=10):
    center=np.asarray(center,float);axis=np.asarray(axis,float)
    annulus(m,center,axis,r*.77,r,3,"co_trim",20)
    tube(m,center-axis,center+axis,r*.76,"co_enamel",20)
    side=np.cross(UP,axis)
    D.beam(m,center+axis*1.2,center+axis*1.2+(side*.55+UP*.4)*r,(.7,.7),"co_rubber",.1)


def accelerator(m,monitor):
    n,z=1260.,540.
    tube(m,(-1860,n,z),(1860,n,z),24,"co_beam",48)
    # Alternating large cryostats and shorter diagnostic collars give the beam
    # a readable hierarchy. Rounded shoulders replace rows of rectangular magnets.
    for index,e in enumerate(range(-1650,1651,275)):
        large=index%4==2
        r=112 if large else 78
        length=212 if large else 182
        half=length/2
        profile=[(30,-half),(r*.72,-half),(r*.94,-half+12),(r,-half+29),
                 (r,half-29),(r*.94,half-12),(r*.72,half),(30,half)]
        B.lathe(m,(e,n,z),X,profile,"co_silver" if large else "co_steel",sides=48)
        for off in (-half+12,half-12):
            annulus(m,(e+off,n,z),X,r*.73,r+5,9,"co_trim",48)
            for k in range(12):
                a=k*math.tau/12
                at=np.array((e+off,n+math.cos(a)*(r-6),z+math.sin(a)*(r-6)))
                D.bolt(m,at-X*6,-X,2.4,3,"co_silver")
        for off in (-half-8,half+8):
            annulus(m,(e+off,n,z),X,25,r*.67,8,"co_silver",48)
            annulus(m,(e+off,n,z),X,27,37,10,"co_beam",40)
        # Ribbed bellows and compression bands connect each cryostat to the next.
        bellows=[]
        for t in range(13):bellows.append((39 if t%2 else 33,half+16+t*4.2))
        B.lathe(m,(e,n,z),X,bellows,"co_trim",sides=32)
        for k in range(6):
            a=k*math.tau/6+.18
            radial=np.array((0,math.cos(a),math.sin(a)))
            tube(m,np.array((e-half+28,n,z))+radial*(r+6),
                 np.array((e+half-28,n,z))+radial*(r+6),3.2,"co_silver",10)
        if large:
            for off in (-34,-18,-2,14,30):
                annulus(m,(e+off,n,z),X,r+1,r+11,8,"co_copper",48)
        # Paired bent vacuum lines, gauge and a compact instrument screen.
        for off in (-44,44):
            S.pipe_run(m,[(e+off,n-r*.7,z-r*.5),(e+off,n-r-45,z-r*.5),
                         (e+off,n-r-75,z-126),(e+off,n-r-75,340)],7,"co_silver",12,30)
            S.flange(m,(e+off,n-r-47,z-r*.5),(0,1,0),9)
        gauge(m,(e+44,n-r-83,z-133),(0,-1,0),12)
        if index%3!=0:
            D.plate(m,(e-34,n-r-25,z+33),(e+34,n-r-12,z+88),"co_trim",4)
            monitor(m,(e,n-r-26,z+62),(0,-1),54,34,index%4)
        # Individually sagging insulated leads rise to the overhead service bus.
        for j in range(3):
            S.pipe_run(m,[(e+25+j*10,n-r*.5,z+r*.82),
                (e+53+j*10,n-150-j*8,z+r+66),(e+90+j*10,n-192-j*8,z+220),
                (e+118+j*10,n-185-j*8,z+260)],3.1,
                "co_copper" if j==2 else "co_rubber",8,36)
    # Circumferential cooling circuits sit in front of the structural rings.
    for e in (-1650,-1100,-550,0,550,1100,1650):
        for offset,radius in ((-64,341),(58,325)):
            points=[(e+offset,n+radius*math.cos(a),z+radius*math.sin(a))
                    for a in np.linspace(-.55,math.pi+1.05,35)]
            S.pipe_run(m,points,5.5,"co_copper" if offset<0 else "co_silver",10,0)
        for degrees in (28,64,115,152,205,245):
            a=math.radians(degrees);radial=np.array((0,math.cos(a),math.sin(a)))
            at=np.array((e,n,z))+radial*350
            tube(m,at-X*65,at+X*65,8,"co_trim",12)
            D.bolt(m,at-X*70,-X,5,8,"co_silver")
    # Broad supply lines and their doglegs fill the gaps between ring assemblies.
    for j in range(5):
        S.pipe_run(m,[(-1840,n-255+j*15,830+j*6),(-1120,n-255+j*15,830+j*6),
            (-980,n-220+j*15,875+j*6),(800,n-220+j*15,875+j*6),
            (940,n-270+j*15,820+j*6),(1820,n-270+j*15,820+j*6)],
            4.5 if j%2 else 6.5,"co_copper" if j==1 else "co_silver",12,42)
    for e in (-1430,-610,610,1430):
        # Rounded pressure vessels, feet and manifolds below the beam.
        B.lathe(m,(e,1535,30),UP,[(23,0),(40,16),(48,35),(48,190),(40,215),(17,228)],
                "co_enamel",sides=32,cap="co_silver")
        for zz in (74,197):annulus(m,(e,1535,zz),UP,48,52,8,"co_trim",32)
        for dx in (-32,32):
            D.beam(m,(e+dx,1535,10),(e+dx,1535,73),(8,8),"co_trim",1)
        S.pipe_run(m,[(e,1535,258),(e,1535,292),(e,1455,330),(e,1390,420)],9,"co_silver",16,35)
        gauge(m,(e,1485,178),(0,-1,0),13)


def instrument_cart(m,e,n,z,w,d,h,heading):
    """A rounded pump skid within the same collision envelope as a flight case."""
    f=B.Frame(e,n,heading,z);axes=(f.x,f.y,UP)
    f.box(m,-w/2,w/2,-d/2,d/2,3,h,None,surface="plastic")
    D.bevel_box(m,f.p(0,0,h*.23),axes,(w,d,h*.46),"co_case",3.5)
    for x in (-w/2+4,w/2-4):
        for y in (-d/2+4,d/2-4):
            D.bevel_box(m,f.p(x,y,h*.68),axes,(5,5,h*.64),"co_trim",1.2)
    D.bevel_box(m,f.p(0,0,h-2),axes,(w,d,4),"co_trim",1.2)
    r=min(d*.32,h*.22)
    B.lathe(m,f.p(-w*.35,0,h*.68),f.x,[(r*.7,0),(r,5),(r,w*.58),(r*.7,w*.7)],
            "co_enamel",sides=24,cap="co_silver")
    for x in (-w*.26,w*.26):annulus(m,f.p(x,0,h*.68),f.x,r,r+1.7,4,"co_trim",24)
    gauge(m,f.p(-w*.15,-d/2-.3,h*.66),-f.y,6.5)
    points=[f.p(w*.20+math.cos(a)*10,-d/2+.8,h*.68+math.sin(a)*10)
            for a in np.linspace(0,math.tau,25)]
    S.pipe_run(m,points,2,"co_rubber",8,0)
    for x in (-w*.36,w*.36):
        D.bevel_box(m,f.p(x,-d/2-.4,h*.2),axes,(8,2,4),"co_silver",.7)


def server_face(m,e,n):
    # Recessed fan cartridges and cable glands dress the existing server blocker.
    D.plate(m,(e-24,n-30,0),(e+24,n+30,138),"co_case",3.5)
    for zz in (48,90,122):
        D.plate(m,(e-20,n-31,zz-15),(e+20,n-29,zz+15),"co_trim",1)
        for xx in (-10,10):
            at=np.array((e+xx,n-32.,zz))
            annulus(m,at,(0,-1,0),7,9,2,"co_silver",16)
            tube(m,at,at+(0,-1,0),2.2,"co_trim",10)
            for k in range(5):
                a=k*math.tau/5
                D.beam(m,at,at+np.array((math.cos(a)*6,-1,math.sin(a)*6)),(2,1),"co_trim",.2)
    for x in (-17,-7,3):
        S.pipe_run(m,[(e+x,n+27,125),(e+x,n+28,100),(e+x+3,n+28,55),
                     (e+x+3,n+27,8)],1.4,"co_copper" if x==3 else "co_rubber",8,12)


def column_services(m):
    for e in (-960,960):
        for n in (-500,300):
            for dx in (-20,-10):
                S.pipe_run(m,[(e+dx,n-30,14),(e+dx,n-30,160),(e+dx,n-18,180),
                             (e+dx,n-18,410)],2.5,"co_silver",10,14)
            D.plate(m,(e-31,n-37,74),(e+31,n-31,146),"co_trim",2.5)
            gauge(m,(e-14,n-39,120),(0,-1,0),8)
            for dx in (7,17):
                D.plate(m,(e+dx-2,n-39,102),(e+dx+2,n-37,106),"co_beam" if dx==7 else "co_amber",.3)
            for dx in (-28,28):
                for zz in (80,140):D.bolt(m,(e+dx,n-38,zz),(0,-1,0),1,.6)
