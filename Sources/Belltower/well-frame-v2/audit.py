"""Verify native review evidence and retain a portable copy in the project."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=Path(tempfile.gettempdir())/'belltower-well-frame-v2'
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
m=json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in m['guards'].items())
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
assert sha(HERE/'build.py')==m['source_sha256']
for name in ('well_frame','west_baseline','west_without_lantern'):
    assert json.loads((OUT/f'compile-{name}.json').read_text())['Success']
assert (ROOT/'Assets/models/maps/belltower/well-frame-v2/west_baseline.vmdl').read_bytes()==(ROOT/'Assets/models/maps/belltower/belltower_centre.vmdl').read_bytes()
for name in ('before-final','after-final'):
    restore=json.loads((OUT/f'review/{name}-restore.json').read_text())
    assert all(value for key,value in restore.items() if key!='Candidate')
b=json.loads((OUT/'review/before-final-camera.json').read_text())['Capture']
a=json.loads((OUT/'review/after-final-camera.json').read_text())['Capture']
for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','TemporaryMatchedInspectionLight','RequestedExposure','SourceSceneSha256'):
    assert a[key]==b[key],key
before=np.asarray(Image.open(OUT/'review/before-final.png').convert('RGB')).astype(int)
after=np.asarray(Image.open(OUT/'review/after-final.png').convert('RGB')).astype(int)
diff=np.max(np.abs(before-after),axis=2)>5
outside=np.ones(diff.shape,bool);outside[250:1024,250:920]=False
outside_fraction=float(diff[outside].mean());assert outside_fraction<.005,outside_fraction
evidence=ROOT/'output/belltower/well-frame-v2';evidence.mkdir(parents=True,exist_ok=True)
for p in (OUT/'review').glob('*final*'):shutil.copy2(p,evidence/p.name)
report={'revision':m['revision'],'review_only':True,'native_compile_receipts_passed':True,'source_lod_triangles':m['lod_triangles'],'original_triangles':m['old_triangles'],'matched_camera_and_light':True,'fresh_baseline_matches_production_definition':True,'outside_fixture_roi_changed_fraction':outside_fraction,'restoration':restore,'shared_sources_unchanged':True}
(HERE/'review.json').write_text(json.dumps(report,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native
status=native.call('compile_status')
assert not status['IsBuilding'] and all(c['Success'] and c['Errors']==0 for c in status['Compilers'])
print(json.dumps(report,indent=2))
