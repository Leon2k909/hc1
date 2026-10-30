"""The exact operator chair accepted in the offline before/after review."""
from pathlib import Path
from functools import lru_cache
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/collider/chair-trial-v1/after.obj'
MATERIAL_DIR='materials/collider/chair-trial-v1'
PAINTS=('op_fabric','op_shell','op_paint','op_alloy')
TILES=dict(op_fabric=6.,op_shell=16.,op_paint=24.,op_alloy=12.)
ORIGIN=np.array((1723.,-55.,256.))
ROTATION=np.array(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)))


@lru_cache(maxsize=1)
def mesh():
    positions=[];uv=[];normals=[];faces=[];paint=''
    for line in (ROOT/'Assets'/RESOURCE).read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);positions.append(ROTATION@np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(ROTATION@np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            faces.append((paint,[positions[v] for v,t,n in ids],[uv[t] for v,t,n in ids],[normals[n] for v,t,n in ids]))
    return faces


def append(model):
    # The existing control-desk generator retains the original player clip.
    for paint,points,uv,normals in mesh():
        model.polygon(paint,[ORIGIN+p for p in points],uv=uv,normals=normals)
