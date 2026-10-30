"""Exact accepted weathered valve, instanced in Collider's existing pipework."""
from pathlib import Path
from functools import lru_cache
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/collider/valve-trial-v1/after.obj'
MATERIAL_DIR='materials/collider/valve-trial-v1'
PLACEMENTS=(((-1280.,280.,770.),(1.,0.,0.)),((1280.,280.,770.),(-1.,0.,0.)))

def frame(at,facing):
    facing=np.asarray(facing,float);facing/=np.linalg.norm(facing)
    up=np.array((0.,0.,1.));assert abs(facing[2])<1e-6
    rotation=np.column_stack((np.cross(up,facing),-facing,up))
    return np.asarray(at,float)-up*13.,rotation

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

def append(model,at,facing):
    origin,rotation=frame(at,facing)
    for paint,points,uv,normals in mesh():
        model.polygon(paint,[origin+rotation@p for p in points],uv=uv,normals=[rotation@n for n in normals])
