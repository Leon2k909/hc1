"""Cast lower crane block and forged safety hook; existing suspension chains stay in the map."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.UP
MATS={f'cb_{n}':f'materials/sewage/crane-blocks-v1/{n}.vmat' for n in ('paint','steel','dark','label','stripes')}
PLACEMENTS=((610,-20,740),(820,240,680))

def local():
 m=K.Model()
 def box(c,size,mat='cb_paint',bevel=.3):P.bevel_box(m,c,(X,Y,Z),size,mat,bevel)
 def axle(c,axis,r,length,mat='cb_steel',sides=32):
  c=np.asarray(c,float);axis=np.asarray(axis,float);P.rod(m,c-axis*length/2,c+axis*length/2,r,mat,sides,caps=True)
 # Two thick cast cheeks with knocked-off corners, tied by side webs and axle spacers.
 for sign in (-1,1):
  box((0,sign*17,42),(46,3,84),bevel=2.1)
  box((sign*20.3,0,42),(5.0,31,78),bevel=1.2)
 for z in (17,63):
  axle((0,0,z),Y,12.2,31,'cb_dark',48)
  for y in (-11,11):P.torus(m,(0,y,z),Y,11.4,.75,'cb_steel',48,8)
 # Bearing caps, machined rings and hex fasteners on each cheek.
 for sign in (-1,1):
  for z,r in ((62,12.5),(19,9.0)):
   axle((0,sign*18.6,z),Y,r,.8,'cb_dark',48)
   axle((0,sign*19.0,z),Y,r-.75,.8,'cb_paint',48)
   P.torus(m,(0,sign*19.45,z),Y,r-.7,.23,'cb_steel',48,8)
   axle((0,sign*19.4,z),Y,3.6,.8,'cb_steel',32)
   axle((0,sign*19.75,z),Y,1.5,.45,'cb_dark',6)
   for a in np.linspace(0,2*math.pi,6,endpoint=False):
    c=P.v(math.cos(a)*(r-2.4),sign*19.4,z+math.sin(a)*(r-2.4))
    axle(c,Y,.52,.45,'cb_steel',6)
  for x in (-17.5,17.5):
   for z in (8,35,77):
    axle((x,sign*18.7,z),Y,.85,.6,'cb_dark',20)
    axle((x,sign*19.15,z),Y,.58,.6,'cb_steel',6)
  # Equipment plate and lower caution band follow the front/back cast faces.
  box((0,sign*18.58,39),(24,.22,13),'cb_dark',.1)
  normal=Y*sign
  P.card(m,'cb_label',[(-11.6,sign*18.72,32.9),(11.6,sign*18.72,32.9),(11.6,sign*18.72,45.1),(-11.6,sign*18.72,45.1)],normal,
         uv=[(0,0),(1,0),(1,1),(0,1)])
  P.card(m,'cb_stripes',[(-18,sign*18.53,3.8),(18,sign*18.53,3.8),(18,sign*18.53,10.4),(-18,sign*18.53,10.4)],normal,
         uv=[(0,0),(1,0),(1,1),(0,1)])
 # Chain guides align with the original two hanging strands at x ±13.
 for x in (-13,13):
  for y in (-8,8):box((x,y,81),(7.0,2.0,5.0),'cb_steel',.4)
 # Swivel shaft and collar carry the forged hook below the housing.
 axle((0,0,-3),Z,4.3,12,'cb_steel',40)
 axle((0,0,-6),Z,7.2,3.5,'cb_dark',40)
 P.torus(m,(0,0,-7.7),Z,6.3,.65,'cb_steel',40,8)
 path=[(0,0,-9),(-6,0,-17),(-12,0,-28),(-13,0,-36),(-8,0,-44),(1,0,-47),(10,0,-44),(14,0,-36),(13,0,-29)]
 P.pipe(m,path,5.0,'cb_steel',sides=20,bend=5)
 axis=P.unit((-3,0,6))
 P.lathe_axis(m,(13,0,-29),axis,[(5,0),(4.6,1.7),(3.1,4.4),(1.4,6.7)],'cb_steel',32,cap='cb_steel')
 # Spring safety latch bridges the mouth; its hinge pin and spring are visible on the near side.
 d=P.unit((1,0,-1));across=np.cross(d,Y)
 P.bevel_box(m,(6,-.5,-22),(d,Y,across),(18,1.5,1.7),'cb_dark',.25)
 axle((0,-1,-16),Y,1.1,4,'cb_steel',24)
 P.torus(m,(0,-3,-16),Y,1.0,.18,'cb_steel',24,8)
 for mat,path in MATS.items():m.material_overrides[mat]=path;m.tile_overrides[mat]=32
 return m

def block(m,centre):
 from riverside_parts import place
 m.extend(place(local(),centre,0));return m

def original(m,e,n,z):
 import sewage_map as R
 m.box((e-23,n-20,z),(e+23,n+20,z+84),'yellow')
 for h in range(0,75,22):m.beam((e-23,n-21,z+h),(e+23,n-21,z+h+22),(9,2),'steel')
 points=[(e+18*math.cos(t),n,z-23+27*math.sin(t)) for t in np.linspace(-math.pi*.95,math.pi*.45,16)]
 for a,b in zip(points,points[1:]):R.tube(m,a,b,6,'steel',12)
 return m
