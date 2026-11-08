from pathlib import Path
import sys,json,numpy as np,hashlib
from collections import Counter
from build import keys,ROOT,OUT,SOURCE,RESOURCE,PROP
plan=json.loads((OUT/'geometry-checks.json').read_text());assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==plan['source_sha256']
a=Counter(keys(SOURCE));b=Counter(keys(OUT/'stage'/RESOURCE/'dressing.obj'))
assert sum((a-b).values())==46 and sum((a&b).values())==plan['other_faces_preserved']
assert sum((b-a).values())==plan['added_triangles']
vs=[];ns=[];areas=[]
for l in (OUT/'stage'/PROP/'bin.obj').read_text().splitlines():
    if l.startswith('v '):vs.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('vn '):ns.append(np.array([float(x) for x in l.split()[1:]]))
    elif l.startswith('f '):
        ids=[x.split('/') for x in l.split()[1:]];a,b,c=[vs[int(x[0])-1] for x in ids];cross=np.cross(b-a,c-a)
        areas.append(np.linalg.norm(cross)/2);assert areas[-1]>1e-8
        assert np.dot(cross,sum(ns[int(i[2])-1] for i in ids))>-1e-6
assert np.isfinite(vs).all() and np.isfinite(ns).all()
# map_kit serializes OBJ vectors to three decimal places.
assert all(abs(np.linalg.norm(n)-1)<.001 for n in ns)
assert all(-9.01<=p[0]<=9.01 and -9.01<=p[2]<=9.01 and 0<=p[1]<=34.001 for p in vs)
report={'triangles':len(areas),'minimum_area':min(areas),'finite_unit_normals':True,'nondegenerate_outward_faces':True,'original_envelope_retained':True,'unrelated_faces_preserved':plan['other_faces_preserved']}
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(report)
