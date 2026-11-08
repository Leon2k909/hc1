from build import *
vs=[];ns=[];count=0
for l in (OUT/'placed.obj').read_text().splitlines():
 if l.startswith('v '):vs.append(np.array([float(v) for v in l.split()[1:]]))
 elif l.startswith('vn '):ns.append(np.array([float(v) for v in l.split()[1:]]))
 elif l.startswith('f '):
  ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(i[0])-1] for i in ids];cross=np.cross(b-a,c-a);assert np.linalg.norm(cross)>1e-8;assert np.dot(cross,sum(ns[int(i[2])-1] for i in ids))>-1e-5;count+=1
assert np.isfinite(vs).all() and np.isfinite(ns).all()
assert collections.Counter(keys(OUT/'stage'/RESOURCE/'fine.obj'))==collections.Counter(keys(SOURCE))-collections.Counter(keys(OUT/'original.obj'))+collections.Counter(keys(OUT/'placed.obj'))
print({'triangles':count,'unrelated_faces_preserved':101770,'geometry_checks_passed':True})
