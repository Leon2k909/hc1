"""Bind the completed matched renders to the exact isolated proposal sources."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/console'
ASSET=ROOT/'Assets/models/props/collider/console-trial-v1'
MATS=ROOT/'Assets/materials/collider/console-trial-v1'
assert not (ROOT/'output/collider-console-accepted-20261030/installed.json').exists(),'Already accepted: use verify_accepted.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,'-X','utf8',str(HERE/'verify.py')],cwd=ROOT,check=True)
manifest=json.loads((OUT/'manifest.json').read_text())
render=json.loads((OUT/'render-report.json').read_text())
process=json.loads((OUT/'render-process.json').read_text())
assert process['exitCode']==0 and process['renderProcessStopped'] and process['gpuRendering'] is False
assert process['threads']==2 and len(process['cpuAffinity'])==2 and process['priority']=='idle'
assert render['sameCameraLightingScaleAndExposure'] and not render['nativeEngineScreenshot']
for name,record in manifest['models'].items():assert render['modelSourceSHA256'][name]==record['meshSHA256']
images=render['images'];assert len(images)==2
a,b=images;assert {a['variant'],b['variant']}=={'before','after'}
for key in ('view','eyeMetres','targetMetres','lens','width','height'):assert a[key]==b[key],key
for record in images:
    path=OUT/record['file'];assert sha(path)==record['sha256']
    with Image.open(path) as img:assert img.size==(1400,1050);img.verify()
# Unique public filename prevents the earlier internal draft being displayed from cache.
shutil.copyfile(OUT/'after-main.png',OUT/'after-panel-v2.png')
assert sha(OUT/'after-panel-v2.png')==next(i['sha256'] for i in images if i['variant']=='after')
files=[p for directory in (ASSET,MATS) for p in directory.iterdir()
       if p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')]
review={'status':'preview-ready-awaiting-user-approval','userApproved':False,'installedInMap':False,
    'oldAssetRetained':True,'editorUsed':False,'engineCompilation':'pending',
    'nativeAppearanceCollisionFitLODsAndPerformance':'pending',
    'baseline':manifest['baseline'],'models':manifest['models'],
    'proposalSourceSHA256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)},
    'protectedSourceSHA256':manifest['protectedSourceSHA256'],
    'verification':json.loads((OUT/'verification.json').read_text()),
    'render':render,'renderProcess':process,'framing':json.loads((OUT/'framing.json').read_text()),
    'presentationImages':{'before':'before-main.png','after':'after-panel-v2.png'}}
for path in (HERE/'review.json',OUT/'review.json'):path.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'oldAssetRetained':True,'installedInMap':False,
                  'sourceFiles':len(files),'images':[r['file'] for r in images]}))
