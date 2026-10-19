import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[5]
BASE=Path(__file__).resolve().parent
OLD=ROOT/'output/lowtide/quality-pass/rebase-2026-10-18/water-filter-gentle'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OLD/'manifest.json').read_text())
for p,h in m['live_before'].items():
    assert (sha(ROOT/p) if (ROOT/p).exists() else None)==h,p
for p,h in m['staged_files'].items():
    assert sha(OLD/'stage'/p)==h,p
assert not (BASE/'manifest.json').exists()
stage=BASE/'stage'
for p in ['Assets/shaders/hc1_lowtide_water_filtered.shader','Assets/shaders/hc1_lowtide_water_filtered.shader.meta']:
    (stage/p).parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(OLD/'stage'/p,stage/p)
material='Assets/materials/lowtide/water-review/lt_water_filter_review.vmat'
model='Assets/models/maps/lowtide/lowtide_water_filter_review.vmdl'
(stage/material).parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(OLD/'stage/Assets/materials/lowtide/lt_water.vmat',stage/material)
text=(ROOT/'Assets/models/maps/lowtide/lowtide_water.vmdl').read_text()
assert text.count('materials/lowtide/lt_water.vmat')==1
(stage/model).parent.mkdir(parents=True,exist_ok=True)
(stage/model).write_text(text.replace('materials/lowtide/lt_water.vmat',material[7:]),encoding='utf-8',newline='\n')
sources=dict(m['sources'])
for p in ['Assets/models/maps/lowtide/lowtide_water.vmdl','Assets/models/maps/lowtide/lowtide_water.obj','Assets/scenes/maps/Lowtide/lowtide.scene']:
    sources[p]=sha(ROOT/p)
files={p.relative_to(stage).as_posix():sha(p) for p in stage.rglob('*') if p.is_file()}
assert all(not (ROOT/p).exists() for p in files)
report=dict(status='native_review_assets_prepared_capture_code_not_installed',sources=sources,files=files,
            capture_code_source=str((OLD/'stage/Code/Map/LowtideWaterReflections.cs').relative_to(ROOT)),
            capture_code_sha256=m['staged_files']['Code/Map/LowtideWaterReflections.cs'],
            production_material_source=str((OLD/'stage/Assets/materials/lowtide/lt_water.vmat').relative_to(ROOT)),
            production_material_sha256=m['staged_files']['Assets/materials/lowtide/lt_water.vmat'],
            original_manifest=str((OLD/'manifest.json').relative_to(ROOT)),
            production_changed=False)
(BASE/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'new_review_assets':len(files),'production_changed':False,'capture_code_changed':False}))
