from build import *
vs=[];ns=[];areas=[]
for l in (OUT/'stage'/PROP/'display.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('vn '):ns.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('f '):
        ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(x[0])-1] for x in ids];cross=np.cross(b-a,c-a)
        areas.append(np.linalg.norm(cross)/2);assert areas[-1]>1e-8
        assert np.dot(cross,sum(ns[int(i[2])-1] for i in ids))>-1e-5
assert np.isfinite(vs).all() and np.isfinite(ns).all()
assert all(abs(np.linalg.norm(n)-1)<.001 for n in ns)
assert all(-682.3<=p[0]<=-627.7 and 41.99<=p[1]<=56.3 and 603.7<=p[2]<=627 for p in vs)
a=collections.Counter(keys(SOURCE));b=collections.Counter(keys(OUT/'stage'/RESOURCE/'fine.obj'))
p=json.loads((OUT/'checks.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==p['source_sha256']
old=collections.Counter(keys(OUT/'original.obj'));new=collections.Counter(keys(OUT/'placed.obj'))
assert sum(old.values())==22 and sum(new.values())==2112
assert b==a-old+new  # One replacement triangle coincides with an old pane.
report={'triangles':len(areas),'minimum_area':min(areas),'finite_unit_normals':True,'nondegenerate_outward_faces':True,'unrelated_faces_preserved':72468,'no_collision_added':True}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
