"""Historical checker for the REJECTED slate skin; not a current-state gate."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/"Tools"))
import lowtide_map as L
import importlib.util
spec=importlib.util.spec_from_file_location("rejected_roof_relief",HERE/"rejected-lowtide_roof_relief.py")
R=importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

parser=argparse.ArgumentParser()
parser.add_argument("--installed",action="store_true")
args=parser.parse_args()
manifest=json.loads((HERE/"roof-relief-manifest.json").read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for name,before in manifest["protectedBefore"].items():
    expected=manifest["changes"][name]["after"] if args.installed and name in manifest["changes"] else before
    assert sha(ROOT/name)==expected,name
folder=ROOT/"Assets/models/maps/lowtide" if args.installed else HERE/"roof-relief-stage"
old=(HERE/"roof-relief-before/lowtide_finish.obj").read_text().splitlines()
new=(folder/"lowtide_finish.obj").read_text().splitlines()
for prefix in ("v ","vt ","vn "):
    previous=[s for s in old if s.startswith(prefix)]
    assert [s for s in new if s.startswith(prefix)][:len(previous)]==previous,prefix
draws=[s for s in old if s.startswith(("usemtl ","f "))]
assert [s for s in new if s.startswith(("usemtl ","f "))][:len(draws)]==draws
resource=(folder/"lowtide_finish.vmdl").read_text()
assert resource.replace(manifest["newMaterialRemap"],"")==(HERE/"roof-relief-before/lowtide_finish.vmdl").read_text()
assert "PhysicsShapeList" not in resource
assert sum(s.startswith("f ") for s in new)==sum(s.startswith("f ") for s in old)+manifest["addedTriangles"]

vertices=[];uvs=[];normals=[];faces=[]
for line in (HERE/"roof-relief-stage/roof-relief-addition.obj").read_text().splitlines():
    if line.startswith("v "):
        x,z,n=map(float,line.split()[1:]);vertices.append((-x,n,z))
    elif line.startswith("vt "):uvs.append(list(map(float,line.split()[1:])))
    elif line.startswith("vn "):
        x,z,n=map(float,line.split()[1:]);normals.append((-x,n,z))
    elif line.startswith("f "):faces.append([[int(i)-1 for i in r.split("/")] for r in line.split()[1:]])
faces=np.asarray(faces)
triangles=np.asarray(vertices)[faces[:,:,0]]
uvs=np.asarray(uvs)[faces[:,:,1]]
normals=np.asarray(normals)[faces[:,0,2]]
cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
areas=np.linalg.norm(cross,axis=1)/2
geometric_normals=cross/(2*areas[:,None])
assert areas.min()>.00001,"Degenerate geometry"
covered=np.zeros(len(triangles),bool)
sample_count=0
uv_error=0.
substrates={}
for side,name in ((1,"east"),(-1,"west")):
    points=[];roofs=[];paint=None
    for line in (ROOT/f"Assets/models/maps/lowtide/lowtide_{name}.obj").read_text().splitlines():
        if line.startswith("v "):
            x,z,n=map(float,line.split()[1:]);points.append((-x,n,z))
        elif line.startswith("usemtl "):paint=line.split()[1]
        elif line.startswith("f ") and paint=="slate":
            roofs.append([points[int(ref.split("/")[0])-1] for ref in line.split()[1:]])
    substrates[side]=np.asarray(roofs)
for panel in manifest["panels"]:
    e0,e1,n0,n1=panel["bounds"]
    sign,side=panel["slope"],panel["side"]
    pitch=panel["pitch"]
    scale=np.sqrt(1+pitch**2)
    normal=np.array((0,sign*pitch,1))/scale
    up=np.array((0,-sign,pitch))/scale
    along=np.array((side,0,0))
    origin=np.array((side*e0,n1 if sign>0 else n0,panel["eaves"]))
    original=substrates[side]
    # Match the actual installed architecture, independently of the relief generator.
    original_x=(original-origin)@along;original_y=(original-origin)@up
    actual=original[(original_x.min(1)>-.002)&(original_x.max(1)<e1-e0+.002)&
                    (original_y.min(1)>-.002)&(original_y.max(1)<(n1-n0)*.5*scale+.002)]
    assert len(actual)==2,("Expected original roof panel",panel,len(actual))
    assert np.abs((actual-origin)@normal).max()<.002,"Relief does not match the installed roof plane"
    relative=triangles-origin
    x=relative@along; y=relative@up; depth=relative@normal
    run=(n1-n0)*.5*scale
    selection=(x.min(1)>-.002)&(x.max(1)<e1-e0+.002)&(y.min(1)>-.002)&(y.max(1)<run+.002)&(depth.min(1)>-.002)&(depth.max(1)<.282)
    covered |= selection
    tops=selection&(geometric_normals@normal>.98)
    assert tops.sum()>40
    seed=L.keyed(e0,panel["eaves"],side,sign,"slate relief")
    phase=R.image_courses()[seed%12];u_phase=(seed//12%8)/8
    expected=np.stack((u_phase+x[tops]/R.SPAN,R.TEXTURE_SCALE-1+phase+y[tops]/R.SPAN),axis=-1)
    error=float(np.abs(uvs[tops]*R.TEXTURE_SCALE-expected).max())
    assert error<.00003,("Texture/geometry misregistration",error)
    uv_error=max(error,uv_error)
    projected=np.stack((x[tops],y[tops]),axis=-1)
    a=projected[:,0];ab=projected[:,1]-a;ac=projected[:,2]-a
    denom=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    for px in np.linspace(.2,e1-e0-.2,9):
        for py in np.linspace(.2,run-.2,13):
            off=np.array((px,py))-a
            u=(off[:,0]*ac[:,1]-off[:,1]*ac[:,0])/denom
            v=(ab[:,0]*off[:,1]-ab[:,1]*off[:,0])/denom
            assert np.any((u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)),("Roof gap",panel,px,py)
            sample_count+=1
assert covered.all(),"Unexpected geometry beyond the four shed roofs"
report=dict(state="installed" if args.installed else "staged",originalTrianglesRetained=sum(s.startswith("f ") for s in old),
            addedTriangles=manifest["addedTriangles"],panels=len(manifest["panels"]),coverageSamples=sample_count,
            maximumUvRegistrationError=uv_error,texturePixelsAndMaterialsUnchanged=True,
            otherModelsSceneAndPhysicsUnchanged=True,collisionAdded=False)
(HERE/"roof-relief-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
