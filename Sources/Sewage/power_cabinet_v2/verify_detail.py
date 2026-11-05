"""Check the cabinet's exported LODs, closed-shell winding, atlas inputs and three placements."""
from collections import Counter
from pathlib import Path
import json
import re

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
MODEL = ROOT / "Assets/models/maps/sewage/power_cabinet_v2"
MATS = ROOT / "Assets/materials/maps/sewage/power_cabinet_v2"
report = {"lods": []}
for lod in range(4):
    v, uv, normals, faces = [], [], [], []
    for line in (MODEL / f"power_cabinet_lod{lod}.obj").read_text().splitlines():
        if line.startswith("v "): v.append(line.split()[1:])
        elif line.startswith("vt "): uv.append(line.split()[1:])
        elif line.startswith("vn "): normals.append(line.split()[1:])
        elif line.startswith("f "): faces.append([[int(x)-1 for x in token.split("/")] for token in line.split()[1:]])
    v, uv, normals, faces = np.array(v,float), np.array(uv,float), np.array(normals,float), np.array(faces,int)
    assert np.isfinite(v).all() and np.isfinite(uv).all() and np.isfinite(normals).all()
    assert ((uv>=-1e-4)&(uv<=1.0001)).all(), f"LOD {lod}: UV outside atlas"
    world = v[:,[2,0,1]]
    lo, hi = world.min(0), world.max(0)
    assert (lo>=np.array((-19.1,-44.0,-.05))).all() and (hi<=np.array((25.0,40.5,122.3))).all(), (lod,lo,hi)
    tri = v[faces[:,:,0]]
    cross = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    valid = np.linalg.norm(cross,axis=1)>1e-8
    agreement = float(((cross*normals[faces[:,:,2]].mean(1)).sum(1)[valid]>0).mean())
    assert agreement>.97, (lod,agreement)
    entry = dict(lod=lod,triangles=len(faces),normals_agree=round(agreement,4),bounds=[lo.round(3).tolist(),hi.round(3).tolist()])
    if lod==0:
        parent = np.arange(len(v))
        def find(i):
            while parent[i]!=i:
                parent[i]=parent[parent[i]];i=parent[i]
            return i
        for a,b,c in faces[:,:,0]:
            parent[find(b)]=find(a);parent[find(c)]=find(a)
        roots = np.array([find(a) for a in faces[:,0,0]])
        closed = opened = 0
        for root in np.unique(roots):
            pick = roots==root
            edges = Counter(tuple(sorted((int(a),int(b)))) for f in faces[pick,:,0] for a,b in zip(f,np.roll(f,-1)))
            if any(count!=2 for count in edges.values()):
                opened+=1;continue
            closed+=1
            t = tri[pick]
            volume = (t[:,0]*np.cross(t[:,1],t[:,2])).sum()/6
            assert volume>=-1e-4, f"Closed shell faces inward at {t.mean((0,1))}"
        entry.update(closed_outward_pieces=closed,open_shells=opened)
    report["lods"].append(entry)

doc = (MODEL / "power_cabinet.vmdl").read_text()
for path in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',doc): assert (ROOT/"Assets"/path).exists(),path
for suffix, size in (("color",4096),("normal",4096),("rough",2048),("metal",2048),("ao",2048),("glow",2048)):
    with Image.open(MATS/f"power_cabinet_{suffix}.png") as texture: assert texture.size==(size,size)
scene = json.loads((ROOT/"Assets/scenes/maps/sewage/sewage.scene").read_text())
def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children",[]))
placed = [x for x in walk(scene["GameObjects"]) if x.get("Name","").startswith("Power cabinet ")]
assert len(placed)==3
for obj in placed:
    assert any("power_cabinet_v2/power_cabinet.vmdl" in str(c.get("Model")) for c in obj.get("Components",[]))
report.update(placed=3,atlas_sizes_valid=True,asset_references_valid=True)
out = ROOT/"output/cabinet-instruments-20261104/verified.json"
out.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
