"""Bind the completed actual-mesh comparison to the private source proposal."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/cooling-unit'
ASSET=ROOT/'Assets/models/props/collider/cooling-unit-trial-v1';MD=ROOT/'Assets/materials/collider/cooling-unit-trial-v1'
assert not (ROOT/'output/collider-cooling-unit-accepted-20261030/installed.json').exists(),'Already accepted: use verify_accepted.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,'-X','utf8',str(HERE/'verify.py')],cwd=ROOT,check=True)
manifest=json.loads((OUT/'manifest.json').read_text());render=json.loads((OUT/'render-report.json').read_text())
process=json.loads((OUT/'render-process.json').read_text());framing=json.loads((OUT/'framing.json').read_text())
assert process['exitCode']==0 and process['renderProcessStopped'] and not process['gpuRendering']
assert process['priority']=='idle' and process['threads']==2 and len(process['cpuAffinity'])==2
assert render['sameCameraLightingScaleAndExposure'] and not render['nativeEngineScreenshot']
for name,record in manifest['models'].items():assert render['modelSourceSHA256'][name]==record['meshSHA256']
images=render['images'];assert len(images)==2
assert {r['variant'] for r in images}=={'before','after'}
for key in ('view','eyeMetres','targetMetres','lens','width','height'):assert images[0][key]==images[1][key]
for r in images:
    path=OUT/r['file'];assert sha(path)==r['sha256']
    with Image.open(path) as img:assert img.size==(1050,1400);img.verify()
shutil.copyfile(OUT/'after-main.png',OUT/'after-refined.png')
files=[p for directory in (ASSET,MD) for p in directory.iterdir() if p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')]
review={'status':'preview-ready-awaiting-user-approval','userApproved':False,'installedInMap':False,'oldAssetRetained':True,
    'editorUsed':False,'engineCompilation':'pending','nativeAppearanceLODsAndPerformance':'pending',
    'baseline':manifest['baseline'],'models':manifest['models'],
    'proposalSourceSHA256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)},
    'protectedSourceSHA256':manifest['protectedSourceSHA256'],'verification':json.loads((OUT/'verification.json').read_text()),
    'render':render,'renderProcess':process,'framing':framing,
    'presentationImages':{'before':'before-main.png','after':'after-refined.png'}}
for path in (HERE/'review.json',OUT/'review.json'):path.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'oldAssetRetained':True,'installedInMap':False,'sourceFiles':len(files)}))
