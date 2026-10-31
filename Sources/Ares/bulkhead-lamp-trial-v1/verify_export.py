"""Check the delivered GLB and prove original HC1 files are untouched."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
path=HERE/'bulkhead_lamp_after.glb';raw=path.read_bytes()
magic,version,size=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and version==2 and size==len(raw)
n,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
doc=json.loads(raw[20:20+n])
assert doc.get('meshes') and doc.get('materials') and doc.get('images')
assert not doc.get('cameras')
triangles=0
for mesh in doc['meshes']:
    for p in mesh['primitives']:
        assert p.get('mode',4)==4
        assert all(k in p['attributes'] for k in ('POSITION','NORMAL','TEXCOORD_0'))
        assert 'material' in p
        triangles+=doc['accessors'][p['indices']]['count']//3
assert all('bufferView' in image for image in doc['images']),'GLB has an external texture dependency'
assert 'KHR_materials_transmission' in doc.get('extensionsUsed',[])
guard=json.loads((HERE/'source-guard.json').read_text())
changed=[p for p,h in guard.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
assert not changed,changed
report={'asset':path.name,'bytes':len(raw),'meshes':len(doc['meshes']),
    'triangles':triangles,'materials':len(doc['materials']),'embeddedImages':len(doc['images']),
    'normalUVAndMaterialOnEveryPrimitive':True,'transmissiveLens':True,
    'externalTextureDependencies':False,'guardedOriginalFilesUnchanged':len(guard),
    'installed':False,'sha256':hashlib.sha256(raw).hexdigest()}
(ROOT/'output/asset-improvement-20261030/bulkhead-lamp/export-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
