from pathlib import Path
import json,hashlib,shutil
root=Path(__file__).resolve().parents[3]
stage=root/'output/belltower/quality/forest-v1-staging'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shader=root/'Sources/Belltower/shaders/belltower_forest.shader'
shutil.copy2(shader,stage/'Assets/shaders/belltower_forest.shader')
entries=json.loads((stage/'import.json').read_text())
for x in entries:
    x['sha256']=sha(root/x['source'])
    target=root/'Assets'/x['path']
    x['expected_sha256']=sha(target) if target.exists() else None
(stage/'import.json').write_text(json.dumps(entries,indent=2)+'\n')
manifest=json.loads((stage/'manifest.json').read_text())
manifest['shader_sha256']=sha(shader)
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Updated guarded forest asset hashes.')
