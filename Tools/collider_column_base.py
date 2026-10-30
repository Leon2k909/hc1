"""The exact column-base mesh approved in the offline before/after review."""
from pathlib import Path
from functools import lru_cache
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/collider/column-base-trial-v1/after.obj'
MATERIAL_DIR='materials/collider/column-base-trial-v1'
ORIGIN=np.array((-960.,-500.,0.))
ROTATION=np.eye(3)


@lru_cache(maxsize=1)
def mesh():
    positions=[];uv=[];normals=[];paint='';faces=[]
    for line in (ROOT/'Assets'/RESOURCE).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);positions.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]]
            faces.append((paint,[positions[v] for v,t,n in ids],[uv[t] for v,t,n in ids],[normals[n] for v,t,n in ids]))
    return faces


def append(model):
    for paint,points,uv,normals in mesh():
        model.polygon(paint,[ORIGIN+p for p in points],uv=uv,normals=normals)
