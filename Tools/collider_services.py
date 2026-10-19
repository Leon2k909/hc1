"""Visible service infrastructure for Collider; gameplay collision stays separate."""
import math
import numpy as np
import map_kit as K
import boxyard_map as B
import collider_detail_geometry as D

UP=np.array((0.,0.,1.))
SERVICE_WINDOWS=((-380.,640.,30.,207.),(380.,640.,30.,207.))


def rounded_path(points, radius=22., steps=6):
    """Trim each bend and join its tangents with a quadratic curve."""
    points=[np.asarray(p,float) for p in points]
    result=[points[0]]
    for previous,corner,following in zip(points,points[1:],points[2:]):
        before,after=corner-previous,following-corner
        trim=min(radius,np.linalg.norm(before)*.3,np.linalg.norm(after)*.3)
        a=corner-K.normalise(before)*trim
        b=corner+K.normalise(after)*trim
        result.append(a)
        for t in np.linspace(0,1,steps+1)[1:]:
            result.append((1-t)**2*a+2*(1-t)*t*corner+t*t*b)
    result.append(points[-1])
    return np.asarray([p for i,p in enumerate(result) if i==0 or np.linalg.norm(p-result[i-1])>.001])


def pipe_run(m,points,radius,paint="co_trim",sides=12,bend=22.):
    points=rounded_path(points,bend)
    tangents=np.array([K.normalise(points[min(i+1,len(points)-1)]-points[max(i-1,0)])
                       for i in range(len(points))])
    side=np.cross(tangents[0],UP)
    if np.linalg.norm(side)<.01:side=np.cross(tangents[0],(1,0,0))
    rings=[]
    for point,tangent in zip(points,tangents):
        side=K.normalise(side-tangent*np.dot(side,tangent))
        other=np.cross(tangent,side)
        rings.append(np.array([point+radius*(side*math.cos(a)+other*math.sin(a))
                               for a in np.linspace(0,math.tau,sides,endpoint=False)]))
    for i in range(len(rings)-1):
        for j in range(sides):
            k=(j+1)%sides
            normal=rings[i][j]+rings[i][k]+rings[i+1][j]+rings[i+1][k]-2*(points[i]+points[i+1])
            normals=[rings[i][j]-points[i],rings[i][k]-points[i],
                     rings[i+1][k]-points[i+1],rings[i+1][j]-points[i+1]]
            B.card(m,paint,[rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]],normal,normals=normals)
    B.card(m,paint,rings[0],-tangents[0])
    B.card(m,paint,rings[-1],tangents[-1])


def flange(m,center,axis,radius):
    center=np.asarray(center,float);axis=K.normalise(axis)
    B.lathe(m,center,axis,[(radius,-2),(radius+3,-2),(radius+3,2),(radius,2)],"co_trim",sides=12)
    side=K.normalise(np.cross(axis,UP));other=np.cross(axis,side)
    for a in np.linspace(0,math.tau,6,endpoint=False):
        p=center+(side*math.cos(a)+other*math.sin(a))*(radius+1.5)
        D.bolt(m,p+axis*2,axis,r=.7,length=.6)


def valve(m,at,facing):
    at=np.asarray(at,float);facing=K.normalise(facing)
    B.lathe(m,at,(0,1,0),[(7,-12),(10,-5),(10,5),(7,12)],"co_steel",sides=12,cap="co_trim")
    for offset in (-14,14):flange(m,at+(0,offset,0),(0,1,0),7)
    pipe_run(m,[at,at+facing*25],2.3,"co_silver",10)
    wheel=at+facing*25
    B.lathe(m,wheel,facing,[(9,-1),(12,-1),(12,1),(9,1),(9,-1)],"co_amber",sides=20)
    side=np.cross(facing,UP)
    for a in np.linspace(0,math.tau,4,endpoint=False):
        m.beam(wheel,wheel+(side*math.cos(a)+UP*math.sin(a))*10,(1.7,1.7),"co_trim")
    D.bolt(m,wheel+facing,facing,r=2.5,length=1.2)


def cable_tray(m,n,z=804.):
    # Two channels, open rungs and a shallow bed of individually routed cables.
    for side in (-1,1):
        y=n+side*16
        D.beam(m,(-1380,y,z+4),(1380,y,z+4),(1.2,8),"co_steel",bevel=.15)
        m.beam((-1380,y-side*2,z),(1380,y-side*2,z),(5,1.2),"co_trim")
    for e in np.arange(-1370,1380,28):
        m.beam((e,n-16,z),(e,n+16,z),(2,1.4),"co_trim")
    for i,off in enumerate((-10,-5,0,5,10)):
        end=1380 if i%2 else -1380
        other=-end
        points=[(other,n+off,z+4),(end*.9,n+off,z+4),
                (end,n+off+50,z+4),(end,n+off+50,z-74)]
        pipe_run(m,points,1.6,"co_rubber" if i!=3 else "co_steel",8,bend=24)
    # Hangers line up with the ceiling's structural beams.
    for e in range(-1200,1201,300):
        m.beam((e,n-24,z-3),(e,n+24,z-3),(3,3),"co_silver")
        for side in (-1,1):
            pipe_run(m,[(e,n+side*22,z-3),(e,n+side*22,876)],.85,"co_trim",8)
            D.plate(m,(e-4,n+side*22-4,873),(e+4,n+side*22+4,876),"co_trim",.25)
            D.bolt(m,(e,n+side*22,z-5),(0,0,-1),1.2,.7)


def overhead_services(m):
    for n in (-820,-500,100,500):cable_tray(m,n)
    for e in (-1280,-1200,-1110,1110,1200,1280):
        for z,r in ((770,5),(796,3.5)):
            pipe_run(m,[(e,-880,z),(e,-360,z),(e,-305,z+24),
                        (e,-205,z+24),(e,-150,z),(e,620,z)],r,
                     "co_silver" if r==5 else "co_trim",12)
            for n in (-790,-500,40,370,570):flange(m,(e,n,z),(0,1,0),r)
        for n in (-600,-100,400):
            D.plate(m,(e-10,n-15,730),(e+10,n+15,756),"co_case",1.2)
            pipe_run(m,[(e,n,756),(e,n,796)],2,"co_silver",10)
            for dx in (-6,6):
                for dy in (-10,10):D.bolt(m,(e+dx,n+dy,729.6),(0,0,-1),.6,.5)
        if abs(e)==1280:valve(m,(e,280,770),(-np.sign(e),0,0))


def service_front(m,glass,wall):
    # Cut the visible surface only. Retain the exact original wall collision,
    # including both door openings, so the new glazing cannot open a route.
    doors=[(-900,160,0,192),(900,160,0,192)]
    old=K.Model();wall(old,"e",(-1400,1400),(650,674),(0,256),doors)
    boxes,hulls=len(m.boxes),len(m.hulls)
    wall(m,"e",(-1400,1400),(650,674),(0,256),doors+list(SERVICE_WINDOWS))
    m.boxes[boxes:]=old.boxes
    m.hulls[hulls:]=old.hulls
    for e,width,bottom,top in SERVICE_WINDOWS:
        lo,hi=e-width/2,e+width/2
        glass.box((lo,661,bottom),(hi,663,top),"co_glass")
        for edge in (lo,e,hi):
            D.plate(m,(edge-3,645,bottom-4),(edge+3,679,top+4),"co_trim",.55)
        for height in (bottom,top):
            D.plate(m,(lo-4,645,height-3),(hi+4,679,height+3),"co_trim",.5)
        D.plate(m,(lo-8,640,bottom-6),(hi+8,679,bottom-3),"co_silver",.4)
        for edge in (lo,hi):
            for height in (bottom+8,top-8):D.bolt(m,(edge,644.5,height),(0,-1,0),.9,.7)


def gallery_fascias(m):
    for n,facing in ((-550,1),(300,-1)):
        front=n+facing*2
        D.plate(m,(-1000,n-3,229),(1000,n+3,254),"co_steel",.5)
        for z in (230,252):
            m.box((-1000,front-3,z),(1000,front+3,z+2),"co_trim")
        for e in range(-960,961,160):
            D.plate(m,(e-7,front-2,231),(e+7,front+2,251),"co_trim",.3)
            for dx in (-4,4):
                for z in (235,247):D.bolt(m,(e+dx,front+facing*2.2,z),(0,facing,0),.8,.65)
        for e in (-960,960):
            toward=-np.sign(e)
            D.beam(m,(e,front,188),(e+toward*80,front,230),(5,9),"co_trim",.5)


def service_instruments(m,monitor):
    for index,e in enumerate((-520,-170,170,520)):
        D.plate(m,(e-145,972,55),(e+145,979,220),"co_case",2.5)
        monitor(m,(e,970,162),(0,-1),250,90,index)
        for zz in (72,82,92):
            D.plate(m,(e-110,969,zz),(e+110,972,zz+4),"co_trim",.6)
        for dx in (-70,-50,-30):
            D.plate(m,(e+dx-3,968,103),(e+dx+3,972,107),"co_amber" if dx==-70 else "co_trim",.5)
    for z in (212,223):
        pipe_run(m,[(-700,970,z),(700,970,z)],2.3,"co_trim",10)
    for e in (-700,0,700):
        D.plate(m,(e-9,968,210),(e+9,976,230),"co_steel",.5)
