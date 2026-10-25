"""File-only rear-yard truck installation with concurrent-change guards."""
from pathlib import Path
import json,hashlib,shutil,os,re,py_compile
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
dest=r/'Assets/models/maps/forestbase';mat=r/'Assets/materials/forestbase/truck041'
audit=json.loads((out/'audit.json').read_text())
assert (out/'truck-preview.png').exists(),'Review the offline preview before installing'
for ext in ('.obj','.vmdl','.mtl'):
    assert (dest/('yard'+ext)).read_bytes()==(out/('yard.before'+ext)).read_bytes(),'Concurrent yard change: '+ext
before=(out/'yard.before.vmdl').read_text();after=(out/'yard.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert before[before.index(marker):]==after[after.index(marker):]
assert before.replace('materials/forestbase/truck/','materials/forestbase/truck041/')==after
assert (out/'yard.before.mtl').read_bytes()==(out/'yard.mtl').read_bytes()
protected=[dest/(name+ext) for name in ('motor','workshop') for ext in ('.obj','.mtl','.vmdl')]
protected+=[p for p in (r/'Assets/materials/forestbase/truck').iterdir() if p.is_file() and p.suffix in ('.png','.vmat')]
protected+=[p for p in (r/'Assets/materials/forestbase/apc').iterdir() if p.is_file() and p.suffix in ('.png','.vmat')]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
sources=[p for p in (out/'materials').iterdir() if p.suffix in ('.png','.vmat')]
for p in sources:
    if p.suffix=='.vmat':
        assert p.read_text().count('{')==p.read_text().count('}'),p
        for ref in re.findall(r'"(materials/forestbase/truck041/[^\"]+\.png)"',p.read_text()):
            assert (out/'materials'/Path(ref).name).exists(),ref
for name in ('forestbase_truck.py','forestbase_truck041.py','forestbase_map.py'):
    py_compile.compile(str(r/'Tools'/name),doraise=True)
def put(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.truck041-pending')
    shutil.copy2(source,temporary);os.replace(temporary,target)
    assert source.read_bytes()==target.read_bytes()
for p in sources:put(p,mat/p.name)
for ext in ('.obj','.vmdl'):put(out/('yard'+ext),dest/('yard'+ext))
layout=r/'output/forestbase/layout.json';shutil.copy2(layout,out/'layout.before.json')
data=json.loads(layout.read_text());data['stats']['yard']['triangles']=audit['trianglesAfter'];layout.write_text(json.dumps(data,indent=2))
for p,hash in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==hash,'Protected source changed: '+p
installed=[dest/'yard.obj',dest/'yard.vmdl']+[mat/p.name for p in sources]
integration={'editorUsed':False,'engineCompileVerified':False,'offlinePreview':'truck-preview.png','audit':audit,
             'allOtherFacesAndPhysicsPreserved':True,'otherTruckAndAPCMaterialsPreserved':True,
             'imageGeneration':{'tool':'built-in image_gen','source':'canvas-source.png','prompt':'texture-prompt.txt'},
             'installed':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in installed},'protectedHashes':hashes}
(out/'integration.json').write_text(json.dumps(integration,indent=2))
print(json.dumps({'truckReplaced':1,'privateMaterialFiles':len(sources),'yardTriangles':audit['trianglesAfter'],'editorUsed':False,'engineCompileVerified':False},indent=2))
