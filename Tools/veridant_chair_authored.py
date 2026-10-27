"""CC0 Dining Chair 02, with its authored mesh, UVs and PBR maps preserved.

Source: Poly Haven, James Ray Cock. See Sources/Veridant/chair-v5/SOURCE.md.
Positions are converted from metres at physical scale. The seat, rather than
the overall bounding box, anchors each existing Veridant chair placement.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np

PAINT='vr_chair_authored'
MATERIAL='materials/veridant/chair-v5/leather.vmat'
INCHES=1/.0254
SOURCE=Path(__file__).resolve().parents[1]/'Sources/Veridant/chair-v5/mesh.npz'


@lru_cache(maxsize=1)
def mesh():
    with np.load(SOURCE,allow_pickle=False) as data:
        return {name:data[name].copy() for name in data.files}


def transform(at,facing,z0=0.):
    data=mesh()
    f=np.array((facing[0],facing[1],0.),float);f/=np.linalg.norm(f)
    s=np.cross((0.,0.,1.),f)
    axes=np.array((s,-f,(0.,0.,1.)))
    positions=(data['positions']-data['anchor'])@axes*INCHES+np.array((*at,z0))
    normals=data['normals']@axes
    return positions,normals,data['uv'],data['faces']


def build_into(model,at,facing,z0=0.,paint='vr_wicker'):
    positions,normals,uv,faces=transform(at,facing,z0)
    for face in faces:
        model.polygon(PAINT,[positions[i] for i in face],
                      normals=[normals[i] for i in face],uv=[uv[i] for i in face])
    model.material_overrides[PAINT]=MATERIAL
    model.tile_overrides[PAINT]=1.
