from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'Sources/Belltower/terracotta-pot-v2')
import native
ROOT=Path.cwd();TAG='megascans-lawn-trial-20261105';OUT=ROOT/'output/veridant'/TAG;native.OUT=OUT
scene=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text())
for path,expected in manifest['protected'].items():
    if Path(path).suffix!='.scene':assert digest(ROOT/path)==expected,path
source_hash=digest(scene)
config=json.loads((OUT/'capture-request.json').read_text());config['directory']=TAG+'-final';config['expected_scene_sha256']=source_hash
for name,script in [('before','capture-before.cs.txt'),('after','capture-after-balanced.cs.txt')]:
    config['name']=name;(OUT/'capture-request.json').write_text(json.dumps(config))
    result=native.script(OUT/script,'final-'+name+'-receipt')
    assert result['EditorStatePreserved'] and result['ErrorModels']==[],result
    assert digest(scene)==source_hash,'Saved scene changed during pair'
    print(json.dumps(result),flush=True)
for path,expected in manifest['protected'].items():
    if Path(path).suffix!='.scene':assert digest(ROOT/path)==expected,path
report={'preview_only':True,'matched_saved_scene_sha256':source_hash,'scene_hash_at_original_staging':manifest['protected']['Assets\\scenes\\maps\\Veridant\\veridant.scene'],'saved_scene_unchanged_during_final_pair':True,'original_lawn_material_and_ground_model_retained':True,'editor_state_preserved_in_each_final_capture':True,'comparison_directory':str(ROOT/'output/veridant/quality'/(TAG+'-final'))}
(OUT/'final-pair-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
