"""Stage a fresh path for the repaired base, bypassing a mapped old OBJ cache."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
from belltower_safe_imports import span


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


out = ROOT/'output/veridant/chair-v2'
previous = json.loads((out/'stage-v7/manifest.json').read_text())
for relative,data in previous['files'].items():
    assert sha(ROOT/relative) == data['after'], ('Shared edit changed',relative)
stage = out/'stage-v8'
assert not stage.exists()
stage.mkdir()
base = Path('Assets/models/maps/veridant/lounger-v2/veridant_dress-base.obj')
fresh = Path('Assets/models/maps/veridant/chair-v2/dress-base.obj')
mtl_name = next(l.split(maxsplit=1)[1].strip() for l in (ROOT/base).read_text().splitlines() if l.startswith('mtllib '))
vmdl = Path('Assets/models/maps/veridant/veridant_dress.vmdl')
original = (ROOT/vmdl).read_text()
updated = original.replace(base.relative_to('Assets').as_posix(),fresh.relative_to('Assets').as_posix())
assert updated != original
a,b = span(original,'_class = "PhysicsShapeList"')
c,d = span(updated,'_class = "PhysicsShapeList"')
assert original[a:b] == updated[c:d]
for destination,source in ((fresh,base),(fresh.parent/mtl_name,base.parent/mtl_name)):
    target = stage/destination
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/source,target)
target = stage/vmdl
target.parent.mkdir(parents=True,exist_ok=True)
target.write_text(updated)
files = {}
for relative in (fresh,fresh.parent/mtl_name,vmdl):
    current = ROOT/relative
    old_hash = sha(current) if current.exists() else None
    if old_hash:
        backup = stage/'before'/relative
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(current,backup)
    files[relative.as_posix()] = {'before':old_hash,'after':sha(stage/relative),
                                 'source':(stage/relative).relative_to(ROOT).as_posix()}
manifest = {**previous,'files':files,'geometry_stage':'stage-v7','fresh_base':fresh.as_posix()}
manifest['protected'] = {**previous['protected'],base.as_posix():sha(ROOT/base)}
(stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'capture-request.json').write_text(json.dumps({'phase':'final','stage':'stage-v8'}))
print(json.dumps({'files':list(files),'physics_unchanged':True,'base_bytes_identical':True}))
