"""Count staged geometry off the editor thread, tied to the imported mesh hashes."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

stage=Path('output/belltower/quality/models/facades-v1')
manifest=json.loads((stage/'native-import.json').read_text())
records=[]
for model in manifest['models']:
    path=stage/(model['name']+'.obj')
    fingerprint=sha256(path.read_bytes()).hexdigest()
    matching=next(f for f in manifest['files'] if Path(f['source']).name==path.name)
    assert fingerprint==matching['sha256']
    counts=Counter()
    material=None
    for line in path.open(encoding='utf-8'):
        if line.startswith('usemtl '): material=line.strip().split()[1]
        elif line.startswith('f '): counts[material]+=len(line.split())-3
    assert sum(counts.values())==model['triangles']
    records.append({'name':model['name'],'sha256':fingerprint,'triangles':sum(counts.values()),'first_material':'ashlar','first_material_triangles':counts['ashlar']})
result={'manifest_sha256':sha256((stage/'native-import.json').read_bytes()).hexdigest(),'models':records}
(stage/'source-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
