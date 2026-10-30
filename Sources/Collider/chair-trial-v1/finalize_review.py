"""Record the completed, verified actual-mesh comparison for user review."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/chair'
ASSET=ROOT/'Assets/models/props/collider/chair-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
verification=json.loads((OUT/'verification.json').read_text())
render=json.loads((OUT/'render-report.json').read_text())
assert not render['nativeEngineScreenshot'] and render['sameCameraLightingScaleAndExposure']
assert len(render['images'])==2
for name,record in manifest['models'].items():
    assert sha(ASSET/(name+'.obj'))==record['meshSHA256']==verification['variants'][name]['meshSHA256']
for path,expected in manifest['protectedSourceSHA256'].items():assert sha(ROOT/path)==expected,path
for view in ('main',):
    pair=[next(i for i in render['images'] if i['view']==view and i['variant']==v) for v in ('before','after')]
    for key in ('eyeMetres','targetMetres','lens','width','height'):assert pair[0][key]==pair[1][key]
    for record in pair:assert sha(OUT/record['file'])==record['sha256'],record['file']
result={'status':'ready-for-user-review','installedInMap':False,'editorUsed':False,
    'engineValidation':'pending','renderSessionExited':True,'renderEvidence':render,
    'geometryVerification':verification,'modelSourceSHA256':{k:v['meshSHA256'] for k,v in manifest['models'].items()}}
(Path(__file__).parent/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'reviewReady':True,'images':len(render['images']),'candidateInstalled':False,
    'afterTriangles':manifest['models']['after']['triangles'],'engineValidation':'pending'}))
