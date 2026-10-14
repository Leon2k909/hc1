"""Check tyre replacement scope, winding, open centres and bank contact."""
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_tyres as T

folder = Path(__file__).parent
before, stage = folder / "tyres-before", folder / "tyres-stage"


def records(path):
    vertices, textures, normals, faces, paint = [], [], [], Counter(), None
    for row in path.read_text().splitlines():
        if row.startswith("v "):
            vertices.append(tuple(map(float,row.split()[1:])))
        elif row.startswith("vt "):
            textures.append(tuple(map(float,row.split()[1:])))
        elif row.startswith("vn "):
            normals.append(tuple(map(float,row.split()[1:])))
        elif row.startswith("usemtl "):
            paint = row.split()[1]
        elif row.startswith("f "):
            tri = []
            for token in row.split()[1:]:
                v,t,n = map(int,token.split("/"))
                tri.append((vertices[v-1],textures[t-1],normals[n-1]))
            faces[(paint,tuple(tri))] += 1
    return vertices,textures,normals,faces


original = records(before / "Assets/models/maps/lowtide/lowtide_fleet.obj")
updated = records(stage / "lowtide_fleet.obj")
old_tyres = records(stage / "original-tyres.obj")
new_tyres = records(stage / "replacement-tyres.obj")
for i in range(3):
    assert updated[i][:len(original[i])] == original[i]
    assert updated[i][len(original[i]):] == new_tyres[i]
expected = Counter((paint,tuple(v for v,uv,n in tri)) for (paint,tri),count in old_tyres[3].items() for _ in range(count))
retained = original[3].copy()
for key,count in original[3].items():
    paint,tri = key
    match = (paint,tuple(v for v,uv,n in tri))
    take = min(expected[match],count)
    retained[key] -= take
    expected[match] -= take
assert not +expected
assert updated[3] == +retained + new_tyres[3], "Unrelated face, UV or normal changed"
remap = f'\t\t\t\t\t\t\t{{ from = "{T.PAINT}.vmat" to = "{T.RESOURCE}" }},\n'
vmdl = (stage / "lowtide_fleet.vmdl").read_text()
assert vmdl.count(remap) == 1
assert vmdl.replace(remap,"") == (before / "Assets/models/maps/lowtide/lowtide_fleet.vmdl").read_text()
for relative in ("Assets/scenes/maps/Lowtide/lowtide.scene", "Assets/models/maps/lowtide/lowtide_fleet_hulls_dirt.obj",
                 "Assets/models/maps/lowtide/lowtide_fleet_hulls_metal.obj"):
    assert (ROOT / relative).read_bytes() == (before / relative).read_bytes(), relative

minimum_alignment = 1.0
for paint,tri in new_tyres[3]:
    points = np.asarray([v for v,uv,n in tri])
    normals = np.asarray([n for v,uv,n in tri])
    cross = np.cross(points[1]-points[0],points[2]-points[0])
    length = np.linalg.norm(cross)
    assert length > 1e-7, "Degenerate tyre triangle"
    alignment = float((normals @ (cross/length)).min())
    assert alignment > 0, alignment
    assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=.002)
    minimum_alignment = min(minimum_alignment,alignment)

terrain = []
for (paint,tri),count in original[3].items():
    if paint in ("lt_mud","lt_mud_wet"):
        terrain.extend([[( -v[0],v[2],v[1]) for v,uv,n in tri]]*count)
terrain = np.asarray(terrain)
tree = cKDTree(terrain[:,:,:2].mean(axis=1))


def surface(points):
    _,nearest = tree.query(points[:,:2],k=24)
    tri = terrain[nearest]
    a,b,c = tri[:,:,0,:],tri[:,:,1,:],tri[:,:,2,:]
    u,v,q = b[...,:2]-a[...,:2],c[...,:2]-a[...,:2],points[:,None,:2]-a[...,:2]
    det = u[...,0]*v[...,1]-u[...,1]*v[...,0]
    s = (q[...,0]*v[...,1]-q[...,1]*v[...,0])/det
    t = (u[...,0]*q[...,1]-u[...,1]*q[...,0])/det
    inside = (s>=-1e-7)&(t>=-1e-7)&(s+t<=1+1e-7)
    assert inside.any(axis=1).all()
    z = a[...,2]+s*(b[...,2]-a[...,2])+t*(c[...,2]-a[...,2])
    return np.where(inside,z,-np.inf).max(axis=1)


contact = []
for e,n,r in T.POSITIONS:
    model = K.Model()
    T.tyre(model,e,n,float(L.mud_z(e,n))-1.5,r)
    assert not model.boxes and not model.hulls
    points = np.unique(np.asarray([p for polygon,_ in model.polygons[T.PAINT] for p in polygon]),axis=0)
    distances = points[:,2]-surface(points)
    radial = np.linalg.norm(points[:,:2]-(e,n),axis=1)
    assert radial.min() > r*.53, "Face reaches the open centre"
    assert distances.min() < 0 < distances.max(), "Floating or fully buried tyre"
    contact.append({"centre":[e,n],"bottom_inches":float(distances.min()),"top_inches":float(distances.max()),
                    "minimum_opening_radius":float(radial.min())})
for i,(e,n,r) in enumerate(T.POSITIONS):
    for e1,n1,r1 in T.POSITIONS[i+1:]:
        assert np.hypot(e1-e,n1-n) > r+r1, "Tyre casings overlap"
report = {"tyres":4,"unrelated_faces_uvs_normals_retained":True,"scene_and_collision_unchanged":True,
          "minimum_normal_alignment":minimum_alignment,"terrain_triangles":len(terrain),"contact":contact,
          "new_triangles":sum(new_tyres[3].values()),"removed_triangles":sum(old_tyres[3].values()),
          "no_casing_overlap":True}
(folder / "tyre-scope-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
