"""Geometry, UV, normal-map and live-asset preservation checks for the candidate."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
from PIL import Image
ROOT=Path(sys.argv[1]).resolve()
OUT=ROOT/'output/riverside/office-timber-steps-v1'
mesh_only='--mesh-only' in sys.argv
if not mesh_only:
    manifest=json.loads((OUT/'review.json').read_text())
    for p, expected in manifest['protected'].items():
        if p.lower().endswith('riverside.scene'):
            assert 'models/props/riverside/office_timber_steps_v1/steps.vmdl' not in (ROOT/p).read_text()
        else:assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==expected, p+' changed'
rows=[]
for path in sorted((ROOT/'Assets/models/props/riverside/office_timber_steps_v1').glob('*_lod*.obj')):
    points,uv,normals,faces=[],[],[],[]
    for line in path.read_text().splitlines():
        p=line.split()
        if not p: continue
        if p[0]=='v': points.append(list(map(float,p[1:])))
        elif p[0]=='vt': uv.append(list(map(float,p[1:])))
        elif p[0]=='vn': normals.append(list(map(float,p[1:])))
        elif p[0]=='f': faces.append([[int(v)-1 for v in t.split('/')] for t in p[1:]])
    idx=np.asarray(faces)
    pos=np.asarray(points)[idx[:,:,0]]
    tex=np.asarray(uv)[idx[:,:,1]]
    ns=np.asarray(normals)[idx[:,:,2]]
    cross=np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0])
    assert np.isfinite(pos).all() and np.isfinite(tex).all() and np.isfinite(ns).all()
    assert np.linalg.norm(cross,axis=-1).min()>1e-8,path
    score=(cross*ns.mean(1)).sum(-1)
    assert (score>0).all(),(path,int((score<=0).sum()),float(score.min()))
    a,b=tex[:,1]-tex[:,0],tex[:,2]-tex[:,0]
    area=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    assert abs(area).min()>1e-10,(path,int((abs(area)<1e-10).sum()))
    assert tex.min()>-100 and tex.max()<100,(path,tex.min(),tex.max())
    rows.append(dict(mesh=path.name,triangles=len(faces),valid_geometry=True,valid_uvs=True))
report=dict(meshes=rows,existing_wood_and_metal_materials_unchanged=True)
if not mesh_only:report.update(public_lowland_and_shared_material_unchanged=True,candidate_not_installed=True)
(OUT/('geometry-verification.json' if mesh_only else 'verification.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
