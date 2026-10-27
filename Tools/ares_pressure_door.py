"""Formed pressure-door assemblies, drawn inside the original sealed collider.

Local X is across the hatch, -Y faces the room and Z is up, in inches. No
interaction, collision, lights or scene objects are introduced by this module.
"""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
from boxyard_map import Frame

PREFIX='materials/ares/pressure-doors-v2'
NAMES=('body','panel','frame','steel','rubber','accent','dark','labels','display','glass','red','green','hazard')
MATERIALS={f'ar_pd_{n}':f'{PREFIX}/{n}.vmat' for n in NAMES}
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));AXES=(X,Y,Z)


def rect(x0,x1,z0,z1,c=1.):
    c=min(c,(x1-x0)*.25,(z1-z0)*.25)
    return [(x0+c,z0),(x1-c,z0),(x1,z0+c),(x1,z1-c),
            (x1-c,z1),(x0+c,z1),(x0,z1-c),(x0,z0+c)]


def inset(profile,d):
    p=np.asarray(profile,float);edges=np.roll(p,-1,axis=0)-p
    area=np.sum(p[:,0]*np.roll(p[:,1],-1)-np.roll(p[:,0],-1)*p[:,1])
    inward=np.c_[-edges[:,1],edges[:,0]]
    inward*=1 if area>0 else -1
    inward/=np.linalg.norm(inward,axis=1)[:,None]
    result=[]
    for i,point in enumerate(p):
        # Intersection of the two offset edge lines, preserving the profile's
        # vertex count and its true clipped-corner distances.
        normals=np.array((inward[i-1],inward[i]))
        values=np.array((np.dot(inward[i-1],point)+d,np.dot(inward[i],point)+d))
        result.append(tuple(np.linalg.solve(normals,values)))
    return result


def cap(m,profile,y,paint,towards=-Y,uvbox=None):
    pts=[(x,y,z) for x,z in profile];uv=None
    if uvbox:
        x0,x1,z0,z1=uvbox
        uv=[((x-x0)/(x1-x0),(z-z0)/(z1-z0)) for x,z in profile]
    P.card(m,'ar_pd_'+paint,pts,towards,uv=uv)


def ring(m,outer,inner,y0,y1,paint):
    for i,a in enumerate(outer):
        b=outer[(i+1)%len(outer)];c=inner[(i+1)%len(inner)];d=inner[i]
        P.card(m,'ar_pd_'+paint,[(a[0],y0,a[1]),(b[0],y0,b[1]),
                 (c[0],y1,c[1]),(d[0],y1,d[1])],-Y)


def slab(m,profile,back,front,paint,bevel=.12,uvbox=None):
    inner=inset(profile,bevel);centre=np.mean(profile,axis=0)
    for i,a in enumerate(profile):
        b=profile[(i+1)%len(profile)];towards=np.array(((a[0]+b[0])/2-centre[0],0,(a[1]+b[1])/2-centre[1]))
        P.card(m,'ar_pd_'+paint,[(a[0],back,a[1]),(b[0],back,b[1]),
                 (b[0],front+bevel,b[1]),(a[0],front+bevel,a[1])],towards)
    ring(m,profile,inner,front+bevel,front,paint)
    cap(m,inner,front,paint,uvbox=uvbox);cap(m,profile,back,paint,Y)


def box(m,c,size,paint,bevel=.12):
    P.bevel_box(m,c,AXES,size,'ar_pd_'+paint,bevel=bevel)


def turned(m,x,z,back,profile,paint='steel',sides=24,close=True):
    P.lathe_axis(m,(x,back,z),-Y,profile,'ar_pd_'+paint,sides=sides,
                 cap='ar_pd_'+paint if close else None)


def bolt(m,x,z,back=-9.0,r=.65):
    turned(m,x,z,back,[(r*1.26,0),(r*1.26,.12),(r,.15),(r,.53),(r*.84,.61)],sides=6)
    # Dark, recessed hex socket inside a chamfered solid head.
    turned(m,x,z,back-.615,[(r*.36,0),(r*.36,.012)],'dark',sides=6)


def tile_uv(tile,s,t):
    return ((tile%4+.025+.95*s)/4,1-(tile//4+.025+.95*(1-t))/4)


def label(m,x0,x1,z0,z1,y,tile):
    P.card(m,'ar_pd_labels',[(x0,y,z0),(x1,y,z0),(x1,y,z1),(x0,y,z1)],-Y,
           uv=[tile_uv(tile,s,t) for s,t in ((0,0),(1,0),(1,1),(0,1))])


def dial(m,x,z):
    slab(m,rect(x-8.4,x+8.4,z-9.4,z+9.4,2),-5.45,-6.7,'frame',.20)
    for dx in (-6.8,6.8):
        for dz in (-7.7,7.7):bolt(m,x+dx,z+dz,-6.7,.43)
    turned(m,x,z,-6.7,[(6.0,0),(6.55,.25),(6.55,1.7),(6.18,2.3),(5.65,2.3)],'steel',sides=48,close=False)
    points=[];uv=[]
    for a in np.linspace(0,math.tau,65)[:-1]:
        xx,zz=math.cos(a),math.sin(a);points.append((x+5.65*xx,-8.92,z+5.65*zz));uv.append(tile_uv(8,(xx+1)/2,(zz+1)/2))
    P.card(m,'ar_pd_labels',points,-Y,uv=uv)
    # Needle and hub are actual objects above the printed dial.
    P.card(m,'ar_pd_red',[(x-.16,-9.02,z-1.1),(x+.16,-9.02,z-1.1),
           (x+.11,-9.02,z+4.5),(x-.03,-9.02,z+4.9)],-Y)
    turned(m,x,z,-9.03,[(.50,0),(.47,.12)],'dark',sides=20)
    P.lathe_axis(m,(x,-6.7,z),-Y,[(5.63,2.34),(5.61,2.39),(4.6,2.43),
           (3.2,2.47),(1.4,2.50),(0,2.51)],'ar_pd_glass',sides=48)


def control(m,x,z):
    # IP-style enclosure, separate rubber bedding and chamfered face bezel.
    slab(m,rect(x-5.2,x+5.2,z-10.2,z+10.2,1.2),-5.4,-6.2,'rubber',.11)
    slab(m,rect(x-4.9,x+4.9,z-9.9,z+9.9,1.1),-6.15,-9.9,'frame',.25)
    slab(m,rect(x-3.75,x+3.75,z-.6,z+7.5,.5),-9.92,-10.23,'rubber',.10)
    P.card(m,'ar_pd_display',[(x-3.35,-10.25,z-.2),(x+3.35,-10.25,z-.2),
           (x+3.35,-10.25,z+7.1),(x-3.35,-10.25,z+7.1)],-Y,
           uv=[(s, t) for s,t in ((0,0),(1,0),(1,1),(0,1))])
    for dx in (-3.6,3.6):
        for dz in (-8.6,8.6):bolt(m,x+dx,z+dz,-9.92,.31)
    for i,paint in enumerate(('dark','green')):
        bx=x-2.0+i*4.0
        turned(m,bx,z-3.6,-9.94,[(1.08,0),(1.08,.28),(.85,.31),(.80,.60)],'rubber',sides=24)
        turned(m,bx,z-3.6,-10.53,[(.76,0),(.72,.22)],paint,sides=24)
    label(m,x-3.6,x+3.6,z-8.4,z-6.0,-10.26,10)
    # Guarded emergency button below the control housing, at reachable height.
    slab(m,rect(x-3.2,x+3.2,z-18.4,z-12.,.7),-5.5,-6.4,'accent',.12)
    turned(m,x,z-15.2,-6.4,[(1.65,0),(1.65,.3),(1.28,.5),(1.28,1.5)],'dark',sides=24)
    turned(m,x,z-15.2,-7.9,[(1.65,0),(1.77,.25),(1.70,.72)],'red',sides=32)


def wheel(m,x,z):
    slab(m,rect(x-11.0,x+11.,z-12.5,z+12.5,3.),-5.4,-7.0,'frame',.20)
    for dx in (-8.6,8.6):
        for dz in (-10.,10.):bolt(m,x+dx,z+dz,-7.0,.55)
    turned(m,x,z,-7.05,[(3.8,0),(4.0,.25),(4.0,1.1),(2.5,1.5),
           (2.3,2.6),(1.8,2.9)],'steel',sides=32)
    P.torus(m,(x,-10.1,z),-Y,8.2,.67,'ar_pd_accent',seg=48,sides=8)
    for i in range(3):
        angle=i*math.tau/3+math.radians(30)
        v=np.array((math.cos(angle),0,math.sin(angle)))
        across=np.cross(-Y,v);centre=np.array((x,-10.1,z))+v*4.9
        P.bevel_box(m,centre,(v,across,-Y),(6.1,1.05,.65),'ar_pd_steel',bevel=.20)
    turned(m,x,z,-10.48,[(1.9,0),(1.9,.34),(1.6,.59)],'frame',sides=24)
    bolt(m,x,z,-11.08,.68)
    label(m,x-10.,x+10.,z-20.5,z-15.3,-5.65,4)


def pressure_door(model,centre,facing,width=180,height=180,border=16):
    local=K.Model();half=width/2
    outer=rect(-half-border,half+border,0,height+border,15)
    bevel=inset(outer,1.0);lip=inset(outer,2.8)
    opening=rect(-half+2,half-2,6,height+1,12)
    seal=rect(-half+6,half-6,10,height-3,10)
    # The casing is a deep stepped assembly rather than an outlined polygon.
    slab(local,outer,-.12,-5.2,'frame',.35)
    ring(local,outer,bevel,-5.2,-7.7,'steel')
    ring(local,bevel,lip,-7.7,-9.4,'frame')
    ring(local,lip,opening,-9.4,-9.4,'frame')
    ring(local,opening,seal,-9.4,-3.5,'steel')
    cap(local,seal,-3.10,'rubber')
    ring(local,opening,inset(opening,1.2),-9.48,-8.6,'rubber')
    unit=0 if width>250 else 1 if centre[0]<0 else 2
    for side in (-1,1):
        # Two complete thick leaves with a true central gap and stepped edges.
        p=[(-half+15,11),(-.65,11),(-.65,height-7),(-half+15,height-7),
           (-half+7,height-15),(-half+7,19)]
        p=[(-side*x,z) for x,z in p]
        xs=[q[0] for q in p];lo,hi=min(xs),max(xs)
        uv=(lo,hi,11,height-7)
        slab(local,p,-3.2,-5.6,'body',.28,uvbox=uv)
        # Replaceable upper skin in a deep pressed reveal, with structural beads.
        low=height*.49;high=height-18
        panel=rect(lo+5.5,hi-5.5,low,high,5.3);inside=inset(panel,1.25)
        ring(local,panel,inside,-7.1,-5.85,'frame')
        cap(local,inside,-5.88,'panel',uvbox=(lo+5.5,hi-5.5,low,high))
        count=2 if hi-lo>100 else 1
        for fraction in ([.34,.66] if count==2 else [.5]):
            xx=lo+8+(hi-lo-16)*fraction
            box(local,(xx,-6.36,(low+high)/2),(2.6,.95,high-low-9),'body',.18)
        # Folded horizontal reinforcement and replaceable, scuffed kick plate.
        slab(local,rect(lo+4,hi-4,height*.43-2.8,height*.43+2.8,1.3),-5.65,-7.35,'body',.22)
        slab(local,rect(lo+5,hi-5,17,34,2.6),-5.65,-7.5,'frame',.22,uvbox=(lo+5,hi-5,17,34))
        for xx in (lo+8,hi-8):
            for zz in (20.3,30.7):bolt(local,xx,zz,-7.5,.47)
        label(local,(lo+hi)/2-14,(lo+hi)/2+14,22,28,-7.52,5)
        # Each leaf has its own replaceable asset/data plate.
        slab(local,rect(lo+7,lo+38,low+6,low+13,.7),-5.9,-6.15,'frame',.10)
        label(local,lo+7.4,lo+37.6,low+6.4,low+12.6,-6.17,unit)

    # Lapped centre mullion, flush witness strip and six working-scale cam dogs.
    box(local,(0,-5.20,(height+4)/2),(1.35,.70,height-15),'rubber',.14)
    for side in (-1,1):
        for zz in (43.,height*.52,height-29.):
            pivot=side*(half+4);toe=side*(half-10)
            slab(local,rect(pivot-6.0,pivot+6.,zz-7.,zz+7.,1.8),-6.1,-9.1,'frame',.25)
            box(local,(toe,-7.35,zz),(7.6,3.5,9.0),'frame',.24)
            arm=[(pivot-side*2,zz-2.7),(toe-side*2,zz-3.7),
                 (toe-side*3,zz+1.8),(pivot,zz+4.1),(pivot+side*3.3,zz+1.5)]
            slab(local,arm,-9.12,-10.25,'steel',.28)
            turned(local,pivot,zz,-9.1,[(2.9,0),(3.05,.25),(3.05,1.4),(2.7,1.65)],'steel',sides=24)
            bolt(local,pivot,zz,-10.77,1.18)
            label(local,pivot-1.7,pivot+1.7,zz-1.0,zz+1.0,-11.45,11)
        for zz in (9.,height+border*.55):
            bolt(local,side*(half+border*.45),zz,-9.42,.90)
        # Slim covered locking rods physically connect the three cam stations.
        box(local,(side*(half+8.2),-8.9,(43+height-29)/2),(1.05,1.0,height-72),'steel',.14)
    for xx in np.linspace(-half+20,half-20,5 if width>250 else 3):
        bolt(local,float(xx),height+border*.52,-9.42,.77)
    wheel(local,-min(half*.45,38),58)
    control(local,max(17,half*.25),61)
    dial(local,min(half*.62,99),64)
    # Threshold wear and a single warning strip, without bright wallpaper trim.
    box(local,(0,-9.25,2.65),(width+14,4.8,5.3),'steel',.16)
    P.card(local,'ar_pd_hazard',[(-half+12,-11.68,.7),(half-12,-11.68,.7),
           (half-12,-11.68,2.45),(-half+12,-11.68,2.45)],-Y,
           uv=[(0,0),((width-24)/9,0),((width-24)/9,1.75/9),(0,1.75/9)])
    for xx in np.linspace(-half+18,half-18,8 if width>250 else 5):
        box(local,(float(xx),-9.25,5.32),(12.,3.8,.10),'rubber',.03)

    points=np.vstack([pts for rows in local.polygons.values() for pts,n in rows])
    assert points[:,0].min()>=-half-border-1e-6 and points[:,0].max()<=half+border+1e-6
    assert points[:,1].min()>=-12 and points[:,1].max()<=0
    assert points[:,2].min()>=0 and points[:,2].max()<=height+border+1e-6
    frame=Frame(centre[0],centre[1],math.degrees(math.atan2(facing[1],facing[0]))+90,centre[2])
    axes=np.array((frame.x,frame.y,frame.z))
    model.material_overrides.update(MATERIALS);model.tile_overrides.update({k:24. for k in MATERIALS})
    for paint,rows in local.polygons.items():
        for index,(pts,normal) in enumerate(rows):
            normals=local.polygon_normals.get((paint,index))
            P.card(model,paint,[frame.o+p@axes for p in pts],normal@axes,
                   normals=[n@axes for n in normals] if normals is not None else None,
                   uv=local.polygon_uvs.get((paint,index)))
    return {'type':'cargo' if width>250 else 'wing','width':width,'height':height,
            'triangles':local.triangle_count(),'locking_dogs':6,'private_materials':len(MATERIALS)}
