"""Verify completed matched renders and record the concrete proposal for review."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/valve'
ASSET=ROOT/'Assets/models/props/collider/valve-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
verification=json.loads((OUT/'verification.json').read_text())
render=json.loads((OUT/'render-report.json').read_text())
assert not render['nativeEngineScreenshot'] and render['sameCameraLightingScaleAndExposure']
assert len(render['images'])==2
for name,d in manifest['models'].items():
    assert sha(ASSET/(name+'.obj'))==d['meshSHA256']==verification['variants'][name]['meshSHA256']
for path,h in manifest['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
pair=[next(i for i in render['images'] if i['view']=='main' and i['variant']==name) for name in ('before','after')]
for key in ('eyeMetres','targetMetres','lens','width','height'):assert pair[0][key]==pair[1][key]
for d in pair:assert sha(OUT/d['file'])==d['sha256']
materials={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Assets/materials/collider/valve-trial-v1').iterdir() if p.suffix in ('.png','.vmat')}
archive=OUT/'revisions/smooth-v1'
old_report=json.loads((archive/'render-report.json').read_text())
old=next(i for i in old_report['images'] if i['variant']=='after' and i['view']=='main')
new=pair[1]
for key in ('eyeMetres','targetMetres','lens','width','height'):assert old[key]==new[key]
for key in ('samples','viewTransform','exposure'):assert old_report[key]==render[key]
assert sha(archive/old['file'])==old['sha256']
display_name='after-surface-v2.png'
shutil.copyfile(OUT/new['file'],OUT/display_name)
assert sha(OUT/display_name)==new['sha256']
result={'status':'ready-for-user-review','installedInMap':False,'editorUsed':False,'engineValidation':'pending',
    'renderSessionExited':True,'renderEvidence':render,'geometryVerification':verification,
    'modelSourceSHA256':{k:v['meshSHA256'] for k,v in manifest['models'].items()},'materialSourceSHA256':materials,
    'revision':'surface-v2','previousProposalComparison':{'previous':'revisions/smooth-v1/'+old['file'],'revised':display_name,
        'identicalCameraLightingScaleAndExposure':True,'previousSHA256':old['sha256'],'revisedSHA256':new['sha256']}}
(Path(__file__).parent/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'reviewReady':True,'images':2,'candidateInstalled':False,'afterTriangles':manifest['models']['after']['triangles'],'engineValidation':'pending'}))
