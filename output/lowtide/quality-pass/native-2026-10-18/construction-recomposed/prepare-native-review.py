from pathlib import Path
import hashlib
import json
import shutil

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
manifest = json.loads((OUT/'manifest.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
assert all(sha(ROOT/p) == h for p,h in manifest['live_before'].items())
assert all(sha(ROOT/p) == h for p,h in manifest['protected_models'].items())
assert all(sha(OUT/'stage'/p) == h for p,h in manifest['staged_files'].items())
stage = OUT/'native-review/stage'
files = {}
def write(relative, text=None, source=None):
    target = stage/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not (ROOT/relative).exists(), relative
    if source is not None: shutil.copy2(source,target)
    else: target.write_text(text,encoding='utf-8')
    files[relative] = sha(target)

for name in manifest['models']:
    prefix = f'Assets/models/maps/lowtide/{name}'
    review = f'Assets/models/maps/lowtide/construction_review/{name}'
    for ext in ('.obj','.mtl'):
        write(review+ext,source=OUT/'stage'/(prefix+ext))
    definition = (ROOT/(prefix+'.vmdl')).read_text()
    source = f'models/maps/lowtide/{name}.obj'
    assert definition.count(source)==1
    definition=definition.replace(source,f'models/maps/lowtide/construction_review/{name}.obj')
    for material in ('lt_drain_iron','lt_drain_edge'):
        definition=definition.replace(f'materials/lowtide/finish/{material}.vmat',f'materials/lowtide/finish/construction_review/{material}.vmat')
    write(review+'.vmdl',text=definition)
for material in ('lt_drain_iron','lt_drain_edge'):
    write(f'Assets/materials/lowtide/finish/construction_review/{material}.vmat',source=OUT/'stage/Assets/materials/lowtide/finish'/f'{material}.vmat')
write('Assets/shaders/hc1_lowtide_finish_metal.shader',source=OUT/'stage/Assets/shaders/hc1_lowtide_finish_metal.shader')
(OUT/'native-review/import-manifest.json').write_text(json.dumps(dict(files=files,production_before=manifest['protected_models'],geometry_manifest_sha256=sha(OUT/'manifest.json')),indent=2)+'\n')
print(json.dumps(dict(review_files=len(files),production_files_verified=len(manifest['protected_models']))))
