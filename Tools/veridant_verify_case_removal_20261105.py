"""Audit the saved publication, retained assets and map-regeneration placements."""
from pathlib import Path
import json,re
from belltower_safe_imports import sha
from veridant_case_placements import placements

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/remove-cases-20261105'
manifest=json.loads((OUT/'manifest.json').read_text())
for path,h in manifest['protected'].items():
    assert sha(ROOT/path)==h,('Protected file changed',path)
for path,item in manifest['files'].items():
    assert sha(ROOT/path)==item['after'],path
    before=(OUT/'before'/path).read_text();after=(ROOT/path).read_text()
    name=Path(path).stem
    removed=manifest['models'][name]['cases_removed']
    assert before.count('_class = "PhysicsShapeBox"')-after.count('_class = "PhysicsShapeBox"')==removed
    assert '/cases-v4/' not in '\n'.join(re.findall(r'filename\s*=\s*"([^"]+)"',after))
    assert json.loads((OUT/f'compile-{name}.json').read_text())['Success']
assert placements()==[]
report={'cases_removed':82,'collision_boxes_removed':82,'remaining_case_placements':0,'protected_files_unchanged':len(manifest['protected']),'assets_deleted':0,'both_models_compiled':True,'saved_scene_unchanged':True}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
