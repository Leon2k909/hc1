"""Approved ReefHall wall light, exact prototype geometry and texture mapping."""
import math
import numpy as np
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
import railhead_dress_detail as D
def model():
    m=K.Model();X,Y,Z=np.eye(3);O=np.array((760.,1100.,110.))
    def P(x,y,z):return O+np.array((x,y,z))
    def B(c,size,paint='rh_gunmetal',b=.12):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
    # Cast backplate, rear gasket and recessed sealed body, within the old enclosure.
    B((0,.18,8),(7,.36,16),b=.32)
    B((0,.43,8),(6.55,.18,15.55),'rh_rubber',.22)
    B((0,1.32,8),(6.65,1.62,15.35),b=.42)
    # Two recessed side channels and longitudinal trim strips.
    for side in (-1,1):
     B((side*2.95,2.13,8),(.40,.25,13.65),'rh_rubber',.10)
     B((side*3.10,2.33,8),(.22,.28,13.55),'rh_stainless',.09)
     for z in (3.,5.,7.,9.,11.,13.):B((side*3.31,1.15,z),(.10,.74,.15),'rh_steel',.04)
    # The lens is an actual convex elliptical extrusion, rather than a glowing box face.
    for k in range(40):
     a=-math.pi/2+math.pi*k/40;b=-math.pi/2+math.pi*(k+1)/40
     def q(t,z):return P(2.68*math.sin(t),1.9+1.1*math.cos(t),z)
     def normal(t):return K.normalise(np.array((math.sin(t)/2.68,math.cos(t)/1.1,0.)))
     na,nb=normal(a),normal(b)
     D._face(m,'rh_frosted_lit',[q(a,1.6),q(b,1.6),q(b,14.4),q(a,14.4)],na+nb,normals=[na,nb,nb,na],uv=[(k/40,0),((k+1)/40,0),((k+1)/40,1),(k/40,1)])
    # Rounded end shoes, gasket seams, front fasteners and restrained diffuser guards.
    for z in (.8,15.2):
     B((0,1.62,z),(6.9,2.76,1.6),b=.35)
     B((0,2.75,z+(.80 if z<8 else -.80)),(5.9,.16,.10),'rh_rubber',.035)
     for x in (-2.35,2.35):
      G.lathe_axis(m,P(x,2.995,z),Y,[(0.,0.),(.19,0.),(.23,.06),(.23,.13),(.17,.18),(0.,.18)],'rh_stainless',sides=24)
      B((x,3.184,z),(.22,.022,.045),'rh_black',.009)
    for z in (4.,12.):
     # A shallow guard follows the convex lens, leaving the opal visible between it.
     pts=[P(2.70*math.sin(t),1.9+1.1*math.cos(t)+.055,z) for t in np.linspace(-math.pi/2,math.pi/2,25)]
     G.tube(m,pts,.075,'rh_gunmetal',sides=8,caps=True)
    R.configure(m)
    # Bake the prototype's projected and grain UVs before joining the room.
    offset=K.uv_offset('wall_light')
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
    m=model()
    for paint,faces in m.polygons.items():
        alias='rh_wl_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs[(paint,i)],normals=m.polygon_normals.get((paint,i)))
