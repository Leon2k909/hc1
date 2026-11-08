from pathlib import Path
import numpy as np,json,re
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/veridant/stair-geometry-fix'
vs=[];ns=[];count=0
for l in (ROOT/'Assets/models/maps/veridant/reception-stair-closure-v1/closure.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('vn '):ns.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('f '):
        ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(x[0])-1] for x in ids]
        normal=np.cross(b-a,c-a);assert np.linalg.norm(normal)>1e-6
        assert np.dot(normal,ns[int(ids[0][2])-1])>0
        count+=1
assert np.isfinite(vs).all() and np.isfinite(ns).all()
assert all(abs(np.linalg.norm(n)-1)<1e-5 for n in ns)
before=(OUT/'before/parent.vmdl').read_text();after=(ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl').read_text()
assert before.split('PhysicsShapeList',1)[1]==after.split('PhysicsShapeList',1)[1]
pattern=r'\{\s*_class = "RenderMeshFile".*?\n\s*\},'
old=re.findall(pattern,before,re.S);new=re.findall(pattern,after,re.S)
assert all(n in new for n in old) and len(new)==len(old)+1
report={'added_triangles':count,'finite_vertices':True,'nondegenerate_outward_faces':True,'unit_normals':True,'physics_byte_equivalent':True,'all_previous_mesh_imports_retained':True}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
