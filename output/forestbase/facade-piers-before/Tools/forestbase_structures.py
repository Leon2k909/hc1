"""Visible steel sections and connections; collision stays with the map builder."""
import math
import numpy as np
import map_kit as K

PAINT='structural_steel'
UP=np.array((0.,0.,1.))


def visual(m):
    return m.__class__.__name__!='CollisionOnlyModel'


def axes(a,b):
    along=K.normalise(np.asarray(b)-np.asarray(a))
    side=np.cross(UP,along)
    if np.linalg.norm(side)<1e-6: side=np.cross((1.,0.,0.),along)
    side=K.normalise(side)
    return along,side,np.cross(along,side)


def chamfer(m,center,basis,size,bevel,paint=PAINT,radius=.12):
    part=K.Model();half=np.asarray(size,float)/2
    bevel(part,-half,half,paint,radius)
    matrix=np.column_stack(basis);center=np.asarray(center,float)
    for name,faces in part.polygons.items():
        for points,normal in faces:
            m.polygon(name,[center+matrix@p for p in points],normal=matrix@normal)


def section(m,a,b,width,depth,bevel,thickness=.5):
    """Rolled I section with separate web/flanges and small edge chamfers."""
    if not visual(m): return
    a,b=np.asarray(a,float),np.asarray(b,float)
    basis=axes(a,b);center=(a+b)/2;length=np.linalg.norm(b-a)
    for sign in (-1,1):
        chamfer(m,center+basis[2]*sign*(depth-thickness)/2,basis,
                (length,width,thickness),bevel)
    chamfer(m,center,basis,(length,thickness,depth-2*thickness),bevel)


def bolt(m,center,normal,radius=.55):
    """A small extruded hex head, with its hidden underside omitted."""
    center=np.asarray(center,float);normal=K.normalise(np.asarray(normal,float))
    side=np.cross(normal,UP if abs(normal[2])<.95 else (1.,0.,0.))
    side=K.normalise(side);up=np.cross(normal,side)
    ring=[center+radius*(side*math.cos(t)+up*math.sin(t))
          for t in np.linspace(0,math.tau,6,endpoint=False)]
    top=[p+normal*.4 for p in ring]
    m.polygon('case_hardware',top,normal=normal)
    for i in range(6):
        j=(i+1)%6
        m.polygon('case_hardware',[ring[i],ring[j],top[j],top[i]])


def pilasters(m,w,bevel):
    """Front-frame strips stop at actual door/window openings."""
    if not visual(m): return
    face,direction=w.outer()
    for r in np.arange(w.run[0]+10,w.run[1],96):
        intervals=[w.z]
        for opening in w.openings:
            if r+3<=opening.r0-1 or r-3>=opening.r1+1: continue
            intervals=[piece for lo,hi in intervals for piece in
                       ((lo,min(hi,opening.z0-1)),(max(lo,opening.z1+1),hi))
                       if piece[1]>piece[0]]
        across=sorted((face+direction*.2,face+direction*3.2))
        for lo,hi in intervals:
            bevel(m,*w.lo_hi(r-3,r+3,*across,lo,hi),PAINT,.3)


def balcony(m,bounds,floor,bevel):
    if not visual(m): return
    x0,x1,y0,y1=bounds
    # Flange tops meet the existing six-inch slab underside. Keep all new
    # framing below the deck and clear of its stair and bridge mouths.
    for a,b in [((x0-76,y0-77,floor-13),(x1+76,y0-77,floor-13)),
                ((x0-74,y0-72,floor-13),(x0-74,y1+39,floor-13)),
                ((x1+74,y0-72,floor-13),(x1+74,y1+39,floor-13)),
                ((x0-74,y1+39,floor-13),(x1+74,y1+39,floor-13))]:
        section(m,a,b,7,14,bevel,.65)
    for x in (x0+14,x1-14):
        a=np.array((x,y0-2,floor-65));b=np.array((x,y0-74,floor-14))
        chamfer(m,(a+b)/2,axes(a,b),(np.linalg.norm(b-a),3.2,3.2),bevel)
        # Brackets attach to solid corner piers, outside all apertures.
        bevel(m,(x-5,y0-3.8,floor-74),(x+5,y0-3.2,floor-55),PAINT,.1)
        for zz in (floor-70,floor-59): bolt(m,(x,y0-3.85,zz),(0,-1,0),.65)


def bridge(m,a,b,width,bevel,rail_gaps=None):
    if not visual(m): return
    a,b=np.asarray(a,float),np.asarray(b,float);delta=b-a
    along,side,up=axes(a,b);length=np.linalg.norm(delta)
    bays=math.ceil(length/100)
    for sign in (-1,1):
        aa,bb=a+side*sign*width/2,b+side*sign*width/2
        section(m,aa-UP*12,bb-UP*12,5,12,bevel,.55)
        section(m,aa-UP*34,bb-UP*34,4,5,bevel,.45)
        for k in range(bays):
            p=aa+delta*k/bays;q=aa+delta*(k+1)/bays
            for start,end in ((p-UP*32,q-UP*8),(p-UP*8,q-UP*32)):
                chamfer(m,(start+end)/2,axes(start,end),
                        (np.linalg.norm(end-start),2.5,2.5),bevel)
        for k in range(bays+1):
            for z,height,spacing,offset in ((12,12,4,2.8),(34,8,2.2,2.3)):
                p=aa+delta*k/bays-UP*z+side*sign*offset
                chamfer(m,p,(along,side,up),(8,.6,height),bevel)
                for dz in (-spacing,spacing): bolt(m,p+UP*dz+side*sign*.31,side*sign,.6)
        start_gap,end_gap=(rail_gaps or {}).get(sign,(0,0))
        start=aa+along*start_gap;end=bb-along*end_gap
        post_count=math.ceil(np.linalg.norm(end-start)/90)
        # Reference bridges use braced side girders. Keep these on the outer
        # face of the existing guards, clipped to the same open junctions.
        # No crossbeam crosses the walking surface or adds a new collider.
        if np.linalg.norm(end-start)>=24:
            outside=side*sign*2
            for k in range(post_count):
                p=start+(end-start)*k/post_count+outside
                q=start+(end-start)*(k+1)/post_count+outside
                for lo,hi in ((p+UP*6,q+UP*39),(p+UP*39,q+UP*6)):
                    chamfer(m,(lo+hi)/2,axes(lo,hi),
                            (np.linalg.norm(hi-lo),2,2),bevel,radius=.18)
            for f in np.linspace(0,1,post_count+1):
                p=start+(end-start)*f+outside
                for z in (6,39):
                    joint=p+UP*z+side*sign*1.15
                    chamfer(m,joint,(along,side,up),(6,.5,5),bevel,radius=.1)
                    for offset in (-1.6,1.6):
                        bolt(m,joint+along*offset+side*sign*.26,side*sign,.42)
        for f in np.linspace(0,1,post_count+1):
            p=start+(end-start)*f
            chamfer(m,p+UP*.25,(along,side,up),(6,6,.5),bevel)
            for offset in (-1.9,1.9): bolt(m,p+along*offset+UP*.51,UP,.4)
    for f in (.05,.5,.95):
        p=a+delta*f
        section(m,p-side*(width/2-2)-UP*20,p+side*(width/2-2)-UP*20,
                5,12,bevel,.55)


def column(m,center,top,bevel):
    """Visible column fits the existing five-inch square movement proxy."""
    if not visual(m): return
    x,y=center
    bevel(m,(x-2.5,y-2.5,0),(x+2.5,y+2.5,1.2),PAINT,.15)
    section(m,(x,y,1.2),(x,y,top),4,4,bevel,.45)
    for dx in (-1.6,1.6):
        for dy in (-1.6,1.6): bolt(m,(x+dx,y+dy,1.21),UP,.38)
