"""Adapt the approved Spillway stringer pallet to Boxyard's existing stack envelope."""
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_splice as S
import railhead_props as RP
CENTRE=(-632.,-589.);LAYERS=3
MATERIAL='models/maps/spillway/pallet_v2/pallet.vmat'
SOURCE=K.ROOT/'Assets/models/maps/spillway/pallet_v2/pallet_lod0.obj'
def original(m,e=CENTRE[0],n=CENTRE[1],z0=0,layers=LAYERS):
 RP.pallet_stack(m,e,n,z0=z0,layers=layers,along='e');return m
def build(m,e=CENTRE[0],n=CENTRE[1],z0=0,layers=LAYERS):
 faces=S.read_obj(SOURCE)[1]
 pts=np.array([list(map(float,c[0].split())) for mat,cs in faces for c in cs]);lo,hi=pts.min(0),pts.max(0)
 scale=np.array((31.5/(hi[0]-lo[0]),5.67/(hi[1]-lo[1]),47.24/(hi[2]-lo[2])))
 centre=(lo+hi)/2;centre[1]=lo[1]
 for layer in range(layers):
  turn=-1 if layer%2 else 1
  for mat,cs in faces:
   points=[];normals=[];uv=[]
   for p,t,normal in cs:
    a,b,c=(np.array(list(map(float,p.split())))-centre)*scale
    points.append((e+turn*c,n+turn*a,z0+layer*5.67+b))
    na,nb,nc=np.array(list(map(float,normal.split())))/scale
    v=np.array((turn*nc,turn*na,nb));v/=np.linalg.norm(v);normals.append(v);uv.append(tuple(map(float,t.split())))
   m.polygon('bxps_wood',points,uv=uv,normals=normals)
 m.material_overrides['bxps_wood']=MATERIAL;m.tile_overrides['bxps_wood']=48.;return m
