"""Stage a slight entrance shoulder rise without rebuilding Riverside's existing meshes."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import map_kit as K

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'output/riverside/entrance-relief-v1'
RESOURCE = 'models/maps/riverside/entrance-relief-v1'
BOUNDS = (-680., -420., -1080., -800.)
BASE = 96.0
RISE = 2.5


def height(e,n):
    u=(e-BOUNDS[0])/(BOUNDS[1]-BOUNDS[0])
    v=(n-BOUNDS[2])/(BOUNDS[3]-BOUNDS[2])
    if not (0<u<1 and 0<v<1):
        return 0.0
    return RISE*math.sin(math.pi*u)**2*math.sin(math.pi*v)**2


def normal(e,n):
    d=.1
    return (-(height(e+d,n)-height(e-d,n))/(2*d),
            -(height(e,n+d)-height(e,n-d))/(2*d),1)


def main():
    model=K.Model()
    model.uv_source_name='riverside_ground'
    model.tile_overrides['rs_mud']=768.0
    xs=np.linspace(BOUNDS[0],BOUNDS[1],23)
    ys=np.linspace(BOUNDS[2],BOUNDS[3],13)
    max_slope=0.0
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            pts=[np.array((e,n,BASE+height(e,n)+.015)) for e,n in
                 ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
            for ids in ((0,1,2),(0,2,3)):
                top=[pts[i] for i in ids]
                face=np.cross(top[1]-top[0],top[2]-top[0])
                assert face[2]>0
                max_slope=max(max_slope,math.degrees(math.atan2(np.linalg.norm(face[:2]),face[2])))
                uv=[K.face_uv(K.to_world(p),np.array((0.,0.,1.)),'rs_mud',
                              K.uv_offset('riverside_ground'),768.0) for p in top]
                model.polygon('rs_mud',top,normals=[normal(p[0],p[1]) for p in top],uv=uv)
    assert max_slope<5
    assert BOUNDS[1] < -360-16, 'Keep clear of the westernmost player spawn'
    assert BOUNDS[3] < -700-32, 'Keep clear of the office footprint'
    assert all(height(e,n)==0 for e in xs for n in (BOUNDS[2],BOUNDS[3]))
    assert all(height(e,n)==0 for e in (BOUNDS[0],BOUNDS[1]) for n in ys)
    dest=OUT/'stage'/RESOURCE
    dest.mkdir(parents=True,exist_ok=True)
    K.write_obj(dest/'entrance_soil_relief.obj',model,'entrance_soil_relief')
    # Reuse the native-compiled single-mesh collider schema from the preceding lawn trial.
    template=ROOT/'Assets/models/maps/cerroblanco/lawn-relief-v1/garden_lawn_relief.vmdl'
    text=template.read_text().replace('models/maps/cerroblanco/lawn-relief-v1',RESOURCE)
    text=text.replace('garden_lawn_relief','entrance_soil_relief')
    text=text.replace('from = "lawn.vmat"','from = "rs_mud.vmat"')
    text=text.replace('materials/buildings/lawn.vmat','materials/riverside/rs_mud.vmat')
    text=text.replace('surface_prop = "grass"','surface_prop = "dirt"')
    (dest/'entrance_soil_relief.vmdl').write_text(text)
    receipt={'map':'Riverside','state':'staged for reversible editor trial','plan_bounds':BOUNDS,
             'base_height_inches':BASE,'maximum_rise_cm':RISE*2.54,'max_slope_degrees':max_slope,
             'triangles':model.triangle_count(),'collision_meshes':1,
             'checks':['all four edges stay level','no paving or stair footprint modified','maximum slope below 5 degrees'],
             'schema_source_sha256':hashlib.sha256(template.read_bytes()).hexdigest()}
    (OUT/'geometry-checks.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
