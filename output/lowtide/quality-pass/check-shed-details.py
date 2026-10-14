"""Verify additive scope and placement of the eight shed vents and four ridges."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
parser=argparse.ArgumentParser();parser.add_argument("--installed",action="store_true");args=parser.parse_args()
manifest=json.loads((HERE/"shed-details-manifest.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,before in manifest["protectedBefore"].items():
    expected=manifest["changes"][name]["after"] if args.installed and name in manifest["changes"] else before
    assert sha(ROOT/name)==expected,name
folder=ROOT/"Assets/models/maps/lowtide" if args.installed else HERE/"shed-details-stage"
old=(HERE/"shed-details-before/lowtide_finish.obj").read_text().splitlines()
new=(folder/"lowtide_finish.obj").read_text().splitlines()
assert "# Lowtide shed slate relief v1" not in new,"Rejected slate geometry must remain absent"
for prefix in ("v ","vt ","vn "):
    previous=[s for s in old if s.startswith(prefix)]
    assert [s for s in new if s.startswith(prefix)][:len(previous)]==previous,prefix
draws=[s for s in old if s.startswith(("usemtl ","f "))]
assert [s for s in new if s.startswith(("usemtl ","f "))][:len(draws)]==draws
resource=(folder/"lowtide_finish.vmdl").read_text()
assert resource.replace("\n".join(manifest["newMaterialRemaps"])+"\n","")==(HERE/"shed-details-before/lowtide_finish.vmdl").read_text()
assert "PhysicsShapeList" not in resource
vertices=[];triangles=[];paint=None;backings=[]
for line in (HERE/"shed-details-stage/shed-details-addition.obj").read_text().splitlines():
    if line.startswith("v "):
        x,z,n=map(float,line.split()[1:]);vertices.append((-x,n,z))
    elif line.startswith("usemtl "):paint=line.split()[1]
    elif line.startswith("f "):
        tri=[vertices[int(r.split("/")[0])-1] for r in line.split()[1:]]
        triangles.append(tri)
        if paint=="lt_hull_black":backings.append(tri)
triangles=np.asarray(triangles);backings=np.asarray(backings)
assert triangles[:,:,2].min()>236,"No detail may enter the ground-level playable route"
area=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)/2
assert area.min()>1e-6
assert len(triangles)==manifest["addedTriangles"]
assert len(manifest["vents"])==8 and len(manifest["ridges"])==4
samples=0
for vent in manifest["vents"]:
    c=np.array(vent["centre"]);normal=np.array(vent["normal"]);r=vent["radius"]
    local=backings-c
    sel=np.abs(local@normal-.12).max(1)<.002
    projected=local[sel][:,:,(1,2)]
    # Each blind vent must have an opaque backing, with no glimpses of brick
    # through the louvre gaps that would reveal the additive construction.
    a=projected[:,0];ab=projected[:,1]-a;ac=projected[:,2]-a
    denom=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    for angle in np.linspace(0,2*np.pi,17)[:-1]:
        for radius in (0,r*.5,r*.95):
            offset=np.array((np.cos(angle),np.sin(angle)))*radius-a
            u=(offset[:,0]*ac[:,1]-offset[:,1]*ac[:,0])/denom
            v=(ab[:,0]*offset[:,1]-ab[:,1]*offset[:,0])/denom
            assert np.any((u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6))
            samples+=1
report=dict(state="installed" if args.installed else "staged",originalTrianglesRetained=sum(s.startswith("f ") for s in old),
            addedTriangles=len(triangles),vents=8,ridges=4,ventBackingSamples=samples,rejectedSlatesAbsent=True,
            otherModelSourcesMaterialsSceneAndPhysicsUnchanged=True,collisionAdded=False)
(HERE/"shed-details-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
