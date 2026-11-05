"""Read the original doorway fixture placement from its deterministic house generator."""
from pathlib import Path
import json,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_map as B
OUT=Path(tempfile.gettempdir())/'belltower-wall-lantern-v2';OUT.mkdir(parents=True,exist_ok=True)
original=B.wall_lantern;found=[]
def record(model,wall,r,z_top,*args,**kwargs):
    fixture=K.Model();accepted=original(fixture,wall,r,z_top,*args,**kwargs)
    if accepted:
        d,sign,out=B.wall_out(wall)
        found.append(dict(axis=wall.axis,run=wall.run,across=wall.across,z=wall.z,outward=wall.outward,r=r,z_top=z_top,reach=kwargs.get('reach',15.),scale=kwargs.get('scale',.8),anchor=wall.point(r,d,z_top).tolist(),yaw=float(np.degrees(np.arctan2(out[1],out[0])))))
    return accepted
B.wall_lantern=record
house=B.HOUSES[9];e0,e1,n0,n1,eave,render,faces,ridge,extras=house
B.solid_house(K.Model(),e0,e1,n0,n1,eave,render,faces,ridge,np.random.default_rng(2024),B.blocks(),plaques=extras.get('plaques',()))
(OUT/'placements.json').write_text(json.dumps(found,indent=2)+'\n')
print(json.dumps(found,indent=2))
