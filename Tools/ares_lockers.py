"""Approved Ares lockers; original steel/brass and lighter formed doors."""
import math
import numpy as np
import map_kit as K
import ares_materials as AM
import riverdale_parts as G
import railhead_dress_detail as D
def model(e,number,n=-709.,z0=0.):
    m=K.Model();X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));C=np.array((float(e),float(n),float(z0)))
    def P(x,d,z):return C+X*x+Y*d+Z*z
    def box(c,size,paint='ar_steel',b=.10):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
    def cyl(c,axis,length,r,paint='ar_steel',sides=20):G.lathe_axis(m,P(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
    def screw(x,d,z):
     cyl((x,d,z),Y,.035,.16,'ar_steel',16)
     box((x,d+.039,z),(.17,.008,.035),'ar_dark',.003)
    # Folded sheet enclosure with a recessed toe plinth and separate top cap.
    box((0,-.4,1.8),(25.,21.2,3.6),'ar_gunmetal',.22)
    box((0,0,83.15),(25.,22.,1.7),'ar_steel',.32)
    box((0,-10.6,43.0),(24.1,.8,79.0),'ar_steel',.20)
    for s in (-1,1):
     box((s*12.05,0,43.0),(.9,22.,79.0),'ar_steel',.21)
     box((s*11.82,10.53,43.0),(1.18,.94,78.8),'ar_steel',.13)
     for d in (-8.6,8.6):cyl((s*9.8,d,0),Z,1.15,.75,'ar_dark',20)
    box((0,0,4.05),(23.3,20.9,.9),'ar_steel',.16)
    # The gasket sits behind a formed door: recessed centre and raised folded edges.
    box((0,10.54,43.0),(23.35,.32,78.2),'ar_dark',.16)
    box((0,10.54,43.0),(22.65,.36,77.0),'ar_white',.20)
    for s in (-1,1):box((s*10.90,10.95,43.0),(.85,.46,76.5),'ar_white',.14)
    for z in (5.05,80.95):box((0,10.95,z),(22.3,.46,.85),'ar_white',.14)
    box((0,10.77,7.2),(20.0,.09,.055),'ar_dark',.012)
    # Pressed ventilation slots with dark recesses and real angled metal blades.
    angle=math.radians(18);out=Y*math.cos(angle)+Z*math.sin(angle);up=-Y*math.sin(angle)+Z*math.cos(angle)
    for centre in (16.,71.0):
     box((0,10.76,centre),(15.0,.08,8.1),'ar_dark',.06)
     for j in range(6):
      G.bevel_box(m,P(0,10.98,centre-3.1+j*1.24),(X,out,up),(14.6,.65,.40),'ar_gunmetal',bevel=.065)
     for x in (-7.57,7.57):box((x,10.82,centre),(.18,.18,8.3),'ar_gunmetal',.035)
    # Three serviceable hinge barrels and their mounting leaves.
    for z in (16.,43.,70.):
     for x in (-11.55,-10.48):
      box((x,10.93,z),(.68,.36,2.8),'ar_steel',.10)
      for zz in (z-.9,z+.9):screw(x,11.13,zz)
     cyl((-11.0,11.10,z-1.7),Z,3.4,.31,'ar_steel',24)
     for zz in (z-1.73,z+1.65):cyl((-11.,11.1,zz),Z,.13,.37,'ar_brass',20)
    # Recessed pull pocket, rounded brass handle and a keyed cylinder.
    box((6.1,10.78,48.2),(3.3,.09,7.2),'ar_dark',.18)
    G.tube(m,[P(6.1,10.90,45.5),P(6.1,11.64,46.0),P(6.1,11.64,50.4),P(6.1,10.90,50.9)],.23,'ar_brass',sides=16,bend_radius=.4)
    for z in (45.5,50.9):cyl((6.1,10.86,z),Y,.20,.39,'ar_brass',24)
    cyl((6.1,10.78,53.1),Y,.40,.47,'ar_brass',32)
    box((6.1,11.19,53.1),(.095,.018,.58),'ar_dark',.012)
    # Small inset identifier: geometry lettering stays sharp without a glowing card.
    box((-1.0,10.83,58.4),(7.1,.21,4.2),'ar_steel',.17)
    box((-1.0,10.95,58.4),(6.6,.05,3.7),'ar_dark',.08)
    segments={'0':'abcedf','1':'bc','2':'abged','3':'abgcd','4':'bcfg','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abcdfg'}
    lines={'a':((0,1),(1,1)),'b':((1,1),(1,.5)),'c':((1,.5),(1,0)),'d':((0,0),(1,0)),'e':((0,0),(0,.5)),'f':((0,.5),(0,1)),'g':((0,.5),(1,.5))}
    for i,char in enumerate(f'{int(number):02d}'):
     for seg in segments[char]:
      a,b=lines[seg];a=np.array((-2.75+i*2.0+a[0]*1.15,57.20+a[1]*2.4));b=np.array((-2.75+i*2.0+b[0]*1.15,57.20+b[1]*2.4))
      dv=b-a;side=np.array((-dv[1],dv[0]))/np.linalg.norm(dv)*.065
      D._face(m,'ar_white',[P(-q[0]-2.0,10.99,q[1]) for q in (a-side,b-side,b+side,a+side)],Y)
    for x in (-11.7,11.7):
     for z in (4.7,81.2):screw(x,11.03,z)
    for paint in m.polygons:
        m.material_overrides[paint]=f"{AM.RESOURCE_DIR}/{paint}.vmat"
        m.tile_overrides[paint]=AM.TILES.get(paint,64.)
    return m

def append_to(target,e,number,n=-709.,z0=0.):
    m=model(e,number,n,z0)
    for paint,faces in m.polygons.items():
        alias="ar_in_locker_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            uv=m.polygon_uvs.get((paint,i))
            if uv is None:
                uv=[K.face_uv(K.to_world(p),K.to_world(normal),paint,K.uv_offset('locker'),m.tile_overrides[paint]) for p in points]
            target.polygon(alias,points,normal,uv=uv,normals=m.polygon_normals.get((paint,i)))
