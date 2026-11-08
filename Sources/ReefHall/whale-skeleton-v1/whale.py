"""Museum-inspired baleen-whale display; all bones retain Reef Hall's original material.
An authored game sculpture, not a scientific reconstruction or copy of a museum scan.
"""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
import reefhall_map as R
CENTRE=(-2300.,0.);Z=475.;LENGTH=640.;BONE='rh_bone'
def unit(v):return np.asarray(v,float)/max(np.linalg.norm(v),1e-10)
def curve(points,steps=8):
 p=[np.asarray(v,float) for v in points];out=[]
 for i in range(len(p)-1):
  a,b,c,d=p[max(i-1,0)],p[i],p[i+1],p[min(i+2,len(p)-1)]
  for j in range(steps):
   t=j/steps;out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
 return out+[p[-1]]
def bone(m,points,radii,flat=1.,steps=6,sides=10):
 path=curve(points,steps);radii=np.interp(np.linspace(0,len(radii)-1,len(path)),np.arange(len(radii)),radii)
 rings=[];normals=[];tangents=[];previous=None
 for i,p in enumerate(path):
  t=unit(path[min(i+1,len(path)-1)]-path[max(i-1,0)])
  u=P.perp(t)[0] if previous is None else unit(previous-t*np.dot(previous,t))
  w=unit(np.cross(t,u));previous=u;tangents.append(t)
  dirs=[u*math.cos(k*2*math.pi/sides)+w*math.sin(k*2*math.pi/sides)*flat for k in range(sides)]
  rings.append([p+d*radii[i] for d in dirs]);normals.append([unit(u*math.cos(k*2*math.pi/sides)+w*math.sin(k*2*math.pi/sides)/flat) for k in range(sides)])
 for i in range(len(path)-1):
  for k in range(sides):
   j=(k+1)%sides;ns=[normals[i][k],normals[i][j],normals[i+1][j],normals[i+1][k]]
   P.card(m,BONE,[rings[i][k],rings[i][j],rings[i+1][j],rings[i+1][k]],ns[0]+ns[1],normals=ns)
 P.card(m,BONE,rings[0],-tangents[0]);P.card(m,BONE,rings[-1],tangents[-1])
def ellipsoid(m,c,scale,sides=14,rings=8):
 c=np.asarray(c,float);s=np.asarray(scale,float)
 ring=[]
 for j in range(1,rings):
  a=-math.pi/2+j*math.pi/rings
  ring.append([c+s*np.array((math.cos(a)*math.cos(k*2*math.pi/sides),math.cos(a)*math.sin(k*2*math.pi/sides),math.sin(a))) for k in range(sides)])
 def face(ps):
  ns=[unit((p-c)/(s*s)) for p in ps];P.card(m,BONE,ps,np.mean(ps,axis=0)-c,normals=ns)
 for k in range(sides):
  j=(k+1)%sides;face([c-(0,0,s[2]),ring[0][j],ring[0][k]]);face([ring[-1][k],ring[-1][j],c+(0,0,s[2])])
 for a,b in zip(ring,ring[1:]):
  for k in range(sides):j=(k+1)%sides;face([a[k],a[j],b[j],b[k]])
def original(m,centre=CENTRE,z=Z,length=LENGTH):R.whale(m,centre,z,length);return m
def build(m,centre=CENTRE,z=Z,length=LENGTH):
 c=np.asarray(centre,float);scale=length/640
 def spine(t):return np.array((c[0],c[1]+t*length/2,z+24*math.sin(t*2.2+.4)-10*t))
 # Separate centra, paired arches and tapered processes along the gently curved spine.
 count=36
 for k in range(count):
  t=-1+1.72*k/(count-1);p=spine(t);belly=math.sin((t+1)/1.86*math.pi)**.7
  r=(3.8+7.5*belly)*scale
  ellipsoid(m,p,(r,r*.54,r*.82),14,7)
  if k>2:
   bone(m,[p+(-r*.72,0,r*.15),p+(-r*.65,0,r*1.1),p+(0,0,r*1.35),p+(r*.65,0,r*1.1),p+(r*.72,0,r*.15)],(r*.22,r*.22,r*.25,r*.22,r*.22),steps=3,sides=8)
   bone(m,[p+(0,0,r),p+(0,-r*.15,r*2),p+(0,-r*.4,r*2.8)],(r*.3,r*.22,r*.07),flat=.6,steps=3,sides=8)
  for side in (-1,1):
   bone(m,[p+(side*r*.7,0,0),p+(side*r*1.5,-r*.18,-r*.1),p+(side*r*2,-r*.35,0)],(r*.32,r*.2,r*.07),flat=.6,steps=3,sides=8)
 # Broad rib basket with continuously curved, individually tapered ribs.
 for k in range(12):
  p=spine(.62-k*.075);reach=(70-abs(k-4)*4.5)*scale
  for side in (-1,1):
   pts=[p+(side*7,0,0),p+(side*reach*.53,-2,-7),p+(side*reach*.95,-6,-reach*.45),p+(side*reach*.85,-10,-reach*.9),p+(side*reach*.52,-12,-reach*1.08)]
   bone(m,pts,(3.5,3.0,2.7,2.25,1.35),flat=.72,steps=6,sides=10)
 # Compact cervical series bridges the thorax to the cranium.
 for t in np.linspace(.735,.765,3):
  p=spine(t)
  ellipsoid(m,p,(8.0,2.2,7.0),14,7)
  bone(m,[p+(-5,0,3),p+(-4,0,10),p+(4,0,10),p+(5,0,3)],(1.7,1.6,1.6,1.7),steps=3,sides=8)
 # Open skull: rear cranium, temporal arches and long separate rostral bones.
 head=spine(.74)+(0,length*.025,0)
 hs=np.array((1.,1.4,1.))
 ellipsoid(m,head+hs*(0,-2,7),(28,28,17),18,10)
 ellipsoid(m,head+hs*(0,18,12),(23,26,12),18,8)
 bone(m,[head+hs*(0,25,15),head+hs*(0,62,9),head+hs*(0,109,2),head+hs*(0,155,-4)],(9,6,3,1.0),flat=.4,steps=8,sides=12)
 for side in (-1,1):
  bone(m,[head+hs*(side*20,-17,4),head+hs*(side*35,-1,9),head+hs*(side*32,25,4),head+hs*(side*21,49,0)],(5,3.8,3.8,2.5),flat=.8,steps=6,sides=10)
  bone(m,[head+hs*(side*27,19,2),head+hs*(side*24,63,-1),head+hs*(side*12,116,-4),head+hs*(side*1.5,155,-5)],(5,4,2.5,1.0),flat=.6,steps=8,sides=12)
  # Long bowed lower mandible, with a substantial rear articulation and tapered tip.
  bone(m,[head+hs*(side*27,-16,-8),head+hs*(side*43,39,-22),head+hs*(side*34,106,-29),head+hs*(side*3,168,-20)],(7.3,5.7,4.5,2.4),flat=.8,steps=10,sides=12)
  ellipsoid(m,head+hs*(side*27,-16,-8),(8,10,7),12,7)
 # Fan-shaped scapula, paired forearm bones and separated phalange chains.
 for side in (-1,1):
  p=spine(.45)
  a=p+(side*23,-20,-8);b=p+(side*30,29,-10);d=p+(side*44,-1,-37)
  for offset in (-1.2,1.2):P.card(m,BONE,[a+(0,0,offset),b+(0,0,offset),d+(0,0,offset)],(0,0,offset))
  for x,y in ((a,b),(b,d),(d,a)):bone(m,[x,y],(2.5,2.5),steps=1,sides=8)
  bone(m,[p+(side*11,0,-2),d],(4.5,5),steps=3,sides=10)
  elbow=p+(side*65,-13,-50);wrist=p+(side*91,-27,-58)
  bone(m,[d,elbow],(6,5.2),steps=4,sides=12)
  for off in (-4,4):bone(m,[elbow+(0,off,0),wrist+(0,off*.8,0)],(3,2.4),steps=4,sides=10)
  ellipsoid(m,wrist,(7,9,4),12,6)
  for digit in range(4):
   q=wrist+(side*3,(digit-1.5)*5,0);count=4+int(digit in (1,2))
   for j in range(count):
    end=q+(side*(8-j*.7),(digit-1.5)*1.9,-.6)
    r=2.15*(1-j/(count+1))
    bone(m,[q,end],(r*.86,r),flat=.7,steps=1,sides=8);ellipsoid(m,end,(r,r*.95,r*.72),10,5);q=end+(side*.65,0,0)
 # Small ventral chevrons on the tapering tail; no solid soft-tissue fluke slab.
 for t in np.linspace(-.92,-.38,9):
  p=spine(t);r=(2.5+(t+.92)*5)
  bone(m,[p+(-r,0,-2),p+(0,-2,-r*2.8),p+(r,0,-2)],(1.2,1.7,1.2),steps=3,sides=8)
 R.configure(m);return m
