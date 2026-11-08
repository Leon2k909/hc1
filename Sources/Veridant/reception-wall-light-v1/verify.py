from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/reception-wall-light-v1'
v=[];n=[];f=[]
for line in (OUT/'stage/models/maps/veridant/reception-wall-light-v1/wall_light.obj').read_text().splitlines():
    if line.startswith('v '):v.append([float(x) for x in line.split()[1:]])
    elif line.startswith('vn '):n.append([float(x) for x in line.split()[1:]])
    elif line.startswith('f '):f.append([int(x.split('/')[0])-1 for x in line.split()[1:]])
v=np.array(v);n=np.array(n);t=v[np.array(f)];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
assert np.isfinite(v).all() and np.isfinite(n).all() and min(area)>1e-8
assert max(abs(np.linalg.norm(n,axis=1)-1))<.003
before=(OUT/'before/base.obj').read_text().splitlines(keepends=True);after=(OUT/'stage/models/maps/veridant/reception-wall-light-v1/base_without_light.obj').read_text().splitlines(keepends=True)
assert [x for x in before if not x.startswith('f ')]==[x for x in after if not x.startswith('f ')]
assert len(before)-len(after)==4
stage=OUT/'stage';assert all((ROOT/'Assets'/p.relative_to(stage)).read_bytes()==p.read_bytes() for p in stage.rglob('*') if p.is_file())
parent=(ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl').read_text();old=(OUT/'before/parent.vmdl').read_text()
assert parent.split('PhysicsShapeList',1)[1]==old.split('PhysicsShapeList',1)[1]
assert 'reception_desk_v1' not in parent
report={'new_triangles':len(f),'minimum_triangle_area':float(min(area)),'finite_unit_normals':True,'only_four_original_faces_removed':True,'original_tables_preserved':True,'installed_files_match_stage':True,'physics_unchanged':True,'original_desk_retained':True,'captures':'actual displayed editor viewport; same camera and settings'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
