"""Approved cabinet render geometry and matching open-underside collision."""
from functools import lru_cache
from pathlib import Path
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/collider/tool-cabinet-trial-v1/after.obj'
MATERIAL_DIR='materials/collider/tool-cabinet-trial-v1'
ORIGIN=np.array((-650.,160.,0.))
@lru_cache(maxsize=1)
def mesh():
    positions=[];uv=[];normals=[];faces=[];paint=''
    for line in (ROOT/'Assets'/RESOURCE).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);positions.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            faces.append((paint,[positions[v] for v,t,n in ids],[uv[t] for v,t,n in ids],[normals[n] for v,t,n in ids]))
    return faces
def append(model):
    for paint,points,uv,normals in mesh():model.polygon(paint,[ORIGIN+p for p in points],uv=uv,normals=normals)
    shapes=json.loads((ROOT/'Sources/Collider/tool-cabinet-trial-v1/accepted-physics.json').read_text())
    for s in shapes:
        if s['kind']=='hull':model.hull([ORIGIN+np.asarray(p) for p in s['points']],s['surface'])
        elif s['kind']=='box':model.collision_box(ORIGIN+np.asarray(s['lo']),ORIGIN+np.asarray(s['hi']),s['surface'])
        else:model.oriented_box(ORIGIN+np.asarray(s['centre']),s['axes'],s['size'],None,surface=s['surface'])
