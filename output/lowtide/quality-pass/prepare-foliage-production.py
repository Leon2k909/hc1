from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import lowtide_trees as TREES

folder = ROOT / 'output/lowtide/quality-pass/foliage'
source = TREES.SOURCE / 'production'
assert not source.exists(), 'Production source already prepared; inspect before retrying'
source.mkdir()
for relative in (TREES.SHADER, TREES.INPUTS):
    shutil.copy2(folder / 'v2-stage' / relative, source / Path(relative).name)
data = (folder / 'v2-stage' / TREES.MATERIAL).read_bytes()
old = b'g_flTintColor "[1 1 1]"'
assert data.count(old) == 1
data = data.replace(old, b'g_flTintColor "[.48 .66 .54]"')
(source / Path(TREES.MATERIAL).name).write_bytes(data)

stage = folder / 'production-stage'
written = TREES.write_assets(stage)
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
changes = {}
for target in written:
    relative = target.relative_to(stage).as_posix()
    live = ROOT / 'Assets' / relative
    changes[relative] = {'before': hashfile(live) if live.exists() else None, 'after': hashfile(target)}
old = json.loads((folder / 'v2-manifest.json').read_text())
scene = ROOT / 'Assets/scenes/maps/Lowtide/lowtide.scene'
shutil.copy2(scene, folder / 'production-scene-before.scene')
(folder / 'production-manifest.json').write_text(json.dumps({
    'changes': changes, 'protected': old['protected'], 'scene_before_sha256': hashfile(scene),
    'material': TREES.MATERIAL, 'shader': TREES.SHADER, 'tint': [.48, .66, .54],
    'status': 'Visually accepted in three guarded viewport comparisons; native persistent application pending.'
}, indent=2) + '\n')
print(json.dumps({'files': len(changes), 'changed_files': [k for k,v in changes.items() if v['before'] != v['after']]}))
