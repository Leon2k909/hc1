import math
import numpy as np
import map_kit as K
import riverdale_parts as P
import orion_map as R
AXES=((1,0,0),(0,1,0),(0,0,1))
CENTRES=[(R.ROCKET[0]+sx*170,R.ROCKET[1]+sy*170,R.ROCKET_Z-10) for sx,sy in ((-1,-1),(1,-1),(1,1),(-1,1))]
def original(m,c):
 e,n,z=c;P.box(m,e-14,e+14,n-10,n+10,z,z+40,'oa_dark');return m
def build(m,c):
 c=np.array(c,float)
 def box(p,size,mat='oa_steel',b=.15):P.bevel_box(m,c+p,AXES,size,mat,b)
 # Flanged mounting plinth and folded panels, with an open front aperture.
 box((0,0,1.1),(28,20,2.2),b=.45)
 box((0,0,3.0),(26.2,18.2,1.6),'oa_dark',.3)
 box((0,8.55,21.8),(26,.7,35.5),b=.25)
 for s in (-1,1):box((s*12.65,0,21.8),(.7,17.8,35.5),b=.22)
 box((0,0,4.25),(26,18,.8),b=.2)
 box((0,0,39.45),(26,18,1.1),b=.4)
 for s in (-1,1):box((s*11.55,-8.65,21.8),(2.0,1.0,34),b=.25)
 for z in (5.8,37.8):box((0,-8.65,z),(22,1.0,2.0),b=.22)
 # Recessed gasket and separate service door, retained dark metal finish.
 box((0,-8.15,21.8),(21.0,.5,30.3),'oa_dark',.3)
 box((0,-8.49,21.8),(19.9,.45,29.3),'oa_steel',.35)
 box((0,-8.76,21.8),(18.8,.12,28.1),'oa_dark',.06)
 for zz in (12,30):
  box((-10.25,-9.0,zz),(1.0,1.2,3.0),b=.22)
  P.rod(m,c+(-10.25,-9.05,zz-1.2),c+(-10.25,-9.05,zz+1.2),.28,'oa_steel',12,True)
 # Connected pull handle, lock bezel and slotted quarter-turn head.
 for zz in (19.2,24.4):box((7.4,-9.05,zz),(1,1.0,1.0),'oa_steel',.2)
 P.pipe(m,[c+(7.4,-9.25,19.2),c+(7.4,-9.7,19.2),c+(7.4,-9.7,24.4),c+(7.4,-9.25,24.4)],.22,'oa_steel',sides=10,bend=.4)
 P.lathe_axis(m,c+(7.4,-8.88,28),(0,-1,0),[(.7,0),(.7,.2),(.5,.34)],'oa_steel',20,cap='oa_steel')
 box((7.4,-9.25,28),(.6,.08,.13),'oa_dark',.025)
 # Vent slots have dark throats with inclined weather blades and a rain hood.
 box((0,-8.88,11),(13,.12,5.0),'oa_dark',.05)
 for zz in (9.2,10.4,11.6,12.8):
  P.bevel_box(m,c+(0,-9.08,zz),((1,0,0),(0,.94,-.342),(0,.342,.94)),(12,.7,.25),'oa_steel',.08)
 box((0,-9.15,14.0),(14,1.3,.5),b=.15)
 # Side terminal cover and three capped cable glands, safely inside the footprint.
 box((13.15,0,22),(1,9,12),'oa_dark',.3)
 box((13.7,0,22),(.3,8,11),b=.12)
 for zz in (18.8,22,25.2):
  P.lathe_axis(m,c+(13.85,0,zz),(1,0,0),[(.65,0),(.65,.14),(.5,.14)],'oa_steel',6,cap='oa_steel')
 for x in (-11.5,11.5):
  for y in (-7.5,7.5):P.lathe_axis(m,c+(x,y,2.23),(0,0,1),[(.6,0),(.6,.44),(.45,.55)],'oa_steel',6,cap='oa_steel')
 for x in (-11,11):
  for y in (-7,7):P.lathe_axis(m,c+(x,y,40.01),(0,0,1),[(.27,0),(.27,.10)],'oa_dark',6,cap='oa_dark')
 return m
