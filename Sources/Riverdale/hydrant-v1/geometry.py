"""Detailed pillar hydrant retaining the original three-outlet silhouette."""
import numpy as np,math
import map_kit as K,riverdale_parts as G
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.))
def make(lod):
 m=K.Model();sides=(48,28,16)[lod]
 def lathe(p,axis,prof,paint='red',n=None):
  # Average profile normals only over shallow joins: curved castings stay smooth, machined steps stay sharp.
  p=np.array(p,dtype=float);axis=G.unit(axis);profile=np.array(prof,dtype=float);e1,e2=G.perp(axis);n=n or sides
  segments=np.column_stack((np.diff(profile[:,1]),-np.diff(profile[:,0])));segments/=np.maximum(np.linalg.norm(segments,axis=1,keepdims=True),1e-9)
  def slope(j,other):
   a=segments[j]
   return G.unit(a+segments[other]) if 0<=other<len(segments) and np.dot(a,segments[other])>.86 else a
  for j,((r0,t0),(r1,t1)) in enumerate(zip(profile,profile[1:])):
   if max(r0,r1)<1e-6:continue
   aa,bb=slope(j,j-1),slope(j,j+1)
   for k in range(n):
    ds=[e1*math.cos(2*math.pi*i/n)+e2*math.sin(2*math.pi*i/n) for i in (k,k+1)]
    if n<=6:
     mid=G.unit(ds[0]+ds[1]);dsnorm=[mid,mid]
    else:dsnorm=ds
    pts=[p+ds[0]*r0+axis*t0,p+ds[1]*r0+axis*t0,p+ds[1]*r1+axis*t1,p+ds[0]*r1+axis*t1]
    normals=[dsnorm[0]*aa[0]+axis*aa[1],dsnorm[1]*aa[0]+axis*aa[1],dsnorm[1]*bb[0]+axis*bb[1],dsnorm[0]*bb[0]+axis*bb[1]]
    start=len(m.polygons[paint]);G._face(m,paint,pts,normals)
    # Stable cylindrical UVs make rim wear follow each casting rather than world projection seams.
    v0=(t0-profile[0,1])/max(profile[-1,1]-profile[0,1],.01);v1=(t1-profile[0,1])/max(profile[-1,1]-profile[0,1],.01)
    uv=[(k/n,v0),((k+1)/n,v0),((k+1)/n,v1),(k/n,v1)]
    if abs(t1-t0)>1e-6:
     for q in range(start,len(m.polygons[paint])):
      points=m.polygons[paint][q][0];m.polygon_uvs[(paint,q)]=[uv[min(range(4),key=lambda i:np.linalg.norm(point-pts[i]))] for point in points]
 def bolt(p,axis=Z,r=.32):
  lathe(p,axis,[(0,0),(r*1.35,0),(r*1.35,.08),(r,.08),(r,.35),(0,.35)],'steel',6)
 # Cast base, barrel and bonnet are separate, with visible flange and gasket seams.
 lathe((0,0,0),Z,[(0,0),(5.7,0),(6,.2),(6,1.1),(5.8,1.4),(4.6,1.8),(4.4,2.4),(4.4,20.7),(4.65,21),(4.65,21.4),(0,21.4)])
 lathe((0,0,21.4),Z,[(0,0),(4.72,0),(4.72,.18),(0,.18)],'dark')
 curve=[(4.35*math.cos(a),1.1+5.2*math.sin(a)) for a in np.linspace(0,math.acos(1.3/4.35),(25,15,9)[lod])]
 lathe((0,0,21.58),Z,[(0,0),(4.85,0),(5,.15),(5,.65),(4.85,.85)]+curve+[(0,curve[-1][1])])
 lathe((0,0,27.8),Z,[(0,0),(1.45,0),(1.45,.45),(1.05,.65),(1.05,1.8),(0,1.8)],'dark',5)
 if lod<2:
  for k in range(4):
   a=math.pi/4+k*math.pi/2;bolt((4.8*math.cos(a),4.8*math.sin(a),1.42),r=.30)
  for k in range(6):
   a=k*math.pi/3;bolt((4.45*math.cos(a),4.45*math.sin(a),22.35),r=.23)
 # Machined outlet necks, captive cap rims and pentagonal operating bosses.
 for index,d in enumerate((X,-X,-Y)):
  r=2.15 if index<2 else 2.55
  lathe(d*3.7+Z*17,d,[(0,0),(r-.4,0),(r-.2,.35),(r-.2,2.2),(r+.1,2.45),(r+.1,2.75),(0,2.75)])
  lathe(d*6.45+Z*17,d,[(0,0),(r+.08,0),(r+.08,.16),(0,.16)],'dark')
  lathe(d*6.61+Z*17,d,[(0,0),(r+.18,0),(r+.28,.2),(r+.28,.65),(r+.06,.92),(r*.74,1.05),(0,1.05)],'dark')
  lathe(d*7.66+Z*17,d,[(0,0),(.72,0),(.72,.55),(.6,.7),(0,.7)],'steel',5)
  if lod<2:
   G.torus(m,d*7.2+Z*17,d,r+.26,.085,'steel',seg=28 if lod==0 else 16,sides=6)
   # Link chains tether the caps; each link alternates its plane along the hanging curve.
   side=G.unit(np.cross(Z,d));start=d*7.15+Z*(17-r-.4);end=d*4.8+side*.6+Z*19.85
   G.bevel_box(m,d*7.05+Z*(17-r-.15),(side,d,Z),(.6,.55,.6),'dark',.10)
   G.bevel_box(m,d*4.45+side*.6+Z*20,(side,d,Z),(.65,.55,.75),'red',.12)
   samples=np.linspace(0,1,257);curve=np.array([start*(1-t)+end*t-Z*(6.5*math.sin(math.pi*t)) for t in samples]);length=np.concatenate(([0.],np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))))
   count=int(math.ceil(length[-1]/(.60 if lod==0 else .65)))+1
   for k,t in enumerate(np.interp(np.linspace(0,length[-1],count),length,samples)):
    p=start*(1-t)+end*t-Z*(6.5*math.sin(math.pi*t));tangent=G.unit(end-start-Z*(6.5*math.pi*math.cos(math.pi*t)))
    normal=G.unit(np.cross(tangent,side)) if k%2 else side
    across=G.unit(np.cross(normal,tangent));rings=[];seg=12 if lod==0 else 8
    for a in np.linspace(0,2*math.pi,seg,endpoint=False):
     center=p+tangent*(.42*math.cos(a))+across*(.24*math.sin(a));outward=G.unit(tangent*(math.cos(a)/.42)+across*(math.sin(a)/.24))
     normals=[outward*math.cos(b)+normal*math.sin(b) for b in np.linspace(0,2*math.pi,4,endpoint=False)]
     rings.append(([center+n*.07 for n in normals],normals))
    for q in range(seg):
     aa,an=rings[q];bb,bn=rings[(q+1)%seg]
     for j in range(4):
      jj=(j+1)%4;G._face(m,'steel',[aa[j],aa[jj],bb[jj],bb[j]],[an[j],an[jj],bn[jj],bn[j]])
   for p in (start,end):G.torus(m,p,side,.35,.11,'dark',seg=16,sides=6)
 # Cast ribs blend the nozzle roots into the barrel without widening the original footprint.
 if lod<2:
  for d in (X,-X,-Y):
   side=G.unit(np.cross(Z,d))
   for sign in (-1,1):G.bevel_box(m,d*4.0+side*(sign*1.2)+Z*13.5,(d,side,Z),(1.2,.38,4),'red',.16)
 if lod<2:
  letters={'F':[[(0,0),(0,1),(1,1)],[(0,.55),(.8,.55)]],'I':[[(.5,0),(.5,1)],[(0,0),(1,0)],[(0,1),(1,1)]],'R':[[(0,0),(0,1),(.8,1),(1,.8),(.8,.55),(0,.55)],[(.5,.55),(1,0)]],'E':[[(1,1),(0,1),(0,0),(1,0)],[(0,.5),(.8,.5)]]}
  for index,char in enumerate('FIRE'):
   for line in letters[char]:
    points=[]
    for xx,zz in line:
     x=-1.6+index*.86+xx*.65;a=x/4.47;points.append(np.array((4.47*math.sin(a),-4.47*math.cos(a),5.6+zz*1.15)))
    G.tube(m,points,.065,'red',sides=6 if lod==0 else 4)
 m.material_overrides={'red':'materials/riverdale/hydrant_v1/cast_red.vmat','dark':'materials/riverdale/hydrant_v1/cap_iron.vmat','steel':'materials/riverdale/rv_zinc.vmat'};m.tile_overrides={p:32 for p in m.polygons}
 return m
