"""Accepted equipment case at the reviewed Collider placement, 2026-10-29."""
from functools import lru_cache
from pathlib import Path
import numpy as np
import boxyard_map as B

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/props/collider/equipment-case-trial-v1/after.obj'
MATERIAL_DIR='materials/collider/equipment-case-trial-v1'
UP=np.array((0.,0.,1.))


@lru_cache(maxsize=1)
def mesh():
    vertices=[];uvs=[];normals=[];paint='';faces=[]
    for line in (ROOT/'Assets'/RESOURCE).read_text(encoding='utf-8').splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uvs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]]
            faces.append((paint,[vertices[v] for v,t,n in ids],[uvs[t] for v,t,n in ids],[normals[n] for v,t,n in ids]))
    return faces


def append(model,e,n,z,w,d,h,heading):
    assert (w,d,h)==(100,56,65), 'The approved case keeps its reviewed dimensions'
    f=B.Frame(e,n,heading,z)
    for paint,points,uv,normals in mesh():
        model.polygon(paint,[f.p(*p) for p in points],uv=uv,
            normals=[f.x*q[0]+f.y*q[1]+UP*q[2] for q in normals])
        model.material_overrides[paint]=f'{MATERIAL_DIR}/{paint}.vmat'
    f.box(model,-w/2,w/2,-d/2,d/2,3,h,None,surface='plastic')
