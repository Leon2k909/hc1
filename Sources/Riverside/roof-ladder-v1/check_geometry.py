from pathlib import Path
import numpy as np,json
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];OUT=REVIEW/'output/riverside/roof-ladder-v1';manifest=json.loads((OUT/'manifest.json').read_text())
checks=[]
for lod,expected in enumerate(manifest['triangles']):
    vertices=[];normals=[];uv=[];faces=[]
    for line in (REVIEW/f'Assets/models/maps/riverside/roof-ladder-v1/ladder_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):vertices.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):normals.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uv.append(list(map(float,line.split()[1:])))
        elif line.startswith('f '):faces.append([list(map(int,p.split('/'))) for p in line.split()[1:]])
    v=np.asarray(vertices);n=np.asarray(normals);tri=np.asarray(faces)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    assert max(abs(np.linalg.norm(n,axis=1)-1))<.00087
    for axis,size in [(0,len(v)),(1,len(uv)),(2,len(n))]:assert tri[:,:,axis].min()>=1 and tri[:,:,axis].max()<=size
    points=v[tri[:,:,0]-1];areas=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)*.5
    assert len(faces)==expected and min(areas)>1e-8
    assert np.max(abs(v[:,0]))<55 and v[:,1].min()>=0 and v[:,1].max()<243 and np.max(abs(v[:,2]))<13
    checks.append(dict(lod=lod,triangles=len(faces),minimum_triangle_area=float(min(areas)),finite=True,indices_valid=True,unit_normals=True))
(OUT/'geometry-verified.json').write_text(json.dumps(checks,indent=2),encoding='utf-8');print(json.dumps(checks,indent=2))
