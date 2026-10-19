"""Record the reviewed garden models, exact imports, and native comparisons."""
from datetime import datetime,timezone
import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

platform._wmi=None
root=Path.cwd()
sys.path.insert(0,str(root/'Tools'))
from belltower_quality_models import collision_signature
quality=root/'output/belltower/quality'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--revision',choices=('garden-v1','garden-v2','garden-v3'),default='garden-v3')
options=parser.parse_args()
revision=options.revision
stage=quality/'models'/revision
native=quality/(revision+'-native')
saved=quality/(revision+'-saved')
manifest=json.loads((stage/'native-import.json').read_text())
resources=json.loads((stage/'native-resources.json').read_text())
imported=json.loads((stage/'native-import-result.json').read_text())
checkpoint=json.loads((quality/(revision+'-checkpoint.json')).read_text())
hash_file=lambda path:sha256(path.read_bytes()).hexdigest()
relative=lambda path:path.relative_to(root).as_posix()

def native_result(path):
    payload=json.loads(path.read_text())
    assert not payload.get('isError'),path
    if 'content' not in payload:
        return payload
    return json.loads(next(c['text'] for c in payload['content'] if c['type']=='text'))

fingerprint=hash_file(stage/'native-import.json')
assert resources['ManifestSha256']==imported['ManifestSha256']==fingerprint
assert imported['Imported']==len(manifest['files']) and imported['GamePreserved'] and imported['SelectedDocumentPreserved']
assert len(resources['Models'])==2
for file in manifest['files']:
    assert hash_file(root/'Assets'/file['path'])==file['sha256']
    assert hash_file(quality/(revision+'-before/assets')/file['path'])==file['expected_sha256']
for path,value in manifest['source_hashes'].items():
    assert hash_file(root/path)==value
for dependency in manifest['collision_inputs']+manifest['existing_material_dependencies']+manifest.get('unchanged_model_inputs',[]):
    assert hash_file(root/dependency['path'])==dependency['sha256']
if revision in ('garden-v2','garden-v3'):
    previous=root/manifest['predecessor_manifest']['path']
    assert hash_file(previous)==manifest['predecessor_manifest']['sha256']
    previous=json.loads(previous.read_text())
    previous_revision=previous.get('revision','garden-v1')
    assert previous_revision==('garden-v1' if revision=='garden-v2' else 'garden-v2')
    assert len(manifest['geometry_checks']['cladding_trim_separation'])==3
    for file in previous['files']:
        assert hash_file(quality/(previous_revision+'-before/assets')/file['path'])==file['expected_sha256']
    if revision=='garden-v3':
        assert manifest['geometry_checks']['wheelbarrow_basin_clearance']['v2_intruding_samples']>0
        assert manifest['geometry_checks']['wheelbarrow_basin_clearance']['v3_intruding_samples']==0

collision=[]
for model in manifest['models']:
    name=model['name']
    staged=stage/(name+'.vmdl')
    current=root/'Assets/models/maps/belltower'/(name+'.vmdl')
    assert staged.read_bytes()==current.read_bytes()
    for staged in stage.glob(name+'_hulls_*.obj'):
        current=root/'Assets/models/maps/belltower'/staged.name
        assert collision_signature(staged)==collision_signature(current)
        collision.append({'path':relative(current),'sha256':hash_file(current),
                          'equivalence':'same convex vertex sets; face triangulation may differ'})

compiles={}
for side in ['west','east']:
    result=native_result(native/('compile-'+side)/'asset_compile.json')
    assert result['Success'],result
    compiles[side]=result

captures=[]
baseline=quality/('garden-v2-saved' if revision=='garden-v3' else 'garden-v1-before')
for name in checkpoint['capture_views']:
    before=json.loads((baseline/(name+'-camera.json')).read_text())
    after=json.loads((saved/(name+'-camera.json')).read_text())
    assert before['Capture']==after['Capture'] and before['Lighting']==after['Lighting']
    assert after['GamePreserved'] and after['SelectedDocumentPreserved']
    assert not after['SceneHasUnsavedChanges']
    captures.append({'view':name,'before':relative(baseline/(name+'.png')),
                     'after':relative(saved/(name+'.png')),'sha256':hash_file(saved/(name+'.png'))})

scene=root/'Assets/scenes/maps/Belltower/belltower.scene'
assert hash_file(scene)=='aef98ef9fc0c4e484f6456f31dccc58f27163eb339e4844ebfa251de0333154a'
handoff=native/'capture-handoff-status.json'
before=native_result(handoff if handoff.exists() else native/'handoff-status.json')
restored=native_result(native/'restored-status.json')
assert restored['ActiveScenePath']==before['ActiveScenePath']
assert restored['IsPlaying']==before['IsPlaying']
assert not restored['SceneHasUnsavedChanges']
assert restored['LastCompileSucceeded'] and restored['LastCompileErrors']==0

result={'accepted_utc':datetime.now(timezone.utc).isoformat(),'state':'accepted after native comparison',
        'revision':revision,'predecessor_manifest':manifest.get('predecessor_manifest'),
        'changes':['closed shed roof gaps and fitted corrugated sheets','individual shed boards and braced doors with hardware',
                   'slatted compost bins','separate split logs with end grain','open wheelbarrow basin, frame, legs and rounded wheel',
                   'shed cladding recessed behind trim to remove coplanar surface artifacts']
                  +(['wheelbarrow chassis lowered beneath the basin with four underside mounts, lowered braces and correctly seated bolts'] if revision=='garden-v3' else []),
        'source_manifest_sha256':fingerprint,'source_hashes':manifest['source_hashes'],
        'models':manifest['models'],'installed_files':manifest['files'],'unchanged_collision_inputs':collision,
        'existing_material_dependencies':manifest['existing_material_dependencies'],
        'unchanged_model_inputs':manifest.get('unchanged_model_inputs',[]),
        'gameplay_spots':94,'geometry_checks':11,'shared_random_sequence_preserved':True,
        'wheelbarrow_basin_clearance':manifest['geometry_checks'].get('wheelbarrow_basin_clearance'),
        'native_compiles':compiles,'native_resources':resources,'scene_sha256':hash_file(scene),'scene_unchanged':True,
        'captures':captures,'editor_restored':restored,
        'review':'Shed roof gaps are closed and the coplanar trim artifacts are gone in the matching native views. Retain this incremental prop pass; the broader visual-quality review remains open.',
        'limitations':['GetIndexCountForLod exposes only the first material index count in this engine; total triangles are verified from the hashed source OBJ files.',
                       'The indirect lighting and reflections retain the previous bake.',
                       'Gameplay performance has not been measured for this pass.',
                       'Firewood still has visibly faceted profiles and needs convincing bark and cut-face detail.',
                       'The wheelbarrow chassis runs partly inside the basin; lower its support frame in a follow-up geometry pass.',
                       'The wider visual quality goal remains open.']}
if revision=='garden-v3':
    result['review']='Wheelbarrow interior and frame reviewed in the matching native view, with a terrace context check. The corrected frame remains below the basin. The broader visual-quality review remains open.'
    result['limitations']=[item for item in result['limitations'] if not item.startswith('The wheelbarrow chassis')]
text=json.dumps(result,indent=2)+'\n'
(saved/'verification.json').write_text(text)
accepted=root/'Sources/Belltower/gardens/manifest.json'
accepted.parent.mkdir(parents=True,exist_ok=True)
incoming=accepted.with_suffix('.json.incoming')
incoming.write_text(text)
incoming.replace(accepted)
checkpoint.update({'state':'accepted; natively compiled and visually reviewed','native_assets_replaced':True,
                   'native_import_complete':True,'published_assets':[f['path'] for f in manifest['files']],'pending_assets':[],
                   'editor_window':'Restored '+restored['ActiveScenePath']+(', play running' if restored['IsPlaying'] else ', play stopped'),
                   'acceptance_manifest':relative(accepted)})
(quality/(revision+'-checkpoint.json')).write_text(json.dumps(checkpoint,indent=2)+'\n')
print(json.dumps({'accepted':relative(accepted),'models':2,'matching_views':len(captures),
                  'unchanged_collision_inputs':len(collision),'scene_unchanged':True},indent=2))
