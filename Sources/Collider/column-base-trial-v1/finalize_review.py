"""Bind the actual-mesh base comparison to its isolated source proposal."""
from pathlib import Path
import hashlib,json,subprocess,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/column-base'
ASSET=ROOT/'Assets/models/props/collider/column-base-trial-v1';MD=ROOT/'Assets/materials/collider/column-base-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,'-X','utf8',str(HERE/'verify.py')],cwd=ROOT,check=True)
d=json.loads((OUT/'manifest.json').read_text());render=json.loads((OUT/'render-report.json').read_text())
process=json.loads((OUT/'render-process.json').read_text())
assert process['exitCode']==0 and process['renderProcessStopped'] and not process['gpuRendering']
assert process['priority']=='idle' and process['threads']==2 and len(process['cpuAffinity'])==2
assert render['sameCameraLightingScaleAndExposure'] and render['sameActualColumnContext']
assert not render['nativeEngineScreenshot'] and render['contextMeshSHA256']==d['contextMeshSHA256']
for name,record in d['models'].items():assert render['modelSourceSHA256'][name]==record['meshSHA256']
images=render['images'];assert len(images)==2
assert {i['variant'] for i in images}=={'before','after'}
for key in ('view','eyeMetres','targetMetres','lens','width','height'):assert images[0][key]==images[1][key]
for i in images:
    path=OUT/i['file'];assert sha(path)==i['sha256']
    with Image.open(path) as img:assert img.size==(1400,1050);img.verify()
files=[p for folder in (ASSET,MD) for p in folder.iterdir() if p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')]
review={'status':'preview-ready-awaiting-user-approval','userApproved':False,'installedInMap':False,'oldAssetRetained':True,
    'editorUsed':False,'engineCompilation':'pending','nativeAppearanceLODsAndPerformance':'pending',
    'baseline':d['baseline'],'models':d['models'],
    'proposalSourceSHA256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)},
    'protectedSourceSHA256':d['protectedSourceSHA256'],'verification':json.loads((OUT/'verification.json').read_text()),
    'render':render,'renderProcess':process,'framing':json.loads((OUT/'framing.json').read_text())}
for path in (HERE/'review.json',OUT/'review.json'):path.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'oldAssetRetained':True,'installedInMap':False,'sourceFiles':len(files)}))
