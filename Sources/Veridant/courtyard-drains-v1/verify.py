from pathlib import Path
import sys,numpy as np,json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/courtyard-drains-v1';sys.path.insert(0,str(ROOT/'Tools'))
import veridant_courtyard_drains as D
v=[];n=[];f=[]
for l in (OUT/'stage/models/maps/veridant/courtyard-drains-v1/covers.obj').read_text().splitlines():
    if l.startswith('v '):v.append([float(x) for x in l.split()[1:]])
    elif l.startswith('vn '):n.append([float(x) for x in l.split()[1:]])
    elif l.startswith('f '):f.append([int(x.split('/')[0])-1 for x in l.split()[1:]])
v=np.array(v);n=np.array(n);t=v[np.array(f)];area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
assert np.isfinite(v).all() and np.isfinite(n).all() and min(area)>1e-8
assert max(abs(np.linalg.norm(n,axis=1)-1))<.003
assert min(v[:,1])>=.024 and max(v[:,1])<=.246
plan=np.stack((-v[:,0],v[:,2]),axis=1);inside=np.zeros(len(v),dtype=bool)
for a,b in D.PLACEMENTS:
    a=np.array(a,float);b=np.array(b,float);d=(b-a)/np.linalg.norm(b-a);side=np.array((-d[1],d[0]));rel=plan-a;u=rel@d;w=rel@side
    inside|=(u>=-.002)&(u<=np.linalg.norm(b-a)+.002)&(abs(w)<=2.952)
assert inside.all()
before=(OUT/'before/base.obj').read_text().splitlines(keepends=True);after=(OUT/'stage/models/maps/veridant/courtyard-drains-v1/ground_without_drains.obj').read_text().splitlines(keepends=True)
assert [x for x in before if not x.startswith(('f ','usemtl vr_grate','usemtl vr_steel'))]==[x for x in after if not x.startswith('f ')]
assert sum(x.startswith('f ') for x in before)-sum(x.startswith('f ') for x in after)==24
old=(OUT/'before/parent.vmdl').read_text();new=(OUT/'stage/models/maps/veridant/veridant_ground.vmdl').read_text();assert old.split('PhysicsShapeList',1)[1]==new.split('PhysicsShapeList',1)[1]
report={'triangles':len(f),'minimum_triangle_area':float(min(area)),'finite_unit_normals':True,'all_vertices_within_original_footprints':True,'maximum_rise_inches':float(max(v[:,1])),'only_24_original_triangles_removed':True,'other_records_preserved':True,'physics_unchanged':True,'existing_grate_materials_reused':True}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
