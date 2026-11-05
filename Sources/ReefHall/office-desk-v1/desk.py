import math
import numpy as np
import map_kit as K
import riverdale_parts as P
import reefhall_map as R
CENTRE=(1960,780);YAW=180.;Z=208.
AXES=((1,0,0),(0,1,0),(0,0,1))
def original(m,centre=CENTRE,yaw=YAW,z=Z):
 fr=R.Frame(centre,(math.cos(math.radians(yaw)),math.sin(math.radians(yaw))))
 R.fbox(m,fr,-36,36,-16,16,z+28,z+30,'rh_laminate')
 for u in (-33,33):R.fbox(m,fr,u-2,u+2,-14,14,z,z+28,'rh_gunmetal')
 R.fbox(m,fr,-31,31,10,12,z+6,z+28,'rh_gunmetal')
 for u in (-13,13):
  R.fbox(m,fr,u-1.5,u+1.5,8,10,z+30,z+36,'rh_gunmetal')
  R.fbox(m,fr,u-12,u+12,8,9.5,z+36,z+51,{'default':'rh_black','back':'rh_screen_data'})
 return m
def local():
 m=K.Model()
 def box(c,size,mat,b=.15):P.bevel_box(m,c,AXES,size,mat,b)
 # A laminate worktop with a shaped edge, steel underframe and cantilever feet.
 box((0,0,29.1),(72,32,1.8),'rh_laminate',.7)
 box((0,0,28.03),(70.6,30.6,.35),'rh_gunmetal',.15)
 for s in (-1,1):
  x=s*32
  box((x,0,1.1),(4.2,28,1.5),'rh_gunmetal',.6)
  for y in (-11.8,11.8):box((x,y,.25),(3.6,3,.5),'rh_black',.2)
  box((x,8,14.4),(2.6,3.5,25.5),'rh_steel',.35)
  box((x,0,27.2),(3.5,28,1.2),'rh_gunmetal',.35)
  for y in (-9,9):
   P.lathe_axis(m,(x,y,27.83),(0,0,1),[(.42,0),(.42,.18)],'rh_steel',6,cap='rh_steel')
 box((0,9,25.5),(63,2.8,3.0),'rh_gunmetal',.3)
 # Recessed cable tray and desktop cable grommet.
 box((0,11.2,24.1),(37,6,.6),'rh_gunmetal')
 box((0,14.1,25.0),(37,.5,2.2),'rh_gunmetal')
 P.torus(m,(0,12,30.04),(0,0,1),1.4,.25,'rh_black',seg=24,sides=6)
 P.cylinder(m,(0,12),1.35,29.98,30.02,'rh_black',24,top='rh_black')
 # Twin slim displays on articulated VESA arms; reuse the existing telemetry artwork.
 box((0,11.2,30.5),(6,6,1),'rh_gunmetal',.45)
 P.rod(m,(0,11.2,31),(0,11.2,42),.72,'rh_steel',16,True)
 for x in (-13,13):
  P.pipe(m,[(0,11.2,40.8),(x*.65,12.2,40.8),(x,10,42.4)],.6,'rh_gunmetal',sides=12,bend=1)
  box((x,9.4,43.5),(4,.8,4),'rh_gunmetal',.3)
  box((x,8.6,43.5),(24,1.3,15),'rh_black',.4)
  P.card(m,'rh_screen_data',[(x-10.9,7.92,37.2),(x+10.9,7.92,37.2),(x+10.9,7.92,50.1),(x-10.9,7.92,50.1)],(0,-1,0),uv=[(0,0),(1,0),(1,1),(0,1)])
  box((x,7.9,36.7),(22,.12,.35),'rh_gunmetal',.04)
  P.pipe(m,[(x,9.7,39),(x,11,35),(0,12.2,31),(0,12,26)],.15,'rh_black',sides=6,bend=.8)
 # Keyboard, individual keys, palm rest and mouse.
 box((-2,-6,30.35),(19,7,.65),'rh_gunmetal',.3)
 for row in range(5):
  for col in range(14):box((-10.35+col*1.27,-3.4-row*1.05,30.78),(1.08,.85,.22),'rh_black',.07)
 box((-2.4,-8.3,30.79),(7.5,.8,.23),'rh_black',.07)
 box((-2,-10.7,30.3),(19,2,.5),'rh_pad_dark',.2)
 box((13,-6.5,30.1),(9,10,.15),'rh_pad_dark',.06)
 box((13,-6.5,30.8),(2.8,4.7,1.2),'rh_black',.55)
 box((13,-5.7,31.42),(.15,1.5,.15),'rh_steel',.06)
 R.configure(m);return m
def build(m,centre=CENTRE,yaw=YAW,z=Z):
 source=local();a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
 def rotate(p):return np.array((c*p[0]-s*p[1],s*p[0]+c*p[1],p[2]))
 for paint,polys in source.polygons.items():
  for i,(ps,n) in enumerate(polys):
   ns=source.polygon_normals.get((paint,i));uv=source.polygon_uvs.get((paint,i))
   m.polygon(paint,[rotate(p)+(centre[0],centre[1],z) for p in ps],rotate(n),uv=uv,normals=[rotate(n) for n in ns] if ns else None)
 m.material_overrides.update(source.material_overrides);m.tile_overrides.update(source.tile_overrides);return m
