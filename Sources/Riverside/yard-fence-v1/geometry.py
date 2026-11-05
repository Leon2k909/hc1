"""Weathered close-range timber privacy fence; existing approved materials."""
import numpy as np
import map_kit as K,riverdale_parts as G
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1))
def make(lod):
 m=K.Model();rng=np.random.default_rng(1);slot=0
 def uv(start,axis,cross):
  nonlocal slot
  polys=m.polygons['wood'][start:];allp=np.array([p for pts,n in polys for p in pts]);lo=allp.min(axis=0);span=np.maximum(allp.max(axis=0)-lo,.01);tile=slot%6;slot+=1
  for j,(pts,n) in enumerate(polys,start):
   points=np.array(pts);a=axis if np.ptp(points[:,axis])>.01 else next(i for i in range(3) if np.ptp(points[:,i])>.01)
   b=cross if cross!=a and np.ptp(points[:,cross])>.01 else next(i for i in range(3) if i!=a and np.ptp(points[:,i])>.01)
   m.polygon_uvs[('wood',j)]=[((8+(tile%2)*1024+(p[a]-lo[a])/span[a]*1008)/2048,1-(8+(3+tile//2)*168+(p[b]-lo[b])/span[b]*152)/2048) for p in pts]
 def timber(c,size,axis=0):
  start=len(m.polygons['wood']);G.bevel_box(m,np.array(c),(X,Y,Z),size,'wood',.12 if lod<2 else 0);uv(start,axis,2 if axis!=2 else 0)
 for k,t in enumerate(np.arange(0,500,5.75)):
  if rng.random()<.06:continue
  h=60*rng.uniform(.94,1);x=t+2.8;start=len(m.polygons['wood'])
  if lod<2:
   nick=.7 if k%9==0 else 0
   profile=[(-2.7,0),(2.7,0),(2.7,h-1.3),(1.4,h),(.4,h),(.1,h-nick),(-.4,h),(-1.4,h),(-2.7,h-1.3)] if nick else [(-2.7,0),(2.7,0),(2.7,h-1.3),(1.4,h),(-1.4,h),(-2.7,h-1.3)]
   G.extrude(m,(x,-.4,0),(x,.4,0),profile,'wood',up=Z,smooth=0)
  else:G._box3(m,np.array((x,0,h/2)),(X,Y,Z),(5.4,.8,h),'wood')
  uv(start,2,0)
  if lod<2:
   for z in (14,48):
    p=np.array((x,-.425,z));G.lathe_axis(m,p,-Y,[(0,0),(.16,0),(.16,.07),(0,.07)],'steel',sides=8 if lod==0 else 6)
    if lod==0:G._box3(m,p-Y*.075,(X,Y,Z),(.15,.012,.03),'dark')
 for z in (14,48):
  for bay in range(4):timber((62.5+bay*125,1.4,z),(125,1.6,3.5))
 for x in (0,125,250,375,500):
  timber((x,2.3,31),(3.5,3.5,62),2)
  timber((x,2.3,62.1),(4.4,4.4,.8),0)
  if lod<2:
   for z in (14,48):
    for dz in (-.8,.8):G.lathe_axis(m,np.array((x,4.12,z+dz)),Y,[(0,0),(.24,0),(.24,.12),(0,.12)],'steel',sides=6)
   # Two L plates fasten each rail to its post, visible on the reverse.
   for z in (14,48):
    G.bevel_box(m,np.array((x,4.16,z)),(X,Y,Z),(5,.12,2.8),'steel',.03)
 for bay in range(4):
  a=np.array((bay*125+3,3.2,8));b=np.array((bay*125+43,3.2,38));start=len(m.polygons['wood']);m.beam(a,b,(2.2,1.4),'wood');uv(start,0,2)
 m.material_overrides={'wood':'materials/riverside/crate_v2/crate.vmat','steel':'materials/lowtide/lt_steel.vmat','dark':'materials/riverside/rs_dark.vmat'};m.tile_overrides={p:48 for p in m.polygons}
 return m
