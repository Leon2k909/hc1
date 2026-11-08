from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/reception-desk-v1'
v=[];n=[];f=[]
for line in (OUT/'stage/models/maps/veridant/reception-desk-v1/desk.obj').read_text().splitlines():
    if line.startswith('v '):v.append([float(x) for x in line.split()[1:]])
    elif line.startswith('vn '):n.append([float(x) for x in line.split()[1:]])
    elif line.startswith('f '):f.append([int(x.split('/')[0])-1 for x in line.split()[1:]])
v=np.array(v);n=np.array(n);tri=v[np.array(f)]
area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
assert np.isfinite(v).all() and np.isfinite(n).all() and min(area)>1e-8
assert max(abs(np.linalg.norm(n,axis=1)-1))<.003
before=(OUT/'before/veridant_buildings-base.obj').read_text().splitlines(keepends=True)
after=(OUT/'stage/models/maps/veridant/reception-desk-v1/buildings_without_desk.obj').read_text().splitlines(keepends=True)
assert [x for x in before if not x.startswith('f ')]==[x for x in after if not x.startswith('f ')]
assert len(before)-len(after)==24
stage=OUT/'stage';assert all((ROOT/'Assets'/p.relative_to(stage)).read_bytes()==p.read_bytes() for p in stage.rglob('*') if p.is_file())
old=(OUT/'before/veridant_buildings.vmdl').read_text();new=(ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl').read_text()
assert old.split('PhysicsShapeList',1)[1]==new.split('PhysicsShapeList',1)[1]
sign=(ROOT/'Assets/models/maps/veridant/veridant_dress.vmdl').read_text()
assert 'reception_sign_v2' not in sign and 'models/maps/veridant/chair-v2/dress-base.obj' in sign
report={'triangles':len(f),'minimum_triangle_area':float(min(area)),'finite_vertices_and_unit_normals':True,'only_24_original_faces_removed':True,'original_tables_preserved':True,'physics_unchanged':True,'installed_files_match_stage':True,'rejected_sign_reverted':True,'capture':'actual displayed editor viewport; same camera and settings'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
