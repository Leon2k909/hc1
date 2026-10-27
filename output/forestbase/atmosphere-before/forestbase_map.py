"""Reference-driven Forest Base map. Plan east/north/up in inches; map_kit exports Source 2 assets.

Four buildings only: motor shelter SW, barracks NW, command N, workshop E.
Run forestbase_materials.py first, then this script. The scene is generated, edit layout here.
All visual props use simplified, authored collision; scene is split for engine frustum/occlusion culling.
"""
import json, math, argparse, os
from collections import deque
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image, ImageDraw
import map_kit as K
import forestbase_materials as M

OUT=K.ASSETS/'models/maps/forestbase'
RES='models/maps/forestbase'
SCENE=K.ASSETS/'scenes/maps/ForestBase/forestbase.scene'
IDS=K.SceneIds('5ff10d4f-93c2-4a2a-bd86-48eab6181c6a')
LIMIT=(-1550,1550,-1450,1450)
LIGHTS=[]
INSTANCES=[]
ROUTES=[]
SPOTS={}

class CollisionOnlyModel(K.Model):
    """Retain the same authored physics without accumulating unused visual faces."""
    def polygon(self,*args,**kwargs): pass
    def extend(self,other):
        self.boxes.extend(other.boxes); self.hulls.extend(other.hulls)
        self.props.extend(other.props)
        return self


def model(visual=True):
    m=K.Model() if visual else CollisionOnlyModel()
    m.material_overrides.update({p:f'{M.RESOURCE}/{p}.vmat' for p in M.TILES})
    m.material_overrides.update({f'sign_{p}':f'{M.RESOURCE}/sign_{p}.vmat' for p in 'ABCDEF'})
    m.material_overrides.update({f'cargo_{p}':f'{M.RESOURCE}/cargo_{p}.vmat' for p in range(4)})
    m.material_overrides.update({p:f'{M.RESOURCE}/{p}.vmat' for p in ('river','waterfall','waterfall_foam','waterfall_current','waterfall_spray')})
    m.tile_overrides.update(M.TILES)
    m.tile_overrides.update({p:128 for p in ('river','waterfall','waterfall_foam','waterfall_current','waterfall_spray')})
    m.tile_overrides.update({f'cargo_{p}':128 for p in range(4)})
    for paint,scan,units in [('asphalt','asphalt_02',192),('concrete','concrete_floor_02',128),('plaster','concrete_wall_007',128),('timber','wood_planks',128),('roof','corrugated_iron_02',106),('steel','metal_plate_02',80),('container','container_side',96),('mud','mud_forest',92),('mud_track','muddy_tracks',92)]:
        if (K.ASSETS/f'materials/forestbase/scans/{scan}.vmat').exists():
            m.material_overrides[paint]=f'materials/forestbase/scans/{scan}.vmat'
            m.tile_overrides[paint]=units
    m.tile_overrides.update({f'sign_{p}':128 for p in 'ABCDEF'})
    return m

def box(m,a,b,p='steel',solid=None): m.box(a,b,p,solid)

def bevel_box(m,lo,hi,paint='olive',radius=1.2,surface=None):
    """Chamfered sheet-metal edges, retaining a single inexpensive collision box."""
    if isinstance(m,CollisionOnlyModel):
        if surface: m.collision_box(lo,hi,surface)
        return
    lo,hi=np.array(lo,float),np.array(hi,float)
    r=min(radius,float(np.min(hi-lo))*.24)
    # Faces, twelve edge strips and eight corner triangles of a clipped cuboid.
    for axis in range(3):
        others=[a for a in range(3) if a!=axis]
        for sign in (-1,1):
            pts=[]
            for u,v in ((-1,-1),(1,-1),(1,1),(-1,1)):
                p=(lo+hi)/2; p[axis]=hi[axis] if sign>0 else lo[axis]
                p[others[0]]=hi[others[0]]-r if u>0 else lo[others[0]]+r
                p[others[1]]=hi[others[1]]-r if v>0 else lo[others[1]]+r
                pts.append(p)
            normal=np.eye(3)[axis]*sign
            if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0: pts.reverse()
            m.polygon(paint,pts)
    for along in range(3):
        a,b=[q for q in range(3) if q!=along]
        for sa in (-1,1):
            for sb in (-1,1):
                edge=(lo+hi)/2; edge[a]=hi[a] if sa>0 else lo[a]; edge[b]=hi[b] if sb>0 else lo[b]
                pts=[]
                for end,inner in ((lo[along]+r,a),(hi[along]-r,a),(hi[along]-r,b),(lo[along]+r,b)):
                    p=edge.copy(); p[along]=end; p[inner]-=r*(sa if inner==a else sb); pts.append(p)
                normal=np.eye(3)[a]*sa+np.eye(3)[b]*sb
                if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0: pts.reverse()
                m.polygon(paint,pts)
    for sx in (-1,1):
        for sy in (-1,1):
            for sz in (-1,1):
                signs=np.array((sx,sy,sz)); c=np.where(signs>0,hi,lo)
                pts=[c-np.eye(3)[a]*signs[a]*r for a in range(3)]
                if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),signs)<0: pts.reverse()
                m.polygon(paint,pts)
    if surface: m.collision_box(lo,hi,surface)

def loft(m,rings,paint,surface=None):
    """Closed convex body through equal-size perimeter rings, outward facing."""
    if isinstance(m,CollisionOnlyModel):
        if surface: m.hull(np.concatenate(rings),surface)
        return
    rings=[np.asarray(r,float) for r in rings]
    center=np.mean(np.concatenate(rings),axis=0)
    faces=[list(rings[0]),list(rings[-1])]
    for a,b in zip(rings,rings[1:]):
        for k in range(len(a)): faces.append([a[k],a[(k+1)%len(a)],b[(k+1)%len(a)],b[k]])
    for pts in faces:
        normal=np.cross(np.array(pts[1])-pts[0],np.array(pts[2])-pts[0])
        if np.dot(normal,np.mean(pts,axis=0)-center)<0: pts.reverse()
        m.polygon(paint,pts)
    if surface: m.hull(np.concatenate(rings),surface)

def transform(src,origin=(0,0,0),angle=0):
    out=model(not isinstance(src,CollisionOnlyModel)); t=np.radians(angle)
    mat=np.array(((np.cos(t),-np.sin(t),0),(np.sin(t),np.cos(t),0),(0,0,1)))
    origin=np.array(origin,float)
    for paint,faces in src.polygons.items():
        for i,(pts,n) in enumerate(faces):
            out.polygon(paint,[mat@p+origin for p in pts],normal=mat@n,
                        uv=src.polygon_uvs.get((paint,i)),
                        normals=[mat@n for n in src.polygon_normals[(paint,i)]] if (paint,i) in src.polygon_normals else None)
    for c,axes,size,s in src.boxes: out.boxes.append((mat@c+origin,tuple(mat@np.array(a) for a in axes),size,s))
    for pts,s in src.hulls: out.hulls.append(([mat@np.array(p)+origin for p in pts],s))
    return out

def panel(m,pts,p):
    m.polygon(p,pts,uv=((0,0),(1,0),(1,1),(0,1)))

def tube(m,a,b,r=1,paint='steel',segments=10):
    """Round visual pipe with smooth radial normals; no extra player collider."""
    if isinstance(m,CollisionOnlyModel): return
    a,b=np.asarray(a,float),np.asarray(b,float); axis=K.normalise(b-a)
    side=K.normalise(np.cross(axis,(0,0,1) if abs(axis[2])<.95 else (1,0,0)))
    up=np.cross(axis,side)
    radial=[side*math.cos(t)+up*math.sin(t) for t in np.linspace(0,math.tau,segments,endpoint=False)]
    for i,normal in enumerate(radial):
        other=radial[(i+1)%segments]
        m.polygon(paint,[a+normal*r,a+other*r,b+other*r,b+normal*r],normals=[normal,other,other,normal])
    m.polygon(paint,[a+n*r for n in reversed(radial)])
    m.polygon(paint,[b+n*r for n in radial])

def bulkhead(m,e,n,z,angle=0):
    """Weatherproof wall light: cast housing, recessed diffuser and wire guard."""
    part=model(not isinstance(m,CollisionOnlyModel))
    bevel_box(part,(-11,-1,-6),(11,0,6),'steel',.4)
    bevel_box(part,(-10,-6,-5),(10,-.5,5),'olive',1.2)
    bevel_box(part,(-8.2,-6.15,-3.2),(8.2,-5.9,3.2),'lamp',.1)
    for x in (-9,9):
        for zz in (-4,4): bevel_box(part,(x-.6,-6.35,zz-.6),(x+.6,-6.1,zz+.6),'steel',.2)
    # A thin protective grille keeps the luminous face distinct from its housing.
    for x in (-5,0,5): tube(part,(x,-6.6,-3.6),(x,-6.6,3.6),.35,segments=6)
    for zz in (-3.6,3.6): tube(part,(-8.5,-6.6,zz),(8.5,-6.6,zz),.35,segments=6)
    m.extend(transform(part,(e,n,z),angle))

def wall_services(m,e,n,z,angle=0):
    """Small distribution cabinet and conduit on a solid facade panel."""
    part=model(not isinstance(m,CollisionOnlyModel))
    bevel_box(part,(-13,-6,0),(13,-.3,33),'olive',.7)
    bevel_box(part,(-11.5,-6.45,1.5),(11.5,-6.05,31.5),'steel',.25)
    bevel_box(part,(-10.4,-6.65,2.6),(10.4,-6.4,30.4),'olive',.15)
    for zz in (6,26):
        bevel_box(part,(-12.3,-7,zz),( -10.8,-6.4,zz+3),'steel',.2)
    box(part,(8.3,-7,14),(9.6,-6.4,18),'steel')
    # Vent slots are backed, unlike the building's usable open windows.
    for zz in (5,7,9): box(part,(-7,-6.8,zz),(6,-6.6,zz+.6),'rubber')
    panel(part,[(-7,-6.81,20),(7,-6.81,20),(7,-6.81,27),(-7,-6.81,27)],'cargo_0')
    for x in (-7,7):
        tube(part,(x,-3,33),(x,-3,53),.6)
        tube(part,(x,-3,53),(x+5,-3,58),.6)
        tube(part,(x+5,-3,58),(x+5,-3,83),.6)
        for zz in (43,68): box(part,(x-.9,-3.9,zz),(x+.9,-.4,zz+1.5),'steel')
    m.extend(transform(part,(e,n,z),angle))

def roof_plant(m,e,n,z,w=100,d=120,h=62,solid='metal'):
    """HVAC enclosure with raised base, service panel, louvers and fan guard."""
    # Cover collision remains the same as the previous plain enclosure.
    bevel_box(m,(e,n,z),(e+w,n+d,z+h),'equipment_paint',1.6,solid)
    for x in (e+5,e+w-5): box(m,(x-2,n+6,z),(x+2,n+d-6,z+5),'olive')
    bevel_box(m,(e+6,n-.8,z+7),(e+w-6,n-.1,z+h-7),'rubber',.3)
    for zz in np.arange(z+10,z+h-8,4):
        m.beam((e+9,n-1.2,zz),(e+w-9,n-1.2,zz),(1.5,1.5),'steel')
    # Concentric guard and visible hub above the dark fan well.
    cx,cy=e+w*.5,n+d*.58; radius=min(w,d)*.30
    m.cylinder((cx,cy),radius,z+h+.08,z+h+.4,'rubber',sides=32)
    for angle in np.linspace(0,math.tau,5,endpoint=False):
        def blade(r,t): return (cx+r*math.cos(t),cy+r*math.sin(t),z+h+.48)
        m.polygon('equipment_paint',[blade(radius*.16,angle),blade(radius*.82,angle+.22),
                  blade(radius*.84,angle+.53),blade(radius*.18,angle+.70)])
    for r in (radius*.35,radius*.65,radius):
        points=[(cx+r*math.cos(t),cy+r*math.sin(t),z+h+1) for t in np.linspace(0,math.tau,24,endpoint=False)]
        for a,b in zip(points,points[1:]+points[:1]): tube(m,a,b,.35,segments=6)
    for t in np.linspace(0,math.tau,8,endpoint=False):
        tube(m,(cx,cy,z+h+1),(cx+radius*math.cos(t),cy+radius*math.sin(t),z+h+1),.4,segments=6)
    m.cylinder((cx,cy),3,z+h+.5,z+h+1.8,'steel',sides=12)
    bevel_box(m,(e+w-.1,n+8,z+9),(e+w+.7,n+35,z+h-9),'olive',.25)
    for zz in (z+14,z+h-16): box(m,(e+w+.7,n+11,zz),(e+w+1.2,n+13,zz+2),'steel')

def rail(m,a,b,height=42):
    a,b=np.array(a,float),np.array(b,float)
    count=max(1,math.ceil(np.linalg.norm(b-a)/90))
    for f in np.linspace(0,1,count+1):
        p=a+(b-a)*f
        m.beam(p,p+(0,0,height),(2.5,2.5),'steel')
        # Upright post collision is axis-aligned; avoid an Euler gimbal singularity
        # in the shared ModelDoc oriented-box exporter for exactly vertical beams.
        m.collision_box(p-(1.25,1.25,0),p+(1.25,1.25,height),'metal')
    for z in (16,height): m.beam(a+(0,0,z),b+(0,0,z),(2.5,2.5),'steel','metal')

def stairs(m,start,end,width=100,topgap=0):
    a,b=np.array(start,float),np.array(end,float)
    run=b-a; steps=math.ceil(abs(run[2])/8)
    along=run.copy(); along[2]=0; length=np.linalg.norm(along); along/=length
    across=np.cross((0,0,1),along)
    for k in range(steps):
        q=a+run*((k+.5)/steps); z=a[2]+run[2]*(k+1)/steps
        # Full solid risers; upper side is tread, every rise <= 12 inches.
        m.oriented_box((q[0],q[1],(z+a[2]-8)/2),(along,across,(0,0,1)),
                       (length/steps,width,z-a[2]+8),'steel','metal')
        edge=q-along*length/steps*.45; edge[2]=z+.25
        m.beam(edge-across*width*.5,edge+across*width*.5,(1,1),'yellow')
    for sign in (-1,1): rail(m,a+sign*across*width/2,b+sign*across*width/2-run*(topgap/length))
    ROUTES.append(dict(kind='stairs',start=list(a),end=list(b),width=width,rise=run[2]/steps))

def lamp(m,e,n,z=260,pole=True,shadow=False):
    if pole:
        m.cylinder((e,n),3,0,z,'steel',sides=8)
        box(m,(e-13,n-13,0),(e+13,n+13,8),'concrete')
        m.beam((e-32,n,z),(e+32,n,z),(4,4),'steel')
    for k in (-1,1):
        box(m,(e+k*22-13,n-9,z-10),(e+k*22+13,n+9,z+4),'steel')
        box(m,(e+k*22-10,n-10,z-8),(e+k*22+10,n-9.8,z+1),'lamp')
    LIGHTS.append((f'Flood {len(LIGHTS)}',(e,n-16,z-26),'5.8,4.3,2.5,1',600,shadow))

def wall(m,axis,run,across,z,out,doors=(),windows=()):
    w=K.Wall(axis,run,across,z,out)
    # A window overlapping a doorway produced a floating sill across the entrance.
    windows=[hole for hole in windows if not any(abs(hole[0]-door[0])<(hole[1]+door[1])/2+2 and hole[2]<door[3] and hole[3]>door[2] for door in doors)]
    for c,width,base,top in doors: w.add(c,width,base,top,'door')
    for c,width,base,top in windows: w.add(c,width,base,top,'window')
    # A wall scan belongs on the facades; the heavily weathered floor scan is
    # reserved for slabs and foundations, where its coarse aggregate is plausible.
    w.build(m,'plaster','plaster','steel',surface='concrete')
    # Recessed window frames, open apertures preserve movement and bullet traces.
    for c,width,base,top in windows:
        for r in (c-width/2,c+width/2): box(m,*w.lo_hi(r-2,r+2,*across,base,top),'steel')
        for zz in (base,top): box(m,*w.lo_hi(c-width/2,c+width/2,*across,zz-2,zz+2),'steel')
    if out:
        face=across[0] if out[0]=='-' else across[1]
        direction=-1 if out[0]=='-' else 1
        outer=sorted((face+direction*.15,face+direction*2))
        deep=sorted((face+direction*.2,face+direction*7))
        for c,width,base,top in windows:
            # Folded sill and rain hood stay outside the aperture.
            bevel_box(m,*w.lo_hi(c-width/2-3,c+width/2+3,*deep,base-3,base-1),'olive',.45)
            bevel_box(m,*w.lo_hi(c-width/2-4,c+width/2+4,*deep,top+2,top+4),'steel',.45)
            for r in (c-width/2-1,c+width/2+1):
                for zz in (base+5,top-5):
                    box(m,*w.lo_hi(r-.6,r+.6,*outer,zz-.6,zz+.6),'olive')
        for c,width,base,top in doors:
            for r in (c-width/2-1.5,c+width/2+1.5):
                bevel_box(m,*w.lo_hi(r-1.5,r+1.5,*outer,base,top+3),'steel',.4)
            bevel_box(m,*w.lo_hi(c-width/2-3,c+width/2+3,*outer,top,top+3),'steel',.4)
    return w

def sign(m,c,z,letter,width=150):
    e,n=c
    box(m,(e-width/2-3,n-3,z-3),(e+width/2+3,n,z+width/4+3),'steel')
    panel(m,[(e-width/2,n-3.1,z),(e+width/2,n-3.1,z),(e+width/2,n-3.1,z+width/4),(e-width/2,n-3.1,z+width/4)],f'sign_{letter}')

def crate(m,e,n,z=0,w=66,h=54,paint='olive'):
    # Reinforced transport case, recessed panel, metal corners, hinges and folding handles.
    bevel_box(m,(e-w/2,n-w*.38,z),(e+w/2,n+w*.38,z+h),paint,1.8,'wood')
    for zz in (z+4,z+h-5):
        box(m,(e-w/2-1,n-w*.38-1,zz),(e+w/2+1,n+w*.38+1,zz+3),'steel')
    for x in (e-w/2+5,e+w/2-5):
        for yy in (n-w*.38-1,n+w*.38-2): box(m,(x-3,yy,z),(x+3,yy+3,z+h),'steel')
    for x in (e-w*.25,e+w*.25):
        box(m,(x-3,n-w*.38-2,z+h-13),(x+3,n-w*.38-1,z+h-4),'steel')
    scale=w/66
    front=n-w*.38
    # A recessed handle well, folded U-handle, lid seam and hardware break up the
    # previous blank case face. All are visual additions inside the existing hull.
    bevel_box(m,(e-12*scale,front-.18,z+h*.52),(e+12*scale,front-.04,z+h*.73),'rubber',.08)
    for x in (e-9*scale,e+9*scale): box(m,(x-scale,front-1.6*scale,z+h*.57),(x+scale,front-.2,z+h*.67),'steel')
    box(m,(e-9*scale,front-1.6*scale,z+h*.57),(e+9*scale,front-.9*scale,z+h*.57+1.8*scale),'steel')
    for y in (-w*.24,0,w*.24):
        bevel_box(m,(e-w*.35,n+y-scale,z+h-.12),(e+w*.35,n+y+scale,z+h+.7*scale),paint,.4*scale)
    for x in (e-w*.28,e+w*.28):
        bevel_box(m,(x-2*scale,front-1.7*scale,z+h*.78),(x+2*scale,front-.2,z+h*.94),'steel',.4*scale)
    label=int(abs(e*3+n*5+z))%3
    panel(m,[(e-w*.19,front-.22,z+h*.20),(e+w*.19,front-.22,z+h*.20),
             (e+w*.19,front-.22,z+h*.39),(e-w*.19,front-.22,z+h*.39)],f'cargo_{label}')

def pallet(m,e,n,z=0,w=88):
    for x in (-w*.4,0,w*.4): box(m,(e+x-4,n-36,z),(e+x+4,n+36,z+6),'timber')
    for y in np.linspace(-32,32,7): box(m,(e-w/2,n+y-3,z+6),(e+w/2,n+y+3,z+9),'timber')

def stack(m,e,n,z=0,rows=2,cols=2,height=1):
    for r in range(rows):
        for c in range(cols):
            ee,nn=e+c*74,n+r*60
            pallet(m,ee,nn,z,w=72)
            for k in range(height): crate(m,ee,nn,z+9+k*54)

def container(m,e,n,z=0,length=250,width=104,height=108,angle=0):
    part=model(not isinstance(m,CollisionOnlyModel))
    box(part,(-length/2,-width/2,0),(length/2,width/2,height),'container','metal')
    for y in (-width/2-1,width/2):
        for x in np.arange(-length/2+8,length/2,12): box(part,(x,y,3),(x+3,y+1.2,height-3),'container')
    for x in (-length/2-2,length/2):
        box(part,(x,-width/2-2,0),(x+3,width/2+2,5),'steel')
        box(part,(x,-width/2-2,height-5),(x+3,width/2+2,height),'steel')
        for y in (-width/2,0,width/2-3): box(part,(x,y,0),(x+3,y+3,height),'steel')
    # Two hinged door leaves with four real locking rods, cam brackets and handles.
    end=length/2+3.05
    for side in (-1,1):
        yc=side*width*.25
        bevel_box(part,(end-width*.008,yc-width*.24,7),(end+.35,yc+width*.24,height-7),'olive',.12)
        for yy in (yc-width*.10,yc+width*.10):
            part.cylinder((end+1.8,yy),.65,8,height-8,'steel',sides=8)
            for zz in (12,height*.5,height-14):
                bevel_box(part,(end+1,yy-2,zz-1.5),(end+3.2,yy+2,zz+1.5),'steel',.4)
            part.beam((end+3.2,yy,height*.44),(end+3.2,yy+side*7,height*.40),(1.1,1.1),'steel')
        for zz in (18,height*.52,height-22):
            hinge=side*(width/2-4)
            bevel_box(part,(end+.1,hinge-2,zz),(end+2.2,hinge+2,zz+5),'steel',.5)
    for x in (-length/2,length/2):
        for y in (-width/2,width/2):
            for zz in (0,height-7):
                bevel_box(part,(x-3,y-3,zz),(x+3,y+3,zz+7),'steel',.8)
    panel(part,[(end+.41,-width*.41,height*.15),(end+.41,-width*.01,height*.15),
                (end+.41,-width*.01,height*.34),(end+.41,-width*.41,height*.34)],'cargo_3')
    panel(part,[(-length*.36,-width/2-1.4,25),(-length*.19,-width/2-1.4,25),
                (-length*.19,-width/2-1.4,45),(-length*.36,-width/2-1.4,45)],'cargo_3')
    m.extend(transform(part,(e,n,z),angle))

def mud_track(m,points,width=160):
    """Soft-edged rain/mud overlay; the original solid ground stays continuous."""
    controls=[np.array(p,float) for p in points]; centers=[]
    for j in range(len(controls)-1):
        p0,p1,p2,p3=controls[max(0,j-1)],controls[j],controls[j+1],controls[min(len(controls)-1,j+2)]
        for t in np.linspace(0,1,8,endpoint=False):
            centers.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    centers.append(controls[-1])
    distances=np.concatenate(([0],np.cumsum([np.linalg.norm(b-a) for a,b in zip(centers,centers[1:])])))
    sections=[]
    for j,(center,distance) in enumerate(zip(centers,distances)):
        tangent=centers[min(j+1,len(centers)-1)]-centers[max(0,j-1)]
        across=np.array((-tangent[1],tangent[0]))/np.linalg.norm(tangent)
        taper=max(.015,min(1,distance/120,(distances[-1]-distance)/120))
        spread=width*taper*(.89+.10*math.sin(distance*.019)+.06*math.sin(distance*.057))
        sections.append((center+across*spread/2,center-across*spread/2))
    for j,(a,b) in enumerate(zip(sections,sections[1:])):
        m.polygon('mud_track',[(*p,.18) for p in (a[0],a[1],b[1],b[0])],
                  uv=((0,distances[j]/92),(1,distances[j]/92),(1,distances[j+1]/92),(0,distances[j+1]/92)))

def wheel(m,x,y,z,r=21,width=13):
    # Rounded radial profile with smooth authored normals. The tire has real sidewalls,
    # a recessed rim and raised tread; no flat black cylinder end cap.
    profile=[(r*.52,-width*.40),(r*.70,-width*.51),(r*.89,-width*.48),
             (r*.98,-width*.34),(r,-width*.18),(r,width*.18),
             (r*.98,width*.34),(r*.89,width*.48),(r*.70,width*.51),(r*.52,width*.40)]
    def point(angle,radial,axial): return np.array((x+math.cos(angle)*radial,y+axial,z+math.sin(angle)*radial))
    # A small convex tire proxy prevents capsules and bullet traces from
    # entering the visible wheels outside the narrower body/chassis hulls.
    m.hull([point(a,r,axial) for axial in (-width*.5,width*.5)
            for a in np.linspace(0,math.tau,12,endpoint=False)],'rubber')
    if isinstance(m,CollisionOnlyModel): return
    def emit(paint,pts,normals=None):
        face=np.cross(pts[1]-pts[0],pts[2]-pts[0]); center=np.mean(pts,axis=0)-np.array((x,y,z))
        if np.dot(face,center)<0:
            pts.reverse()
            if normals is not None: normals.reverse()
        m.polygon(paint,pts,normals=normals)
    for k in range(40):
        a,b=2*math.pi*k/40,2*math.pi*(k+1)/40
        for j in range(len(profile)-1):
            rr,aa=profile[j]; rs,ab=profile[j+1]
            pts=[point(a,rr,aa),point(b,rr,aa),point(b,rs,ab),point(a,rs,ab)]
            normals=[]
            for angle,idx in ((a,j),(b,j),(b,j+1),(a,j+1)):
                prev=np.array(profile[max(0,idx-1)]); nxt=np.array(profile[min(len(profile)-1,idx+1)])
                dr,dy=nxt-prev; normals.append((dy*math.cos(angle),-dr,dy*math.sin(angle)))
            emit('rubber',pts,normals)
        # Two rows of off-road tread blocks oriented around the axle.
        for side in (-1,1):
            angle=a+side*.025; center=point(angle,r+.25,side*width*.20)
            tangent=(-math.sin(angle),0,math.cos(angle)); radial=(math.cos(angle),0,math.sin(angle))
            m.oriented_box(center,(tangent,(0,-1,0),radial),(r*.12,width*.40,1),'rubber')
    for side in (-1,1):
        yy=side*width*.37
        for k in range(32):
            a,b=2*math.pi*k/32,2*math.pi*(k+1)/32
            emit('steel',[point(a,r*.54,yy),point(b,r*.54,yy),point(b,r*.35,yy+side*.8),point(a,r*.35,yy+side*.8)])
            emit('steel',[point(a,r*.35,yy+side*.8),point(b,r*.35,yy+side*.8),np.array((x,y+yy+side*.8,z))])
        # Dark recessed cooling holes and an axle cap break up the former
        # featureless rim disk. The profile around the rim remains continuous.
        for angle in np.linspace(0,math.tau,8,endpoint=False):
            bx,bz=x+r*.43*math.cos(angle),z+r*.43*math.sin(angle)
            face=y+yy+side*1.05
            # A masked-looking dark recess needs only a disk, not a capped
            # cylinder for each hole. Keep it clear of the angled rim lip.
            points=[np.array((bx+math.cos(a)*r*.058,face,bz+math.sin(a)*r*.058))
                    for a in np.linspace(0,math.tau,12,endpoint=False)]
            if side>0: points.reverse()
            m.polygon('rubber',points)
        tube(m,(x,y+yy+side*.85,z),(x,y+yy+side*2.6,z),r*.18,'steel',segments=20)
        for angle in np.linspace(0,2*math.pi,8,endpoint=False):
            bx,bz=x+r*.26*math.cos(angle),z+r*.26*math.sin(angle)
            bevel_box(m,(bx-.75,y+yy-1,bz-.75),(bx+.75,y+yy+1,bz+.75),'steel',.3)

def vehicle_canvas(m):
    """Canvas over five bows: rounded shoulders, gravity sag and gathered flaps."""
    profile=[(-44,50),(44,50),(44,113),(38,124),(25,130),(-25,130),(-38,124),(-44,113)]
    m.hull([(xx,yy,zz) for xx in (-139,41) for yy,zz in profile],'metal')
    if isinstance(m,CollisionOnlyModel): return
    def cloth(s,u):
        xx=-139+180*s
        if u<.2: yy,zz=-44,50+62*u/.2
        elif u>.8: yy,zz=44,112-62*(u-.8)/.2
        else:
            a=((u-.2)/.6-.5)*math.pi
            yy,zz=44*math.sin(a),112+18*math.cos(a)
        between=math.sin((xx+133)/41*math.pi)**2
        side=min(1,abs(yy)/44)**4
        wrinkle=(1.25*between+.65*math.sin(zz*.25+xx*.14))*side*math.sin((zz-50)/80*math.pi)
        yy+=math.copysign(wrinkle,yy if yy else 1)
        zz-=1.7*between*(1-side)
        return np.array((xx,yy,zz))
    def normal(s,u):
        return K.normalise(np.cross(cloth(s+.0001,u)-cloth(s-.0001,u),cloth(s,u+.0001)-cloth(s,u-.0001)))
    for k in range(30):
        for j in range(30):
            coords=[(k/30,j/30),((k+1)/30,j/30),((k+1)/30,(j+1)/30),(k/30,(j+1)/30)]
            m.polygon('tarp',[cloth(s,u) for s,u in coords],
                      uv=[(s*180/96,u*230/96) for s,u in coords],normals=[normal(s,u) for s,u in coords])
    m.polygon('tarp',[(41,yy,zz) for yy,zz in profile])
    def flap(u,v):
        yy=-44+88*u; top=112+18*math.sqrt(max(0,1-(yy/44)**2))
        zz=67+(top-67)*v
        gathered=(1.5*math.cos(yy*.31)+.6*math.cos(yy*.73+v*5))*math.sin(v*math.pi)*math.sin(u*math.pi)
        return np.array((-139-gathered,yy,zz))
    for k in range(24):
        for j in range(12):
            coords=[(k/24,j/12),(k/24,(j+1)/12),((k+1)/24,(j+1)/12),((k+1)/24,j/12)]
            normals=[]
            for u,v in coords:
                dy=flap(u+.0001,v)-flap(u-.0001,v); dz=flap(u,v+.0001)-flap(u,v-.0001)
                normals.append(K.normalise(np.cross(dz,dy)))
            m.polygon('tarp',[flap(u,v) for u,v in coords],uv=[(u,v) for u,v in coords],normals=normals)
    for yy in (-32,0,32):
        tube(m,(-141,yy,72),(-141,yy,118),.38,'tarp',segments=6)
    tube(m,(-142,-32,124),(-142,32,124),2.2,'tarp',segments=12)


def truck(m,e,n,angle=0,apc=False):
    t=model(not isinstance(m,CollisionOnlyModel))
    if apc:
        lower=[(-145,-54),(90,-54),(142,-40),(151,-27),(151,27),(142,40),(90,54),(-145,54)]
        shoulder=[(-142,-54),(90,-54),(139,-38),(146,-25),(146,25),(139,38),(90,54),(-142,54)]
        deck=[(-138,-46),(88,-46),(124,-32),(131,-23),(131,23),(124,32),(88,46),(-138,46)]
        loft(t,[[(x,y,33) for x,y in lower],[(x,y,60) for x,y in shoulder],[(x,y,79) for x,y in deck]],'olive','metal')
        base=[(-110,-47),(88,-47),(115,-30),(115,30),(88,47),(-110,47)]
        top=[(-105,-40),(82,-40),(106,-26),(106,26),(82,40),(-105,40)]
        loft(t,[[(x,y,79) for x,y in base],[(x,y,101) for x,y in top]],'olive','metal')
        tube(t,(-20,0,101),(-20,0,107),26,'steel',segments=32)
        tube(t,(-20,0,107),(-20,0,119),20,'olive',segments=32)
        tube(t,(-3,0,117),(62,0,121),1.8,'steel',segments=12)
        tube(t,(52,0,120.4),(66,0,121.25),3,'steel',segments=12)
        tube(t,(66.1,0,121.25),(66.3,0,121.26),1.75,'rubber',segments=12)
        tube(t,(-25,0,119),(-25,0,121),11,'olive',segments=24)
        tube(t,(-28,-5,122),(-22,-5,122),.65,segments=8)
        tube(t,(-28,-5,121),(-28,-5,122),.65,segments=8)
        tube(t,(-22,-5,121),(-22,-5,122),.65,segments=8)
        for x in (-104,-37,33,106):
            tube(t,(x,-58,23),(x,58,23),3.1,segments=12)
            for side in (-1,1):
                wheel(t,x,side*58,23,23,16)
                tube(t,(x-16,side*39,44),(x+12,side*53,25),1.8,segments=10)
                for k in range(12):
                    a,b=math.pi*k/12,math.pi*(k+1)/12
                    points=[(x+math.cos(a)*27,side*48,23+math.sin(a)*27),
                            (x+math.cos(b)*27,side*48,23+math.sin(b)*27),
                            (x+math.cos(b)*27,side*67,23+math.sin(b)*27),
                            (x+math.cos(a)*27,side*67,23+math.sin(a)*27)]
                    t.polygon('olive',points,both_sides=True)
        for yy in (-17,17):
            bevel_box(t,(108,yy-10,83),(113,yy+10,92),'steel',.5)
            panel(t,[(113.1,yy-8,85),(113.1,yy+8,85),(113.1,yy+8,90),(113.1,yy-8,90)],'glass')
        # Mount the lamps on the actual sloped glacis. The old x=136 mounts
        # at z=51..59 sat inside the hull (its bow is x=146..151 there).
        bow_normal=K.normalise((19,0,15))
        def bow(y,z,offset=.12):
            return np.array((146-(z-60)*15/19,y,z))+bow_normal*offset
        for yy in (-18,18):
            center=bow(yy,69)
            tube(t,center,center+bow_normal*3,4.5,'olive',segments=20)
            tube(t,center+bow_normal*3,center+bow_normal*3.3,3.7,'steel',segments=20)
            tube(t,center+bow_normal*3.31,center+bow_normal*3.36,2.9,'lamp',segments=20)
            for dz in (-2,2):
                tube(t,bow(yy-4,69+dz,3.8),bow(yy+4,69+dz,3.8),.32,segments=6)
        # A shallow service hatch, weld seams and captive fasteners follow the
        # armor plane rather than intersecting it as axis-aligned boxes would.
        hatch=[bow(-11,63),bow(11,63),bow(11,77),bow(-11,77)]
        t.polygon('steel',hatch)
        inner=[bow(-10.6,63.4,.18),bow(10.6,63.4,.18),bow(10.6,76.6,.18),bow(-10.6,76.6,.18)]
        t.polygon('olive',inner)
        for yy in (-8,8):
            for zz in (65,75):
                center=bow(yy,zz,.26)
                tube(t,center,center+bow_normal*.3,.55,'steel',segments=6)
        bevel_box(t,(-99,-34,101),(-66,34,105),'steel',.8)
        for x in np.arange(-96,-68,4):
            t.beam((x,-31,105.2),(x+1.5,31,106.1),(1.5,1.5),'olive')
        for x in (24,61):
            tube(t,(x,-16,101),(x,-16,102.5),12,'olive',segments=24)
            tube(t,(x-4,-17,103.5),(x+4,-17,103.5),.5,segments=8)
        for side in (-1,1):
            # Upper troop-compartment access panels sit on the inward sloping
            # side armor, with narrow welded borders and small folding handles.
            def side_point(x,z,offset=.15):
                return np.array((x,side*(47-(z-79)*7/22+offset),z))
            for left,right in ((-103,-59),(-55,-11),(32,75)):
                corners=[side_point(left,82),side_point(right,82),side_point(right,97),side_point(left,97)]
                if side>0: corners.reverse()
                t.polygon('steel',corners)
                inner=[side_point(left+.4,82.4,.21),side_point(right-.4,82.4,.21),
                       side_point(right-.4,96.6,.21),side_point(left+.4,96.6,.21)]
                if side>0: inner.reverse()
                t.polygon('olive',inner)
                for xx in (left+2,right-2):
                    for zz in (84,95):
                        center=side_point(xx,zz,.3)
                        tube(t,center,center+np.array((0,side*.4,0)),.45,'steel',segments=6)
                xx=(left+right)/2
                tube(t,side_point(xx-3,91,.7),side_point(xx+3,91,.7),.45,'steel',segments=8)
            for xx in (-125,-65,0,60,95):
                tube(t,(xx,side*52.5,64),(xx,side*53,64),.75,'steel',segments=8)
            for xx in (-130,-92):
                bevel_box(t,(xx-8,min(side*47,side*52),66),(xx+8,max(side*47,side*52),83),'olive',1)
                tube(t,(xx-4,side*51,84),(xx+4,side*51,84),.7,segments=8)
            tube(t,(-120,side*34,94),(-120,side*34,158),.45,segments=8)
            pts=[(-45,side*52.90,63),(16,side*52.90,63),(16,side*48.68,73),(-45,side*48.68,73)]
            if side>0: pts.reverse()
            panel(t,pts,'vehicle_stencil_1')
        bevel_box(t,(-148,-37,36),(-144,37,69),'olive',.7)
        for yy in (-23,23):
            tube(t,(-149,yy-5,53),(-149,yy+5,53),1,segments=10)
        # Tow eye and simple bow winch stay within the vehicle silhouette.
        tube(t,(139,-13,37),(139,13,37),5,'steel',segments=16)
        tube(t,(148,-23,36),(148,23,36),2,'steel',segments=10)
    else:
        box(t,(-140,-41,25),(126,41,36),'steel')
        bevel_box(t,(48,-45,37),(134,45,82),'olive',2,'metal')
        # Slanted cab front, narrow A pillars and inset upper glass.
        loft(t,[[(48,-45,82),(134,-45,82),(134,45,82),(48,45,82)],
                [(50,-41,119),(114,-41,119),(114,41,119),(50,41,119)]],'olive','metal')
        bevel_box(t,(48,-44,118),(116,44,122),'olive',1)
        for side in (-1,1):
            yy=lambda zz: side*(45-(zz-82)*4/37+.18)
            pts=[(57,yy(86),86),(127,yy(86),86),(111,yy(114),114),(57,yy(114),114)]
            if side>0: pts.reverse()
            t.polygon('glass',pts)
            t.beam((87,yy(86)+side*.2,86),(86,yy(114)+side*.2,114),(1.1,1.1),'olive')
            bevel_box(t,(55,min(side*45.4,side*46.4),43),(126,max(side*45.4,side*46.4),81),'olive',.2)
            box(t,(57,min(side*46.5,side*47.6),73),(67,max(side*46.5,side*47.6),75),'steel')
            # Folded access steps and an outer wheel fender.
            for zz,xx in ((25,53),(32,55)):
                bevel_box(t,(xx,min(side*45,side*57),zz),(xx+18,max(side*45,side*57),zz+2),'steel',.4)
            for k in range(12):
                a,b=math.pi*k/12,math.pi*(k+1)/12
                pts=[(93+math.cos(a)*26,side*42,22+math.sin(a)*26),
                     (93+math.cos(b)*26,side*42,22+math.sin(b)*26),
                     (93+math.cos(b)*26,side*59,22+math.sin(b)*26),
                     (93+math.cos(a)*26,side*59,22+math.sin(a)*26)]
                t.polygon('olive',pts,both_sides=True)
        def windshield(xy,z): return 134-(z-82)*20/37+.3,xy,z
        t.polygon('glass',[windshield(-39,87),windshield(39,87),windshield(36,114),windshield(-36,114)])
        t.beam(windshield(0,87),windshield(0,114),(1.2,1.2),'olive')
        for yy in (-21,21):
            t.beam(windshield(yy-12,89),windshield(yy+10,92),(1,.7),'rubber')
        bevel_box(t,(131,-47,38),(139,47,45),'steel',1)
        bevel_box(t,(-139,-44,37),(41,44,50),'olive',1.2,'metal')
        vehicle_canvas(t)
        for x in (-133,-92,-51,-10,35):
            for side in (-1,1):
                for zz in (55,68,81,94,107):
                    t.beam((x,side*44.3,zz),(x,side*44.8,zz+7),(.65,.65),'rubber')
                box(t,(x-1.5,min(side*45,side*46),48),(x+1.5,max(side*45,side*46),51),'steel')
        # Tailgate hinges, inset rear curtain, reflectors, chassis and spare tire.
        bevel_box(t,(-141,-44,39),(-139,44,67),'olive',.5)
        for yy in (-28,28):
            box(t,(-143,yy-4,40),(-141,yy+4,48),'steel')
            box(t,(-143,yy-5,60),(-141,yy+5,63),'yellow')
        for x in (-104,-45,93):
            t.beam((x,-48,22),(x,48,22),(7,7),'steel')
        bevel_box(t,(-13,-49,24),(30,-38,39),'steel',2)
        for x in (-104,-45,93):
            for yy in (-48,48): wheel(t,x,yy,22)
        for yy in (-33,33):
            bevel_box(t,(134,yy-8,54),(138,yy+8,67),'steel',1)
            box(t,(138,yy-6,56),(138.4,yy+6,65),'lamp')
        for yy in (-59,59):
            t.beam((90,yy*.76,96),(87,yy,108),(2,2),'steel')
            box(t,(82,yy-2,98),(92,yy+2,111),'steel')
        box(t,(134,-21,48),(135,21,74),'rubber')
        for z in np.arange(49,73,4): box(t,(135,-20,z),(136,20,z+1.5),'steel')
        for side in (-1,1):
            yy=side*47.65
            pts=[(76,yy,54),(121,yy,54),(121,yy,65),(76,yy,65)]
            if side>0: pts.reverse()
            panel(t,pts,'vehicle_stencil_0')
            # Door hinges, stamped panel lip and fasteners at the bed rails.
            for zz in (47,71): bevel_box(t,(125,min(side*46,side*48),zz),(128,max(side*46,side*48),zz+4),'steel',.3)
            for xx in (-129,-92,-51,-10,33):
                tube(t,(xx,side*44.1,44),(xx,side*44.8,44),.55,'steel',segments=8)
        tube(t,(43,38,47),(43,38,125),2.3,'steel',segments=12)
        tube(t,(43,38,125),(43,38,139),1.4,'steel',segments=12)
        bevel_box(t,(54,-23,122.1),(74,23,124),'olive',.7)
        for yy in (-12,12): tube(t,(56,yy,124),(72,yy,124),.4,'steel',segments=8)
    # Rename vehicle surfaces rather than overriding the shared chunk's olive,
    # steel or tarp bindings, which also belong to buildings and logistics.
    vehicle=model(not isinstance(m,CollisionOnlyModel)); mapping={'olive':'vehicle_paint','steel':'vehicle_metal','rubber':'vehicle_rubber','tarp':'vehicle_canvas','glass':'vehicle_glass'}
    for paint,faces in t.polygons.items():
        target=mapping.get(paint,paint)
        for i,(points,normal) in enumerate(faces):
            vehicle.polygon(target,points,normal=normal,uv=t.polygon_uvs.get((paint,i)),normals=t.polygon_normals.get((paint,i)))
    vehicle.boxes.extend(t.boxes); vehicle.hulls.extend(t.hulls)
    m.extend(transform(vehicle,(e,n,0),angle))

def bench(m,e,n,z=0):
    box(m,(e-70,n-20,z+32),(e+70,n+20,z+37),'timber','wood')
    for x in (e-62,e+62):
        for y in (n-15,n+15): box(m,(x-3,y-3,z),(x+3,y+3,z+32),'steel')
    for k in range(7):
        x=e-52+k*17
        box(m,(x-2,n+18,z+45),(x+2,n+21,z+68),'steel')
        box(m,(x-6,n+18,z+43),(x+6,n+21,z+46),'yellow')

def shelf(m,e,n,z=0):
    for x in (e-60,e+60):
        for y in (n-21,n+21): box(m,(x-2,y-2,z),(x+2,y+2,z+114),'steel')
    for zz in (14,46,78,110):
        box(m,(e-64,n-24,z+zz),(e+64,n+24,z+zz+3),'steel')
        for k in (-1,1): crate(m,e+k*33,n,z+zz+3,w=37,h=26)
    m.collision_box((e-64,n-24,z),(e+64,n+24,z+114),'metal')

def console(m,e,n,z):
    # Dual displays, keyboard, rack controller and a seat; all fit against the rear wall.
    box(m,(e-70,n-20,z+32),(e+70,n+20,z+37),'steel','metal')
    for x in (e-62,e+62):
        for y in (n-15,n+15): box(m,(x-3,y-3,z),(x+3,y+3,z+32),'steel')
    for offset in (-34,34):
        x=e+offset
        box(m,(x-3,n+8,z+37),(x+3,n+12,z+48),'steel')
        box(m,(x-30,n+9,z+47),(x+30,n+15,z+84),'steel')
        panel(m,[(x-27,n+8.8,z+50),(x+27,n+8.8,z+50),(x+27,n+8.8,z+81),(x-27,n+8.8,z+81)],'screen')
        box(m,(x-22,n-17,z+37),(x+22,n-4,z+39),'rubber')
        for row in range(4):
            for key in range(12):
                box(m,(x-20+key*3.4,n-16+row*3,z+39),(x-17.5+key*3.4,n-14+row*3,z+39.7),'steel')
    box(m,(e+48,n-13,z),(e+68,n+16,z+29),'steel','metal')
    for zz in range(5,27,4): box(m,(e+51,n-13.2,z+zz),(e+65,n-13,z+zz+1),'glass')
    for x in (e-17,e+17):
        for y in (n-56,n-29): box(m,(x-2,y-2,z),(x+2,y+2,z+24),'steel')
    box(m,(e-20,n-59,z+23),(e+20,n-27,z+28),'rubber')
    box(m,(e-20,n-59,z+28),(e+20,n-54,z+53),'rubber')

def building(name,c,size,base=96,command=False,visual=True):
    m=model(visual); e,n=c; w,d=size; x0,x1=e-w/2,e+w/2; y0,y1=n-d/2,n+d/2
    # Platform does not fill doorways; front apron is 96 high, reached by two 12-inch stair runs.
    box(m,(x0-85,y0-90,0),(x1+85,y1+55,base),'concrete','concrete')
    floor=base+144; roof=base+288
    box(m,(x0,y0,base-8),(x1,y1,base),'concrete','concrete')
    # Keep the stairwell cut open in the upper slab. This was a critical clearance issue in old scripted maps.
    sx=x1-138
    box(m,(x0,y0,floor-10),(sx-54,y1,floor),'concrete','concrete')
    box(m,(sx-54,y1-42,floor-10),(x1,y1,floor),'concrete','concrete')
    box(m,(x0,y0,roof-10),(x1,y1,roof),'roof','metal')
    for level in (base,floor):
        windows=[(x,62,level+50,level+110) for x in np.arange(x0+72,sx-100,120)]
        wall(m,'e',(x0,x1),(y0,y0+10),(level,level+134),'-n',[(e,96,level,level+105)],windows)
        wall(m,'e',(x0,x1),(y1-10,y1),(level,level+134),'+n',[(e-100,88,level,level+105)],[(x0+95,64,level+50,level+110)])
        wall(m,'n',(y0,y1),(x0,x0+10),(level,level+134),'-e',[(n,88,level,level+105)],[(y1-75,56,level+50,level+110)])
        wall(m,'n',(y0,y1),(x1-10,x1),(level,level+134),'+e',[(n,88,level,level+105)])
        # A central hallway and two small rooms. Its cross-partition has two usable doors.
        wall(m,'e',(x0+10,sx-55),(n+15,n+23),(level,level+134),None,
             [(x0+90,80,level,level+104),(sx-130,80,level,level+104)])
        wall(m,'n',(n+23,y1-10),(e-105,e-97),(level,level+134),None)
        for x in (x0+60,e+20):
            if command:
                console(m,x,y1-60,level)
            else:
                box(m,(x-45,y1-70,level+16),(x+45,y1-29,level+23),'steel')
                box(m,(x-43,y1-69,level+23),(x+43,y1-30,level+32),'tarp')
                box(m,(x-42,y1-68,level+32),(x-23,y1-31,level+38),'plaster')
                m.collision_box((x-45,y1-70,level),(x+45,y1-29,level+32),'wood')
                shelf(m,x,n+58,level)
        # Room light; nonshadowed bounced light keeps the budget modest.
        LIGHTS.append((name+f' room {level}',(e-90,n+55,level+118),'4.2,2.7,1.3,1',350,False))
        bevel_box(m,(e-137,n+43,level+125),(e-53,n+55,level+132),'steel',.9)
        bevel_box(m,(e-134,n+45,level+124.5),(e-56,n+53,level+125),'lamp',.15)
        for x in (e-123,e-95,e-67): box(m,(x-.5,n+44.7,level+124.2),(x+.5,n+53.3,level+125),'steel')
    stairs(m,(sx,y0+60,base),(sx,y1-42,floor),100)
    # Exterior balcony is an actual ring, not a slab blocking the stair opening.
    box(m,(x0-80,y0-82,floor-6),(x1+80,y0,floor),'steel','metal')
    box(m,(x0-80,y0,floor-6),(x0,y1+45,floor),'steel','metal')
    box(m,(x1,y0,floor-6),(x1+80,y1+45,floor),'steel','metal')
    box(m,(x0,y1,floor-6),(x1,y1+45,floor),'steel','metal')
    rail(m,(x0-80,y0-82,floor),(e-55,y0-82,floor))
    rail(m,(e+55,y0-82,floor),(x1+80,y0-82,floor))
    rail(m,(x0-80,y0-82,floor),(x0-80,n-55,floor))
    rail(m,(x0-80,n+55,floor),(x0-80,y1+45,floor))
    rear_edge=y1+(100 if command else 45)
    rail(m,(x0-80,rear_edge,floor),(x1+80,rear_edge,floor))
    # Leave a balcony opening for the bridge on the building's east edge.
    rail(m,(x1+80,y0-82,floor),(x1+80,n-55,floor))
    rail(m,(x1+80,n+55,floor),(x1+80,y1+45,floor))
    stairs(m,(e,y0-82-540,0),(e,y0-82,floor),100)
    stairs(m,(x0-20,y0-90-216,0),(x0-20,y0-90,base),110)
    stairs(m,(x1+20,y0-90-216,0),(x1+20,y0-90,base),110)
    # Fascia panels, pilasters, drainage downpipes, window hoods and slab coping.
    for x in np.arange(x0+10,x1,96):
        box(m,(x-3,y0-3,base),(x+3,y0,roof),'steel')
    for z in (base+3,floor+3,roof-8):
        box(m,(x0-3,y0-5,z),(x1+3,y0,z+6),'steel')
    for x in (x0+14,x1-14):
        tube(m,(x,y0-10,base+9),(x,y0-10,roof-16),2.2)
        elbow=[(x,y0-10+4*(1-math.cos(t)),roof-16+4*math.sin(t)) for t in np.linspace(0,math.pi/2,5)]
        for a,b in zip(elbow,elbow[1:]): tube(m,a,b,2.2)
        tube(m,elbow[-1],(x,y0-6,roof-2),2.2)
        for zz in np.arange(base+30,roof-20,72):
            box(m,(x-3.2,y0-13.2,zz),(x+3.2,y0-2,zz+1.8),'steel')
        tube(m,(x,y0-10,base+9),(x,y0-18,base+5),2.2)
    tube(m,(x0-3,y0-6,roof-2),(x1+3,y0-6,roof-2),3)
    for x in (x0+70,e,x1-85):
        for z in (base+118,floor+118):
            bulkhead(m,x,y0-3,z+2.5)
            LIGHTS.append((f'{name} door {x} {z}',(x,y0-23,z-10),'4.3,2.5,1.1,1',260,False))
    for level in (base,floor):
        wall_services(m,x1-43,y0-3,level+29)
        wall_services(m,x1-48,y1+3,level+29,180)
    sign(m,(e-160,y0-6),base+113,'C' if command else 'B',140)
    if command:
        # Roof access: two opposite external stairs, avoiding a single dominant perch.
        # Roof stairs on the rear apron leave both side balcony bridge joints unobstructed.
        box(m,(x0-80,y1,floor-6),(x1+80,y1+100,floor),'steel','metal')
        stairs(m,(x0-8,y1+48,floor),(e,y1+48,roof),76,topgap=70)
        stairs(m,(x1+8,y1+48,floor),(e,y1+48,roof),76,topgap=70)
        # Narrow join starts at the final tread; a wide landing here creates a 24-inch capsule snag.
        box(m,(e-24,y1-30,roof-6),(e+24,y1+100,roof),'steel','metal')
        for a,b in [((x0,y0,roof),(x1,y0,roof)),((x0,y0,roof),(x0,y1,roof)),((x1,y0,roof),(x1,y1,roof))]: rail(m,a,b)
        crate(m,e-100,n-70,roof,w=90,h=56)
        roof_plant(m,e+40,n-45,roof)
        # Mast and parabolic satellite dish, silhouetted against the waterfall as in all five references.
        for x in (e-25,e+25): m.beam((x,n+35,roof),(e,n+35,roof+285),(4,4),'steel')
        for z in range(30,281,45):
            m.beam((e-22,n+35,roof+z),(e+22,n+35,roof+z+36),(2,2),'steel')
        for x in (-70,0,65):
            m.beam((e+x,n+35,roof+50),(e+x,n+35,roof+350-abs(x)),(2,2),'steel')
            box(m,(e+x-2,n+33,roof+345-abs(x)),(e+x+2,n+37,roof+350-abs(x)),'lamp')
        dish(m,(e+175,n+40,roof+136),76)
    else:
        roof_plant(m,x0+40,y1-115,roof,135,90,68,solid=None)
        crate(m,e,n,roof,w=76,h=56)
    return m

def dish(m,c,r):
    c=np.array(c,float)
    # Dish opens towards south and is tilted up, with smooth per-vertex normals.
    axis=K.normalise((0,-.84,.54)); u=np.array((1,0,0)); v=np.cross(axis,u)
    def at(rad,theta): return c+u*rad*math.cos(theta)+v*rad*math.sin(theta)+axis*(rad/r)**2*25
    def normal(rad,theta): return K.normalise(axis-(u*math.cos(theta)+v*math.sin(theta))*50*rad/(r*r))
    for ring in range(6):
        for seg in range(40):
            a,b=2*math.pi*seg/40,2*math.pi*(seg+1)/40
            pts=[at(r*ring/6,a),at(r*(ring+1)/6,a),at(r*(ring+1)/6,b),at(r*ring/6,b)]
            normals=[normal(r*ring/6,a),normal(r*(ring+1)/6,a),normal(r*(ring+1)/6,b),normal(r*ring/6,b)]
            if ring==0: pts=pts[:3]; normals=normals[:3]
            uv=[(.5+np.dot(p-c,u)/(r*2),.5+np.dot(p-c,v)/(r*2)) for p in pts]
            m.polygon('dish_paint',pts,normals=normals,uv=uv)
            # The generic double-sided helper copies a flat back normal. Preserve
            # the curved normals and continuous projection on both physical faces.
            order=[0]+list(range(len(pts)-1,0,-1))
            m.polygon('dish_paint',[pts[i] for i in order],normals=[-normals[i] for i in order],uv=[uv[i] for i in order])
    for a in (0,2*math.pi/3,4*math.pi/3): m.beam(at(r,a),c+axis*65,(2,2),'steel')
    m.beam(c-(0,0,80),c,(5,5),'steel')
    m.beam(c+axis*52,c+axis*69,(8,8),'steel')

def shed(c,size,workshop=False,visual=True):
    m=model(visual); e,n=c; w,d=size; x0,x1=e-w/2,e+w/2; y0,y1=n-d/2,n+d/2
    box(m,(x0-20,y0-28,-8),(x1+20,y1+20,0),'concrete','concrete')
    wall(m,'e',(x0,x1),(y1-10,y1),(0,180),'+n')
    if workshop:
        wall(m,'e',(x0,x1),(y0,y0+10),(0,180),'-n',[(e,240,0,152)])
        wall(m,'n',(y0,y1),(x0,x0+10),(0,180),'-e',[(n-40,96,0,105)])
        wall(m,'n',(y0,y1),(x1-10,x1),(0,180),'+e',[(n+70,96,0,105)])
        for x in np.arange(x0+12,x1,32): box(m,(x,y0-3,0),(x+3,y0,180),'steel')
    else:
        for x in (x0,x1): box(m,(x-4,y0,0),(x+4,y1,170),'steel')
    # Two pitched roof planes and visible trusses, with roof-sheet ridges.
    ridge=205
    for a,b in ((y0-18,n),(n,y1+18)):
        za,zb=(176,ridge) if a<n else (ridge,176)
        m.polygon('roof',[(x0-20,a,za),(x1+20,a,za),(x1+20,b,zb),(x0-20,b,zb)],both_sides=True)
    for x in np.linspace(x0,x1,5):
        m.beam((x,y0,172),(x,n,ridge),(5,5),'steel')
        m.beam((x,n,ridge),(x,y1,172),(5,5),'steel')
        m.beam((x,y0,172),(x,y1,172),(4,4),'steel')
        for y in (y0,y1):
            box(m,(x-4,y-4,0),(x+4,y+4,172),'steel','metal')
            m.beam((x,y,140),(x+(25 if x<e else -25),y,172),(4,4),'steel')
    for x in (e-w*.25,e+w*.25):
        box(m,(x-40,n-4,168),(x+40,n+4,171),'lamp')
        LIGHTS.append((f'Hangar {e} {x}',(x,n,145),'4.6,3.2,1.6,1',490,True))
    sign(m,(e,y0-12),156,'E' if workshop else 'A',160)
    if workshop:
        for x in (x0+85,x1-85):
            bench(m,x,y1-50); shelf(m,x,y1-105)
        truck(m,e-80,n+40,90)
        for x in (e-140,e+40): box(m,(x-6,n-130,0),(x+6,n+30,115),'yellow','metal')
        wheel(m,x1-65,n-65,22)
    else:
        truck(m,e-w*.28,n,90); truck(m,e+w*.22,n,90)
        bench(m,x0+85,y1-55)
    return m

def bridge(m,a,b,width=104):
    a,b=np.array(a,float),np.array(b,float)
    delta=b-a; side=np.cross((0,0,1),K.normalise(delta))
    m.beam(a-(0,0,3),b-(0,0,3),(width,6),'steel','metal')
    for s in (-1,1):
        aa,bb=a+side*width/2,b+side*width/2
        rail(m,aa,bb)
        m.beam(aa-(0,0,32),bb-(0,0,32),(4,4),'steel')
        for k in range(math.ceil(np.linalg.norm(delta)/100)):
            f0=k/math.ceil(np.linalg.norm(delta)/100); f1=(k+1)/math.ceil(np.linalg.norm(delta)/100)
            p,q=aa+(bb-aa)*f0,aa+(bb-aa)*f1
            m.beam(p-(0,0,30),q,(3,3),'steel')
            m.beam(p,q-(0,0,30),(3,3),'steel')
    for f in (.05,.5,.95):
        p=a+(b-a)*f
        for s in (-1,1):
            q=p+side*(width/2-4)
            box(m,(q[0]-2.5,q[1]-2.5,0),(q[0]+2.5,q[1]+2.5,q[2]-5),'steel','metal')
    ROUTES.append(dict(kind='bridge',start=list(a),end=list(b),width=width))

def fence(m,a,b,h=120):
    a,b=np.array((*a,0),float),np.array((*b,0),float)
    delta=b-a; along=K.normalise(delta); side=np.cross((0,0,1),along)
    count=math.ceil(np.linalg.norm(delta)/160)
    for f in np.linspace(0,1,count+1):
        p=a+delta*f
        m.beam(p,p+(0,0,h+16),(3,3),'steel')
        m.beam(p+(0,0,h),p+(0,0,h+16)+side*14,(2,2),'steel')
    # Fixed collision is tall enough to prevent jumping/mantling over; alpha card is perforated visually.
    m.collision_box(np.minimum(a,b)-(3,3,0),np.maximum(a,b)+(3,3,h),'metal')
    pts=[a+(0,0,4),b+(0,0,4),b+(0,0,h),a+(0,0,h)]
    length=np.linalg.norm(delta)
    m.polygon('fence',pts,both_sides=True,uv=((0,h/64),(length/64,h/64),(length/64,0),(0,0)))
    for z in (h-2,h+13): m.beam(a+(0,0,z),b+(0,0,z),(1,1),'steel')

def barrier(m,a,b):
    a,b=np.array(a,float),np.array(b,float); delta=b-a; length=np.linalg.norm(delta)
    t=model(not isinstance(m,CollisionOnlyModel)); t.prism([(-length/2,-14),(length/2,-14),(length/2,14),(-length/2,14)],0,38,'concrete','concrete')
    box(t,(-length/2,-7,38),(length/2,7,46),'concrete','concrete')
    m.extend(transform(t,(*(a+b)/2,0),math.degrees(math.atan2(delta[1],delta[0]))))

def rock(m,c,size,seed,kind=None):
    rng=np.random.default_rng(seed); c=np.array(c,float); size=np.array(size,float)
    kind=kind or ('cliff' if seed in range(130,143) else 'boulder')
    if (OUT/f'{kind}/cliff.vmdl').exists():
        if kind=='boulder': size[2]*=.62 if seed!=87 else 1
        yaw=float(rng.uniform(0,360)) if kind=='boulder' else 10
        INSTANCES.append((f'Rock {seed}',f'{RES}/{kind}/cliff.vmdl',tuple(c),yaw,tuple(size)))
        return
    # Broken strata from irregular rings, smoothed normals; no playable rock collision beyond clips.
    rings,segments=12,23
    pts=[]
    for k in range(rings):
        z=k/(rings-1); rad=(1-.48*z)*(1+.12*math.sin(z*13+seed))
        pts.append([c+size*np.array((rad*math.cos(2*math.pi*j/segments+.2*k)*rng.uniform(.82,1.13),
                      rad*math.sin(2*math.pi*j/segments+.2*k)*rng.uniform(.82,1.13),z-.25+rng.uniform(-.035,.035))) for j in range(segments)])
    for k in range(rings-1):
        for j in range(segments):
            m.polygon('rock',[pts[k][j],pts[k][(j+1)%segments],pts[k+1][(j+1)%segments],pts[k+1][j]])
    m.polygon('rock',pts[-1])

def tree(seed=0,lod=0):
    m=model(); rng=np.random.default_rng(seed); height=850
    m.cylinder((0,0),10,0,height*.94,'bark',sides=10 if lod==0 else 6)
    tiers=(19,11,6)[lod]; branches=(8,6,4)[lod]
    for k,z in enumerate(np.linspace(95,height-25,tiers)):
        radius=170*(1-z/height)**.75+12
        for j in range(branches):
            a=2*math.pi*j/branches+k*2.399+rng.uniform(-.18,.18)
            forward=np.array((math.cos(a),math.sin(a),0)); side=np.cross((0,0,1),forward)
            root=np.array((0,0,z)); tip=root+forward*radius+(0,0,-radius*.16)
            if lod==0: m.beam(root,tip,(2,2),'bark')
            # Branch fans have twig alpha silhouettes; tiers vary in yaw, droop and spread.
            for tilt in (0,.6) if lod==0 else (0,):
                lateral=side*radius*.43+np.array((0,0,radius*tilt))
                pts=[root-lateral*.1,tip-lateral,tip+lateral,root+lateral*.1]
                panel(m,pts,'needles'); m.polygon('needles',pts[::-1],uv=((0,0),(1,0),(1,1),(0,1)))
    return m

def write_trees():
    for variant in range(3):
        name=f'fir_{variant}'
        for lod in range(3): K.write_model(OUT,RES,f'{name}_lod{lod}',tree(variant+20,lod))
        # Proven ModelDoc LOD syntax from the project's grass assets.
        source=(OUT/f'{name}_lod0.vmdl').read_text()
        start=source.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"')
        end=source.index('\n\t\t]\n',start)
        meshes='\t\t\t{ _class = "RenderMeshList" children = [\n'
        for lod in range(3):
            meshes += f' {{ _class = "RenderMeshFile" name = "lod{lod}" filename = "{RES}/{name}_lod{lod}.obj" import_scale = 1.0 import_rotation = [0,0,0] import_translation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }},\n'
        meshes+=' ] },\n { _class = "LODGroupList" children = [\n'
        for lod,threshold in enumerate((0,12,30)): meshes+=f' {{ _class = "LODGroup" switch_threshold = {threshold}.0 meshes = ["lod{lod}"] }},\n'
        meshes+=' ] },'
        K.write_text(OUT/f'{name}.vmdl',source[:start]+meshes+source[end:])

def build(visual_chunks=None):
    visuals=set(visual_chunks) if visual_chunks is not None else {'ground','yard','logistics','links','vista','motor','barracks','command','workshop'}
    LIGHTS.clear(); INSTANCES.clear(); ROUTES.clear(); SPOTS.clear()
    ground=model('ground' in visuals); yard=model('yard' in visuals); logistics=model('logistics' in visuals)
    links=model('links' in visuals); vista=model('vista' in visuals)
    box(vista,(-7000,-7000,-430),(7000,7000,-350),'mud')
    # Inaccessible forest floor meets the tree roots. Leave the entrance gorge
    # below this level so the bridge, torrent and exposed banks keep their depth.
    for lo,hi in [((-7000,-7000,-125),(-1550,7000,-120)),
                  ((1550,-7000,-125),(7000,7000,-120)),
                  ((-1550,1450,-125),(1550,2820,-120)),
                  ((-1550,2820,-125),(-50,3510,-120)),
                  ((900,2820,-125),(1550,3510,-120)),
                  ((-1550,3510,-125),(1550,7000,-120)),
                  ((-1550,-7000,-125),(-550,-1450,-120)),
                  ((550,-7000,-125),(1550,-1450,-120))]:
        box(vista,lo,hi,'mud')
    # The fall has a real recessed plunge basin; it no longer disappears into
    # the raised leaf-litter slab. All of this stays beyond the northern clips.
    box(vista,(-50,2820,-330),(900,3510,-315),'mud')
    outer=[]; inner=[]
    for angle in np.linspace(0,2*math.pi,24,endpoint=False):
        x,y=math.cos(angle),math.sin(angle); ray=max(abs(x),abs(y))
        outer.append((425+x*475/ray,3165+y*345/ray,-120))
        variation=1+.055*math.sin(angle*5+.3)+.028*math.cos(angle*9)
        inner.append((425+x*365*variation,3165+y*230*variation,-285+math.sin(angle*7)*8))
    for k in range(24):
        j=(k+1)%24
        vista.polygon('mud',[outer[k],outer[j],inner[j],inner[k]])
    # A shallow leaf-litter bank joins the raised compound to the background
    # forest floor. It stays behind the existing fence and closed player clips.
    for side in range(4):
        segments=20
        for k in range(segments):
            lo=-1550+3100*k/segments; hi=-1550+3100*(k+1)/segments
            if side==3 and (lo<550 and hi>-550): continue
            def verge(along,depth):
                edge=1450 if side in (0,3) else 1550
                across=edge+depth
                e,n=(along,across) if side==0 else (-across,along) if side==1 else (across,along) if side==2 else (along,-across)
                return (e,n,-8-depth*112/300)
            for start,end in ((0,140),(140,300)):
                points=[verge(lo,start),verge(hi,start),verge(hi,end),verge(lo,end)]
                if side in (2,3): points.reverse()
                vista.polygon('mud',points)
    box(ground,(-1550,-1450,-18),(1550,1450,0),'asphalt','concrete')
    mud_track(ground,[(0,-1430),(10,-1180),(-12,-920),(16,-620),(0,-360)],170)
    mud_track(ground,[(1190,-1400),(1190,-1190),(1110,-880),(1270,-550),(1230,-200),(1250,125)],130)
    mud_track(ground,[(-1040,-910),(-835,-1010),(-530,-1120),(-210,-1135),(0,-1110)],120)
    # Shallow irregular rain puddles: visual overlays preserve the collision surface.
    rain=np.random.default_rng(932)
    for e,n,rx,ry in [(-530,-1240,130,48),(180,-1260,140,55),(1150,-1250,105,50),(-1280,-100,115,65),
                       (-640,430,85,48),(450,530,120,65),(1320,1060,80,45),(120,560,145,40),
                       (1070,-250,75,40),(430,-390,98,35),(-40,-470,80,48)]:
        pts=[]
        for a in np.linspace(0,2*math.pi,28,endpoint=False):
            r=rain.uniform(.84,1.12); pts.append((e+math.cos(a)*rx*r,n+math.sin(a)*ry*r,.38))
        ground.polygon('water',pts,uv=[(.5+(p[0]-e)/(rx*2.25),.5+(p[1]-n)/(ry*2.25)) for p in pts])
    for e in (-1545,1545): box(ground,(e-5,-1430,.05),(e+5,1430,.12),'mud')
    # Retaining ledges and wet verge strips; puddles follow the asphalt material's roughness mask.
    for a,b in [((-1550,-1450),(-1550,1450)),((1550,-1450),(1550,1450)),((-1550,1450),(1550,1450)),((-1550,-1450),(-180,-1450)),((180,-1450),(1550,-1450))]:
        fence(ground,a,b,150)
        barrier(ground,a,b)
    # Entrance bridge over the gorge is a short combat pocket, sealed at the outer gate.
    box(ground,(-180,-1710,-38),(180,-1450,0),'concrete','concrete')
    # Underside structure for the existing bridge footprint, rooted on the
    # gorge bed. These visual supports do not extend the playable deck.
    for e in (-140,140):
        box(vista,(e-18,-1710,-66),(e+18,-1450,-38),'concrete')
        for n in (-1500,-1650):
            box(vista,(e-35,n-40,-350),(e+35,n+40,-64),'concrete')
    for e0,e1 in ((-1550,-550),(550,1550)):
        box(vista,(e0,-1460,-125),(e1,-1450,0),'concrete')
    for e in (-170,170): rail(links,(e,-1710,0),(e,-1420,0),72)
    fence(ground,(-180,-1710),(180,-1710),150)
    barrier(ground,(-180,-1690),(180,-1690))
    for x in (-1460,-800,-180,520,1380): lamp(ground,x,-1200,shadow=x in (-800,520))
    for x,y in [(-1450,550),(-500,1300),(480,1330),(1440,650),(-600,50),(650,100)]: lamp(ground,x,y)
    # Road edge lines, parking bays and ground-level flank cover.
    for n in np.arange(-1370,250,120): box(ground,(-36,n,.15),(-30,n+64,.3),'yellow')
    for e in (-1350,-1120,-890):
        box(ground,(e,-980,.1),(e+165,-977,.25),'yellow')
        box(ground,(e,-980,.1),(e+3,-650,.25),'yellow')
    motor=shed((-1060,-555),(720,390),visual='motor' in visuals)
    barracks=building('Barracks',(-950,850),(680,430),visual='barracks' in visuals)
    command=building('Command',(265,920),(620,430),command=True,visual='command' in visuals)
    workshop=shed((1100,520),(660,560),workshop=True,visual='workshop' in visuals)
    truck(yard,-900,-995,0,True)
    truck(yard,-1360,-840,-20)
    # Two-high cargo shields the southwest spawns from elevated command sightlines.
    container(yard,-1250,-1100,length=400,height=114)
    container(yard,-1250,-1100,z=114,length=400,height=114)
    container(yard,-565,-630,angle=90)
    stack(yard,-1440,-305,rows=2,cols=2,height=2)
    stack(yard,-650,-1040,rows=2,cols=2,height=2)
    barrier(yard,(-575,-500),(-400,-500))
    # Low rocky island separates motor pool from barracks; front and east passages remain open.
    rock(vista,(-1180,135,-40),(270,125,155),87)
    fence(yard,(-1500,-220),(-980,-220),100)
    barrier(yard,(-980,-220),(-790,-220))
    # Central camouflaged logistics shelter, with actual narrow circulation between cases.
    box(logistics,(-375,-15,-4),(335,370,0),'concrete','concrete')
    for x in (-365,-15,325):
        for n in (0,360): box(logistics,(x-3,n-3,0),(x+3,n+3,126),'steel','metal')
    logistics.polygon('tarp',[(-395,-25,125),(350,-25,125),(350,385,138),(-395,385,138)],both_sides=True)
    for n in (0,360): logistics.beam((-375,n,125),(335,n,125),(4,4),'steel')
    stack(logistics,-290,290,rows=1,cols=3,height=2)
    stack(logistics,180,20,rows=2,cols=1,height=2)
    bench(logistics,-210,55)
    sign(logistics,(-145,-25),90,'D',128)
    LIGHTS.append(('Logistics task',(-30,100,115),'1.1,0.8,0.46,1',320,False))
    # Container alleys and staggered shipping cases block end-to-end shots. 100–160 inch gaps.
    for e,n,ang in [(680,-810,90),(1200,-1040,0),(1360,-290,90),(300,-1050,0),(680,-245,0),(-470,295,90)]:
        container(logistics,e,n,angle=ang)
    for e,n,rows,cols,h in [(870,-1150,2,2,2),(950,-620,2,2,2),(325,-625,2,2,2),(-120,-820,1,3,2),
                          (1250,-70,1,2,2),(425,335,1,2,2),(-655,110,1,1,2),(-770,590,1,1,1),(-260,1050,1,1,2)]:
        stack(logistics,e,n,rows=rows,cols=cols,height=h)
    # Stacked shipping cover screens the northeast team spawn from the command roof.
    # Both ends remain open for independent exits into the east and rear lanes.
    for east in (865,1225):
        container(logistics,east,1230,length=350,height=114)
        container(logistics,east,1230,z=114,length=350,height=114)
    # A forklift with fork carriage and driver cage, in the reference's southeast storage yard.
    f=model('logistics' in visuals); box(f,(-52,-28,18),(52,28,46),'yellow','metal')
    for x in (-32,35):
        for y in (-30,30): wheel(f,x,y,15,15,9)
    for x in (-30,32):
        for y in (-24,24): f.beam((x,y,40),(x,y,111),(3,3),'steel')
    box(f,(-34,-27,109),(35,27,113),'yellow')
    box(f,(-14,-16,43),(14,16,55),'rubber')
    box(f,(-18,12,55),(18,17,80),'rubber')
    for y in (-26,26): box(f,(50,y-3,9),(56,y+3,142),'steel')
    for y in (-20,20): box(f,(54,y-3,12),(109,y+3,16),'steel')
    logistics.extend(transform(f,(1130,-860,0),-25))
    # Elevated route between upper floors. Third landing and workshop stair provide a south/east return.
    bridge(links,(-530,850,240),(-125,920,240),100)
    bridge(links,(655,920,240),(1070,920,240),104)
    bridge(links,(1070,920,240),(1070,1020,240),104)
    box(links,(1015,980,234),(1150,1100,240),'steel','metal')
    stairs(links,(1485,470,0),(1485,1010,240),104)
    box(links,(1150,980,234),(1540,1100,240),'steel','metal')
    rail(links,(1265,1100,240),(1540,1100,240))
    rail(links,(1265,980,240),(1430,980,240))
    # Barracks upper bridge has no front rail over the end joints.
    sign(links,(980,917),194,'F',120)
    # Two reference guard towers are inaccessible backdrop silhouettes, not added gameplay buildings.
    for e,n in ((-1730,-1110),(1740,-1190)):
        for dx in (-38,38):
            for dy in (-38,38): vista.beam((e+dx,n+dy,-80),(e+dx,n+dy,195),(5,5),'steel')
        for z in (-30,60,150):
            vista.beam((e-38,n-38,z),(e+38,n-38,z+70),(3,3),'steel')
        box(vista,(e-49,n-49,185),(e+49,n+49,191),'steel')
        box(vista,(e-43,n-43,191),(e+43,n+43,250),'olive')
        box(vista,(e-30,n-44,205),(e+30,n-43,230),'glass')
        box(vista,(e-52,n-52,250),(e+52,n+52,257),'roof')
        box(vista,(e-8,n-45,236),(e+8,n-44,244),'lamp')
    # Forest walls at three depths; all are outside collision boundaries. Gorge cuts across the foreground.
    rng=np.random.default_rng(774)
    for side in range(4):
        for k in range(48):
            along=rng.uniform(-2500,2500); across=rng.uniform(1750,3300)
            e,n=(along,across) if side==0 else (-across,along) if side==1 else (across,along) if side==2 else (along,-across-350)
            if side==3 and abs(e)<550: continue
            # Keep trees rooted on the rim, rather than floating over the basin.
            if -60<e<930 and 2800<n<3520: e=-200 if e<425 else 1050
            scale=rng.uniform(.7,1.55)
            variant="abc"[k%3]
            path=f'{RES}/fir/fir_{variant}.vmdl' if k%5 else f'{RES}/pine/pine_{variant}.vmdl'
            if not (K.ASSETS/path).exists(): path=f'{RES}/fir_{k%3}.vmdl'
            edge=1450 if side in (0,3) else 1550
            depth=(abs(n) if side in (0,3) else abs(e))-edge
            root=-8-min(300,depth)*112/300
            INSTANCES.append((f'Fir {side} {k}',path,(e,n,root),rng.uniform(0,360),(scale,scale,scale)))
    young=np.random.default_rng(4812)
    for side in range(4):
        for k in range(22):
            along=young.uniform(-1480,1480); depth=young.uniform(75,280)
            if side==3 and abs(along)<650: continue
            edge=1450 if side in (0,3) else 1550; across=edge+depth
            e,n=(along,across) if side==0 else (-across,along) if side==1 else (across,along) if side==2 else (along,-across)
            variant="abc"[k%3]; path=f'{RES}/sapling/sapling_{variant}.vmdl'
            if not (K.ASSETS/path).exists(): continue
            scale=young.uniform(1.1,2.4)
            INSTANCES.append((f'Young fir {side} {k}',path,(e,n,-8-depth*112/300),young.uniform(0,360),(scale,scale,scale)))
    # Large broken cliff masses rather than extra traversable terrain.
    for k in range(38):
        a=2*math.pi*k/38
        c0=(2450*math.cos(a),2450*math.sin(a),-230)
        rock(vista,c0,(rng.uniform(250,550),rng.uniform(220,450),rng.uniform(500,1250)),k+80)
    # Closed, overlapping scan masses form a ridge. The former thin cliff scans
    # had exposed cut edges and were stretched vertically into hanging curtains.
    # Broad lower banks and offset upper outcrops keep the rock relief readable.
    for k in range(10):
        e0=-3100+k*760
        rock(vista,(e0,4050+rng.uniform(-150,180),-320),
             (rng.uniform(620,860),rng.uniform(600,850),rng.uniform(1350,1800)),500+k,kind='boulder')
        rock(vista,(e0+rng.uniform(-220,220),4380+rng.uniform(-80,160),400),
             (rng.uniform(500,710),rng.uniform(460,650),rng.uniform(1000,1550)),520+k,kind='boulder')
    # The waterfall face also uses closed outcrops; the open coastal scan's narrow
    # side profile otherwise creates an artificial vertical fin at this angle.
    rock(vista,(410,3830,-290),(650,390,1800),550,kind='boulder')
    rock(vista,(410,3790,600),(620,390,1100),570,kind='boulder')
    for e0,seed in ((-520,551),(1360,552)):
        rock(vista,(e0,3730,-280),(720,630,1800),seed,kind='boulder')
        rock(vista,(e0+110,3960,460),(480,440,1050),seed+10,kind='boulder')
    rock(vista,(410,3540,990),(430,285,300),402)
    # Thin, irregular streams curl over the lip, separate on the rock face and
    # fan out into the plunge basin. Continuous normals avoid a faceted curtain.
    for stream,(center,width) in enumerate(((198,62),(277,77),(355,96),(444,83),(531,69),(615,56))):
        def cascade(u,t):
            widen=1+.18*t+.13*math.sin(t*11+stream)*t
            curl=55*(1-math.exp(-t*24))
            return np.array((center+(u-.5)*width*widen+math.sin(t*9+stream)*9*t,
                             3270-curl-86*t+math.sin(u*math.pi)*12+math.sin(t*10+stream)*7*t,
                             1070-1322*t+math.sin(u*math.pi*2+stream)*3))
        def normal(u,t):
            du=cascade(u+.001,t)-cascade(u-.001,t)
            dt=cascade(u,t+.001)-cascade(u,t-.001)
            return K.normalise(np.cross(dt,du))
        for k in range(6):
            for j in range(28):
                uv=[(k/6,j/28),(k/6,(j+1)/28),((k+1)/6,(j+1)/28),((k+1)/6,j/28)]
                points=[cascade(u,t) for u,t in uv]; normals=[normal(u,t) for u,t in uv]
                vista.polygon('waterfall',points,uv=uv,normals=normals)
                vista.polygon('waterfall',points[::-1],uv=uv[::-1],normals=[-n for n in normals[::-1]])
    pool=[(20,2890,-255),(830,2890,-255),(830,3440,-255),(20,3440,-255)]
    vista.polygon('river',pool,both_sides=True,uv=((0,0),(1,0),(1,1),(0,1)))
    for k,center in enumerate((220,350,485,610)):
        e,n=center,3100+math.sin(k*2.4)*35
        vista.polygon('waterfall_foam',[(e-85,n-175,-253),(e+85,n-175,-253),(e+85,n+80,-253),(e-85,n+80,-253)],
                      uv=((0,0),(1,0),(1,1),(0,1)))
        # A few softly masked local plumes, below the eye level of the compound.
        vista.polygon('waterfall_spray',[(e-145,n-12,-244),(e+145,n-12,-244),(e+105,n+40,40),(e-105,n+40,40)],
                      uv=((0,0),(1,0),(1,1),(0,1)),both_sides=True)
    # A shallow descending torrent under the entrance bridge, with broken
    # patches of whitewater instead of a single still dark water rectangle.
    def river(t,side):
        center=math.sin(t*7)*35
        width=310+45*math.sin(t*5+.2)
        return (center+side*width,-1450-t*1650,-250-t*36+math.sin(t*9)*2)
    # Smooth irregular slopes cover the former rectangular opening in the
    # forest slab. The wet inner strip descends below the river surface.
    # The channel stops beneath the existing compound, not in open view.
    segments=28
    def riverbank(t,side,depth):
        e,n,z=river(t,side)
        inner=e-side*(24+12*math.sin(t*19+side))
        across=inner*(1-depth)+side*550*depth
        return np.array((across,n,(z-16)*(1-depth)+(-120)*depth+math.sin(t*23+side)*9*math.sin(depth*math.pi)))
    def banknormal(t,side,depth):
        along=riverbank(t+.001,side,depth)-riverbank(t-.001,side,depth)
        across=riverbank(t,side,depth+.001)-riverbank(t,side,depth-.001)
        normal=K.normalise(np.cross(along,across))
        return normal if normal[2]>0 else -normal
    for k in range(segments):
        t0,t1=(k-.9)/segments,(k+1-.9)/segments
        vista.polygon('river',[river(t0,-1),river(t1,-1),river(t1,1),river(t0,1)],both_sides=True)
        for side in (-1,1):
            for d0,d1 in ((0,.22),(.22,.52),(.52,1)):
                coords=[(t0,d0),(t1,d0),(t1,d1),(t0,d1)]
                points=[riverbank(t,side,d) for t,d in coords]
                if np.cross(points[1]-points[0],points[2]-points[0])[2]<0: coords.reverse(); points.reverse()
                vista.polygon('mud_track' if d0<.22 else 'mud',points,
                              normals=[banknormal(t,side,d) for t,d in coords])
    for k in range(10):
        t=(k+.6)/10
        e,n,z=river(t,0); e+=math.sin(k*2.1)*110
        lower=river(t+145/1650,0)[2]+1.5; upper=river(t-145/1650,0)[2]+1.5
        vista.polygon('waterfall_current',[(e-100,n-145,lower),(e+100,n-145,lower),(e+100,n+145,upper),(e-100,n+145,upper)],
                      uv=((0,0),(1,0),(1,1),(0,1)))
    for side in (-1,1):
        for k in range(8): rock(vista,(side*(450+k%2*160),-1800-k*170,-460),(240,220,480),k+side+290)
    return dict(ground=ground,motor=motor,barracks=barracks,command=command,workshop=workshop,yard=yard,logistics=logistics,links=links,vista=vista)

RED=[(-1420+x*82,-1280+y*86,0) for y in range(2) for x in range(4)]
BLUE=[(920+x*88,1320+y*86,0) for y in range(2) for x in range(4)]
DM=[(-1410,-1250,0),(-700,-1250,0),(-1410,-100,0),(-1400,500,0),(-1180,850,96),(-1080,790,240),
    (-430,1160,0),(105,980,96),(10,900,240),(710,620,0),(1420,1090,0),(1400,410,0),
    (1000,-1250,0),(270,-1380,0),(-180,-440,0),(600,-490,0)]
OBJECTIVES=[('A',(-1000,-760,0)),('B',(-40,-90,0)),('C',(1120,-390,0))]

def component(t,key,**p): return K.component(IDS,t,key,**p)
def go(name,key,pos=(0,0,0),comps=(),children=(),tags=''):
    return K.game_object(IDS,name,key,K.to_world(pos),components=comps,children=children,tags=tags)

def collider(key,size,trigger=True):
    return component('Sandbox.BoxCollider',key,Scale=K.vec(size),Center='0,0,0',IsTrigger=trigger,Static=True)

def zone(name,key,bounds,extras=()):
    lo,hi=map(np.array,bounds); c=(lo+hi)/2; size=np.abs(K.to_world(hi-lo))
    return go(name,key,c,comps=[component('Zone',key+'/zone',DisplayName=name,Color='0.5,0.7,0.6,1'),collider(key+'/box',size),*extras],tags='zone')

def spawn(name,key,p,team,tags=''):
    return K.game_object(IDS,name,key,K.to_world((p[0],p[1],p[2]+2)),K.yaw_rotation(K.plan_yaw((-p[0],-p[1]))),tags=tags,
                         components=[component('TeamSpawnPoint',key+'/point',Team=team)])

def mode(name,key,modes,children,inverse=False):
    return go(name,key,comps=[component('Facepunch.GameModeObject',key+'/mode',GameModes=modes,Inverse=inverse)],children=children)

def write_scene(models):
    sceneobjects=[]
    sceneobjects.append(go('Scene Information','info',comps=[
        component('Sandbox.SceneInformation','info/scene',Title='Forest Base',Description='A compact forest military outpost, with motor pool, barracks, command, logistics, workshop and elevated catwalks.'),
        component('Facepunch.MapInformation','info/map',Image='ui/maps/forestbase.png',IsVisibleInMenu=True),
        component('Facepunch.MapSpawnSettings','info/spawns',UseMapSpawnPoints=False,AllowNavMeshSpawns=False)]))
    chunks=[]
    for name,m in models.items():
        path=f'{RES}/{name}.vmdl'
        comps=[component('Sandbox.ModelRenderer',name+'/renderer',Model=path,RenderType='On',Tint='1,1,1,1')]
        if m.boxes or m.hulls: comps += [component('Sandbox.ModelCollider',name+'/collider',Model=path,Static=True,IsTrigger=False)]
        chunks.append(go(name.title(),name,comps=comps))
    sceneobjects.append(go('Military Outpost','geometry',children=chunks))
    forest=[]
    for i,(name,path,pos,yaw,scale) in enumerate(INSTANCES):
        forest.append(K.game_object(IDS,name,f'forest/{i}',K.to_world(pos),K.yaw_rotation(yaw),scale=K.vec(scale),
                components=[component('Sandbox.ModelRenderer',f'forest/{i}/render',Model=path,RenderType='On',Tint='1,1,1,1')]))
    sceneobjects.append(go('Forest Backdrop','forest',children=forest))
    sceneobjects += [
        K.game_object(IDS,'Cool Daylight','sun',(0,0,2500),K.angles_rotation(36,-35),components=[
            component('Sandbox.DirectionalLight','sun/light',LightColor='0.64,0.71,0.82,1',SkyColor='0.19,0.25,0.31,1',
                      Shadows=True,ContactShadows=True,ShadowCascadeCount=4,ShadowBias=.0005)]),
        go('Sky','sky',comps=[component('Sandbox.SkyBox2D','sky/box',SkyMaterial='materials/skybox/skybox_overcast_01.vmat',SkyIndirectLighting=True,Tint='0.36,0.43,0.50,1')]),
        go('Forest Mist','fog',comps=[component('Sandbox.GradientFog','fog/gradient',Color='0.28,0.35,0.4,0.5',StartDistance=2100,EndDistance=11000,FalloffExponent=1.3,Height=1800,VerticalFalloffExponent=1.5)]),
        go('Reflections','reflections',(0,0,190),comps=[component('Sandbox.EnvmapProbe','reflections/probe',Mode='Realtime',Projection='Box',Resolution='Medium',
             UpdateStrategy='OnEnabled',MultiBounce=False,MaxDistance=4200,ZNear=4,ZFar=8000,Feathering=200,Bounds={'Mins':'-1800,-1800,-300','Maxs':'1800,1800,1100'})]),
        go('Rain Reflections','rainfx',comps=[component('Sandbox.PostProcessVolume','rainfx/volume',IsInfinite=True,Priority=10,BlendWeight=1,EditorPreview=True),
             component('Sandbox.ScreenSpaceReflections','rainfx/ssr',RoughnessCutoff=.28)]),
        go('Warm Military Lights','lights',children=[go(name,f'light/{i}',pos,comps=[component('Sandbox.PointLight',f'light/{i}/point',LightColor=color,Radius=radius,Shadows=shadow,Attenuation=1,FogMode='Enabled',FogStrength=.25)]) for i,(name,pos,color,radius,shadow) in enumerate(LIGHTS)])]
    # In addition to visible fences: six closed player clips, plus ceiling. No escape into scenery by jumping or stacking.
    clips=[]
    for i,(lo,hi) in enumerate([((-1570,-1730,-200),(-1550,1470,1800)),((1550,-1730,-200),(1570,1470,1800)),
            ((-1570,1450,-200),(1570,1470,1800)),((-1570,-1470,-200),(-180,-1450,1800)),
            ((180,-1470,-200),(1570,-1450,1800)),((-180,-1730,-200),(180,-1710,1800)),
            ((-200,-1710,-200),(-180,-1450,1800)),((180,-1710,-200),(200,-1450,1800)),
            ((-1570,-1730,1600),(1570,1470,1620))]):
        lo,hi=np.array(lo),np.array(hi)
        clips.append(go(f'Boundary Clip {i}',f'clip/{i}',(lo+hi)/2,comps=[collider(f'clip/{i}/box',np.abs(K.to_world(hi-lo)),False)],tags='playerclip'))
    sceneobjects.append(go('Closed Player Boundary','clips',children=clips))
    area=zone('Military AO','play',((-1550,-1710,-150),(1550,1450,1590)))
    area['Components'].append(component('Facepunch.PlayArea','play/area',Zone={'_type':'component','component_id':IDS('play/zone'),'go':IDS('play'),'component_type':'Zone'}))
    sceneobjects.append(area)
    sceneobjects += [mode('Team Spawns','spawns',['Deathmatch','Gun Game','Retakes'],
        [spawn(f'Red {i+1}',f'spawn/red/{i}',p,'Terrorist') for i,p in enumerate(RED)]+
        [spawn(f'Blue {i+1}',f'spawn/blue/{i}',p,'CounterTerrorist') for i,p in enumerate(BLUE)],True),
        mode('Free For All Spawns','dm',['Deathmatch','Gun Game'],[spawn(f'DM {i+1}',f'spawn/dm/{i}',p,'Unassigned','deathmatch') for i,p in enumerate(DM)])]
    for letter,p in OBJECTIVES:
        sceneobjects.append(go(f'Domination {letter}',f'dom/{letter}',p,comps=[component('Facepunch.ObjectiveSpot',f'dom/{letter}/spot',Kind='Domination',Label=letter)]))
    for i,(label,p) in enumerate([('Motor Pool',(-1040,-790,0)),('Command',(165,810,96)),('Logistics',(-40,-90,0)),('Workshop',(1220,480,0)),('Catwalk',(-320,888,240))]):
        sceneobjects.append(go(f'Hot Zone {label}',f'hot/{i}',p,comps=[component('Facepunch.ObjectiveSpot',f'hot/{i}/spot',Kind='HotZone',Label=label)]))
    for i,(name,rect) in enumerate([('A Motor Pool',((-1530,-1120,0),(-510,-225,190))),('B Barracks',((-1410,530,90),(-510,1120,400))),
          ('C Command',((-150,570,90),(660,1190,400))),('D Logistics',((-400,-1400,0),(1500,360,190))),
          ('E Workshop',((750,230,0),(1460,820,185))),('F Catwalk',((-530,795,225),(1080,975,320)))]):
        sceneobjects.append(zone(name,f'callout/{i}',rect,[component('Facepunch.MapLocation',f'callout/{i}/location')]))
    for i,(name,rect) in enumerate([('Motor Pool',((-1390,-810,0),(-980,-365,135))),('Logistics',((780,-640,0),(1150,-350,135)))]):
        site=zone(f'Bomb Site {chr(65+i)}',f'bomb/{i}',rect,[component('BombSite',f'bomb/{i}/site',Index=i,DamageFalloffDistance=1750,MaxBombDamage=500)])
        site['Tags']='zone,bombsite'; sceneobjects.append(site)
    for team,rect in [('Terrorist',((-1530,-1400,0),(-1000,-1130,150))),('CounterTerrorist',((850,1285,0),(1370,1430,150)))]:
        sceneobjects.append(zone(f'Buy {team}',f'buy/{team}',rect,[component('Facepunch.BuyZone',f'buy/{team}/buy',Team=team)]))
    # Defuse Retakes have their own points, excluded from other modes.
    retakes=[]
    for letter,points in [('A',[(-1370,-480,0),(-1100,-300,0),(-650,-900,0),(-720,-400,0)]),('B',[(950,-400,0),(1200,-250,0),(600,-500,0),(1200,-1200,0)])]:
        for k,p in enumerate(points):
            role='defender' if k<2 else 'attacker'; team='Terrorist' if k<2 else 'CounterTerrorist'
            retakes.append(spawn(f'{letter} {role} {k}',f'retakes/{letter}/{k}',p,team,f'retakes,{letter},{role}'))
    sceneobjects.append(mode('Retakes','retakes',['Retakes'],retakes))
    sceneobjects.append(go('Minimap','minimap',(0,0,1700),comps=[component('Facepunch.MinimapRenderer','minimap/renderer',CurrentMinimapPath='ui/minimaps/minimap_forestbase.png',ExportResolution='1024,1024',Size=3500)]))
    for path in ['prefabs/game_modes/team_deathmatch.prefab','prefabs/game_modes/bomb_defusal.prefab','scenes/maps/defusemap_01/game_setup.prefab']:
        sceneobjects.append(K.prefab_instance(IDS,path))
    data={'__guid':IDS('scene'),'GameObjects':sceneobjects,'SceneProperties':{'NetworkInterpolation':True,'PhysicsMode':'Physics3D','TimeScale':1,'WantsSystemScene':True,
          'Metadata':{'Title':'Forest Base','Image':'ui/maps/forestbase.png','IsVisibleInMenu':'True','GameModes':'prefabs/game_modes/team_deathmatch.prefab, prefabs/game_modes/bomb_defusal.prefab'},
          'NavMesh':{'Enabled':True,'IncludeStaticBodies':True,'IncludeKeyframedBodies':False,'EditorAutoUpdate':True,'AgentHeight':72,'AgentRadius':24,'AgentStepSize':18,'AgentMaxSlope':40,
          'ExcludedBodies':'zone,playerclip','IncludedBodies':'','DeferGeneration':False,'CustomBounds':True,'Bounds':{'Mins':'-1730,-1550,-100','Maxs':'1450,1550,650'}}},
          'ResourceVersion':3,'Title':'Forest Base','Description':'Reference military forest compound for 10–15 players.','__references':[],'__version':3}
    SCENE.parent.mkdir(parents=True,exist_ok=True); K.write_text(SCENE,json.dumps(data,indent=2)+'\n')
    meta=SCENE.with_name(SCENE.name+'.meta')
    if not meta.exists(): K.write_text(meta,json.dumps({'guid':IDS('scene-resource')},indent=2))

def minimap(models):
    image=Image.new('RGB',(1024,1024),(29,36,35)); d=ImageDraw.Draw(image)
    def p(e,n): return ((e+1750)/3500*1024,(1750-n)/3500*1024)
    for name,m in models.items():
        if name=='vista': continue
        for paint,faces in m.polygons.items():
            color=M.COLORS.get(paint,(110,122,118))
            for pts,normal in faces:
                if normal[2]>.7: d.polygon([p(*q[:2]) for q in pts],fill=color)
    for letter,c in [('A',(-1060,-555)),('B',(-950,850)),('C',(265,920)),('D',(600,-650)),('E',(1100,520))]:
        x,y=p(*c); d.ellipse((x-14,y-14,x+14,y+14),fill=(25,31,28)); d.text((x-4,y-6),letter,fill=(243,216,135))
    path=K.ASSETS/'ui/minimaps/minimap_forestbase.png'; path.parent.mkdir(parents=True,exist_ok=True); image.save(path)

def main():
    chunks=('ground','motor','barracks','command','workshop','yard','logistics','links','vista')
    parser=argparse.ArgumentParser(); parser.add_argument('--no-trees',action='store_true')
    parser.add_argument('--chunks',nargs='+',choices=chunks,help='Rebuild only these visual chunks; preserve other assets and the minimap.')
    args=parser.parse_args()
    if args.chunks:
        missing=[name for name in chunks if name not in args.chunks and not (OUT/f'{name}.vmdl').exists()]
        if missing: parser.error('A partial rebuild requires existing other chunks: '+', '.join(missing))
    if not args.no_trees: write_trees()
    report=K.ROOT/'output/forestbase'; report.mkdir(parents=True,exist_ok=True)
    previous=report/'layout.json'
    stats=json.loads(previous.read_text()).get('stats',{}) if args.chunks and previous.exists() else {}
    models=build(visual_chunks=args.chunks)
    for name,m in models.items():
        if args.chunks and name not in args.chunks: continue
        count=K.write_model(OUT,RES,name,m)
        stats[name]=dict(triangles=count,boxes=len(m.boxes),hulls=len(m.hulls))
        print(name,stats[name])
    write_scene(models)
    if not args.chunks: minimap(models)
    K.write_text(report/'layout.json',json.dumps(dict(stats=stats,routes=ROUTES,red=RED,blue=BLUE,dm=DM,objectives=OBJECTIVES,lights=len(LIGHTS),trees=len(INSTANCES)),indent=2))
    print('Forest Base scene written:',SCENE)

if __name__=='__main__': main()
