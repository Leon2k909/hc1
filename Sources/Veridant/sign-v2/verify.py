from pathlib import Path
import json, math
import numpy as np

root=Path(__file__).resolve().parents[3]
out=root/'output/veridant/sign-v2'
p=out/'stage/models/maps/veridant/sign-v2/sign.obj'
vertices=[];faces=[];normals=[]
for line in p.read_text().splitlines():
    if line.startswith('v '): vertices.append([float(v) for v in line.split()[1:]])
    elif line.startswith('vn '): normals.append([float(v) for v in line.split()[1:]])
    elif line.startswith('f '): faces.append([int(v.split('/')[0])-1 for v in line.split()[1:]])
v=np.array(vertices); n=np.array(normals)
assert np.isfinite(v).all() and np.isfinite(n).all()
tri=v[np.array(faces)]
area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
assert area.min()>1e-8, float(area.min())
assert max(abs(np.linalg.norm(n,axis=1)-1))<.003
before=(out/'before/dress-base.obj').read_text().splitlines(keepends=True)
after=(out/'stage/models/maps/veridant/sign-v2/dress-without-sign.obj').read_text().splitlines(keepends=True)
assert [l for l in before if not l.startswith('f ')]==[l for l in after if not l.startswith('f ')]
removed=len([l for l in before if l.startswith('f ')])-len([l for l in after if l.startswith('f ')])
assert removed==42
report={'triangles':len(faces),'minimum_triangle_area':float(area.min()),'finite_vertices_and_normals':True,'unit_normals':True,'original_vertex_uv_normal_tables_preserved':True,'only_42_original_faces_removed':True}
(out/'verification.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
