"""Check additional explanatory renders without changing the approved source proposal."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
PARENT=ROOT/'output/asset-improvement-20261030/column-base';OUT=PARENT/'base-only-review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
review=json.loads((HERE/'review.json').read_text())
for path,h in review['proposalSourceSHA256'].items():assert sha(ROOT/path)==h,path
for path,h in review['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
r=json.loads((OUT/'render-report.json').read_text());p=json.loads((OUT/'render-process.json').read_text())
assert r['columnHiddenForClarity'] and r['contextTrianglesShown']==0 and not r['nativeEngineScreenshot']
assert r['sameCameraLightingScaleAndExposure'] and r['renderDevice']=='CPU'
assert p['exitCode']==0 and p['renderProcessStopped'] and p['priority']=='idle' and p['threads']==2 and not p['gpuRendering']
assert len(r['images'])==2
for name,record in review['models'].items():assert r['modelSourceSHA256'][name]==record['meshSHA256']
a,b=r['images'];assert {a['variant'],b['variant']}=={'before','after'}
for key in ('view','eyeMetres','targetMetres','lens','width','height'):assert a[key]==b[key],key
for i in r['images']:
    path=OUT/i['file'];assert sha(path)==i['sha256']
    with Image.open(path) as img:assert img.size==(1400,1050);img.verify()
result={'originalAndProposalSourcesUnchanged':True,'allAcceptedUpgradesPreserved':True,
    'columnHiddenInBothViewsForClarity':True,'matchingCameraLightingScaleAndExposure':True,
    'editorUsed':False,'renderProcessStopped':True,'installedInMap':False,'images':r['images']}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
for path in (HERE/'review.json',PARENT/'review.json'):
    d=json.loads(path.read_text());d['additionalComponentOnlyComparison']='output/asset-improvement-20261030/column-base/base-only-review/verification.json'
    path.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='images'}))
