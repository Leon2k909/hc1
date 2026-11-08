import json
from pathlib import Path
from collections import Counter
ROOT=Path.cwd()
def walk(xs):
    for x in xs:
        yield x
        yield from walk(x.get('Children',[]))
report=[]
for path in (ROOT/'Assets/scenes/maps').rglob('*.scene'):
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    roots=data.get('GameObjects',[])
    doors=[]
    for x in walk(roots):
        cs=x.get('Components',[])
        types=[c.get('__type','') for c in cs]
        if 'door' in x.get('Name','').lower() or any('door' in t.lower() for t in types):
            doors.append({'name':x.get('Name'),'position':x.get('Position'),'types':types})
    report.append({'scene':path.relative_to(ROOT).as_posix(),'roots':[x.get('Name',x.get('__Prefab')) for x in roots], 'doors':doors})
dest=Path(__file__).with_name('inventory.json')
dest.write_text(json.dumps(report,indent=2))
for r in report:
    print(r['scene'], 'usable:',dict(Counter(t for d in r['doors'] for t in d['types'] if 'door' in t.lower())), 'door-named:',len(r['doors']))
    if any(n in r['scene'].lower() for n in ['veridant','cerro','reefhall','spillway']):
        print('  visual roots:',r['roots'][:24])
