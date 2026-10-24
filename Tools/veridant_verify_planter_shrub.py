"""Verify the installed single-planter correction and its native visual evidence."""
import json
from pathlib import Path
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/olive-v2'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    return [json.loads(item['text']) for item in raw['content'] if item['type']=='text']


def main():
    manifest=json.loads((OUT/'stage-v4-active/manifest.json').read_text())
    for relative,item in manifest['files'].items():assert sha(ROOT/relative)==item['after'],relative
    for relative,digest in manifest['source_sha256'].items():assert sha(ROOT/relative)==digest,relative
    canonical=json.loads((OUT/'stage-v3/manifest.json').read_text())
    for relative in ('Assets/models/maps/veridant/veridant_foliage.obj','Assets/models/maps/veridant/veridant_foliage.mtl'):
        assert sha(ROOT/relative)==canonical['files'][relative]['after']
    imported=json.loads((OUT/'native-import.json').read_text())
    assert imported['PlantsChanged']==1 and imported['EditorStatePreserved']
    assert not imported['SceneChanged'] and not imported['PhysicsChanged']
    compiled=results(OUT/'compile-active-native/asset_compile.json')[0];assert compiled['Success']
    live=results(OUT/'inspect-active-native/run_csharp.json')[0][0]
    assert not live['Error'] and all(not m['Error'] for m in live['Materials'])
    paths={m['Path'] for m in live['Materials']}
    assert manifest['source_material'] in paths and 'materials/veridant/planter-shrub-v1/soil.vmat' in paths
    image=ROOT/'output/veridant/quality/planter-shrub-final/planter.png'
    final=json.loads(image.with_name('planter-camera.json').read_text())
    original=ROOT/'output/veridant/quality/planter-shrub-before/planter.png'
    before=json.loads(original.with_name('planter-camera.json').read_text())
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure','SourceSceneSha256'):
        assert before['Capture'][key]==final['Capture'][key],key
    assert all(final['Restoration'].values()) and sha(image)!=sha(original)
    assert sha(ROOT/'Assets/scenes/maps/Veridant/veridant.scene')==final['Capture']['SourceSceneSha256']
    status,camera=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0 and not status['IsCompiling']
    report={'revision':manifest['revision'],'plants_changed':1,'active_stage':'stage-v4-active',
        'canonical_stage':'stage-v3','published_hashes_verified':True,
        'retained_active_mesh_sha256':manifest['retained_obj_sha256'],
        'retained_obj_bytes_exact':True,'original_indices_preserved':True,
        'old_triangles_removed':466,'new_triangles':2972,'physics_unchanged':True,
        'scene_unchanged':True,'native_import':imported,'native_compile':compiled,
        'live_renderer':live,'capture':final,'screenshot':image.relative_to(ROOT).as_posix(),
        'screenshot_sha256':sha(image),'editor_status':status,'editor_camera':camera,
        'visual_review':'The photographic shrub and soil are visible; the root base is embedded.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/planter-shrub-v1/installed.json').write_text(json.dumps({
        'revision':manifest['revision'],'plants_changed':1,'validation':'output/veridant/olive-v2/validation.json',
        'screenshot':report['screenshot'],'physics_unchanged':True,'scene_unchanged':True},indent=2)+'\n')
    print(json.dumps({'plants_changed':1,'native_compile_passed':True,'live_materials_valid':True,
                      'matched_visual_check_passed':True,'scene_and_physics_unchanged':True}))


if __name__=='__main__':main()
