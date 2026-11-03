"""Bind the actual full-model renders, exported collision checks and source hashes."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if (OUT/'native-review-20261031/review.json').exists():
    raise SystemExit('Native review already exists; use finalize_native_review.py to validate it. Offline images do not supersede it.')
d=json.loads((HERE/'candidate.json').read_text())
v=json.loads((OUT/'verification.json').read_text())
r=json.loads((OUT/'render-report.json').read_text())
p=json.loads((OUT/'render-process.json').read_text())
assert p['exitCode']==0 and p['renderProcessStopped'] and not p['gpuRendering'] and p['threads']==2
assert v['allCollisionProbesPassed'] and v['checkedFromExportedModelDocAndHullFiles']
assert r['sameCameraLightingScaleAndExposure'] and r['fullObjectInAllViews'] and not r['GPUUsed']
assert r['previousModelSHA256']==d['models']['before']['meshSHA256']
assert r['revisedModelSHA256']==d['models']['after']['meshSHA256']
assert v['modelsSHA256']['after']==r['revisedModelSHA256']
refinement_path=OUT/'collision-refinement/change.json'
refinement=json.loads(refinement_path.read_text()) if refinement_path.exists() else None
if refinement:
    assert refinement['visibleOBJUnchanged']==r['revisedModelSHA256']
    assert refinement['renderMeshAndMaterialBindingsUnchanged']
changed=refinement['changedFiles'] if refinement else {}
current_proposal={}
for rel,h in {**d['protectedSourceSHA256'],**r['proposalSourceSHA256']}.items():
    if rel in changed:
        change=changed[rel];assert h in (change['before'],change['after'])
        assert sha(ROOT/change['backup'])==change['before']
        assert sha(ROOT/rel)==change['after'],rel
    else:assert sha(ROOT/rel)==h,rel
    if rel in r['proposalSourceSHA256']:current_proposal[rel]=sha(ROOT/rel)
for image in r['images']:
    path=OUT/image['file'];assert sha(path)==image['sha256']
    with Image.open(path) as im:assert im.size==(1600,1200)
main={i['variant']:i for i in r['images'] if i['view']=='main'}
assert set(main)=={'before','after'}
for key in ('eyeMetres','targetMetres'):assert main['before'][key]==main['after'][key]
canvas=Image.new('RGB',(2000,842),(23,25,27));draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
for x,variant,title in ((20,'before','Before — saved equipment case'),(1020,'after','Proposed — maintenance tool cabinet')):
    draw.text((x,18),title,font=font,fill=(229,231,228))
    with Image.open(OUT/(variant+'-main.png')) as im:
        im=im.convert('RGB');im.thumbnail((960,720),Image.Resampling.LANCZOS);canvas.paste(im,(x,67))
draw.text((20,805),'Actual model renders • same camera, lighting and scale • original retained',font=small,fill=(172,182,179))
canvas.save(OUT/'before-after.png')
review=dict(d)
review.update(status='preview-ready-awaiting-user-approval',geometryAndCollisionVerification=v,
              proposalSourceSHA256=current_proposal,renderImages=r['images'],collisionOnlyRefinement=refinement,
              comparisonImage='output/asset-improvement-20261030/tool-cabinet/before-after.png',
              comparisonSHA256=sha(OUT/'before-after.png'),nativeEngineScreenshot=False,
              renderProcessStopped=True,wholeObjectShown=True,nativeCollisionAndAppearance='pending')
for path in (HERE/'review.json',OUT/'review.json'):path.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'originalRetained':True,'installedInMap':False,
                  'actualWholeModelComparison':True,'collisionChecksPassed':True,'renderProcessStopped':True}))
