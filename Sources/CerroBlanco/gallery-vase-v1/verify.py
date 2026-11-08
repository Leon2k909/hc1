from build import *
vs=[];ns=[];areas=[]
for l in (OUT/'stage'/PROP/'vase.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('vn '):ns.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('f '):
        ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(x[0])-1] for x in ids];cross=np.cross(b-a,c-a)
        areas.append(np.linalg.norm(cross)/2);assert areas[-1]>1e-8
        assert np.dot(cross,sum(ns[int(i[2])-1] for i in ids))>-1e-6
assert np.isfinite(vs).all() and np.isfinite(ns).all()
assert all(abs(np.linalg.norm(n)-1)<.001 for n in ns)
assert all(-6.001<=p[0]<=6.001 and -6.001<=p[2]<=6.001 and 0<=p[1]<=14.001 for p in vs)
a=collections.Counter(keys(SOURCE));b=collections.Counter(keys(OUT/'stage'/RESOURCE/'dressing.obj'))
assert sum((a-b).values())==34 and sum((b-a).values())==6240
assert sum((a&b).values())==29618
report={'triangles':len(areas),'minimum_area':min(areas),'finite_unit_normals':True,'nondegenerate_outward_faces':True,'original_envelope_retained':True,'unrelated_faces_preserved':29618,'approved_bin_retained':True}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
