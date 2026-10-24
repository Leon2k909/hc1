"""Record post-import source, editor, compilation and matched visual evidence."""
import json
from pathlib import Path
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/lounger-v3'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    rows=[]
    for item in raw['content']:
        if item['type']=='text':
            try:rows.append(json.loads(item['text']))
            except json.JSONDecodeError:pass
    return rows


def main():
    manifest=json.loads((OUT/'stage-v3/manifest.json').read_text())
    for relative,item in manifest['files'].items():assert sha(ROOT/relative)==item['after'],relative
    for group in ('source_sha256','protected_sha256'):
        for relative,digest in manifest[group].items():assert sha(ROOT/relative)==digest,relative
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['Stage']=='stage-v3' and receipt['PlacementsUpdated']==8 and receipt['EditorStatePreserved']
    assert not any(receipt[k] for k in ('PhysicsChanged','SceneChanged','MaterialRemapsChanged'))
    materials=results(OUT/'compile-native/call_tools.json')[:7]
    models=results(OUT/'compile-smoothed-native/call_tools.json')
    assert len(materials)==7 and len(models)==3 and all(r['Success'] for r in materials+models)
    status,camera,compile_state=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0 and not status['IsCompiling']
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    captures={}
    for view in ('garden','deck','roof'):
        image=ROOT/f'output/veridant/quality/lounger-v3-final/{view}.png'
        meta=json.loads(image.with_name(view+'-camera.json').read_text())
        assert all(meta['Restoration'].values())
        captures[view]={'path':image.relative_to(ROOT).as_posix(),'sha256':sha(image),**meta}
    before=ROOT/'output/veridant/quality/lounger-v3-before/garden.png'
    baseline=json.loads(before.with_name('garden-camera.json').read_text())
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure','SourceSceneSha256'):
        assert baseline['Capture'][key]==captures['garden']['Capture'][key],key
    assert sha(before)!=captures['garden']['sha256']
    counts=[n for model in manifest['models'].values() for n in model['triangles_per_instance']]
    assert len(counts)==8 and max(counts)<16000
    report={'revision':manifest['revision'],'stage':'stage-v3','placements_updated':8,
            'all_published_source_hashes_verified':True,'all_protected_files_unchanged':True,
            'physics_unchanged':True,'scene_unchanged':True,'shared_map_meshes_unchanged':True,
            'material_compiles':materials,'model_compiles':models,'native_import':receipt,
            'triangles_per_instance':counts,'total_lounger_triangles':sum(counts),
            'matched_garden_camera_and_exposure':True,'captures':captures,
            'editor_status':status,'editor_camera':camera,'compile_status':compile_state,
            'visual_review':'Garden and rooftop captures inspected after smoothing the seam folds.',
            'performance_note':'Geometry budget verified; frame-rate impact was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    installed={'revision':manifest['revision'],'stage':'stage-v3','placements_updated':8,
               'validation':'output/veridant/lounger-v3/validation.json',
               'screenshot':captures['roof']['path'],'source_hook':'Tools/veridant_lounger.py:build_into',
               'physics_unchanged':True,'scene_unchanged':True}
    (ROOT/'Sources/Veridant/lounger-v3/installed.json').write_text(json.dumps(installed,indent=2)+'\n')
    print(json.dumps({'placements_updated':8,'material_compiles_passed':7,'model_compiles_passed':3,
                      'protected_files_unchanged':True,'max_triangles_per_lounger':max(counts),
                      'editor_and_camera_restored':True}))


if __name__=='__main__':main()
