"""Geometry, UV, normal-map and live-asset preservation checks for the candidate."""
from pathlib import Path
from collections import Counter
import hashlib, json, sys
import numpy as np
from PIL import Image
ROOT=Path(sys.argv[1]).resolve()
OUT=ROOT/'output/riverside/trailer-door-v1'
mesh_only='--mesh-only' in sys.argv
if not mesh_only:
    manifest=json.loads((OUT/'review.json').read_text())
    concurrent=[]
    for p, expected in manifest['protected'].items():
        actual=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
        if p.lower().endswith(('riverside_low.obj','riverside_low.vmdl')):
            assert actual==expected,p+' changed'
        elif actual!=expected:concurrent.append(p)
    # Other chats can install unrelated props into the shared pad/scene during this review.
    # Verify the rejected gate's actual triangles, not an obsolete hash of the entire pad.
    def face_keys(path):
        points=[];mat=None;keys=[]
        for line in path.read_text().splitlines():
            p=line.split()
            if not p:continue
            if p[0]=='v':points.append(tuple(round(float(v),4) for v in p[1:]))
            elif p[0]=='usemtl':mat=p[1]
            elif p[0]=='f':keys.append((mat,tuple(sorted(points[int(t.split('/')[0])-1] for t in p[1:]))))
        return Counter(keys)
    gate=face_keys(ROOT/'Assets/models/props/riverside/entrance_gate_v1/review/old_gate.obj')
    pad=face_keys(ROOT/'Assets/models/maps/riverside/riverside_pad.obj')
    assert sum(gate.values())==82 and not gate-pad,'Original gate changed'
    scene=(ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text()
    assert 'entrance_gate_v1' not in scene and 'trailer_door_v1' not in scene,'Candidate unexpectedly installed'
rows=[]
for path in sorted((ROOT/'Assets/models/props/riverside/trailer_door_v1').glob('*_lod*.obj')):
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
    assert tex.min()>=0 and tex.max()<=1,(path,tex.min(),tex.max())
    rows.append(dict(mesh=path.name,triangles=len(faces),valid_geometry=True,valid_uvs=True))
normal=np.asarray(Image.open(ROOT/'Assets/materials/riverside/trailer_door_v1/door_normal.png'),float)/127.5-1
assert np.allclose(np.linalg.norm(normal,axis=-1),1,atol=.015)
assert normal[:,:,2].min()>0
report=dict(meshes=rows,normal_map_valid=True)
if not mesh_only:
    report.update(door_lowland_files_unchanged=True,original_gate_82_faces_intact=True,candidates_not_installed=True,concurrent_shared_file_changes=concurrent)
(OUT/('installed/mesh-verification.json' if mesh_only else 'verification.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
