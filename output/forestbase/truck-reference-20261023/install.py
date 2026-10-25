"""File-only installation authorized by the user's no-editor constraint."""
from pathlib import Path
import os,json,hashlib,shutil
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
report=json.loads((out/'audit.json').read_text());dest=r/'Assets/models/maps/forestbase'
for name in report:
    for ext in ('.obj','.mtl','.vmdl'):
        assert (dest/(name+ext)).read_bytes()==(out/(name+'.before'+ext)).read_bytes(),f'Concurrent change: {name+ext}'
        if ext=='.vmdl':
            a=(out/(name+ext)).read_text();b=(dest/(name+ext)).read_text();marker='_class = "PhysicsShapeList"'
            assert a[a.index(marker):]==b[b.index(marker):]
def put(src,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.truck-pending')
    shutil.copy2(src,temporary);os.replace(temporary,target)
mat=r/'Assets/materials/forestbase/truck'
for ext in ('.png','.vmat'):
    for p in (out/'materials').glob('*'+ext):put(p,mat/p.name)
for name in report:
    for ext in ('.mtl','.obj','.vmdl'):put(out/(name+ext),dest/(name+ext))
layout=r/'output/forestbase/layout.json'
if layout.exists():
    data=json.loads(layout.read_text())
    for name,row in report.items():data['stats'][name]['triangles']=row['trianglesAfter']
    layout.write_text(json.dumps(data,indent=2))
integration={'editorUsed':False,'engineCompileVerified':False,'offlinePreview':'truck-preview.png',
             'trucksReplaced':sum(x['trucks'] for x in report.values()),'allOtherFacesUnchanged':True,'allPhysicsUnchanged':True,
             'chunks':report,'installed':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for name in report for p in [dest/(name+'.obj'),dest/(name+'.vmdl')]}}
(out/'integration.json').write_text(json.dumps(integration,indent=2))
print('Installed source files for four trucks. No editor used. Engine verification deferred.')
