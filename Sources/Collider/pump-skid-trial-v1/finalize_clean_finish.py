"""Verify the cleaner paint revision against its exact previous preview."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
BASE=ROOT/'output/asset-improvement-20261030/pump-skid';OUT=BASE/'clean-finish-review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
change=json.loads((OUT/'material-change.json').read_text())
render=json.loads((OUT/'render-report.json').read_text())
before=json.loads((OUT/'before-render-report.json').read_text())
process=json.loads((OUT/'render-process.json').read_text())
assert process['exitCode']==0 and process['renderProcessStopped'] and process['threads']==2 and not process['gpuRendering']
assert render['revisedModelSHA256']==before['revisedModelSHA256']==change['geometrySHA256']
for key in ('lights','resolution','samples','CPUThreads','GPUUsed'):
    assert render[key]==before[key],key
for path,h in change['unchangedFiles'].items():assert sha(ROOT/path)==h,path
for path,r in change['changedFiles'].items():assert sha(ROOT/path)==r['after'],path
for path,h in {**change['protectedSourceSHA256'],**render['proposalSourceSHA256']}.items():assert sha(ROOT/path)==h,path
old=next(r for r in before['images'] if r['view']=='main' and r['variant']=='revised')
assert sha(OUT/'before-revised-main.png')==old['sha256']
assert len(render['images'])==1
new=render['images'][0]
assert new['eyeMetres']==old['eyeMetres'] and new['targetMetres']==old['targetMetres']
assert sha(OUT/new['file'])==new['sha256'] and Image.open(OUT/new['file']).size==(1600,1200)
review=json.loads((HERE/'review.json').read_text())
candidate=json.loads((HERE/'candidate.json').read_text())
review.update(candidate,status='preview-ready-awaiting-user-approval',installedInMap=False,userApproved=False,
    finishAdjustment='Broad dark mottling removed; fine pits, normals and exposed-metal edges preserved',
    materialChangeVerification=change,proposalSourceSHA256=render['proposalSourceSHA256'],
    renderImages=render['images'],renderEvidence='output/asset-improvement-20261030/pump-skid/clean-finish-review/',
    beforeSameMeshImage='output/asset-improvement-20261030/pump-skid/clean-finish-review/before-revised-main.png',
    materialOnlyRevision=True,wholeModelShown=True,renderProcessStopped=True,editorUsed=False,
    previousSurfaceCloseupIsHistorical=True,additionalSurfaceCloseup=False,
    generatedReferenceIsHistorical=True,engineCompilation='pending')
review['materialRecipe']='Sources/Collider/pump-skid-trial-v1/refine_valve_finish.py; coating(), adapted from the accepted valve recipe'
for p in (HERE/'review.json',BASE/'review.json',OUT/'review.json'):p.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'changedTextureFiles':len(change['changedFiles']),
                  'geometryUnchanged':True,'fineNormalAndMetalMapsUnchanged':True,'originalMapUntouched':True,
                  'sameCameraAndLighting':True,'renderProcessStopped':True}))
