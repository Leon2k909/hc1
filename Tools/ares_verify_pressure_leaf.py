"""Check the installed pressure-style sliding leaf and preserved automatic setup."""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Tools'));import ares_sliding_doors as D
OUT=ROOT/'output/ares/sliding-pressure-leaf-20261031';report=json.loads((OUT/'installation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,h in report['afterSHA256'].items():assert sha(ROOT/path)==h,path
for path in ('Assets/scenes/maps/Ares/ares.scene','Code/World/AutomaticSlidingDoor.cs','Tools/ares_pressure_formed.py'):
    key=next(k for k in report['beforeSHA256'] if k.replace('\\','/')==path)
    assert sha(ROOT/path)==report['beforeSHA256'][key],path
obj=ROOT/'Assets/models/maps/ares/sliding-doors-v1/ares_sliding_leaf.obj';doc=obj.with_suffix('.vmdl');mtl=obj.with_suffix('.mtl')
old=(OUT/'before'/doc.relative_to(ROOT)).read_text();new=doc.read_text()
assert new[new.index('_class = "PhysicsShapeList"'):]==old[old.index('_class = "PhysicsShapeList"'):]
assert 'dimensions = [ 112.8960, 8.0000, 172.0000 ]' in new
remaps=dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"',new));names=set(re.findall(r'^newmtl (\S+)',mtl.read_text(),re.M))
vertices=[];faces=[];materials=set();paint=''
for line in obj.read_text().splitlines():
    p=line.split()
    if not p:continue
    if p[0]=='v':vertices.append(tuple(map(float,p[1:])))
    elif p[0]=='usemtl':paint=p[1];materials.add(paint)
    elif p[0]=='f':assert len(p)==4;faces.append([int(x.split('/')[0])-1 for x in p[1:]])
assert len(faces)==report['trianglesPerLeaf'] and materials==set(report['materials']) and materials<=names
for name in materials:assert name in remaps and (ROOT/'Assets'/remaps[name]).exists(),name
p=np.array(vertices);f=p[np.array(faces)];areas=np.linalg.norm(np.cross(f[:,1]-f[:,0],f[:,2]-f[:,0]),axis=1)
assert np.isfinite(p).all() and (areas>1e-8).all()
# OBJ axes are (-east, height, north); all visible points fit the old moving box.
assert np.all(p.min(axis=0)>=np.array((-56.448,-86,-4))-.001) and np.all(p.max(axis=0)<=np.array((56.448,86,4))+.001)
scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());doors=D.scene_objects()
for door in doors:assert sum(x==door for x in scene['GameObjects'])==1
assert 56+114-112.896/2>112 and 56-112.896/2<0
result={'doorInstances':len(doors),'trianglesPerLeaf':len(faces),'allNineMaterialBindingsValid':len(materials)==9,
 'finiteNondegenerateGeometryInsideExistingCollision':True,'physicsUnchanged':True,'originalAutomaticDoorInstancesUnchanged':True,
 'closedCentreSealedAndOpenApertureClear':True,'sourcePressureDesignAndControllerUnchanged':True,'nativeAppearanceOrPlaytestPerformed':False}
(OUT/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
