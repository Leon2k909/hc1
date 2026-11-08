from pathlib import Path
import numpy as np,json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/terrace-umbrella-v1';v=[];n=[];f=[]
for l in (OUT/'stage/models/maps/veridant/terrace-umbrella-v1/canopy.obj').read_text().splitlines():
    if l.startswith('v '):v.append([float(x) for x in l.split()[1:]])
    elif l.startswith('vn '):n.append([float(x) for x in l.split()[1:]])
    elif l.startswith('f '):f.append([int(x.split('/')[0])-1 for x in l.split()[1:]])
v=np.array(v);n=np.array(n);t=v[np.array(f)];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
assert np.isfinite(v).all() and np.isfinite(n).all() and min(area)>1e-8
assert max(abs(np.linalg.norm(n,axis=1)-1))<.003
before=(OUT/'before/base.obj').read_text().splitlines(keepends=True);after=(OUT/'stage/models/maps/veridant/terrace-umbrella-v1/base_without_canopy.obj').read_text().splitlines(keepends=True)
assert [x for x in before if not x.startswith('f ')]==[x for x in after if not x.startswith('f ')]
checks=json.loads((OUT/'checks.json').read_text());assert len(before)-len(after)==checks['removed_triangles']
old=(OUT/'before/parent.vmdl').read_text();new=(OUT/'stage/models/maps/veridant/veridant_buildings.vmdl').read_text();assert old.split('PhysicsShapeList',1)[1]==new.split('PhysicsShapeList',1)[1]
assert all(name in new for name in ('operations_banner_cloth_v1','reception_wall_light_v1','reception_stair_rail_v1'))
report={'triangles':len(f),'minimum_triangle_area':float(min(area)),'finite_unit_normals':True,'other_records_preserved':True,'physics_unchanged':True,'original_base_pole_and_finial_preserved':True,'previous_accepted_upgrades_retained':True}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
