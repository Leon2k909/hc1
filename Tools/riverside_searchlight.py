"""Formed industrial searchlight. Beam/lens anchor and tower collision stay with the caller."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.v(0,0,1)
MATS={f'sl_{n}':f'materials/riverside/searchlight-v1/{n}.vmat' for n in ('enamel','alloy','rubber','plate','brass')}

def body():
    m=K.Model()
    def b(c,size,mat='sl_enamel',bevel=.12):P.bevel_box(m,c,(X,Y,Z),size,mat,bevel)
    def rod(a,b,r,mat='sl_alloy',sides=16):P.rod(m,a,b,r,mat,sides,caps=True)
    def turned(profile,mat='sl_enamel',sides=64):
        # Profile is (axial x, radius), with smooth per-corner normals.
        for (x0,r0),(x1,r1) in zip(profile[:-1],profile[1:]):
            slope=P.unit((r0-r1,x1-x0))
            for i in range(sides):
                aa=[2*math.pi*k/sides for k in (i,i+1)]
                ds=[P.v(0,-math.cos(a),math.sin(a)) for a in aa]
                ps=[X*x0+ds[0]*r0,X*x0+ds[1]*r0,X*x1+ds[1]*r1,X*x1+ds[0]*r1]
                ns=[X*slope[0]+ds[0]*slope[1],X*slope[0]+ds[1]*slope[1],X*slope[0]+ds[1]*slope[1],X*slope[0]+ds[0]*slope[1]]
                uv=[((x0+12)/24,i/sides),((x0+12)/24,(i+1)/sides),((x1+12)/24,(i+1)/sides),((x1+12)/24,i/sides)]
                keep=[0,2,3] if r0<1e-8 else [0,1,2] if r1<1e-8 else [0,1,2,3]
                P.card(m,mat,[ps[k] for k in keep],ns[0],uv=[uv[k] for k in keep],normals=[ns[k] for k in keep])
    # Cast rear cap, tapered barrel and a distinct rolled front flange.
    turned([(-10.2,0),(-10.2,3.4),(-9.9,4.6),(-9.1,6.2),(-7.8,7.5),(-5.8,8.25),(-3.5,8.6),(5.8,8.6),(7.1,9.0),(8.0,9.45),(8.65,9.45),(8.9,9.15),(8.9,8.1),(7.8,8.1)])
    # Deep fin grooves and machined cooling rings read around the entire rear casting.
    for x,r in ((-8.4,7.4),(-7.1,8.0),(-5.8,8.5),(-4.5,8.8)):
        turned([(x-.23,r-.55),(x-.23,r+.25),(x-.1,r+.45),(x+.1,r+.45),(x+.23,r+.25),(x+.23,r-.55)],'sl_enamel')
    # Front lens retaining ring and gasket; the original luminous lens sits at x=10.2, radius=8.
    turned([(8.7,8.12),(8.7,9.6),(9.0,9.85),(9.7,9.85),(10.0,9.55),(10.0,8.18),(9.7,8.10),(8.7,8.12)],'sl_alloy')
    turned([(9.95,8.01),(9.95,8.30),(10.15,8.30),(10.15,8.01),(9.95,8.01)],'sl_rubber')
    for a in np.linspace(0,2*math.pi,8,endpoint=False):
        d=P.v(0,math.cos(a),math.sin(a));at=X*9.85+d*9.04
        rod(at-X*.07,at+X*.24,.28,sides=6)
        P.torus(m,at,X,.33,.055,'sl_alloy',20,6)
    # A short pressed rain visor, safely outside the existing beam's aperture.
    for k in range(32):
        a0=math.radians(23+134*k/32);a1=math.radians(23+134*(k+1)/32)
        d0=P.v(0,math.cos(a0),math.sin(a0));d1=P.v(0,math.cos(a1),math.sin(a1))
        for r,n in ((10.32,1),(10.10,-1)):
            ps=[X*7.7+d0*r,X*12.4+d0*r,X*12.4+d1*r,X*7.7+d1*r]
            P.card(m,'sl_enamel',ps,(d0+d1)*n,normals=[d0*n,d0*n,d1*n,d1*n])
        for x,n in ((7.7,-X),(12.4,X)):
            P.card(m,'sl_enamel',[X*x+d0*10.1,X*x+d1*10.1,X*x+d1*10.32,X*x+d0*10.32],n)
    for a in (23,157):
        d=P.v(0,math.cos(math.radians(a)),math.sin(math.radians(a)))
        P.card(m,'sl_enamel',[X*7.7+d*10.1,X*12.4+d*10.1,X*12.4+d*10.32,X*7.7+d*10.32],P.v(0,-d[2],d[1]))
    # Side trunnions, adjustment wheels and visible axle hardware.
    for sign in (-1,1):
        rod((0,sign*8.0,0),(0,sign*10.3,0),2.2,'sl_enamel',32)
        rod((0,sign*9.8,0),(0,sign*10.6,0),2.55,'sl_rubber',32)
        rod((0,sign*12.4,0),(0,sign*13.1,0),1.9,'sl_alloy',32)
        rod((0,sign*13.05,0),(0,sign*13.65,0),.70,'sl_alloy',6)
        # Short knurled grip lever is bolted to each trunnion's outer face.
        b((1.6,sign*13.3,-.9),(3.3,.45,.65),'sl_alloy',.15)
    # Rear electrical gland, weather boot and a protected ventilation cover.
    rod((-10.0,0,0),(-11.4,0,0),1.35,'sl_brass',6)
    rod((-11.2,0,0),(-12.2,0,0),.86,'sl_rubber',20)
    b((-3.2,0,-8.48),(5.8,4.0,.65),'sl_enamel',.18)
    for i in range(6):b((-5.2+i*.8,0,-8.85),(.23,2.9,.20),'sl_rubber',.05)
    # Fixed engraved identification plate on the camera-facing side.
    b((3.7,-8.58,.1),(5.7,.22,2.9),'sl_alloy',.08)
    P.card(m,'sl_plate',[(.98,-8.705,-1.25),(6.42,-8.705,-1.25),(6.42,-8.705,1.45),(.98,-8.705,1.45)],-Y,uv=[(0,0),(1,0),(1,1),(0,1)])
    for x in (1.2,6.2):
        for z in (-1.05,1.25):rod((x,-8.71,z),(x,-8.82,z),.10,'sl_alloy',10)
    bind(m);return m

def bind(m):
    for paint,path in MATS.items():m.material_overrides[paint]=path;m.tile_overrides[paint]=12

def searchlight(m,sl,head,axis):
    sl,head,axis=[np.asarray(p,float) for p in (sl,head,axis)]
    side=P.unit(np.cross(Z,axis));up=P.unit(np.cross(axis,side));rot=np.column_stack((axis,side,up))
    src=body();dst=K.Model()
    for paint,faces in src.polygons.items():
        for i,(points,normal) in enumerate(faces):
            q=[rot@np.asarray(p)+head for p in points]
            n=rot@np.asarray(normal)
            uv=src.polygon_uvs.get((paint,i));normals=src.polygon_normals.get((paint,i))
            P.card(dst,paint,q,n,uv=uv,normals=[rot@np.asarray(a) for a in normals] if normals is not None else None)
    m.extend(dst)
    horizontal=P.unit((axis[0],axis[1],0));axes=(horizontal,side,Z)
    def b(at,size,mat='sl_enamel',bevel=.1):P.bevel_box(m,at,axes,size,mat,bevel)
    # The mount remains upright on the tower rail when the lamp pitches down.
    P.cylinder(m,head,2.5,head[2]-16,head[2]-12.0,'sl_alloy',32,top='sl_alloy',bottom='sl_alloy')
    P.cylinder(m,head,3.35,head[2]-13.8,head[2]-12.8,'sl_enamel',32,top='sl_enamel',bottom='sl_enamel')
    b(head-Z*12.0,(6.0,25.7,1.35))
    for sign in (-1,1):
        b(head+side*(sign*11.6)-Z*5.6,(4.6,1.25,12.0),bevel=.3)
        for z in (-10.5,-8.1):
            at=head+side*(sign*12.28)+Z*z
            P.rod(m,at,at+side*(sign*.3),.32,'sl_alloy',6,caps=True)
    # Flexible supply cable descends to the existing rail mount.
    cable=[head-axis*12.0,head-axis*14.8-Z*2.5,head-axis*14.8-Z*9.8,head-Z*13.6-side*2.7]
    P.pipe(m,cable,.32,'sl_rubber',sides=12,bend=2.5)
    bind(m);return m

def model():
    m=K.Model();searchlight(m,(0,0,-6),(0,0,0),X)
    # Same emitting polygon as the original; no edits to lens/beam materials.
    side,up=P.perp(X)
    P.card(m,'rs_lamp_search',[X*10.2+(side*math.cos(2*math.pi*k/12)+up*math.sin(2*math.pi*k/12))*8 for k in range(12)],X)
    return m
