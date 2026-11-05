"""Approved ReefHall circulation pump, exact prototype geometry and texture mapping."""
import math
import numpy as np
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
import railhead_dress_detail as D
def model():
    m=K.Model();X,Y,Z=np.eye(3);O=np.array((-380.,1610.,0.))
    def P(x,y,z):return O+np.array((x,y,z))
    def box(c,size,paint='rh_gunmetal',b=.25,axes=None):G.bevel_box(m,P(*c),axes or (X,Y,Z),size,paint,bevel=b)
    def turn(c,axis,profile,paint='rh_pipe',sides=48):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
    def cylinder(c,axis,r,length,paint='rh_gunmetal',sides=32):
     turn(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
    def bolt(c,axis,r=.72,length=.65):
     cylinder(c,axis,r*1.30,.18,'rh_gunmetal',24)
     cylinder(tuple(np.array(c)+axis*.18),axis,r,length,'rh_stainless',6)
    def ring(c,axis,r,inner,depth,paint='rh_pipe',sides=48):
     turn(c,axis,[(inner,0),(r-.25,0),(r,.25),(r,depth-.25),(r-.25,depth),(inner,depth),(inner,0)],paint,sides)
    # Chamfered skid and bearing feet preserve the original base's 68 x 36 envelope.
    box((0,0,1.2),(68,36,2.4),b=.5)
    for y in (-13.,13.):box((0,y,4.8),(64,5.5,4.8),'rh_steel',.3)
    for x in (-29.,29.):
     for y in (-13.,13.):bolt((x,y,7.2),Z,1.1,.9)
    for x in (-23.,-6.):
     for y in (-10.,10.):
      box((x,y,9.3),(7,9,4.2),'rh_steel_blue',.35);bolt((x,y*1.25,11.5),Z,.85,.8)
    for y in (-10.,10.):box((18,y,8.6),(10,8,5.6),'rh_pipe',.35);bolt((18,y*1.25,11.5),Z,.85,.8)
    # Motor stator, real longitudinal cooling fins and stepped end shields.
    turn((0,0,26),X,[(0,-28),(10.5,-28),(12.6,-26),(13,-24),(13,-3),(11,-1),(0,-1)],'rh_steel_blue')
    for k in range(24):
     a=2*math.pi*k/24;rad=Y*math.cos(a)+Z*math.sin(a);tan=-Y*math.sin(a)+Z*math.cos(a)
     if rad[2]>.86:continue # terminal enclosure seats on a flat crown
     c=np.array((-13.5,0.,26.))+rad*14.10
     box(c,(19.5,.72,2.6),'rh_steel_blue',.14,(X,tan,rad))
    turn((0,0,26),X,[(0,-31),(11.5,-31),(14.7,-29.5),(15.5,-27.8),(15.5,-25),(14.7,-24),(0,-24)],'rh_steel_blue')
    # Rear fan grille has visible slots between bars, with a dark recessed fan.
    ring((-31.5,0,26),-X,14.3,11.7,.65,'rh_gunmetal')
    cylinder((-31.3,0,26),-X,11.65,.10,'rh_black')
    for y in np.arange(-9.6,10.,2.4):
     h=math.sqrt(11.6**2-y*y)*2
     box((-32.05,y,26),(.42,.60,h),'rh_steel_blue',.12)
    turn((0,0,26),X,[(0,-2),(13.5,-2),(15.3,-.7),(15.3,1),(13,2.3),(0,2.3)],'rh_steel_blue')
    for k in range(6):
     a=2*math.pi*k/6;bolt((2.35,11.8*math.cos(a),26+11.8*math.sin(a)),X,.8,.9)
    # Shaft and coupling: a small separate guard with open side ribs.
    cylinder((2.5,0,26),X,3.0,6,'rh_stainless')
    for x in (3.,7.):ring((x,0,26),X,8.8,6.8,.9,'rh_gunmetal',32)
    for k in range(12):
     a=2*math.pi*k/12;rad=Y*math.cos(a)+Z*math.sin(a);tan=-Y*math.sin(a)+Z*math.cos(a)
     box(np.array((5.5,0,26))+rad*8.2,(4,.9,1.2),'rh_gunmetal',.15,(X,tan,rad))
    # Cast volute: a full rounded housing, with a split flange and perimeter bolts.
    turn((0,0,26),X,[(0,8.5),(13,8.5),(16.8,10),(18.9,13),(19.6,17),(19.6,20.5),(18.8,23),(14,26),(0,26)],'rh_pipe',64)
    ring((19,0,26),X,20.,17.5,1.4,'rh_pipe_dark',64)
    for k in range(10):
     a=2*math.pi*(k+.5)/10;bolt((20.5,18.0*math.cos(a),26+18.0*math.sin(a)),X,.80,.95)
    # Horizontal inlet and vertical delivery stubs retain the old end positions.
    cylinder((25,0,26),X,7,11,'rh_pipe')
    ring((36,0,26),X,11.5,5.2,4,'rh_pipe',48)
    cylinder((35.6,0,26),X,5.18,.12,'rh_black')
    for k in range(8):
     a=2*math.pi*(k+.5)/8;bolt((40,9*math.cos(a),26+9*math.sin(a)),X,.65,.65)
    cylinder((18,0,42),Z,7,24,'rh_pipe')
    ring((18,0,66),Z,11.5,5.2,4,'rh_pipe',48)
    cylinder((18,0,65.7),Z,5.18,.12,'rh_black')
    for k in range(8):
     a=2*math.pi*(k+.5)/8;bolt((18+9*math.cos(a),9*math.sin(a),70),Z,.65,.65)
    # Terminal enclosure, gasketed lid, four screws and a short armoured cable.
    box((-13,0,42.7),(17,13,7.8),'rh_steel_blue',.65)
    box((-13,0,46.8),(18,14,.6),'rh_rubber',.2)
    box((-13,0,48),(18.6,14.6,1.8),'rh_steel_blue',.45)
    for x in (-20.,-6.):
     for y in (-5.,5.):bolt((x,y,49),Z,.40,.30)
    cylinder((-21.5,0,44),-X,1.7,2.4,'rh_gunmetal',24)
    G.tube(m,[P(-24,0,44),P(-27,-3,44),P(-28,-9,40),P(-28,-12,32)],.70,'rh_rubber',sides=12,bend_radius=2.)
    for z in np.arange(33,39,1.2):G.torus(m,P(-28,-12,z),Z,.76,.12,'rh_gunmetal',seg=16,sides=6)
    # Small mechanical pressure dial on a brass take-off, with real ticks and needle.
    cylinder((18,-6,55),-Y,.80,5.5,'rh_brass',20)
    turn((18,-11.5,57),-Y,[(0,0),(2.7,0),(3.1,.5),(3.1,2.2),(2.7,2.5),(0,2.5)],'rh_stainless',48)
    D.disc(m,'rh_coral_white',P(18,-14.05,57),-Y,2.63,48)
    for k in range(11):
     a=math.radians(-210+k*24);a0=P(18+2.02*math.cos(a),-14.10,57+2.02*math.sin(a));a1=P(18+2.40*math.cos(a),-14.10,57+2.40*math.sin(a))
     D.rod(m,a0,a1,.055,'rh_black',6)
    D.rod(m,P(18,-14.14,57),P(19.55,-14.14,58.2),.09,'rh_black',8)
    D.disc(m,'rh_brass',P(18,-14.16,57),-Y,.30,16)
    # Small front identification plate, deliberately unlit.
    box((-13,-7.45,44.1),(10,.16,3.4),'rh_stainless',.12)
    for z,length in ((45,7.4),(44.1,5.6),(43.2,7.4)):box((-13,-7.55,z),(length,.05,.18),'rh_black',.02)
    R.configure(m)
    # Bake the prototype's projected and grain UVs before joining the room.
    offset=K.uv_offset('circulation_pump')
    for paint,faces in m.polygons.items():
        for i,(points,normal) in enumerate(faces):
            if (paint,i) in m.polygon_uvs:continue
            world=[K.to_world(p) for p in points];wn=K.to_world(normal);tile=m.tile_overrides[paint]
            coords=[K.face_uv(p,wn,paint,offset,tile) for p in world]
            if paint in m.grain_paints:
                edges=[world[(j+1)%len(world)]-p for j,p in enumerate(world)]
                along=K.normalise(max(edges,key=lambda e:np.linalg.norm(e)));across=np.cross(wn,along)
                coords=[(float(np.dot(p,across)/tile+offset[0]),float(np.dot(p,along)/tile+offset[1])) for p in world]
            m.polygon_uvs[(paint,i)]=coords
    return m

def append_to(target):
    # The original plinth and cover boxes, with no legacy render faces.
    fr=R.Frame((-380,1610),(1,0))
    R.fbox(target,fr,-34,34,-18,18,0,8,None,R.METAL)
    R.fbox(target,fr,-34,40,-21,21,8,48,None,R.METAL)
    m=model()
    for paint,faces in m.polygons.items():
        alias='rh_cp_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs[(paint,i)],normals=m.polygon_normals.get((paint,i)))
