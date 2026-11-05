"""Preserve the matched evidence and verify guarded source/installation hashes."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=Path(tempfile.gettempdir())/'belltower-bistro-table-v2'
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        while chunk:=f.read(8*1024*1024):h.update(chunk)
    return h.hexdigest()
m=json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in m['guards'].items())
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
assert sha(HERE/'build.py')==m['source_sha256']
for name in ('bistro_table','west_baseline','west_without_table'):
    assert json.loads((OUT/f'compile-{name}.json').read_text())['Success']
assert (ROOT/'Assets/models/maps/belltower/bistro-table-v2/west_baseline.vmdl').read_bytes()==(ROOT/'Assets/models/maps/belltower/belltower_west.vmdl').read_bytes()
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
outside=np.ones(diff.shape,bool);outside[235:880,380:900]=False
outside_fraction=float(diff[outside].mean());assert outside_fraction<.005,outside_fraction
evidence=ROOT/'output/belltower/bistro-table-v2';evidence.mkdir(parents=True,exist_ok=True)
for p in (OUT/'review').glob('*final*'):shutil.copy2(p,evidence/p.name)
report={'revision':m['revision'],'review_only':True,'native_compile_receipts_passed':True,'source_lod_triangles':m['lod_triangles'],'original_triangles':m['old_triangles'],'matched_camera_and_light':True,'fresh_baseline_matches_production_definition':True,'outside_table_roi_changed_fraction':outside_fraction,'restoration':restore,'shared_sources_unchanged':True}
(HERE/'review.json').write_text(json.dumps(report,indent=2)+'\n')
# Check the accepted installation independently of the preview.
chair=Path(tempfile.gettempdir())/'belltower-bistro-chair-v2/install-stage'
manifest=json.loads((chair/'manifest.json').read_text())
assert all(sha(ROOT/p)==data['after'] for p,data in manifest['files'].items())
assert all(not (ROOT/p).exists() for p in manifest['deleted'])
scene=json.loads((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_text())
def walk(value):
    if isinstance(value,dict):
        yield value
        for item in value.values():yield from walk(item)
    elif isinstance(value,list):
        for item in value:yield from walk(item)
chairs=[o for o in walk(scene) if o.get('Name')=='Bistro chairs'];assert len(chairs)==1
assert len(chairs[0]['Children'])==21
print(json.dumps({'table_review':report,'chair_installed_source_hashes_verified':len(manifest['files']),'saved_chairs':21,'retired_chair_files_absent':len(manifest['deleted'])},indent=2))
