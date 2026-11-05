"""Approved Riverside porch drinks fridge, placed two inches from the storefront wall."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
MAT="materials/riverside/drinks-fridge-v1"
CENTER=(96.,624.,20.)
def model():
    m=K.Model();X=np.array((1.,0.,0.));Y=np.array((0.,-1.,0.));Z=np.array((0.,0.,1.));C=np.array(CENTER)
    def P(x,d,z):return C+X*x+Y*d+Z*z
    def box(c,size,paint,b=.10,skip=()):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b,skip=skip)
    def lathe(c,axis,prof,paint,sides=24):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in prof],paint,sides=sides)
    def cylinder(c,axis,length,r,paint,sides=16):lathe(c,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides)
    def bolt(c,axis=Y,r=.12):cylinder(c,axis,.06,r,'steel',12)
    FONT={
     'D':[[(0,0),(0,1),(.65,1),(1,.75),(1,.25),(.65,0),(0,0)]],
     'R':[[(0,0),(0,1),(.8,1),(1,.8),(1,.65),(.8,.5),(0,.5)],[(.5,.5),(1,0)]],
     'I':[[(.5,0),(.5,1)],[(.1,0),(.9,0)],[(.1,1),(.9,1)]],
     'N':[[(0,0),(0,1),(1,0),(1,1)]],
     'K':[[(0,0),(0,1)],[(1,1),(0,.5),(1,0)]],
     'S':[[(1,.92),(.8,1),(.2,1),(0,.8),(0,.6),(1,.4),(1,.15),(.8,0),(.2,0),(0,.08)]],
     'C':[[(1,1),(.2,1),(0,.8),(0,.2),(.2,0),(1,0)]],
     'O':[[ (.2,0),(0,.2),(0,.8),(.2,1),(.8,1),(1,.8),(1,.2),(.8,0),(.2,0)]],
     'L':[[(0,1),(0,0),(1,0)]],
     'A':[[(0,0),(0,.75),(.5,1),(1,.75),(1,0)],[(0,.48),(1,.48)]],
     'M':[[(0,0),(0,1),(.5,.45),(1,1),(1,0)]],
     'E':[[(1,1),(0,1),(0,0),(1,0)],[(0,.5),(.85,.5)]]}
    def word(text,mapper,height,width,stroke,gap,paint):
     assert all(c in FONT for c in text)
     for index,char in enumerate(text):
      for path in FONT[char]:
       for aa,bb in zip(path,path[1:]):
        a=np.array((index*(width+gap)+aa[0]*width,aa[1]*height));b=np.array((index*(width+gap)+bb[0]*width,bb[1]*height))
        delta=b-a;side=np.array((-delta[1],delta[0]))/np.linalg.norm(delta)*stroke*.5
        D._face(m,paint,[mapper(*q) for q in (a-side,b-side,b+side,a+side)],Y)
    # Closed rear and sides; the cabinet front is open, not another picture card.
    box((0,0,5.2),(30,28,9.6),'enamel',.45,skip=('+y',))
    for s in (-1,1):
     box((s*14.25,0,40.3),(1.5,28,61.8),'enamel',.35)
     box((s*13.44,-.4,38.2),(.10,24.6,53.0),'liner',.025)
    box((0,-13.4,40.3),(28.5,1.2,61.8),'enamel',.3)
    box((0,-12.72,38.2),(26.7,.12,53.0),'liner',.025)
    box((0,0,70.5),(30,28,3.),'enamel',.40)
    box((0,-.4,66.1),(26.8,24.6,.18),'liner',.035)
    for x in (-11.8,11.8):
     for d in (-10.8,10.8):cylinder((x,d,0),Z,.5,1.1,'frame',20)
    # Recessed compressor intake, grille bars and service-panel screws.
    box((0,12.8,5.1),(27.2,.18,6.6),'frame',.05)
    for z in np.linspace(2.7,7.6,8):box((0,13.95,z),(25.4,.38,.23),'enamel',.055)
    for x in (-12.9,12.9):box((x,13.82,5.1),(.45,.50,6.0),'enamel',.12)
    box((0,13.8,1.25),(26.6,.45,1.0),'enamel',.15)
    box((0,13.8,9.0),(26.6,.45,.85),'enamel',.15)
    for x in (-12.,12.):bolt((x,14.04,8.4))
    # Four steel-wire shelves with raised retaining lips and label carriers.
    for row,z in enumerate((14.5,27.,39.5,52.)):
     for x in np.linspace(-12.3,12.3,12):G.tube(m,[P(x,-10.8,z),P(x,10.8,z)],.055,'steel',sides=8)
     for d in (-10.8,10.8):G.tube(m,[P(-12.3,d,z),P(12.3,d,z)],.10,'steel',sides=10)
     for x in (-12.3,12.3):G.tube(m,[P(x,-10.8,z),P(x,10.8,z)],.10,'steel',sides=10)
     box((0,11.0,z+.35),(25.0,.45,.60),'liner',.06)
     for x in (-8.4,-2.8,2.8,8.4):box((x,11.25,z+.35),(1.8,.025,.32),'label',.006)
     # Rows are stocked with separate cans/bottles, leaving depth between products.
     for depth in (2.5,8.0):
      for col,x in enumerate((-8.4,-2.8,2.8,8.4)):
       paint=('red','blue','green')[(row+col)%3]
       base=z+.14
       if row==0:
        profile=[(0,0),(1.16,0),(1.30,.20),(1.34,.60),(1.34,2.5),(1.34,5.7),(1.34,6.7),(1.25,7.2),(.60,8.4),(.48,8.5),(.48,9.2),(0,9.2)]
        paints=[paint,paint,paint,paint,'label',paint,paint,paint,paint,'frame','frame']
        lathe((x,depth,base),Z,profile,paints,24)
        cylinder((x,depth,base+9.20),Z,.38,.53,paint,20)
       else:
        profile=[(0,0),(1.08,0),(1.23,.14),(1.30,.32),(1.30,1.65),(1.30,2.05),(1.30,4.15),(1.30,4.55),(1.30,5.7),(1.21,6.0),(1.12,6.10),(0,6.10)]
        paints=['steel','steel',paint,paint,paint,'label',paint,paint,paint,'steel','steel']
        lathe((x,depth,base),Z,profile,paints,24)
        G.torus(m,P(x,depth,base+6.12),Z,1.12,.045,'steel',seg=24,sides=6)
        G.torus(m,P(x,depth-.13,base+6.15),Z,.24,.055,'frame',seg=16,sides=6)
       text={'red':'COLA','blue':'SODA','green':'LIME'}[paint]
       radius=1.365 if row==0 else 1.325
       def print_surface(a,b):
        angle=(a-.88)/radius
        return P(x+radius*math.sin(angle),depth+radius*math.cos(angle),base+(3.60 if row==0 else 2.73)+b)
       word(text,print_surface,.60,.35,.047,.12,'frame')
    # Framed closed glass door, gasket, hinge barrels and a vertical pull handle.
    for s in (-1,1):
     box((s*13.2,12.7,38.0),(1.35,1.6,55.2),'frame',.17)
     box((s*13.15,11.75,38.0),(1.6,.28,56.0),'frame',.08)
    for z in (10.7,65.4):box((0,12.7,z),(27.6,1.6,1.35),'frame',.17)
    G._box3(m,P(0,13.28,38.0),(X,Y,Z),(25.05,.06,53.3),'glass')
    for z in (17,59):
     cylinder((-13.65,12.65,z-1.0),Z,2.0,.34,'steel',20)
     for zz in (z-.75,z+.75):bolt((-13.65,13.05,zz))
    for z in (28.,50.):cylinder((11.65,12.9,z),Y,.86,.31,'steel',20)
    G.tube(m,[P(11.65,13.78,28),P(11.65,13.78,50)],.31,'steel',sides=20)
    # Visible interior diffusers reuse the map's existing cool-lamp material; the
    # saved porch-fridge point light remains the only local light for this asset.
    for x in (-12.65,12.65):box((x,10.7,38.1),(.30,.35,51.6),'led',.08)
    # A simple unlit header avoids another luminous picture across the door.
    # The plaque sits proud of the cabinet's d=14 front, including the top slab.
    box((0,13.99,68.8),(27.7,.22,4.6),'red',.2)
    word('DRINKS',lambda a,b:P(-8.1+a,14.13,67.75+b),2.0,2.05,.14,.78,'label')
    for x in (-13.4,13.4):bolt((x,14.11,68.8),r=.10)
    m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('enamel','liner','frame','steel','red','blue','green','label')}
    m.material_overrides.update(glass=MAT+'/glass.vmat',led='materials/riverside/rs_lamp_cool.vmat')
    m.tile_overrides={p:16 for p in m.polygons}
    return m

def append_to(target):
    import riverside_parts as P
    legacy=K.Model()
    P.fridge(legacy,CENTER[:2],(0.,-1.),CENTER[2])
    target.boxes.extend(legacy.boxes)
    target.hulls.extend(legacy.hulls)
    m=model()
    for paint,faces in m.polygons.items():
        alias="rsvf_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
