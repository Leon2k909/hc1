"""Check retained geometry and ray coverage through the formerly open quay end."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
p=argparse.ArgumentParser()
p.add_argument("--installed",action="store_true")
args=p.parse_args()
manifest=json.loads((HERE/"perimeter-manifest.json").read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for path,before in manifest["protectedBefore"].items():
    expected=manifest["changes"][path]["after"] if args.installed and path in manifest["changes"] else before
    assert sha(ROOT/path)==expected,path
source=ROOT/"Assets/models/maps/lowtide" if args.installed else HERE/"perimeter-stage"
old=(HERE/"perimeter-before/lowtide_finish.obj").read_text().splitlines()
new=(source/"lowtide_finish.obj").read_text().splitlines()
for prefix in ("v ","vt ","vn "):
    previous=[s for s in old if s.startswith(prefix)]
    assert [s for s in new if s.startswith(prefix)][:len(previous)]==previous,prefix
old_draws=[s for s in old if s.startswith(("usemtl ","f "))]
new_draws=[s for s in new if s.startswith(("usemtl ","f "))]
assert new_draws[:len(old_draws)]==old_draws,"All original triangle indices and materials must survive unchanged"
old_resource=(HERE/"perimeter-before/lowtide_finish.vmdl").read_text()
resource=(source/"lowtide_finish.vmdl").read_text()
inserted="\n".join(manifest["newMaterialRemaps"])+"\n"
assert resource.replace(inserted,"")==old_resource,"Only material remaps may change in model resource"
assert "PhysicsShapeList" not in resource

# Cast horizontal rays through the old open end at both sides. Each sample must
# intersect opaque facade, frame, stone or sealed-window geometry behind it.
verts=[]
triangles=[]
for line in (HERE/"perimeter-stage/perimeter-addition.obj").read_text().splitlines():
    if line.startswith("v "):
        x,z,n=map(float,line.split()[1:])
        verts.append((-x,n,z)) # OBJ -> authored east, north, height
    elif line.startswith("f "):
        triangles.append([verts[int(v.split("/")[0])-1] for v in line.split()[1:]])
triangles=np.asarray(triangles)
coverage={}
for sign,side in ((1,"east"),(-1,"west")):
    selected=triangles[(np.abs(triangles[:,:,0]).min(1)>=2219)&
        (np.abs(triangles[:,:,0]).max(1)<=2701)&
        (triangles[:,:,1].min(1)>=-1060)&(triangles[:,:,1].max(1)<=-1025)]
    projected=selected[:,:,(0,2)]
    a=projected[:,0]; ab=projected[:,1]-a; ac=projected[:,2]-a
    denom=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    valid=np.abs(denom)>1e-7
    a,ab,ac,denom=a[valid],ab[valid],ac[valid],denom[valid]
    tested=0
    for e in np.linspace(2221,2699,25):
        for z in np.linspace(1,899,46):
            offset=np.array((sign*e,z))-a
            u=(offset[:,0]*ac[:,1]-offset[:,1]*ac[:,0])/denom
            v=(ab[:,0]*offset[:,1]-ab[:,1]*offset[:,0])/denom
            assert np.any((u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)),f"Uncovered shell at {side}: {e},{z}"
            tested+=1
    coverage[side]=tested
report={"state":"installed" if args.installed else "staged",
        "originalTrianglesRetained":sum(s.startswith("f ") for s in old),
        "addedTriangles":manifest["addedTriangles"],"newCollision":False,
        "otherModelsSceneAndPhysicsUnchanged":True,"quayEndCoverageSamples":coverage,
        "wallSections":2*len(manifest["eastWalls"]),"sealedWindows":manifest["sealedWindows"]}
(HERE/"perimeter-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
