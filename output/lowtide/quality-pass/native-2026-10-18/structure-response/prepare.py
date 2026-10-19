import hashlib
import json
from pathlib import Path
import uuid

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
stage=OUT/'stage'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.suffix in ('.vmat','.shader'))
assert len(files)==3
for rel in files:
    p=Path(str(stage/rel)+'.meta')
    p.write_text(json.dumps(dict(guid=str(uuid.uuid5(uuid.NAMESPACE_URL,rel))),indent=2)+'\n')
files=sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
assert all(not (ROOT/'Assets'/p).exists() for p in files), 'Inspect existing destination before importing'
protected=['Assets/scenes/maps/Lowtide/lowtide.scene','Assets/materials/lowtide/lt_timber.vmat','Assets/materials/buildings/iron_black.vmat']
protected += ['Assets/models/maps/lowtide/lowtide_'+side+suffix for side in ['east','west'] for suffix in ['.obj','.vmdl']]
protected += ['Assets/'+p for p in ['materials/railhead/rw_wood_color.png','materials/railhead/wood_normal.png','materials/railhead/wood_rough.png','materials/railhead/wood_ao.png','materials/buildings/iron_black_color.png','materials/buildings/iron_normal.png','materials/buildings/iron_rough.png']]
data=dict(assets={p:sha(stage/p) for p in files},protected={p:sha(ROOT/p) for p in protected},status='unbound_native_review_candidate')
(OUT/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(dict(files=len(files),protected=len(protected))))
