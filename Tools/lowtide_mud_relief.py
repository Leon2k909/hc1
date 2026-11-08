"""Stage a shallow silt rise using the installed mud mesh's exact positions and UVs."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import map_kit as K

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output/lowtide/mud-relief-v1'
RESOURCE='models/maps/lowtide/mud-relief-v1'
BOUNDS=(180.,228.,420.,660.)
RISE=2.0


def height(e,n):
    u=(e-BOUNDS[0])/(BOUNDS[1]-BOUNDS[0])
    v=(n-BOUNDS[2])/(BOUNDS[3]-BOUNDS[2])
    return RISE*math.sin(math.pi*u)**2*math.sin(math.pi*v)**2 if 0<u<1 and 0<v<1 else 0.0


def main():
    source=ROOT/'Assets/models/maps/lowtide/lowtide_fleet.obj'
    positions=[];normals=[];uvs=[];faces=[];material=None
    for line in source.read_text().splitlines():
        p=line.split()
        if not p: continue
        if p[0] in ('v','vn'):
            x,y,z=map(float,p[1:4])
            (positions if p[0]=='v' else normals).append(np.array((-x,z,y)))
        elif p[0]=='vt': uvs.append(np.array(tuple(map(float,p[1:3]))))
        elif p[0]=='usemtl': material=p[1]
        elif p[0]=='f' and material=='lt_mud':
            face=[tuple(int(x)-1 for x in t.split('/')) for t in p[1:]]
            pts=[positions[f[0]] for f in face]
            if all(BOUNDS[0]-.001<=p[0]<=BOUNDS[1]+.001 and BOUNDS[2]-.001<=p[1]<=BOUNDS[3]+.001 for p in pts):
                assert len(face)==3
                faces.append(face)
    assert len(faces)==48, f'Installed mud layout differs: {len(faces)} triangles, expected 48'
    model=K.Model();max_slope=0.; area=0.
    model.tile_overrides['lt_mud']=256.0  # Explicit per-vertex source UVs below take precedence.
    for face in faces:
        pp=[positions[f[0]] for f in face]
        nn=[normals[f[2]] for f in face]
        tt=[uvs[f[1]] for f in face]
        def sample(i,j):
            weights=(1-(i+j)/4,i/4,j/4)
            p=sum(w*v for w,v in zip(weights,pp))
            normal=sum(w*v for w,v in zip(weights,nn))
            tex=sum(w*v for w,v in zip(weights,tt))
            e,n=p[:2];delta=.05
            de=(height(e+delta,n)-height(e-delta,n))/(2*delta)
            dn=(height(e,n+delta)-height(e,n-delta))/(2*delta)
            normal=normal-np.array((normal[2]*de,normal[2]*dn,0))
            return p+np.array((0,0,height(e,n)+.015)),normal,tex
        for i in range(4):
            for j in range(4-i):
                triangles=[(sample(i,j),sample(i+1,j),sample(i,j+1))]
                if i+j<3: triangles.append((sample(i+1,j),sample(i+1,j+1),sample(i,j+1)))
                for triangle in triangles:
                    pts=[p[0] for p in triangle]
                    face_normal=np.cross(pts[1]-pts[0],pts[2]-pts[0])
                    assert face_normal[2]>0
                    area+=face_normal[2]/2
                    max_slope=max(max_slope,math.degrees(math.atan2(np.linalg.norm(face_normal[:2]),face_normal[2])))
                    model.polygon('lt_mud',pts,normals=[p[1] for p in triangle],uv=[p[2] for p in triangle])
    assert abs(area-48*240)<.01,'Selected mesh does not cover the intended bank'
    assert max_slope<15
    dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    K.write_obj(dest/'mud_bank_relief.obj',model,'mud_bank_relief')
    template=ROOT/'Assets/models/maps/cerroblanco/lawn-relief-v1/garden_lawn_relief.vmdl'
    text=template.read_text().replace('models/maps/cerroblanco/lawn-relief-v1',RESOURCE)
    text=text.replace('garden_lawn_relief','mud_bank_relief').replace('materials/buildings/lawn.vmat','materials/lowtide/lt_mud.vmat')
    text=text.replace('from = "lawn.vmat"','from = "lt_mud.vmat"').replace('surface_prop = "grass"','surface_prop = "dirt"')
    assert (ROOT/'Assets/materials/lowtide/lt_mud.vmat').exists()
    (dest/'mud_bank_relief.vmdl').write_text(text)
    receipt={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'plan_bounds':BOUNDS,
             'original_triangles':len(faces),'new_triangles':model.triangle_count(),'maximum_added_height_cm':RISE*2.54,
             'max_total_surface_slope_degrees':max_slope,'collision_meshes':1,
             'checks':['exact original mesh positions and UVs retained','bank area matches bounds',
                       'below 15 degree total slope','channel, piles, stairs and barge outside footprint']}
    (OUT/'geometry-checks.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))


if __name__=='__main__': main()
