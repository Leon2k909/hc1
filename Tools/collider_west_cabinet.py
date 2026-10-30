"""Accepted west cabinet, keeping the existing Collider cover envelope."""
from pathlib import Path
from functools import lru_cache
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/collider/west-cabinet-trial-v1/after.obj'


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
            ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
            faces.append((paint,[positions[v] for v,t,n in ids],[uv[t] for v,t,n in ids],[normals[n] for v,t,n in ids]))
    return faces


def append(model,e=-430.,n=80.):
    origin=np.array((e,n,0.))
    for paint,points,uv,normals in mesh():
        model.polygon(paint,[p+origin for p in points],uv=uv,normals=normals)
    model.box((e-24,n-30,0),(e+24,n+30,138),None,'metal')
