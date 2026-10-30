"""Smooth Ares wall services with bolted flanges and anchored pipe hangers.

All geometry is drawn only. Existing routes, radii and map materials are retained.
"""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P

X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
AXES=(X,Y,Z)
PAINTS={'ar_pipe':'ar_pw_pipe','ar_copper':'ar_pw_copper','ar_gunmetal':'ar_pw_cast',
        'ar_ext_metal':'ar_pw_metal','ar_dark':'ar_pw_rubber'}
MATERIALS={p:f'materials/ares/pipework-v1/{p[6:]}.vmat' for p in PAINTS.values()}


def placements():
    import ares_map as A
    rows=[]
    for side in (-1,1):
        for k,(z,r,paint) in enumerate(((300.,7.,'ar_pipe'),(322.,5.,'ar_copper'),(342.,9.,'ar_pipe'))):
            rows.append(dict(name=f'wing_{side}_{k}',a=(side*(A.HALL_E+A.WALL),A.HALL_N0+14+22*k,z),
                b=(side*A.WING_E,A.HALL_N0+14+22*k,z),r=r,paint=paint,wall_n=A.HALL_N0))
    for k,(z,r,paint) in enumerate(((228.,8.,'ar_pipe'),(252.,6.,'ar_copper'),(274.,10.,'ar_pipe'))):
        for side in (-1,1):
            e0,e1=(-A.WING_E,-190.) if side<0 else (190.,A.WING_E)
            rows.append(dict(name=f'cargo_south_{side}_{k}',a=(e0,A.CON_N0+16+24*k,z),
                b=(e1,A.CON_N0+16+24*k,z),r=r,paint=paint,wall_n=A.CON_N0))
    for k,(z,r,paint) in enumerate(((270.,7.,'ar_pipe'),(292.,5.,'ar_copper'))):
        for side in (-1,1):
            rows.append(dict(name=f'cargo_north_{side}_{k}',a=(side*A.WING_E,A.HALL_N0-A.WALL-14-20*k,z),
                b=(side*1150.,A.HALL_N0-A.WALL-14-20*k,z),r=r,paint=paint,wall_n=A.HALL_N0-A.WALL))
    return rows


def box(m,centre,size,paint='ar_gunmetal',bevel=.12):
    P.bevel_box(m,centre,AXES,size,paint,bevel=bevel)


def nut(m,c,axis,r=.44):
    P.lathe_axis(m,c,axis,[(r,0),(r,.40),(r*.82,.50)],
                 'ar_ext_metal',sides=6,cap='ar_ext_metal')


def flange(m,x,r):
    # Two weld-neck halves, a compressed gasket seam and four through-bolts.
    profile=[(r+.06,-2.7),(r+1.47,-1.20),(r+1.65,-.99),
             (r+1.65,-.29),(r+1.44,-.11),(r+.06,-.11)]
    paints=['ar_gunmetal','ar_ext_metal','ar_gunmetal','ar_ext_metal','ar_gunmetal']
    P.lathe_axis(m,(x,0,0),X,profile,paints,sides=32)
    P.lathe_axis(m,(x,0,0),X,[(rr,-t) for rr,t in reversed(profile)],list(reversed(paints)),sides=32)
    P.lathe_axis(m,(x,0,0),X,[(r+1.40,-.105),(r+1.40,.105)],'ar_dark',sides=32)
    # Low weld toes read as a local material transition, not another square collar.
    for side in (-1,1):
        P.lathe_axis(m,(x+side*2.65,0,0),X,
                     [(r,-.12),(r+.11,0),(r,.12)],'ar_ext_metal',sides=32)
    for angle in np.arange(4)*math.tau/4+math.pi/4:
        y,z=math.cos(angle)*(r+.94),math.sin(angle)*(r+.94)
        P.rod(m,(x-1.6,y,z),(x+1.6,y,z),.23,'ar_gunmetal',sides=8)
        for side in (-1,1):
            axis=X*side;start=np.array((x+side*1.20,y,z))
            P.lathe_axis(m,start,axis,[(.68,0),(.68,.11),(.51,.18)],'ar_ext_metal',sides=8)
            nut(m,start+axis*.17,axis)


def hanger(m,x,r,distance):
    # A slim wall-mounted cantilever carries a threaded drop and split saddle.
    high=r+5.0;wall=-distance+.35
    box(m,(x,wall+.10,high),(5.1,.55,8.3),bevel=.18)
    for dx in (-1.55,1.55):
        for dz in (-2.7,2.7):nut(m,(x+dx,wall+.40,high+dz),Y,.36)
    y0,y1=wall+.45,2.0
    box(m,(x,(y0+y1)/2,high),(1.7,y1-y0,1.40),bevel=.14)
    # Triangular web at the root, with true thickness and a restrained bevelled arm.
    triangle=[(y0,high-.7),(y0,high-5.0),(y0+min(12.,distance*.38),high-.7)]
    for side in (-1,1):
        P.card(m,'ar_gunmetal',[(x+side*.24,y,z) for y,z in triangle],side*X)
    for i,(y,z) in enumerate(triangle):
        yy,zz=triangle[(i+1)%3]
        P.card(m,'ar_gunmetal',[(x-.24,y,z),(x+.24,y,z),(x+.24,yy,zz),(x-.24,yy,zz)],
               (0,(z+zz)/2-np.mean(triangle,axis=0)[1],-((y+yy)/2-np.mean(triangle,axis=0)[0])))
    P.rod(m,(x,0,r+.45),(x,0,high+1.0),.24,'ar_ext_metal',sides=12)
    nut(m,(x,0,high+.7),Z,.43)
    # Rounded saddle band, softened lips, black isolation liner at contact.
    profile=[(r+.10,-.87),(r+.54,-.87),(r+.70,-.67),(r+.70,.67),(r+.54,.87),(r+.10,.87)]
    P.lathe_axis(m,(x,0,0),X,profile,'ar_gunmetal',sides=32)
    for side in (-1,1):
        P.lathe_axis(m,(x,0,0),X,[(r+.12,side*.88),(r+.12,side*.99)],'ar_dark',sides=32)
    box(m,(x,0,r+.63),(2.0,1.8,1.0),bevel=.13)


def pipe_end_caps(model,a,b,r,paint,wall_n=None):
    """Close both tube rims with shallow dished heads, using the tube's exact rings."""
    import ares_map as A
    a,b=np.asarray(a,float),np.asarray(b,float)
    along=(b-a)/np.linalg.norm(b-a)
    assert abs(along[0])>.999999 and r>0
    if wall_n is None:
        wall_n=min((A.HALL_N0,A.CON_N0,A.HALL_N0-A.WALL),key=lambda n:abs(a[1]-n))
    away=np.array((0.,1. if a[1]>wall_n else -1.,0.))
    sides=48 if r>=7 else 32
    depth=.30*r
    rings=[0.,.06]+list(np.linspace(math.pi/12,math.pi/2,6))
    before=model.triangle_count()
    for centre,axis in ((a,-along),(b,along)):
        def point(theta,phi):
            radial=away*math.cos(phi)+Z*math.sin(phi)
            p=centre+radial*(r*math.cos(theta))+axis*(depth*math.sin(theta))
            normal=radial*(math.cos(theta)/r)+axis*(math.sin(theta)/depth)
            normal/=np.linalg.norm(normal)
            return p,normal
        for j,(t0,t1) in enumerate(zip(rings,rings[1:])):
            for k in range(sides):
                p0,p1=k*math.tau/sides,(k+1)*math.tau/sides
                samples=[(t0,p0),(t0,p1),(t1,p1)]
                if j<len(rings)-2:samples.append((t1,p0))
                pts,normals=zip(*(point(t,p) for t,p in samples))
                finish='ar_pw_metal' if j==0 and paint=='ar_pipe' else PAINTS.get(paint,paint)
                uv=[(np.dot(p-centre,away)/48,np.dot(p-centre,Z)/48) for p in pts]
                P.card(model,finish,pts,sum(normals),uv=uv,normals=normals)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p:48. if p in ('ar_pw_pipe','ar_pw_copper') else 16. for p in MATERIALS})
    return dict(caps=2,sides=sides,depth=depth,triangles=model.triangle_count()-before)


def pipe_run(model,a,b,r,paint,bracket=120.,wall_n=None):
    import ares_map as A
    a,b=np.asarray(a,float),np.asarray(b,float)
    length=float(np.linalg.norm(b-a));r=float(r)
    assert length>12 and r>0 and bracket>24
    assert abs(a[1]-b[1])<1e-6 and abs(a[2]-b[2])<1e-6
    if wall_n is None:
        wall_n=min((A.HALL_N0,A.CON_N0,A.HALL_N0-A.WALL),key=lambda n:abs(a[1]-n))
    distance=abs(a[1]-wall_n)
    assert distance>r+1 and distance<80
    along=(b-a)/length;away=np.array((0.,1. if a[1]>wall_n else -1.,0.))
    axes=np.array((along,away,Z));local=K.Model()
    sides=48 if r>=7 else 32
    # Smooth vertex normals and cylindrical UVs preserve a continuous highlight.
    for i in range(sides):
        angles=(i*math.tau/sides,(i+1)*math.tau/sides)
        d0,d1=[np.array((0.,math.cos(t),math.sin(t))) for t in angles]
        pts=[d0*r,d1*r,X*length+d1*r,X*length+d0*r]
        P.card(local,paint,pts,d0+d1,normals=[d0,d1,d1,d0],
               uv=[(0,angles[0]*r/48),(0,angles[1]*r/48),
                   (length/48,angles[1]*r/48),(length/48,angles[0]*r/48)])
    joints=[k*bracket for k in range(1,int(length//bracket)+1) if k*bracket<length-4]
    supports=list(np.arange(bracket*1.25,length-8,bracket*2))
    for x in joints:flange(local,x,r)
    for x in supports:hanger(local,float(x),r,distance)
    assert not local.boxes and not local.hulls
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p:48. if p in ('ar_pw_pipe','ar_pw_copper') else 16. for p in MATERIALS})
    # P.card re-winds reflected frames, retaining per-vertex normals and UVs.
    for key,rows in local.polygons.items():
        for index,(pts,normal) in enumerate(rows):
            ns=local.polygon_normals.get((key,index))
            assert np.isfinite(pts).all() and np.isfinite(normal).all()
            P.card(model,PAINTS[key],[a+p@axes for p in pts],normal@axes,
                   uv=local.polygon_uvs.get((key,index)),
                   normals=[n@axes for n in ns] if ns is not None else None)
    caps=pipe_end_caps(model,a,b,r,paint,wall_n)
    return dict(triangles=local.triangle_count(),sides=sides,joints=len(joints),
                supports=len(supports),radius=r,length=length,end_caps=caps)
