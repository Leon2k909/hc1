"""A compact pole transformer: formed tank, glazed bushings and bolted pole brackets."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.v(0,0,1)
MATS={n:f'materials/riverside/pole-transformer-v1/{n[3:]}.vmat' for n in
      ('tx_coat','tx_lid','tx_alloy','tx_ceramic','tx_dark','tx_brass','tx_label')}

def model(primary=None):
    m=K.Model();c=np.array((0.,-3.,0.))
    def b(p,size,mat='tx_alloy',bevel=.07):P.bevel_box(m,p,(X,Y,Z),size,mat,bevel)
    def rod(a,b,r,mat='tx_alloy',sides=16):P.rod(m,a,b,r,mat,sides,caps=True)
    def turned(centre,profile,mat,sides=64,tank_uv=False):
        centre=np.asarray(centre,float)
        for (r0,z0),(r1,z1) in zip(profile[:-1],profile[1:]):
            if abs(r1-r0)+abs(z1-z0)<1e-8:continue
            slope=P.unit((z1-z0,r0-r1))
            for k in range(sides):
                a0=2*math.pi*k/sides;a1=2*math.pi*(k+1)/sides
                d0=P.v(math.sin(a0),math.cos(a0),0);d1=P.v(math.sin(a1),math.cos(a1),0)
                points=[centre+d0*r0+Z*z0,centre+d1*r0+Z*z0,centre+d1*r1+Z*z1,centre+d0*r1+Z*z1]
                ns=[d0*slope[0]+Z*slope[1],d1*slope[0]+Z*slope[1],d1*slope[0]+Z*slope[1],d0*slope[0]+Z*slope[1]]
                uv=[(k/sides,(z0+16)/32),((k+1)/sides,(z0+16)/32),((k+1)/sides,(z1+16)/32),(k/sides,(z1+16)/32)] if tank_uv else None
                keep=[0,2,3] if r0<1e-8 else [0,1,2] if r1<1e-8 else [0,1,2,3]
                P.card(m,mat,[points[i] for i in keep],d0*slope[0]+Z*slope[1],uv=[uv[i] for i in keep] if uv else None,normals=[ns[i] for i in keep])
    # Tank and rolled lower seam; the lid is a separate pressing with a fitted rim.
    turned(c,[(0,-16),(7.1,-16),(7.8,-15.8),(8.45,-15.2),(8.7,-14.3),(8.7,12.7),(8.5,14.0),(7.9,14.7),(0,14.7)],'tx_coat',64,True)
    turned(c,[(0,14.55),(8.7,14.55),(9.12,14.85),(9.18,15.5),(8.95,16.0),(8.2,16.3),(5,16.75),(0,16.9)],'tx_lid',64)
    for z,r in ((-14.9,8.55),(14.8,9.12)):
        P.torus(m,c+Z*z,Z,r,.14,'tx_lid',64,6)
    # Lid clamp shoes, studs, washers and hex nuts.
    for a in np.linspace(0,2*math.pi,8,endpoint=False):
        radial=P.v(math.sin(a),math.cos(a),0);tangent=P.v(math.cos(a),-math.sin(a),0)
        at=c+radial*8.8+Z*14.4
        P.bevel_box(m,at,(tangent,radial,Z),(1.0,.75,1.9),'tx_alloy',.08)
        rod(at-Z*.2,at+Z*1.25,.14,sides=12)
        P.cylinder(m,at[:2],.29,at[2]+.5,at[2]+.77,'tx_alloy',6,top='tx_alloy')
    # Fabricated pole saddles. The pole sits at local y12; straps and bolts hold the tank off the timber.
    for z in (-8.5,7.5):
        b((0,5.45,z),(13.5,1.0,2.1),'tx_alloy',.12)
        for x in (-5.4,5.4):
            b((x,8.1,z),(1.2,5.7,2.1),'tx_alloy',.12)
            rod((x,9.75,z),(x,11.1,z),.23,sides=12)
            for y in (9.75,10.9):
                rod((x,y-.12,z),(x,y+.12,z),.47,sides=6)
        P.pipe(m,[(-5.8,10.5,z),(-4.9,14.3,z),(0,17.0,z),(4.9,14.3,z),(5.8,10.5,z)],.30,'tx_alloy',sides=10,bend=1.5)
    for x in (-8.3,8.3):P.torus(m,(x,-3,13.0),X,.67,.18,'tx_coat',24,6)
    # Primary glazed bushing with rounded rain sheds and an exposed terminal stud.
    def bushing(at,scale=1.,height=10.2):
        at=np.asarray(at,float)
        profile=[(0,0),(1.18,0),(1.35,.3),(1.35,.65),(1.05,.85)]
        for z in (1.05,2.75,4.45,6.15):
            profile += [(.78,z),(1.45,z+.25),(1.52,z+.53),(1.35,z+.78),(.78,z+1.0)]
        profile += [(.72,8.0),(.62,8.7),(.50,8.95),(0,8.95)]
        turned(at,[(r*scale,z*height/8.95) for r,z in profile],'tx_ceramic',32)
        rod(at+Z*(height-.25),at+Z*(height+1.1),.23*scale,'tx_brass',16)
        for z in (height+.3,height+.85):P.cylinder(m,at[:2],.42*scale,at[2]+z,at[2]+z+.18,'tx_brass',6,top='tx_brass')
        return at+Z*(height+1.0)
    primary_at=bushing((0,-3,16.9))
    # Two front secondary terminals, seated through the upper tank wall.
    for x in (-4.7,4.7):
        at=P.v(x,-9.9,8.0)
        b((x,-9.45,7.6),(2.1,1.2,2.8),'tx_coat',.15)
        turned(at,[(0,0),(.85,0),(.9,.25),(.7,.5),(.6,2.9),(.9,3.1),(.9,3.4),(.55,3.6),(0,3.6)],'tx_ceramic',24)
        rod(at+Z*3.5,at+Z*4.5,.18,'tx_brass',12)
        b(at+Z*4.25,(1.15,.55,.38),'tx_brass',.06)
        for y in (-.2,.2):rod(at+P.v(0,y,4.15),at+P.v(0,y,4.6),.14,'tx_alloy',12)
        P.pipe(m,[at+P.v(0,0,4.4),at+P.v(x*.25,-2,4.4),at+P.v(x*.35,-2,-4)],.16,'tx_dark',sides=10,bend=1.3)
    # Ground lug, drain plug, conduit stub and identification plate.
    b((-8.65,-3.4,-9.2),(.7,1.8,2.1),'tx_brass',.12)
    rod((-9.0,-3.4,-9.2),(-8.5,-3.4,-9.2),.35,'tx_alloy',6)
    P.pipe(m,[(-9.0,-3.4,-9.2),(-9.4,-3.4,-12),(-8.7,1,-15.3),(-6.4,5,-15.6)],.10,'tx_brass',sides=8,bend=1.2)
    rod((7.8,-5.6,-12.0),(9.2,-5.6,-12.0),.40,'tx_alloy',6)
    # Curved plate follows the can rather than hovering on a flat rectangular backing.
    for k in range(12):
        u0=k/12;u1=(k+1)/12;a0=math.pi+.46-u0*.92;a1=math.pi+.46-u1*.92
        ds=[P.v(math.sin(a),math.cos(a),0) for a in (a0,a1)]
        ps=[c+ds[0]*8.78+Z*(-1.9),c+ds[1]*8.78+Z*(-1.9),c+ds[1]*8.78+Z*3.2,c+ds[0]*8.78+Z*3.2]
        P.card(m,'tx_label',ps,-Y,uv=[(u0,0),(u1,0),(u1,1),(u0,1)],normals=[ds[0],ds[1],ds[1],ds[0]])
    for x in (-3.6,3.6):
        for z in (-1.55,2.85):rod((x,-11.12,z),(x,-11.27,z),.14,'tx_alloy',12)
    # A continuous service lead reaches the actual upper crossarm's insulator.
    if primary is not None:
        end=np.asarray(primary,float)
        P.pipe(m,[primary_at,primary_at+P.v(0,0,5.0),end*.55+primary_at*.45+P.v(0,0,3),end],.20,'tx_dark',sides=12,bend=3.0)
    for paint,path in MATS.items():m.material_overrides[paint]=path;m.tile_overrides[paint]=16
    return m

def transformer(dst,centre,facing,primary=None):
    from riverside_parts import place
    facing=np.asarray(facing,float);angle=math.degrees(math.atan2(facing[1],facing[0]))-90
    theta=math.radians(angle);rot=np.array(((math.cos(theta),-math.sin(theta),0),(math.sin(theta),math.cos(theta),0),(0,0,1)))
    local=None if primary is None else rot.T@(np.asarray(primary,float)-np.asarray(centre,float))
    dst.extend(place(model(local),centre,angle))
    return dst
