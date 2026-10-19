"""Validate parcel-v4 source consistency; native visual acceptance is separate.

Writes regeneration metadata only. Use --check-only for a read-only check.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from map_daylight import apply_profile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/quality/parcel-v4-production'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    published=json.loads((STAGE/'native-publish-result.json').read_text())
    assert published['Updated']==18 and published['GamePreserved'] and published['SelectedDocumentPreserved']
    manifest=json.loads((STAGE/'publish-manifest.json').read_text())
    assert len(manifest['assets'])==18
    scene_relative='Assets/scenes/maps/Belltower/belltower.scene'
    scene=json.loads((ROOT/scene_relative).read_text())
    expected_scene=json.loads((STAGE/'belltower.scene').read_text())
    daylight_changes=apply_profile(expected_scene)
    assert scene==expected_scene, 'Saved scene differs from the published vegetation plus the current daylight profile'
    for rec in manifest['assets']:
        assert sha(ROOT/rec['source'])==rec['source_sha256']
        if rec['target']!=scene_relative:
            assert sha(ROOT/rec['target'])==rec['source_sha256'], rec['target']
        assert sha(STAGE/'before-publication'/rec['target'])==rec['expected_sha256']
    installed={rec['target']:rec['source_sha256'] for rec in manifest['assets']}
    assert len(installed)==18
    installed[scene_relative]=sha(ROOT/scene_relative)
    trial_path=ROOT/'output/belltower/quality/parcel-v4-forest/manifest.json'
    compile_path=ROOT/'output/belltower/quality/parcel-v4-model-compile.json'
    material_path=STAGE/'native-trial-manifest.json'
    assert sha(trial_path)==manifest['model_manifest_sha256']
    assert sha(compile_path)==manifest['model_compile_log_sha256']
    assert sha(material_path)==manifest['material_manifest_sha256']
    trial=json.loads(trial_path.read_text())
    terrain=json.loads(material_path.read_text())
    assert sha(ROOT/trial['generator'])==trial['generator_sha256']
    assert sha(ROOT/terrain['generator_path'])==terrain['generator_sha256']
    assert sha(ROOT/'Assets/shaders/belltower_forest.shader')==trial['shader_sha256']
    assert sha(ROOT/'Sources/Belltower/generated/forest-trees-v1.png')==trial['atlas_sha256']
    for path,expected in terrain['source_sha256'].items():
        assert sha(ROOT/path)==installed.get(path,expected), path
    roots={obj.get('Name'):obj for obj in scene['GameObjects'] if obj.get('Name') in ('Distant woodland','Landscape trees')}
    assert len(roots['Distant woodland']['Children'])==88
    assert len(roots['Landscape trees']['Children'])==1600
    model_refs=[child['Components'][0]['Model'] for child in roots['Distant woodland']['Children']]
    assert all(x.startswith('models/maps/belltower/forest/parcel-v4/') for x in model_refs)
    assert all((ROOT/'Assets'/(x+'_c')).is_file() for x in model_refs)
    before_scene=json.loads((STAGE/'before-publication/Assets/scenes/maps/Belltower/belltower.scene').read_text())
    apply_profile(before_scene)
    other=lambda data:[obj for obj in data['GameObjects'] if obj.get('Name') not in roots]
    assert other(scene)==other(before_scene), 'Unrelated scene roots changed'
    assert {k:v for k,v in scene.items() if k!='GameObjects'}=={k:v for k,v in before_scene.items() if k!='GameObjects'}
    for name,filename in (('Distant woodland','forest.json'),('Landscape trees','trees.json')):
        assert roots[name]==json.loads((ROOT/'Sources/Belltower/landscape'/filename).read_text())
    compiles=json.loads(compile_path.read_text())
    assert len(compiles)==88 and set(compiles)==set(model_refs)
    assert all(record['Success'] for record in compiles.values())
    records=json.loads((trial_path.parent/'import.json').read_text())
    assert len(records)==264 and len({record['path'] for record in records})==264
    assets={}
    for record in records:
        assert sha(ROOT/record['source'])==record['sha256'], record['source']
        assert sha(ROOT/'Assets'/record['path'])==record['sha256'], record['path']
        assets[record['path']]=record['sha256']
    assert {path for path in assets if path.endswith('.vmdl')}==set(model_refs)
    for relative in model_refs:
        model=ROOT/'Assets'/relative
        assert 'PhysicsShape' not in model.read_text(), relative
        compiled=Path(str(model)+'_c')
        assert compiled.stat().st_size>0
        assert compiled.stat().st_mtime>=max(model.stat().st_mtime,model.with_suffix('.obj').stat().st_mtime), relative
    report_path='output/belltower/quality/parcel-v4-production/verification.json'
    published_at=datetime.fromtimestamp((STAGE/'native-publish-result.json').stat().st_mtime,timezone.utc).isoformat()
    accepted=ROOT/'Sources/Belltower/landscape/textures.json'
    textures=json.loads(accepted.read_text())
    textures['generator_sha256']=sha(ROOT/'Tools/belltower_vista_paint.py')
    for path in textures['source_sha256']:
        expected=installed.get(path,terrain['source_sha256'].get(path))
        assert expected is not None and sha(ROOT/path)==expected, path
        textures['source_sha256'][path]=expected
    textures.pop('accepted_at_utc',None)
    textures['published_at_utc']=published_at
    textures['revision']='parcel-v4'
    textures['parcel_scale']=.9
    textures['publication_report']='output/belltower/quality/parcel-v4-production/native-publish-result.json'
    textures['source_verification_report']=report_path
    textures['native_review']=None
    textures['native_visual_review_verified']=False
    forest_path=ROOT/'Sources/Belltower/landscape/forest-manifest.json'
    forest=json.loads(forest_path.read_text())
    forest.update({key:trial[key] for key in ('generator_sha256','trees','triangles','sectors','colliders','shadow_casting','minimum_distance','maximum_distance')})
    forest['revision']='parcel-v4'
    forest['source_group_sha256']=sha(ROOT/'Sources/Belltower/landscape/forest.json')
    forest['assets']=assets
    forest['staged_group_sha256']=trial['source_group_sha256']
    forest['landscape_inputs']={path:installed['Assets/'+path] for path in forest['landscape_inputs']}
    forest.pop('accepted_date',None)
    forest['published_at_utc']=published_at
    forest['saved_verification']=report_path
    forest['saved_verification_scope']='Installed sources, compilation and scene consistency only.'
    forest['previous_visual_verification']='output/belltower/quality/forest-v8-saved/verification.json'
    forest['native_visual_review_verified']=False
    forest['visual_scope']='Parcel-v4 post-publication native views and gameplay performance remain unverified.'
    forest['runtime_performance_verified']=False
    forest['native_resource_report']='output/belltower/quality/parcel-v4-model-compile.json'
    report={'revision':'parcel-v4','terrain_files':15,'near_trees':1600,'forest_sectors':88,
            'source_hashes_match':True,'backups_match':True,'compiled_sector_models':88,
            'forest_asset_inputs_checked':264,'gameplay_scene_roots_preserved':True,
            'gameplay_scene_roots_checked':len(other(scene)),
            'saved_groups_match_generator_caches':True,
            'scene_sha256':installed[scene_relative],
            'daylight_profile_changes_since_publication':daylight_changes,
            'daylight_profile_generator_sha256':sha(ROOT/'Tools/map_daylight.py'),
            'native_visual_review_verified':False,'runtime_performance_verified':False}
    updates={accepted:textures,forest_path:forest,STAGE/'verification.json':report}
    changed=[p.relative_to(ROOT).as_posix() for p,data in updates.items() if json.loads(p.read_text())!=data]
    if not args.check_only:
        for path,data in updates.items():
            path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'installed_files':18,'backups':18,'forest_asset_inputs':264,'compiled_sectors':88,
                      'near_trees':1600,'metadata_changed':changed,'check_only':args.check_only,
                      'native_visual_review_verified':False}))

if __name__=='__main__':main()
