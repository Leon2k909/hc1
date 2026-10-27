import collections
import json
from pathlib import Path

root=Path(__file__).resolve().parents[3]
out=root/'output/ares/crate-v2'
before=json.loads((out/'stage-v5/before/Assets/scenes/maps/Ares/ares.scene').read_text())
after=json.loads((root/'Assets/scenes/maps/Ares/ares.scene').read_text())
diffs=json.loads((out/'scene-diff-without-cases.json').read_text())

def parent(path,doc):
    parts=path.split('/')[1:]
    value=doc
    for key in parts[:-1]:
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value,parts[-1]

groups=collections.Counter()
changes=collections.defaultdict(list)
for path,a,b in diffs:
    p,key=parent(path,after)
    kind=p.get('__type',p.get('Name','')) if isinstance(p,dict) else ''
    if a is None:
        groups[(kind,key,json.dumps(b,sort_keys=True))]+=1
    elif b is not None:
        changes[key].append((a,b))
for (kind,key,value),count in groups.items():
    print('ADD',count,kind or '<metadata>',key,value[:250])
for key,rows in changes.items():
    unique=list(dict.fromkeys((json.dumps(a),json.dumps(b)) for a,b in rows))
    print('CHANGE',key,len(rows),'unique',len(unique),unique[:3])
