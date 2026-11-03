"""Verify and record the exact installed cabinet without rebuilding the map."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,re
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/collider-tool-cabinet-accepted-20261031'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'Tools'))
import prepare_install as P
import map_kit as K,collider_map as M
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'plan.json').read_text());review=json.loads((HERE/'review.json').read_text())
for name,h in plan['protectedOtherFiles'].items():
    if name!='Tools/collider_map.py':assert sha(ROOT/name)==h,name
for name,h in plan['proposalSourceSHA256'].items():assert sha(ROOT/name)==h,name
source=ROOT/'Assets/models/maps/collider/collider_detail.obj'
before=OUT/'before/Assets/models/maps/collider/collider_detail.obj'
original=Counter(P.faces(before));removed=Counter(P.faces(P.TRIAL/'before.obj',P.ORIGIN));added=Counter(P.faces(P.TRIAL/'after.obj',P.ORIGIN))
assert Counter(P.faces(source))==original-removed+added
assert sum(original.values())==283193 and sum(added.values())==23646 and sum(removed.values())==2420
old_doc=(OUT/'before/Assets/models/maps/collider/collider_detail.vmdl').read_text()
doc=source.with_suffix('.vmdl').read_text();oldblocks=P.blocks(old_doc);current=P.blocks(doc)
oldbox=[b[0] for b in oldblocks if 'PhysicsShapeBox' in b[0] and np.allclose(P.values(b[0],'origin'),(160,650,26.5)) and np.allclose(P.values(b[0],'dimensions'),(80,42,47))]
assert len(oldbox)==1
unrelated=Counter(b[0] for b in oldblocks)-Counter(oldbox)
assert not unrelated-Counter(b[0] for b in current)
assert len(current)==len(oldblocks)-1+39+2
assert 'installed_hulls_rubber.obj' in doc and 'tool-cabinet-trial-v1/after_hulls_rubber.obj' not in doc
model=K.Model();M.hardcase(model,-650,160,0,80,42,50,0);M.configure(model)
assert sum(len(p)-2 for group in model.polygons.values() for p,n in group)==23646
assert len(model.boxes)==39 and len(model.hulls)==10 and len(model.material_overrides)==7
assert all(len(p)==32 for p,surface in model.hulls if surface=='rubber')
collision=json.loads((OUT/'native-collision.json').read_text());assert collision['Passed'] and collision['Count']==25
assert all(c['HitObject']=='Equipment and signs' for c in collision['Checks'] if c['ExpectedHit'])
assert all(c['Passed'] for c in collision['Checks'])
records=[];synchronized=[]
for record in plan['files']:
    target=ROOT/record['path'];stage=OUT/'stage'/record['path'];assert sha(target)==sha(stage)
    current_record={**record,'after':sha(target)};records.append(current_record)
    primary=ROOT/'output/collider/stage'/record['path'].removeprefix('Assets/')
    # Primary staging uses assets/models/...; update only if it still matches the archived baseline.
    primary=ROOT/'output/collider/stage/assets'/record['path'].removeprefix('Assets/')
    if primary.exists() and sha(primary)==record['before']:
        primary.write_bytes(target.read_bytes());synchronized.append(primary.relative_to(ROOT).as_posix())
result={**plan,'status':'accepted-installed-in-map','installedInMap':True,'originalRetained':False,
    'originalAvailableInRollback':True,'files':records,'userApproved':True,'engineCompilation':'compiled-and-up-to-date',
    'nativePhysicsChecks':25,'nativePhysicsPassed':True,'sceneFileUnchanged':True,'unrelatedRenderTrianglesUnchanged':True,
    'unrelatedPhysicsBlocksUnchanged':True,'visibleApprovedMeshUnchanged':True,
    'tyreCollisionSimplification':json.loads((OUT/'hull-fix.json').read_text()),
    'installedTyreHullSHA256':sha(ROOT/'Assets/models/props/collider/tool-cabinet-trial-v1/installed_hulls_rubber.obj'),
    'generator':{'path':'Tools/collider_map.py','sha256':sha(ROOT/'Tools/collider_map.py'),
                 'helper':'Tools/collider_tool_cabinet.py','helperSHA256':sha(ROOT/'Tools/collider_tool_cabinet.py'),
                 'physicsSHA256':sha(HERE/'accepted-physics.json'),'exactSelectedBranchVerified':True},
    'nativeScreenshot':{'path':(OUT/'installed.png').relative_to(ROOT).as_posix(),'sha256':sha(OUT/'installed.png'),
                        'scope':'Native offscreen rendering of saved Collider visual objects; active play session not edited'},
    'primaryStageSynchronized':synchronized}
for path in (HERE/'installed.json',OUT/'installed.json'):path.write_text(json.dumps(result,indent=2)+'\n')
review.update(status='accepted-installed-in-map',installedInMap=True,userApproved=True,originalRetained=False,
              originalAvailableInRollback=True,nativeInstallation=result)
for path in (HERE/'review.json',ROOT/'output/asset-improvement-20261030/tool-cabinet/review.json'):
    path.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','removedTriangles','addedTriangles','detailTrianglesAfter','nativePhysicsChecks','sceneFileUnchanged','unrelatedRenderTrianglesUnchanged','unrelatedPhysicsBlocksUnchanged')}))
