"""Verify the installed mesh delta, immutable physics and completed native QA."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,ast,re
import native
sys.path.insert(0,str(native.ROOT/'Tools'))
import riverdale_splice as S
import ares_interior as I
ROOT=native.ROOT;OUT=native.OUT
manifest=json.loads((OUT/'manifest.json').read_text());plan=json.loads((OUT/'install-plan.json').read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
for row in plan:
    assert sha((ROOT/row['relative']).read_bytes())==row['after'],f'Installed file changed: {row["relative"]}'
assert sha((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_bytes())==manifest['scene_sha256']
report=[]
for item in manifest['models']:
    name=item['name'];before=Counter(S.read_obj(OUT/'before'/item['primary'])[1])
    removed=Counter(S.read_obj(OUT/f'{name}-removed.obj')[1]);added=Counter(S.read_obj(OUT/f'{name}-added.obj')[1])
    current=Counter(S.read_obj(ROOT/item['primary'])[1]);kept=before-removed;restyled=Counter()
    count=0
    for (material,corners),n in kept.items():
        points=[list(map(float,p.split())) for p,uv,nrm in corners]
        if name=='ares_hall' and material=='ar_hazard' and all(208-1e-3<=p[1]<=214+1e-3 and abs(p[0])<=1101 and -721<=p[2]<=765 for p in points):
            restyled[(I.FRAME,corners)]+=n;count+=n
        else:restyled[(material,corners)]+=n
    assert current==restyled+added,name+' contains an unexpected geometry edit'
    original=(OUT/'before'/item['document']).read_bytes().decode('utf-8')
    document=(ROOT/item['document']).read_bytes().decode('utf-8')
    marker='_class = "PhysicsShapeList"'
    assert original[original.index(marker):]==document[document.index(marker):],name+' physics differs'
    assert re.findall(r'filename\s*=\s*"([^"]+)"',original)==re.findall(r'filename\s*=\s*"([^"]+)"',document)
    assert 'interior-v1/ares_' not in document
    report.append(dict(Model=name,UnexpectedGeometryChanges=0,PreservedTriangles=sum(kept.values()),
        RestyledToeTriangles=count,RemovedTriangles=sum(removed.values()),AddedTriangles=sum(added.values()),
        PhysicsBytesPreserved=True,ExistingImportsPreserved=True))
for path in ('Tools/ares_map.py','Tools/ares_interior.py'):ast.parse((ROOT/path).read_text())
capture=json.loads((OUT/'capture-installed.json').read_text())
assert capture['UserStatePreserved'] and not capture['ErrorModels']
assert len(capture['HallMaterials'])==6
assert json.loads((OUT/'source-collision-verification.json').read_text())['Identical']
result=dict(Installed=True,Models=report,SourceSceneUnchanged=True,GeneratedCollisionIdentical=True,
            NativeErrorModels=0,NativeUserStatePreserved=True,CompiledModels=2)
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
