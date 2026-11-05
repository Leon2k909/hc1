"""Formed grit bin, retaining Riverdale's existing finish and sign artwork."""
import math,numpy as np
import map_kit as K
import riverdale_map as R
import riverdale_yard as Y
import riverdale_parts as G
import railhead_dress_detail as D
def model():
 m=K.Model();X=np.array((1.,0,0));F=np.array((0.,1,0));Z=np.array((0.,0,1));C=np.array((-1250.,258.,0.))
 def P(x,y,z):return C+X*x+F*y+Z*z
 def face(paint,pts,hint):D._face(m,paint,pts,hint)
 def box(c,size,paint='rv_yd_bin',b=.15,axes=None):G.bevel_box(m,P(*c),axes or (X,F,Z),size,paint,bevel=b)
 def ring(hx,hy,r,z,slope=0):
  points=[]
  for cx,cy,a0 in ((hx-r,hy-r,0),(-hx+r,hy-r,math.pi/2),(-hx+r,-hy+r,math.pi),(hx-r,-hy+r,3*math.pi/2)):
   for k in range(9):
    a=a0+k*math.pi/16;x=cx+r*math.cos(a);y=cy+r*math.sin(a);points.append(P(x,y,z-slope*y))
  return points
 def loft(rings,paint,caps=True):
  if caps:face(paint,rings[0],-Z);face(paint,rings[-1],Z)
  N=len(rings[0]);normals={}
  for i in range(len(rings)-1):
   for k in range(N):
    j=(k+1)%N;a=rings[i];b=rings[i+1]
    n=K.normalise(np.cross(a[j]-a[k],b[k]-a[k]));hint=(a[k]+a[j]+b[k]+b[j])/4-C;hint[2]=0
    normals[i,k]=n if np.dot(n,hint)>0 else -n
  def normal(i,k):return K.normalise(sum((normals[q,p] for q in (i-1,i) if 0<=q<len(rings)-1 for p in ((k-1)%N,k)),np.zeros(3)))
  for i,(a,b) in enumerate(zip(rings,rings[1:])):
   for k in range(N):
    j=(k+1)%N
    D._face(m,paint,[a[k],a[j],b[j],b[k]],normals[i,k],normals=[normal(i,k),normal(i,j),normal(i+1,j),normal(i+1,k)])
 # Tapered moulded body with a rounded foot and shoulder, within the old footprint.
 loft([ring(15.8,9.8,1.7,.45),ring(16.2,10.2,1.9,.8),ring(16.4,10.4,2.,2.),ring(17.,11.,2.,23.4,.16),ring(17.,11.,2.,24.5,.16),ring(16.7,10.7,1.8,25.,.16)],'rv_yd_bin')
 # Dark seating gap beneath a deep rolled weather lip; original rearward lid slope.
 loft([ring(17.2,11.4,2.,24.85,.16),ring(17.2,11.4,2.,25.25,.16)],'rv_black')
 loft([ring(17.5,11.9,2.2,25.35,.16),ring(18.,12.4,2.5,25.8,.16),ring(18.,12.4,2.5,27.0,.16),ring(17.7,12.1,2.3,27.5,.16)],'rv_yd_bin')
 # Broad inset lid top and moulded ribs strengthen the lid without changing its silhouette.
 for x in (-11.,11.):
  axisY=(F-Z*.16);axisY=axisY/np.linalg.norm(axisY);axisZ=np.cross(X,axisY)
  box((x,0,27.6),(1.15,18.,.35),b=.14,axes=(X,axisY,axisZ))
 # Two rear knuckle hinges, a through pin and separate fixing feet.
 for x in (-10.5,10.5):
  box((x,-10.8,25.5),(3.7,.45,3.),'rv_yd_bin',.12)
  for dx in (-1.1,0,1.1):
   G.lathe_axis(m,P(x+dx-.45,-11.5,28.9),X,[(0,0),(.55,0),(.55,.9),(0,.9)],'rv_zinc',sides=24)
  G.lathe_axis(m,P(x-1.9,-11.5,28.9),X,[(0,0),(.19,0),(.19,3.8),(0,3.8)],'rv_zinc',sides=16)
 # Recessed handle pocket on the front, with a real void beneath its grip.
 box((0,11.02,22.35),(8.8,.22,2.6),'rv_black',.5)
 for x in (-3.6,3.6):box((x,11.6,22.55),(.65,1.1,1.6),'rv_yd_bin',.18)
 box((0,12.05,23.2),(7.6,.75,.7),'rv_yd_bin',.23)
 # Low moulded skids and unobtrusive front fasteners.
 for x in (-11.3,11.3):box((x,0,.4),(3.,16.,.8),'rv_black',.25)
 for x in (-3.6,3.6):
  G.lathe_axis(m,P(x,12.48,23.15),F,[(0,0),(.12,0),(.12,.04),(0,.04)],'rv_zinc',sides=16)
 Y.printed(m,'sand',P(0,11.05,14.),(0,1),7.5)
 R.configure(m)
 # Object-space UVs keep contact dirt at the foot and the lid's wear on its top.
 for paint,faces in list(m.polygons.items()):
  if paint!='rv_yd_bin':continue
  for i,(points,n) in enumerate(faces):
   local=[p-C for p in points];is_lid=abs(n[2])>.65 and sum(p[2] for p in local)/len(local)>25
   alias='sb_lid' if is_lid else 'sb_body'
   if is_lid:uv=[(p[0]/36+.5,p[1]/25+.5) for p in local]
   else:uv=[((p[0] if abs(n[1])>=abs(n[0]) else p[1])/36+.5,p[2]/32) for p in local]
   m.polygon(alias,points,n,uv=uv,normals=m.polygon_normals.get((paint,i)))
  del m.polygons[paint]
 for alias in ('sb_body','sb_lid'):
  m.material_overrides[alias]='models/maps/riverdale/sand-bin-v2/'+alias+'.vmat';m.tile_overrides[alias]=36
 return m
