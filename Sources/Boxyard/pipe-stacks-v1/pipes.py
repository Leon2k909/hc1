"""Six hollow steel tubes on dunnage, with formed steel shipping bands."""
import math
import numpy as np
from scipy.spatial import ConvexHull
import map_kit as K
import riverdale_parts as P
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.UP
MATS={f'ps_{n}':f'materials/boxyard/pipe-stacks-v1/{n}.vmat' for n in ('outer','inner','rim','band')}
PLACEMENTS=((782.,-480.,90.),(640.,-816.,0.))

def local(e,n):
 import boxyard_map as B
 m=K.Model();r=4.3
 centres=[(y,z) for z,ys in ((3+r,(-2*r,0,2*r)),(3+r+2*r*math.sin(math.pi/3),(-r,r)),(3+r+4*r*math.sin(math.pi/3),(0,))) for y in ys]
 for x in (-55.,55.):P.bevel_box(m,(x,0,1.5),(X,Y,Z),(4,28,3),'rw_wood',.12)
 for y,z in centres:
  shift=(B.keyed('pipe',e,n,z,y)%9)-4.;a=-80+shift;b=80+shift
  offset=(B.keyed('surface',e,n,y,z)%1000)/997
  profile=[(a,4.08),(a+.22,4.3),(b-.22,4.3),(b,4.08),(b,3.93),(b-.18,3.86),(a+.18,3.86),(a,3.93),(a,4.08)]
  for j,((x0,r0),(x1,r1)) in enumerate(zip(profile[:-1],profile[1:])):
   mat='ps_outer' if j==1 else 'ps_inner' if j in (4,5,6) else 'ps_rim'
   slope=P.unit((r0-r1,x1-x0))
   for k in range(48):
    ds=[P.v(0,math.cos(2*math.pi*i/48),math.sin(2*math.pi*i/48)) for i in (k,k+1)]
    at=P.v(0,y,z);ps=[at+X*x0+ds[0]*r0,at+X*x0+ds[1]*r0,at+X*x1+ds[1]*r1,at+X*x1+ds[0]*r1]
    ns=[X*slope[0]+d*slope[1] for d in (ds[0],ds[1],ds[1],ds[0])]
    uv=[((x0-a)/160+offset,k/48),((x0-a)/160+offset,(k+1)/48),((x1-a)/160+offset,(k+1)/48),((x1-a)/160+offset,k/48)]
    P.card(m,mat,ps,ns[0],uv=uv,normals=ns)
  seam=P.v(0,y+math.cos(2.2)*4.3,z+math.sin(2.2)*4.3)
  P.rod(m,seam+X*(a+.25),seam+X*(b-.25),.035,'ps_rim',6)
 # Rounded shipping bands follow the convex outside of the 3-2-1 bundle.
 points=np.array([(y+math.cos(a)*4.36,z+math.sin(a)*4.36) for y,z in centres for a in np.linspace(0,2*math.pi,48,endpoint=False)])
 outline=points[ConvexHull(points).vertices]
 for x in (-49.,49.):
  for i,p in enumerate(outline):
   q=outline[(i+1)%len(outline)];d=P.unit((q[1]-p[1],p[0]-q[0]));normal=P.v(0,*d)
   a=P.v(x,p[0],p[1]);b=P.v(x,q[0],q[1]);outer=.085
   P.card(m,'ps_band',[a-X*.58+normal*outer,b-X*.58+normal*outer,b+X*.58+normal*outer,a+X*.58+normal*outer],normal)
   for sign in (-1,1):P.card(m,'ps_band',[a+X*(sign*.58),b+X*(sign*.58),b+X*(sign*.58)+normal*outer,a+X*(sign*.58)+normal*outer],X*sign)
  # Crimped buckle and rivet heads on the near side of the bundle.
  P.bevel_box(m,(x,-12.95,7.0),(X,Y,Z),(2.0,.38,1.65),'ps_band',.09)
  for dx in (-.55,.55):P.rod(m,(x+dx,-13.15,7),(x+dx,-13.32,7),.17,'ps_rim',12,caps=True)
 # Small timber chocks stop the lowest row rolling off the bearers.
 for x in (-55.,55.):
  for sign in (-1,1):
   ends=[]
   for xx in (x-1.65,x+1.65):
    tri=[P.v(xx,sign*10.3,3),P.v(xx,sign*13.6,3),P.v(xx,sign*13.6,6.1)];ends.append(tri)
    P.card(m,'rw_wood',tri,X*(-1 if xx<x else 1))
   for i in range(3):
    j=(i+1)%3;P.card(m,'rw_wood',[ends[0][i],ends[0][j],ends[1][j],ends[1][i]],P.v(0,sign,1) if i==2 else -Z if i==0 else Y*sign)
 for mat,path in MATS.items():m.material_overrides[mat]=path;m.tile_overrides[mat]=32
 return m

def stack(m,e,n,heading):
 from riverside_parts import place
 m.extend(place(local(e,n),(e,n,0),heading));return m
