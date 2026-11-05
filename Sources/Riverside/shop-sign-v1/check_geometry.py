from pathlib import Path
import json,numpy as np
REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shop-sign-v1';manifest=json.loads((OUT/'manifest.json').read_text())
checks=[]
for lod,expected in enumerate(manifest['triangles']):
    vertices=[];normals=[];uv=[];faces=[]
    for line in (REVIEW/f'Assets/models/maps/riverside/shop-sign-v1/shop_sign_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):vertices.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):normals.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uv.append(list(map(float,line.split()[1:])))
        elif line.startswith('f '):faces.append([list(map(int,p.split('/'))) for p in line.split()[1:]])
    v=np.asarray(vertices);n=np.asarray(normals)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    assert max(abs(np.linalg.norm(n,axis=1)-1))<.00087
    # OBJ is Y-up: X width, Y height and Z depth.
    assert np.max(abs(v[:,0]))<=84.001 and v[:,1].min()>=0 and v[:,1].max()<86 and np.max(abs(v[:,2]))<41
    areas=[]
    for face in faces:
        assert len(face)==3
        for vi,ti,ni in face:assert 1<=vi<=len(v) and 1<=ti<=len(uv) and 1<=ni<=len(n)
        x,y,z=v[[p[0]-1 for p in face]];areas.append(float(np.linalg.norm(np.cross(y-x,z-x))*.5))
    assert len(faces)==expected and min(areas)>1e-8
    checks.append(dict(lod=lod,triangles=len(faces),minimum_triangle_area=min(areas),finite=True,indices_valid=True))
(OUT/'geometry-verified.json').write_text(json.dumps(checks,indent=2),encoding='utf-8');print(json.dumps(checks,indent=2))
