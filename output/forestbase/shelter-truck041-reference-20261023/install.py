"""Install only the requested shelter truck source, preserving other props."""
from pathlib import Path
import json,hashlib,shutil,os,re,py_compile
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
dest=r/'Assets/models/maps/forestbase';audit=json.loads((out/'audit.json').read_text())
assert (out/'truck-preview.png').exists()
for ext in ('.obj','.vmdl','.mtl'):
    assert (dest/('motor'+ext)).read_bytes()==(out/('motor.before'+ext)).read_bytes(),'Concurrent motor change: '+ext
before=(out/'motor.before.vmdl').read_text();after=(out/'motor.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert before[before.index(marker):]==after[after.index(marker):]
for slot,path in re.findall(r'from\s*=\s*"(shelter_truck_[^\"]+)"\s+to\s*=\s*"([^\"]+)"',after):
    assert (r/'Assets'/path).exists(),path
    for texture in re.findall(r'"(materials/forestbase/truck041/[^\"]+\.png)"',(r/'Assets'/path).read_text()):
        assert (r/'Assets'/texture).exists(),texture
protected=[dest/(name+ext) for name in ('yard','workshop') for ext in ('.obj','.mtl','.vmdl')]
for folder in ('truck','truck041','apc'):
    protected.extend(p for p in (r/'Assets/materials/forestbase'/folder).iterdir() if p.is_file() and p.suffix in ('.png','.vmat'))
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
for name in ('forestbase_truck.py','forestbase_truck041.py','forestbase_map.py'):
    py_compile.compile(str(r/'Tools'/name),doraise=True)
def put(source,target):
    temporary=target.with_name(target.name+'.shelter-truck-pending')
    shutil.copy2(source,temporary);os.replace(temporary,target)
    assert source.read_bytes()==target.read_bytes()
for ext in ('.obj','.mtl','.vmdl'):put(out/('motor'+ext),dest/('motor'+ext))
layout=r/'output/forestbase/layout.json';shutil.copy2(layout,out/'layout.before.json')
data=json.loads(layout.read_text());data['stats']['motor']['triangles']=audit['trianglesAfter'];layout.write_text(json.dumps(data,indent=2))
for p,hash in hashes.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==hash,'Protected source changed: '+p
installed=[dest/('motor'+ext) for ext in ('.obj','.mtl','.vmdl')]
integration={'editorUsed':False,'engineCompileVerified':False,'offlinePreview':'truck-preview.png','audit':audit,
             'allOtherFacesAndPhysicsPreserved':True,'otherTruckAndAPCMaterialsPreserved':True,'newTextureSources':0,
             'installed':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in installed},'protectedHashes':hashes}
(out/'integration.json').write_text(json.dumps(integration,indent=2))
print(json.dumps({'truckReplaced':1,'motorTriangles':audit['trianglesAfter'],'editorUsed':False,'engineCompileVerified':False},indent=2))
