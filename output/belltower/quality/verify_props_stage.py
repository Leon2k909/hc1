"""Record the actual publication boundary for the furniture pass."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/belltower/quality'
BEFORE=OUT/'before-props-v1'
def digest(path,kind='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,kind).hexdigest()

staged=json.loads((OUT/'model-import.json').read_text())
assert staged['spots']==94 and staged['invalid_spots']==0 and staged['unreachable_spots']==0
protected=[]
for old in (BEFORE/'Assets/models/maps/belltower').glob('*_hulls_*.obj'):
    current=ROOT/old.relative_to(BEFORE)
    assert digest(old)==digest(current),current
    protected.append(str(current.relative_to(ROOT)))
scene=Path('Assets/scenes/maps/Belltower/belltower.scene')
assert digest(BEFORE/scene)==digest(ROOT/scene)
scans=json.loads((ROOT/'Sources/Belltower/scans/manifest.json').read_text())
wood=next(a for a in scans['assets'] if a['id']=='brown_planks_03')
for record in wood['files'].values():
    assert digest(ROOT/'Assets'/record['path'],'md5')==record['md5']
files={f['path']:{'staged':digest(ROOT/f['source']), 'installed':digest(ROOT/'Assets'/f['path'])}
       for f in staged['files']}
report={
    'status':'staged; native model/material import and visual review pending',
    'gameplaySpots':94,'invalidSpots':0,'unreachableSpots':0,
    'collisionUnchanged':protected,'sceneUnchanged':digest(ROOT/scene),
    'originalWoodMapsVerified':len(wood['files']),
    'models':staged['models'],'files':files,
    'allNewModelsStillStaged':all(x['staged']!=x['installed'] for x in files.values()),
    'nativeBeforeViews':['props-v1-viewport-before/cart','props-v1-viewport-before/bench'],
    'newModelsReviewedInEngine':False,
    'lighting':'daylight-v7; furniture revision has not been rebaked'
}
(OUT/'props-v1-stage-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('files','collisionUnchanged')},indent=2))
