"""Bind the actual revised mesh/PBR sources to its matched rendered comparisons."""
from pathlib import Path
import hashlib,json
from PIL import Image

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/pump-skid';VIEWS=OUT/'realism-review'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=json.loads((OUT/'manifest.json').read_text())
geometry=json.loads((OUT/'verification.json').read_text())
repairs=json.loads((OUT/'surface-repair-verification.json').read_text())
assert repairs['intendedRoundGuardOpenings']==24 and repairs['unintendedGuardGridGaps']==0
assert repairs['outletUVSeams']==0
render=json.loads((VIEWS/'render-report.json').read_text())
process=json.loads((VIEWS/'render-process.json').read_text())
assert process['exitCode']==0 and process['renderProcessStopped'] and process['threads']==2 and not process['gpuRendering']
assert render['sameCameraLightingScaleAndExposure'] and render['fullObjectInComparisonViews']
assert render['revisedModelSHA256']==candidate['models']['after']['meshSHA256']
assert render['previousModelSHA256']=='0bc0ceac2f1b6d1af505d20963ee052fc918a5de1bf5f372cf7901ab4df7571e'
assert geometry['variants']['after']['meshSHA256']==candidate['models']['after']['meshSHA256']
for p,h in {**render['protectedSourceSHA256'],**render['proposalSourceSHA256']}.items():assert sha(ROOT/p)==h,p
pair=[r for r in render['images'] if r['view']=='main']
assert {r['variant'] for r in pair}=={'previous','revised'}
assert pair[0]['eyeMetres']==pair[1]['eyeMetres'] and pair[0]['targetMetres']==pair[1]['targetMetres']
assert len(render['images'])==3
for r in render['images']:
    p=VIEWS/r['file'];assert sha(p)==r['sha256'];assert Image.open(p).size==(1600,1200)
atlas=ROOT/'Assets/materials/collider/pump-skid-trial-v1'
for name in ('ps_cast_skin','ps_motor_skin'):
    for suffix in ('color','normal','rough','metal'):
        assert Image.open(atlas/(name+'_'+suffix+'.png')).size==(2048,4096)
archive=json.loads((OUT/'revision-01/archive.json').read_text())
for p,h in archive['files'].items():assert sha(OUT/'revision-01'/p)==h,p
assert (ROOT/'Assets/models/props/collider/pump-skid-trial-v1/before.obj').is_file()
review={**candidate,'status':'preview-ready-awaiting-user-approval','userApproved':False,'installedInMap':False,
        'surfaceRepairVerification':repairs,
        'nativeEngineScreenshot':False,'geometryVerification':geometry,'originalRetained':True,
        'proposalSourceSHA256':render['proposalSourceSHA256'],'renderImages':render['images'],
        'renderEvidence':'output/asset-improvement-20261030/pump-skid/realism-review/',
        'wholePreviousAndRevisedModelsCompared':True,'additionalSurfaceCloseup':True,
        'previousProposalPreserved':True,'renderProcessStopped':True,'editorUsed':False,
        'generatedReferenceOnly':'output/asset-improvement-20261030/pump-skid/realism-review/finish-reference-v3.png',
        'imageGenerationMode':'built-in image_gen','imageGenerationPrompt':'Sources/Collider/pump-skid-trial-v1/finish-reference-prompt.txt',
        'actualModelRenderedFromOBJAndPBR':True,'skinTexturePixels':[2048,4096],
        'materialRecipe':'Sources/Collider/valve-trial-v1/valve_surface.py; coating()',
        'engineCompilation':'pending','nativeAppearanceLODsAndPerformance':'pending'}
for p in (HERE/'review.json',OUT/'review.json',VIEWS/'review.json'):p.write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'status':review['status'],'revision':candidate['realismRevision'],'triangles':candidate['models']['after']['triangles'],
                  'materialBenchmark':'accepted valve revision 2','castingAndMotorTextures':'2048 x 4096',
                  'matchedWholeObjectImages':2,'surfaceDetailImages':1,'originalMapUntouched':True,'renderProcessStopped':True}))
