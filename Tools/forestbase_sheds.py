"""Pitched sheet roofs and bolted steel frames for the two reference halls."""
import math
import numpy as np
import forestbase_structures as S


def bounds(center,size):
    e,n=center;w,d=size
    return e-w/2,e+w/2,n-d/2,n+d/2


def roof_height(n,center,depth):
    # Meet the existing 180-inch walls exactly; the overhang drains below them.
    return 205-25*abs(n-center)/(depth/2)


def roof_collisions(m,center,size,workshop):
    """Append a workshop lintel and missing roof slabs after legacy props."""
    e,n=center;w,d=size;x0,x1,y0,y1=bounds(center,size)
    if workshop:
        m.collision_box((e-w/4,y0-5,154),(e+w/4,y0+5,170),'metal')
    across=np.array((1.,0.,0.))
    for a,b in ((y0-18,n),(n,y1+18)):
        aa=np.array((e,a,roof_height(a,n,d)));bb=np.array((e,b,roof_height(b,n,d)))
        along=(bb-aa)/np.linalg.norm(bb-aa);up=np.cross(across,along)
        m.boxes.append(((aa+bb)/2-up,(across,along,up),(w+40,np.linalg.norm(bb-aa),2),'metal'))
    if workshop:
        for a,b in ((x0,x0+10),(x1-10,x1)):
            m.hull([(x,y,z) for x in (a,b) for y,z in ((y0,180),(n,205),(y1,180))],'metal')


def visuals(m,center,size,workshop,bevel,tube):
    if not S.visual(m):return
    e,n=center;w,d=size;x0,x1,y0,y1=bounds(center,size)
    roof=lambda y:roof_height(y,n,d)
    left,right=x0-20,x1+20
    def skin(points,reverse=False):
        if reverse:points=list(reversed(points))
        m.polygon('roof',points,uv=[(p[0]/106,math.hypot(p[1]-n,p[2]-205)/106) for p in points])
    for a,b in ((y0-18,n),(n,y1+18)):
        top=[(left,a,roof(a)),(right,a,roof(a)),(right,b,roof(b)),(left,b,roof(b))]
        skin(top);skin([(x,y,z-.18) for x,y,z in top],True)
        # Raised sheet laps align with quarter tiles of the existing scan.
        for x in np.arange(left+26.5,right-1,26.5):
            profile=((-0.75,.03),(-.5,.55),(.5,.55),(.75,.03))
            for (u,z),(v,zz) in zip(profile,profile[1:]):
                skin([(x+u,a,roof(a)+z),(x+v,a,roof(a)+zz),
                      (x+v,b,roof(b)+zz),(x+u,b,roof(b)+z)])
        for y in (a,b):
            if y==n:continue
            skin([(left,y,roof(y)),(right,y,roof(y)),(right,y,roof(y)-3),(left,y,roof(y)-3)],y<n)
    # Folded ridge and end flashings close the formerly paper-thin silhouette.
    for a,b in ((-6,0),(0,6)):
        za=206 if a==0 else roof(n+a)+.3;zb=206 if b==0 else roof(n+b)+.3
        skin([(left-1,n+a,za),(right+1,n+a,za),(right+1,n+b,zb),(left-1,n+b,zb)])
    for x in (left,right):
        for a,b in ((y0-18,n),(n,y1+18)):
            points=[(x,a,roof(a)),(x,b,roof(b)),(x,b,roof(b)-3),(x,a,roof(a)-3)]
            if x==right:points.reverse()
            skin(points)
    # Truss spacing and post proxies match the original five-frame structure.
    for x in np.linspace(x0,x1,5):
        for y in (y0,y1):
            if workshop and abs(x-e)<.001 and y==y0:
                continue
            S.section(m,(x,y,.75),(x,y,172),7,7,bevel,.28)
            bevel(m,(x-4,y-4,0),(x+4,y+4,.75),S.PAINT,.12)
            for dx in (-2.8,2.8):
                for dy in (-2.8,2.8):S.bolt(m,(x+dx,y+dy,.76),(0,0,1),.38)
            start=np.array((x,y,137.));end=np.array((x+(25 if x<e else -25),y,170.))
            S.chamfer(m,(start+end)/2,S.axes(start,end),(np.linalg.norm(end-start),3,3),bevel)
        S.section(m,(x,y0,174),(x,n,199),4,6,bevel,.25)
        S.section(m,(x,n,199),(x,y1,174),4,6,bevel,.25)
        S.section(m,(x,y0,170),(x,y1,170),4,4,bevel,.25)
        ys=np.linspace(y0,y1,5)
        for k,(a,b) in enumerate(zip(ys,ys[1:])):
            start=np.array((x,a,170 if k%2==0 else roof(a)-6))
            end=np.array((x,b,roof(b)-6 if k%2==0 else 170))
            S.chamfer(m,(start+end)/2,S.axes(start,end),(np.linalg.norm(end-start),2,2),bevel,radius=.12)
        for y in ys[1:-1]:
            bevel(m,(x-1,y-1,170),(x+1,y+1,roof(y)-6),S.PAINT,.15)
        for y in (y0,n,y1):
            z=roof(y)-7;normal=(-1,0,0) if x==x0 else (1,0,0)
            bevel(m,(x-2.5,y-4,z-4),(x+2.5,y+4,z+4),S.PAINT,.2)
            for dy in (-2.3,2.3):S.bolt(m,(x+normal[0]*2.51,y+dy,z),normal,.5)
    if workshop:
        S.section(m,(e-w/4,y0,162),(e+w/4,y0,162),10,16,bevel,.6)
        for x in (e-w/4,e+w/4):
            bevel(m,(x-5.5,y0-5.5,155),(x+5.5,y0+5.5,169),S.PAINT,.2)
            for z in (158,166):S.bolt(m,(x,y0-5.51,z),(0,-1,0),.65)
    for y in np.linspace(y0,y1,5):
        S.chamfer(m,(e,y,roof(y)-1.5),((1,0,0),(0,1,0),(0,0,1)),(w+24,2.4,3),bevel,radius=.15)
    # Keep the existing sign legible in front of the gutter, on short brackets.
    for x in (e-52,e+52):
        S.chamfer(m,(x,y0-14,170),((1,0,0),(0,1,0),(0,0,1)),(2,28,2),bevel,radius=.12)
    # Open gutters, rear downpipes and post clips use existing metal materials.
    for y,sign in ((y0-20,-1),(y1+20,1)):
        z=roof(y)-1
        for a,b in (((e,y,z-4),(w+42,4,.35)),((e,y-2,z-2),(w+42,.35,4)),((e,y+2,z-2),(w+42,.35,4))):
            S.chamfer(m,a,((1,0,0),(0,1,0),(0,0,1)),b,bevel,radius=.08)
        if sign==1:
            for x in (x0+12,x1-12):
                tube(m,(x,y,z-3),(x,y,6),1.4,S.PAINT)
                tube(m,(x,y,6),(x,y+8,3),1.4,S.PAINT)
                for zz in (28,96,154):bevel(m,(x-2.2,y-2,zz),(x+2.2,y+1,zz+1.5),S.PAINT,.15)
    for x in np.arange(left+26.5,right-1,53):
        for y in (y0,y0+d*.25,y1-d*.25,y1):
            slope=25/(d/2)*(1 if y<n else -1)
            S.bolt(m,(x,y,roof(y)+.6),(0,-slope,1),.24)
    if workshop:
        for x,normal in ((x0-.12,(-1,0,0)),(x1+.12,(1,0,0))):
            points=[(x,y0,180),(x,n,205),(x,y1,180)]
            if normal[0]>0:points.reverse()
            m.polygon('roof',points,normal=normal,uv=[(p[1]/106,p[2]/106) for p in points])
