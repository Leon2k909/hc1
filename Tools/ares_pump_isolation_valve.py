"""Approved northeast pump valve: preserve reviewed pipe ends and original physics."""
from pathlib import Path
from functools import lru_cache
import copy,json,numpy as np
import map_kit as K
@lru_cache(maxsize=1)
def patch():
    return json.loads((Path(__file__).resolve().parents[1]/'Sources/Ares/pump-isolation-valve-v1/retained-pipe.json').read_text())
def apply_pipe_gap(model):
    center=np.array(patch()['center']);result=K.Model();removed=0
    for paint,rows in model.polygons.items():
        for i,(points,normal) in enumerate(rows):
            p=np.array(points)
            selected=paint=='ar_in_alloy' and p[:,2].min()<108.64 and p[:,2].max()>75.36 and p[:,2].min()>=63.99 and p[:,2].max()<134 and np.linalg.norm(p[:,:2]-center[:2],axis=1).max()<6.02
            if selected:
                removed+=len(points)-2
                continue
            result.polygon(paint,points,normal,uv=model.polygon_uvs.get((paint,i)),normals=model.polygon_normals.get((paint,i)))
    assert removed==32,('Original selected pump pipe changed',removed)
    for face in patch()['faces']:
        result.polygon('ar_in_alloy',face['points'],uv=face['uv'],normals=face['normals'])
    model.polygons=result.polygons;model.polygon_uvs=result.polygon_uvs;model.polygon_normals=result.polygon_normals
def scene_object(ids):
    # Retain the installed node's stable IDs, pose, and shared model reference.
    return copy.deepcopy(patch()['node'])
