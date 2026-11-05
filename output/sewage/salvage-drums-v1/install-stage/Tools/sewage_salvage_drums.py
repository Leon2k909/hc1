"""Detailed salvage overpacks, adapted to the existing Sewage cover envelope."""
from pathlib import Path
from functools import lru_cache
import math
import numpy as np
import map_kit as K
import riverdale_splice as S
MATS={f'sd_{n}':f'materials/sewage/salvage-drums-v1/{n}.vmat' for n in ('olive','oxide')}
PLACEMENTS=((-670,-680,0),(-956,-430,0),(-710,640,0),(820,-650,0),(850,500,0),(-580,830,352))

@lru_cache(maxsize=1)
def source():
 root=Path(__file__).resolve().parents[1] if Path(__file__).parent.name=='Tools' else Path(__file__).resolve().parents[3]
 _,faces=S.read_obj(root/'Sources/Sewage/salvage-drums-v1/source-drum-lod0.obj')
 points=np.array([list(map(float,p.split())) for _,corners in faces for p,uv,n in corners])
 radial=np.hypot(points[:,0],points[:,2]).max();bottom=points[:,1].min();top=points[:,1].max()
 return faces,21.3/radial,56/(top-bottom),bottom

def drum(m,centre,variant='olive',yaw=0,collision=False):
 faces,sr,sz,bottom=source();paint='sd_'+variant
 angle=math.radians(yaw);rot=np.array(((math.cos(angle),-math.sin(angle),0),(math.sin(angle),math.cos(angle),0),(0,0,1)))
 c=np.asarray(centre,float)
 for _,corners in faces:
  points=[];uvs=[];normals=[]
  for p,uv,n in corners:
   a,b,d=map(float,p.split());points.append(c+rot@np.array((-a*sr,d*sr,(b-bottom)*sz)))
   a,b,d=map(float,n.split());normal=rot@np.array((-a/sr,d/sr,b/sz));normal/=np.linalg.norm(normal);normals.append(normal)
   uvs.append(tuple(map(float,uv.split())))
  m.polygon(paint,points,uv=uvs,normals=normals)
 m.material_overrides[paint]=MATS[paint];m.tile_overrides[paint]=1
 if collision:
  old=K.Model();e,n,z=centre;old.cylinder((e,n),20,z,z+54,'rust',sides=24,surface='metal')
  m.boxes.extend(old.boxes);m.hulls.extend(old.hulls)
 return m

def emit(m,centre):
 index=PLACEMENTS.index(tuple(centre));return drum(m,centre,'oxide' if index in (1,3) else 'olive',(15,70,-20,120,-60,35)[index],True)

def original(m,e,n,z):
 import sewage_map as R
 m.cylinder((e,n),20,z,z+54,'rust',sides=24,surface='metal')
 for h in (3,17,40,51):R.torus(m,(e,n,z+h),(0,0,1),20,1.3,'steel',24)
 m.cylinder((e+8,n-5),3,z+54,z+56,'steel',sides=10)
 return m
