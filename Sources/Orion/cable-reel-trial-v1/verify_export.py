"""Validate the isolated reel export and exact preservation of original files."""
from pathlib import Path
import hashlib,json,struct
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
p=HERE/'cable_reel_after.glb';raw=p.read_bytes();magic,version,size=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and version==2 and size==len(raw)
n,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
doc=json.loads(raw[20:20+n]);assert len(doc.get('meshes',[]))==1 and not doc.get('cameras')
triangles=0
for mesh in doc['meshes']:
    for primitive in mesh['primitives']:
        assert primitive.get('mode',4)==4
        assert all(k in primitive['attributes'] for k in ('POSITION','NORMAL','TEXCOORD_0'))
        if 'material' not in primitive:
            print(json.dumps({'unassignedTriangles':doc['accessors'][primitive['indices']]['count']//3,
                'availableMaterials':[m.get('name') for m in doc.get('materials',[])]}))
        assert 'material' in primitive
        triangles+=doc['accessors'][primitive['indices']]['count']//3
assert all('bufferView' in image for image in doc['images'])
guard=json.loads((HERE/'source-guard.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
record={'asset':p.name,'bytes':len(raw),'meshes':len(doc['meshes']),'triangles':triangles,
    'materials':len(doc['materials']),'embeddedImages':len(doc['images']),'externalTextureDependencies':False,
    'everyPrimitiveHasNormalsUVsMaterial':True,'protectedOriginalsUnchanged':len(guard),
    'installed':False,'sha256':hashlib.sha256(raw).hexdigest()}
(ROOT/'output/asset-improvement-20261030/orion-cable-reel/export-validation.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
