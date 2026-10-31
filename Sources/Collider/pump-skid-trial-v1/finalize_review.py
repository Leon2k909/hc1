"""Bind the verified full-object comparisons to the exact uninstalled proposal."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261030/pump-skid'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=json.loads((OUT/'manifest.json').read_text())
geometry=json.loads((OUT/'verification.json').read_text())
render=json.loads((OUT/'render-report.json').read_text())
process=json.loads((OUT/'render-process.json').read_text())
assert process['exitCode']==0 and process['renderProcessStopped'] and process['threads']==2 and not process['gpuRendering']
assert render['fullObjectInAllViews'] and render['sameCameraLightingScaleAndExposure']
assert len(render['images'])==4 and render['CPUThreads']==2 and not render['GPUUsed']
for path,h in {**render['protectedSourceSHA256'],**render['proposalSourceSHA256']}.items():
    assert sha(ROOT/path)==h,path
for view in ('main','rear'):
    pair=[r for r in render['images'] if r['view']==view]
    assert {r['variant'] for r in pair}=={'before','after'}
    assert pair[0]['eyeMetres']==pair[1]['eyeMetres'] and pair[0]['targetMetres']==pair[1]['targetMetres']
    for record in pair:
        path=OUT/record['file'];assert sha(path)==record['sha256']
        assert Image.open(path).size==(1400,1050)
review={**candidate,'status':'preview-ready-awaiting-user-approval','userApproved':False,'installedInMap':False,
        'nativeEngineScreenshot':False,'originalRetained':True,'geometryVerification':geometry,
        'proposalSourceSHA256':render['proposalSourceSHA256'],'fullObjectViews':['main','rear'],
        'renderImages':render['images'],'renderProcessStopped':True,
        'beforeIsActualSavedEquipmentCase':True,'afterIsProposedPumpReplacement':True,
        'noEditorOrGPUUsed':True,'renderEvidence':'output/asset-improvement-20261030/pump-skid/'}
for p in (OUT/'review.json',Path(__file__).with_name('review.json')):
    p.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'wholeObjectViews':2,'matchedImages':4,
                  'originalMapAndPriorAcceptedAssetsUnchanged':True,'rendererStopped':True}))
