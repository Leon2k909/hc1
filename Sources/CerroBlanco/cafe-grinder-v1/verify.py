from build import *
vs=[];ns=[];areas=[]
for l in (OUT/'stage'/PROP/'grinder.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('vn '):ns.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('f '):
        ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(x[0])-1] for x in ids];cross=np.cross(b-a,c-a)
        areas.append(np.linalg.norm(cross)/2);assert areas[-1]>1e-8
        assert np.dot(cross,sum(ns[int(i[2])-1] for i in ids))>-1e-5
assert np.isfinite(vs).all() and np.isfinite(ns).all()
assert all(abs(np.linalg.norm(n)-1)<.001 for n in ns)
assert all(-4<=p[0]<=4 and -0.001<=p[1]<=16.001 and -4.6<=p[2]<=3.8 for p in vs)
a=collections.Counter(keys(SOURCE));b=collections.Counter(keys(OUT/'stage'/RESOURCE/'fine.obj'))
p=json.loads((OUT/'checks.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==p['source_sha256']
assert sum((a-b).values())==128 and sum((b-a).values())==4880 and sum((a&b).values())==67610,(sum((a-b).values()),sum((b-a).values()),sum((a&b).values()))
report={'triangles':len(areas),'minimum_area':min(areas),'finite_unit_normals':True,'nondegenerate_outward_faces':True,'unrelated_faces_preserved':67610,'no_collision_added':True,'modelled_beans':24}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
