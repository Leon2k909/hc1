"""Rebase only the two model resources onto an independent concurrent fix."""
import copy
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT/'Tools'))
import belltower_stage_market_crates_v3 as S
import belltower_market_crates_v3 as M
import belltower_map as B
import map_kit as K

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
m = json.loads((OUT/'stage-compact/manifest.json').read_text())
for group in ('source_sha256', 'protected_sha256'):
    for name, digest in m[group].items(): assert sha(ROOT/name) == digest, name
for name, row in m['files'].items():
    if name.endswith('.vmdl'): continue
    assert (sha(ROOT/name) if (ROOT/name).exists() else None) == row['before'], name
S.STAGE = OUT/'stage-native'
assert not S.STAGE.exists()
S.STAGE.mkdir()
old, new = K.Model(), K.Model()
for index, (origin, x, size) in enumerate(M.OLD_ROWS):
    yaw = math.degrees(math.atan2(x[1], x[0]))
    destination, angle = M.location(index, yaw)
    h = size/2
    B.Place(origin, yaw).box(old, (-h,-h,0), (h,h,size), None, B.WOOD)
    B.Place(destination, angle).box(new, (-h,-h,0), (h,h,size), None, B.WOOD)
for side in ('west', 'east'):
    name = f'Assets/models/maps/belltower/belltower_{side}.vmdl'
    source = ROOT/name
    before = sha(source)
    S.patch_vmdl(source, old if side == 'west' else old.mirrored(),
                 new if side == 'west' else new.mirrored(),
                 f'models/maps/belltower/market-crates-v3/{side}.obj', side)
    assert sha(source) == before
    backup = OUT/'before-native'/name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, backup)
    target = S.STAGE/name
    m['files'][name] = {'source': target.relative_to(ROOT).as_posix(), 'before': before,
                        'after': sha(target), 'backup': backup.relative_to(ROOT).as_posix()}
m['rebase_note'] = 'Preserve the concurrent comma fix before the existing shop awning nodes in both model resources.'
(S.STAGE/'manifest.json').write_text(json.dumps(m, indent=2)+'\n')
print(json.dumps({'rebased_resources': 2, 'total_guarded_files': len(m['files'])}))
