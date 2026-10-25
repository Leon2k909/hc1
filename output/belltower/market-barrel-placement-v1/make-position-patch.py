"""Extract the verified barrel translations without snapshotting shared models."""
import collections
import itertools
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).resolve().parent
template = json.loads((folder/'r4/manifest.json').read_text())
patch = {'files': {}, 'models': template['models']}
for name, row in template['files'].items():
    mapping = {}
    counts = collections.Counter()
    before = root/row['backup'].replace('/r4/', '/r6/')
    after = root/row['source'].replace('/r4/', '/r6/')
    side = 'west' if '/west/' in name or 'belltower_west' in name else 'east'
    offsets = [[-p['new'][0]+p['old'][0],0.,p['new'][1]-p['old'][1]]
               for p in template['models'][side]['translations']]
    with before.open('rb') as a, after.open('rb') as b:
        for old, new in itertools.zip_longest(a,b):
            assert old is not None and new is not None
            if old == new:
                continue
            assert old.startswith(b'v ') and new.startswith(b'v ')
            assert b'\r' not in old and b'\r' not in new and old.endswith(b'\n') and new.endswith(b'\n')
            delta = [y-x for x,y in zip(map(float,old.split()[1:]),map(float,new.split()[1:]))]
            assert len(delta)==3 and any(max(abs(x-y) for x,y in zip(delta,v)) < .0021 for v in offsets)
            key,value = old.decode().rstrip('\n'),new.decode().rstrip('\n')
            if key in mapping:
                assert mapping[key]==value
            mapping[key]=value
            counts[key]+=1
    assert sum(counts.values())==row['moved_position_rows']
    patch['files'][name] = {'positions':mapping,'occurrences':dict(counts),'changed_rows':sum(counts.values())}
(folder/'position-patch.json').write_text(json.dumps(patch,separators=(',',':'))+'\n')
print(json.dumps({'files':len(patch['files']),'selected_position_rows':sum(p['changed_rows'] for p in patch['files'].values())}))
