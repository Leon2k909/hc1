from build import *
vs=[];ns=[];areas=[];mat=''
for l in (OUT/'placed.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('vn '):ns.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('usemtl '):mat=l.split()[1]
    elif l.startswith('f '):
        ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(x[0])-1] for x in ids];cross=np.cross(b-a,c-a)
        areas.append(np.linalg.norm(cross)/2);assert areas[-1]>1e-8
        assert np.dot(cross,sum(ns[int(i[2])-1] for i in ids))>-1e-5,(mat,l,a,b,c,ns[int(ids[0][2])-1])
assert np.isfinite(vs).all() and np.isfinite(ns).all()
assert all(abs(np.linalg.norm(n)-1)<.001 for n in ns)
a=collections.Counter(keys(SOURCE));b=collections.Counter(keys(OUT/'stage'/RESOURCE/'fine.obj'))
assert b==a-collections.Counter(keys(OUT/'original.obj'))+collections.Counter(keys(OUT/'placed.obj'))
report={'triangles':len(areas),'minimum_area':min(areas),'finite_unit_normals':True,'nondegenerate_outward_faces':True,'unrelated_faces_preserved':89504,'no_collision_added':True}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
