import numpy as np
import math
import map_kit as K
import riverdale_parts as P
import orion_map as R
Z=R.ROCKET_Z-10+46
CENTRES=[(R.ROCKET[0]+sx*170,R.ROCKET[1]+sy*170,Z) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
def original(m,c):
 e,n,z=c;P.box(m,e-3.5,e+3.5,n-3.5,n+3.5,z-3.5,z+3.5,'oa_lamp_warm');return m
def build(m,c):
 c=np.array(c,float)
 # Flanged cast base reaches the unchanged equipment-box top, six inches below the old lamp centre.
 P.lathe_axis(m,c,(0,0,1),[(3.3,-6),(3.5,-5.8),(3.5,-5.2),(3.2,-5),(2.7,-5),(2.7,-3.7),(2.5,-3.25)],'oa_steel',48)
 P.lathe_axis(m,c,(0,0,1),[(2.55,-3.3),(2.75,-3),(2.75,-2.65),(2.45,-2.5)],'oa_dark',48)
 # Rounded luminous diffuser, using exactly the original warm lamp material.
 P.lathe_axis(m,c,(0,0,1),[(2.15,-2.6),(2.35,-2.3),(2.4,-1.7),(2.4,1.7),(2.3,2.3),(1.9,2.7),(.7,2.95)],'oa_lamp_warm',48,cap='oa_lamp_warm')
 P.lathe_axis(m,c,(0,0,1),[(2.6,2.7),(2.95,2.95),(2.95,3.2),(2.5,3.48),(.6,3.48)],'oa_steel',48,cap='oa_steel')
 for zz,r in ((-2.6,3),(0,3.12),(2.55,2.95)):
  P.torus(m,c+(0,0,zz),(0,0,1),r,.12,'oa_dark',seg=48,sides=6)
 for k in range(8):
  a=k*math.pi/4;pts=[c+(r*math.cos(a),r*math.sin(a),zz) for r,zz in ((2.7,-3),(3,-2.6),(3.12,-1.8),(3.12,1.7),(2.95,2.55),(2.6,2.9))]
  for p,q in zip(pts,pts[1:]):P.rod(m,p,q,.14,'oa_dark',8)
 for k in range(4):
  a=math.pi/4+k*math.pi/2;p=c+(2.93*math.cos(a),2.93*math.sin(a),-5.1)
  P.lathe_axis(m,p,(0,0,1),[(.29,0),(.29,.24),(.22,.3)],'oa_steel',6,cap='oa_steel')
 # Service screws and moulded ribbing on the base.
 for zz in (-4.7,-4.3,-3.9):P.torus(m,c+(0,0,zz),(0,0,1),2.72,.07,'oa_steel',seg=40,sides=5)
 return m
