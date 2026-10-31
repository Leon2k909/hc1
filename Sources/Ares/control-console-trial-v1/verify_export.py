"""Validate the private candidate GLB and check all protected originals."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
path=HERE/'control_console_after.glb';raw=path.read_bytes()
magic,version,size=struct.unpack_from('<4sII',raw);assert magic==b'glTF' and version==2 and size==len(raw)
n,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
doc=json.loads(raw[20:20+n]);assert len(doc.get('meshes',[]))==1
assert not doc.get('cameras');assert doc.get('materials') and doc.get('images')
triangles=0
for mesh in doc['meshes']:
    for p in mesh['primitives']:
        assert p.get('mode',4)==4
        assert all(k in p['attributes'] for k in ('POSITION','NORMAL','TEXCOORD_0'))
        assert 'material' in p
        triangles+=doc['accessors'][p['indices']]['count']//3
assert all('bufferView' in image for image in doc['images'])
guard=json.loads((HERE/'source-guard.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
original=ROOT/'Assets/materials/ares/ar_screens_color.png';cloned=HERE/'textures/ar_screens_color.png'
assert original.read_bytes()==cloned.read_bytes()
report={'asset':path.name,'bytes':len(raw),'meshes':len(doc['meshes']),'triangles':triangles,
    'materials':len(doc['materials']),'embeddedImages':len(doc['images']),
    'everyPrimitiveHasNormalsUVsMaterial':True,'externalTextureDependencies':False,
    'originalScreenAtlasByteIdentical':True,'protectedOriginalFilesUnchanged':len(guard),
    'installed':False,'sha256':hashlib.sha256(raw).hexdigest()}
(ROOT/'output/asset-improvement-20261030/ares-control-console/export-validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
