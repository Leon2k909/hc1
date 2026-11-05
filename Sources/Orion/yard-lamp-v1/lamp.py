"""Oval die-cast post-light head fitted to the existing Orion yard pole."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.UP
CENTRE=(181.,166.,96.)
MATS={f'yl_{n}':f'materials/orion/yard-lamp-v1/{n}.vmat' for n in ('coat','seal','alloy')}

def local():
 m=K.Model()
 def turned(profile,mat='yl_coat',sides=48):
  for (r0,z0),(r1,z1) in zip(profile[:-1],profile[1:]):
   slope=P.unit((z1-z0,r0-r1))
   for k in range(sides):
    aa=[2*math.pi*i/sides for i in (k,k+1)]
    ds=[P.v(math.cos(a)*5,math.sin(a)*6,0) for a in aa]
    ns=[P.unit((math.cos(a)/5*slope[0],math.sin(a)/6*slope[0],slope[1])) for a in aa]
    ps=[ds[0]*r0+Z*z0,ds[1]*r0+Z*z0,ds[1]*r1+Z*z1,ds[0]*r1+Z*z1]
    normals=[ns[0],ns[1],ns[1],ns[0]];keep=[0,2,3] if r0==0 else [0,1,2] if r1==0 else [0,1,2,3]
    P.card(m,mat,[ps[i] for i in keep],ns[0],normals=[normals[i] for i in keep])
 turned([(0,-3.55),(.8,-3.55),(.94,-3.25),(1,-2.25),(1,1),(.98,2.25),(.88,2.9),(.65,3.4),(0,3.4)])
 turned([(.80,-3.67),(.88,-3.67),(.92,-3.4),(.88,-3.25),(.80,-3.25)],'yl_seal')
 # Shallow convex diffuser, preserving the original lowest emitting plane at z -4.1.
 for j,(r0,z0,r1,z1) in enumerate(((0,-4.1,.36,-4.08),(.36,-4.08,.75,-3.99),(.75,-3.99,1,-3.8))):
  for k in range(48):
   aa=[2*math.pi*i/48 for i in (k,k+1)]
   ds=[P.v(math.cos(a)*4,math.sin(a)*5,0) for a in aa]
   ps=[ds[0]*r0+Z*z0,ds[1]*r0+Z*z0,ds[1]*r1+Z*z1,ds[0]*r1+Z*z1]
   keep=[0,2,3] if r0==0 else [0,1,2,3]
   P.card(m,'oa_lamp_warm',[ps[i] for i in keep],-Z)
 # Recessed cooling ribs and inspection fasteners are part of the upper casting.
 for x in (-2,-1,0,1,2):P.bevel_box(m,(x,0,3.55),(X,Y,Z),(.18,5.4,.60),'yl_coat',.065)
 for x in (-3.3,3.3):
  for y in (-3.5,3.5):
   P.cylinder(m,(x,y),.28,2.65,3.1,'yl_alloy',6,top='yl_alloy')
   P.torus(m,(x,y,3.04),Z,.31,.035,'yl_alloy',16,5)
 # Thin guard bars sit just outside the emitting glass.
 for y in (-3.2,0,3.2):
  half=3.8*math.sqrt(1-(y/5)**2)
  P.pipe(m,[(-half-.3,y,-3.35),(-half,y,-4.13),(half,y,-4.13),(half+.3,y,-3.35)],.065,'yl_alloy',sides=8,bend=.18)
 # Rear hinge and latch hardware break up the housing's seam.
 P.rod(m,(-1.7,5.62,-.6),(1.7,5.62,-.6),.22,'yl_alloy',16,caps=True)
 P.bevel_box(m,(0,-5.78,-1.7),(X,Y,Z),(1.5,.35,.85),'yl_alloy',.1)
 for mat,path in MATS.items():m.material_overrides[mat]=path;m.tile_overrides[mat]=8
 return m

def head(m,centre=CENTRE):
 from riverside_parts import place
 m.extend(place(local(),centre,0));return m

def original(m,centre=CENTRE):
 c=np.asarray(centre,float)
 m.box(c+(-5,-6,-4),c+(5,6,4),'oa_dark')
 P.card(m,'oa_lamp_warm',[c+P.v(-4,-5,-4.1),c+P.v(4,-5,-4.1),c+P.v(4,5,-4.1),c+P.v(-4,5,-4.1)],-Z)
 return m
