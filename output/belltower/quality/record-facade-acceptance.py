"""Record the reviewed native facade pass without editing any live assets."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

root=Path.cwd()
platform._wmi=None
sys.path.insert(0,str(root/'Tools'))
from belltower_quality_models import collision_signature
quality=root/'output/belltower/quality'
stage=quality/'models/facades-v1'
native=quality/'facades-v1-native'
saved=quality/'facades-v1-saved'
manifest=json.loads((stage/'native-import.json').read_text())
resources=json.loads((stage/'native-resources.json').read_text())
checkpoint=json.loads((quality/'facades-v1-checkpoint.json').read_text())
hash_file=lambda path:sha256(path.read_bytes()).hexdigest()
relative=lambda path:path.relative_to(root).as_posix()

def native_result(path):
    payload=json.loads(path.read_text())
    assert not payload.get('isError'), path
    return json.loads(next(c['text'] for c in payload['content'] if c['type']=='text'))

assert resources['ManifestSha256']==hash_file(stage/'native-import.json')
assert len(resources['Models'])==3
for file in manifest['files']:
    assert hash_file(root/'Assets'/file['path'])==file['sha256']
    assert hash_file(quality/'facades-v1-before/assets'/file['path'])==file['expected_sha256']
for path,fingerprint in manifest['source_hashes'].items():
    assert hash_file(root/path)==fingerprint

collision=[]
for model in manifest['models']:
    name=model['name']
    staged=stage/(name+'.vmdl')
    current=root/'Assets/models/maps/belltower'/(name+'.vmdl')
    assert staged.read_bytes()==current.read_bytes(), current
    collision.append({'path':relative(current),'sha256':hash_file(current)})
    for staged in stage.glob(name+'_hulls_*.obj'):
        current=root/'Assets/models/maps/belltower'/staged.name
        assert collision_signature(staged)==collision_signature(current), current
        collision.append({'path':relative(current),'sha256':hash_file(current),'equivalence':'same convex vertex sets; face triangulation may differ'})

compiles={}
for side in ['centre','west','east']:
    result=native_result(native/('compile-'+side)/'asset_compile.json')
    assert result['Success']
    compiles[side]=result

captures=[]
for name in checkpoint['capture_views']:
    before=json.loads((quality/'facades-v1-before'/(name+'-camera.json')).read_text())
    after=json.loads((saved/(name+'-camera.json')).read_text())
    assert before['Capture']==after['Capture']
    assert before['Lighting']==after['Lighting']
    assert after['GamePreserved'] and after['SelectedDocumentPreserved']
    assert not after['SceneHasUnsavedChanges']
    captures.append({'view':name,'before':relative(quality/'facades-v1-before'/(name+'.png')),
                     'after':relative(saved/(name+'.png')),'sha256':hash_file(saved/(name+'.png'))})

scene=root/'Assets/scenes/maps/Belltower/belltower.scene'
assert hash_file(scene)=='aef98ef9fc0c4e484f6456f31dccc58f27163eb339e4844ebfa251de0333154a', 'Scene changed since accepted forest save'
documents=native_result(native/'documents-restored/run_csharp.json')
assert documents['Active']=='scenes/maps/sewage/sewage.scene' and not documents['Playing']
assert all(not d['HasUnsavedChanges'] for d in documents['Documents'])

result={'accepted_utc':datetime.now(timezone.utc).isoformat(),'state':'accepted after native comparison',
        'changes':['profiled cornices and window heads','bevelled window surrounds and sloped sills',
                   'varied upper shutter angles','individual bevelled coping stones within original cap bounds'],
        'source_manifest_sha256':hash_file(stage/'native-import.json'),'source_hashes':manifest['source_hashes'],
        'models':manifest['models'],'installed_files':manifest['files'],'unchanged_collision_inputs':collision,
        'gameplay_spots':94,'geometry_checks':35,'native_compiles':compiles,'native_resources':resources,
        'scene_sha256':hash_file(scene),'scene_unchanged':True,'captures':captures,'editor_restored':documents,
        'review':'Window heads and cornices cast clearer profile shadows; coping joints are visible. No new visual defects were observed in the six matching views.',
        'limitations':['This engine exposes only the first material index count through GetIndexCountForLod; full triangle totals are verified from the hashed source OBJ files.',
                       'Gameplay performance has not been measured for this pass.',
                       'The wider AAA quality goal remains open; distant woodland, repeated facades and box-like garden props still need refinement.']}
text=json.dumps(result,indent=2)+'\n'
(saved/'verification.json').write_text(text)
accepted=root/'Sources/Belltower/facades/manifest.json'
accepted.parent.mkdir(parents=True,exist_ok=True)
incoming=accepted.with_suffix('.json.incoming')
incoming.write_text(text)
incoming.replace(accepted)
checkpoint.update({'state':'accepted; natively compiled and visually reviewed','native_meshes_replaced':True,
                   'editor_window':'Released to Sewage; saved Sewage tab restored, play stopped',
                   'acceptance_manifest':relative(accepted),'next_steps':['Continue the broader visual quality work offline while Sewage uses the editor.']})
(quality/'facades-v1-checkpoint.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
print(json.dumps({'accepted':relative(accepted),'models':len(manifest['models']),'matching_views':len(captures),
                  'unchanged_collision_inputs':len(collision),'scene_unchanged':True,'editor_released':True},indent=2))
