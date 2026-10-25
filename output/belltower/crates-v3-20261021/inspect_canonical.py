"""Read only: ensure concurrent authoring updates retained the crate group."""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT/'Tools'))
import belltower_stage_market_crates_v3 as S
import belltower_market_crates_v3 as M
import belltower_crates as C
import belltower_map as B
import map_kit as K

def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def faces(path, wanted=None):
    points = {p for mat, face in wanted for p in face} if wanted else None
    sparse = {}; count = 0; material = None; result = Counter()
    for line in path.open('rb'):
        if line.startswith(b'v '):
            count += 1
            p = S.pos(line[2:].decode())
            if points is None or p in points: sparse[count] = p
        elif line.startswith(b'usemtl '): material = line.split()[1]
        elif line.startswith(b'f '):
            ids = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in ids):
                key = (material, frozenset(sparse[i] for i in ids))
                if wanted is None or key in wanted: result[key] += 1
    return result

old = K.Model()
for origin, x, size in M.OLD_ROWS:
    C.build(old, B.Place(origin, math.degrees(math.atan2(x[1], x[0]))), size)
parser = argparse.ArgumentParser()
parser.add_argument('--side', choices=['west', 'east'])
args = parser.parse_args()
report_path = OUT/'canonical-check.json'
result = json.loads(report_path.read_text()) if report_path.exists() else {}
for side in ((args.side,) if args.side else ('west', 'east')):
    previous = S.keys(old if side == 'west' else old.mirrored())
    candidate = faces(ROOT/f'Assets/models/maps/belltower/market-crates-v3/{side}.obj')
    source = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
    before = sha(source)
    actual = faces(source, previous+candidate)
    assert before == sha(source), 'The authoring file changed during inspection.'
    result[side] = {'sha256': before, 'old_faces_present': sum((actual & previous).values()),
                    'new_faces_present': sum((actual & candidate).values()), 'new_faces_expected': sum(candidate.values())}
    print(json.dumps({side: result[side]}), flush=True)
    report_path.write_text(json.dumps(result, indent=2)+'\n')
