"""Stage the single duplicate separator fix without changing imported meshes."""
import copy
import json
import re
import shutil
import belltower_stage_stone_wear as S

source = S.OUT/'props-rebase-v6/manifest.json'
report = copy.deepcopy(json.loads(source.read_text()))
stage = S.OUT/'props-syntax-v7'
assert not stage.exists()
stage.mkdir()
files = {}
for side in ('west', 'east', 'centre'):
    relative = f'Assets/models/maps/belltower/belltower_{side}.vmdl'
    current = S.ROOT/relative
    raw = current.read_bytes()
    pattern = rb'},,([\r\n\s]*{[\r\n\s]*_class = "RenderMeshFile"[\r\n\s]*name = "stone_wear_'+side.encode()+rb'")'
    corrected, count = re.subn(pattern, rb'},\1', raw)
    assert count == 1, (side, count)
    a, b = S.span(raw.decode(), '_class = "PhysicsShapeList"')
    c, d = S.span(corrected.decode(), '_class = "PhysicsShapeList"')
    assert raw.decode()[a:b] == corrected.decode()[c:d]
    assert re.findall(rb'filename\s*=\s*"([^"]+\.obj)"', raw) == re.findall(rb'filename\s*=\s*"([^"]+\.obj)"', corrected)
    target = stage/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(corrected)
    backup = stage/'before'/relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(current, backup)
    files[relative] = {'before': S.sha(current), 'after': S.sha(target),
                       'source': target.relative_to(S.ROOT).as_posix(),
                       'backup': backup.relative_to(S.ROOT).as_posix()}
report['files'] = files
report['repair_of'] = 'props-rebase-v6'
report['repair'] = 'Remove one duplicate comma immediately preceding each stone_wear render import.'
report['source_sha256']['Tools/belltower_stage_stone_wear.py'] = S.sha(S.ROOT/'Tools/belltower_stage_stone_wear.py')
report['source_sha256']['Tools/belltower_repair_stone_modeldoc.py'] = S.sha(S.ROOT/'Tools/belltower_repair_stone_modeldoc.py')
for relative, item in files.items():
    assert S.sha(S.ROOT/relative) == item['before'] == S.sha(S.ROOT/item['backup'])
for group in ('source_sha256', 'protected_sha256'):
    for relative, digest in report[group].items():
        assert S.sha(S.ROOT/relative) == digest, relative
(stage/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
(S.OUT/'native-import-v6.json').write_bytes((S.OUT/'native-import.json').read_bytes())
(S.OUT/'import-request.json').write_text(json.dumps({'stage': stage.name})+'\n')
print(json.dumps({'stage': stage.name, 'model_files': len(files), 'physics_and_imports_exact': True}))
