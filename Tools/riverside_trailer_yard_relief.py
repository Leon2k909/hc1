"""Small yard-edge rise, preserving Riverside's existing mud and clipped grass patches."""
from pathlib import Path
import json
import math
import numpy as np
import map_kit as K

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'output/riverside/trailer-yard-relief-v1'
RESOURCE='models/maps/riverside/trailer-yard-relief-v1'
BOUNDS=(-1130.,-900.,1690.,1870.)
RISE=1.5


def height(e,n):
    u=(e-BOUNDS[0])/(BOUNDS[1]-BOUNDS[0]);v=(n-BOUNDS[2])/(BOUNDS[3]-BOUNDS[2])
    return RISE*math.sin(math.pi*u)**2*math.sin(math.pi*v)**2 if 0<u<1 and 0<v<1 else 0.


def normal(e,n):
    d=.1
    return (-(height(e+d,n)-height(e-d,n))/(2*d),-(height(e,n+d)-height(e,n-d))/(2*d),1)


def clip(poly,axis,value,greater):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ai=a[axis]>=value if greater else a[axis]<=value
        bi=b[axis]>=value if greater else b[axis]<=value
        if ai: result.append(a)
        if ai!=bi:
            result.append(a+(b-a)*((value-a[axis])/(b[axis]-a[axis])))
    return result


def main():
    model=K.Model();model.tile_overrides.update({'rs_mud':768.,'rs_yard':512.})
    max_slope=0.
    def add(paint,pts,uv):
        nonlocal max_slope
        lifted=[np.array((p[0],p[1],p[2]+height(p[0],p[1])+.015)) for p in pts]
        face=np.cross(lifted[1]-lifted[0],lifted[2]-lifted[0])
        if np.linalg.norm(face)<1e-9: return
        assert face[2]>0
        max_slope=max(max_slope,math.degrees(math.atan2(np.linalg.norm(face[:2]),face[2])))
        model.polygon(paint,lifted,normals=[normal(p[0],p[1]) for p in lifted],uv=uv)
    xs=np.linspace(BOUNDS[0],BOUNDS[1],24);ys=np.linspace(BOUNDS[2],BOUNDS[3],19)
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            pts=[np.array((e,n,0.)) for e,n in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
            for ids in ((0,1,2),(0,2,3)):
                tri=[pts[i] for i in ids]
                uv=[K.face_uv(K.to_world(p),np.array((0.,0.,1.)),'rs_mud',K.uv_offset('riverside_ground'),768.) for p in tri]
                add('rs_mud',tri,uv)
    vertices=[];texcoords=[];paint=None;clipped_count=0;original_area=0.;new_area=0.
    for line in (ROOT/'Assets/models/maps/riverside/riverside_patches.obj').read_text().splitlines():
        p=line.split()
        if not p: continue
        if p[0]=='v':
            x,y,z=map(float,p[1:4]);vertices.append(np.array((-x,z,y)))
        elif p[0]=='vt': texcoords.append(np.array(tuple(map(float,p[1:3]))))
        elif p[0]=='usemtl': paint=p[1]
        elif p[0]=='f' and paint=='rs_yard':
            ids=[tuple(int(i)-1 for i in t.split('/')) for t in p[1:]]
            poly=[np.concatenate((vertices[i[0]],texcoords[i[1]])) for i in ids]
            for axis,value,greater in ((0,BOUNDS[0],True),(0,BOUNDS[1],False),(1,BOUNDS[2],True),(1,BOUNDS[3],False)):
                poly=clip(poly,axis,value,greater)
                if not poly: break
            if len(poly)<3: continue
            clipped_count+=1
            for k in range(1,len(poly)-1):
                a,b,c=poly[0],poly[k],poly[k+1]
                area=np.cross(b[:3]-a[:3],c[:3]-a[:3])[2]/2
                if area<1e-8: continue
                original_area+=area
                def sample(i,j): return a*(1-(i+j)/12)+b*(i/12)+c*(j/12)
                for i in range(12):
                    for j in range(12-i):
                        tris=[(sample(i,j),sample(i+1,j),sample(i,j+1))]
                        if i+j<11: tris.append((sample(i+1,j),sample(i+1,j+1),sample(i,j+1)))
                        for tri in tris:
                            pts=[p[:3] for p in tri]
                            new_area+=np.cross(pts[1]-pts[0],pts[2]-pts[0])[2]/2
                            add('rs_yard',pts,[p[3:] for p in tri])
    assert clipped_count>0,'Expected existing grass patches in the selected yard'
    assert abs(original_area-new_area)<.001,'Grass coverage changed'
    assert max_slope<4
    assert all(height(e,n)==0 for e in xs for n in (BOUNDS[2],BOUNDS[3]))
    assert all(height(e,n)==0 for e in (BOUNDS[0],BOUNDS[1]) for n in ys)
    # Cross lane begins at N 1900; barrel sits at E -1300, N 1700.
    assert BOUNDS[3]<1900 and BOUNDS[0]>-1300+40 and BOUNDS[2]>1650
    dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    K.write_obj(dest/'trailer_yard_relief.obj',model,'trailer_yard_relief')
    template=ROOT/'Assets/models/maps/cerroblanco/lawn-relief-v1/garden_lawn_relief.vmdl'
    text=template.read_text().replace('models/maps/cerroblanco/lawn-relief-v1',RESOURCE).replace('garden_lawn_relief','trailer_yard_relief')
    old='{ from = "lawn.vmat" to = "materials/buildings/lawn.vmat" }'
    assert old in text
    text=text.replace(old,'{ from = "rs_mud.vmat" to = "materials/riverside/rs_mud.vmat" },\n'
                      '{ from = "rs_yard.vmat" to = "materials/riverside/rs_yard.vmat" }')
    text=text.replace('surface_prop = "grass"','surface_prop = "dirt"')
    (dest/'trailer_yard_relief.vmdl').write_text(text)
    report={'maximum_rise_cm':RISE*2.54,'max_slope_degrees':max_slope,'plan_bounds':BOUNDS,
            'triangles':model.triangle_count(),'clipped_grass_faces':clipped_count,
            'original_grass_area_sq_inches':original_area,'preserved_grass_area_sq_inches':new_area,
            'collision_meshes':1,'checks':['boundary heights preserved','grass coverage and UVs retained',
                                        'barrel and cross lane clear','below 4 degrees total slope']}
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__': main()
