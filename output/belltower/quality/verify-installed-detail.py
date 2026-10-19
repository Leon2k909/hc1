"""Check installed detail against its validated staging and pre-pass collision."""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'Tools'))
import belltower_quality_materials as materials

root=Path(__file__).resolve().parents[3]
quality=root/'output/belltower/quality'
model=root/'Assets/models/maps/belltower'
before=quality/'before-props-v1/Assets/models/maps/belltower'
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
def physics(path):
    return path.read_text().partition('_class = "PhysicsShapeList"')[2].partition('\n\t\t]\n')[0]
manifest=json.loads((quality/'model-import.json').read_text())
assert manifest['spots']==94 and manifest['invalid_spots']==manifest['unreachable_spots']==0
previous=json.loads((quality/'before-hall-v1/model-import.json').read_text())
staged={item['path']:root/item['source'] for batch in (previous,manifest) for item in batch['files']}
models={item['name']:item for batch in (previous,manifest) for item in batch['models']}
installed={}
for part in ('centre','west','east'):
    for ext in ('obj','mtl','vmdl'):
        name=f'belltower_{part}.{ext}'
        digest=sha(model/name)
        assert digest==sha(staged[f'models/maps/belltower/{name}']),name
        installed[name]=digest
    assert physics(model/f'belltower_{part}.vmdl')==physics(before/f'belltower_{part}.vmdl'),part
collisions={}
for path in sorted(before.glob('*_hulls_*.obj')):
    digest=sha(model/path.name)
    assert digest==sha(path),path.name
    collisions[path.name]=digest
source_manifest=json.loads((root/'Sources/Belltower/scans/manifest.json').read_text())
original_maps={}
for asset_id in ('brown_planks_03','rough_plaster_broken'):
    asset=next(item for item in source_manifest['assets'] if item['id']==asset_id)
    for item in asset['files'].values():
        with (root/'Assets'/item['path']).open('rb') as stream:
            assert hashlib.file_digest(stream,'md5').hexdigest()==item['md5'],item['path']
    original_maps[asset_id]=len(asset['files'])
native=json.loads((quality/'props-v1-native-resources.json').read_text())
assert all(not item['IsError'] for item in native['Materials'])
def payload(result):
    assert not result.get('isError'),result
    return result.get('structuredContent') or json.loads(next(item['text'] for item in result['content'] if item['type']=='text'))
detail=json.loads((quality/'hall-plaster-native-results.json').read_text())
assert payload(detail['hallCompile'])['Success']
assert payload(detail['hallImport'])['MatchPreserved']
plaster=[]
for result in detail['plasterCompile']:
    data=payload(result)
    assert data['Success'],data
    path=root/'Assets'/data['Path']
    assert path.read_text(encoding='utf-8')==materials.material_text(path.stem),path
    plaster.append(data['Path'])
assert len(plaster)==8
assert sha(root/'Assets/shaders/belltower_plaster.shader')==sha(root/'Sources/Belltower/shaders/belltower_plaster.shader')
decks=json.loads((quality/'hall-v2-deck-checks.json').read_text())
assert len(decks)==2 and all(item['finite'] and item['inside_original_slab'] and item['stairwells_clear'] and not item['collision_added'] for item in decks)
captures=[]
for path in sorted((quality/'hall-plaster-final').glob('*-camera.json')):
    result=json.loads(path.read_text())
    assert result['GamePreserved'] and result['SelectedDocumentPreserved'] and result['TrialPlasterSlots']==0
    assert not result['SceneHasUnsavedChanges']
    light,=result['Lighting']
    assert light['TexturesValid'] and light['BakeVersion']==1
    for key,stem in (('Irradiance','irradiance'),('Distance','distance'),('Relocation','relocation')):
        assert light[key]==f'lighting/belltower/daylight-v9/{stem}.vtex'
    assert path.with_name(path.name.replace('-camera.json','.png')).is_file()
    captures.append(str(path.relative_to(quality)))
assert len(captures)>=6
assert sha(root/'Assets/ui/maps/belltower.png')==sha(quality/'hall-plaster-final/map-art.png')
def nodes(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from nodes(child)
    elif isinstance(value,list):
        for child in value: yield from nodes(child)
def resource_path(value):
    return value.get('Path') if isinstance(value,dict) else value
scene=json.loads((root/'Assets/scenes/maps/Belltower/belltower.scene').read_text())
cache=json.loads((root/'Sources/Belltower/lighting/indirect.json').read_text())
volume,= [item for item in nodes(scene) if item.get('__type')=='Sandbox.IndirectLightVolume']
cached,= [item for item in nodes(cache) if item.get('__type')=='Sandbox.IndirectLightVolume']
lighting={}
for key in ('IrradianceTexture','DistanceTexture','RelocationTexture'):
    path=resource_path(volume[key])
    assert path==resource_path(cached[key]),key
    compiled=root/'Assets'/(path+'_c')
    assert compiled.is_file(),compiled
    lighting[key]={'path':path,'sha256':sha(compiled)}
bake=json.loads((quality/'daylight-v9/bake-result.json').read_text())
assert bake['Passes']==2 and bake['SavedFinalIrradiance'] and bake['GamePreserved']
assert bake['CapturedReflections']==0 and len(bake['RetainedReflectionTextures'])==3
scene_changes=json.loads((quality/'daylight-v9-save/scene-differences.json').read_text())
assert len(scene_changes)==3 and {x['path'].split('/')[-1] for x in scene_changes}==set(lighting)
report={'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'installed_matches_validated_stage':True,'models':list(models.values()),
        'placement_and_reachability':{'spots':94,'invalid':0,'unreachable':0,'evidence':'model-import.json'},
        'installed_sha256':installed,'collision_unchanged_sha256':collisions,'vmdl_physics_unchanged':True,
        'original_maps_md5_verified':original_maps,'native_prop_materials_valid':len(native['Materials']),
        'plaster_materials_installed_and_compiled':plaster,'hall_model_compiled':True,'hall_deck_checks':decks,
        'native_capture_evidence':captures,
        'saved_lighting_matches_cache':lighting,
        'two_pass_lighting_bake':bake,'saved_scene_gameplay_preserved':True,'menu_image_matches_native_capture':True,
        'remaining_validation':'Full runtime performance checks remain pending; the wider visual quality goal is still open.'}
(quality/'installed-detail-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ('installed_matches_validated_stage','models','placement_and_reachability','vmdl_physics_unchanged','original_maps_md5_verified','native_prop_materials_valid','native_capture_evidence','remaining_validation')},indent=2))
