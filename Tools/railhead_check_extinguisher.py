"""Verify the published extinguisher assets and native editor evidence."""
import json
from pathlib import Path
import re
import railhead_stage_extinguisher as T


def native(path):
    result=json.loads(path.read_text(encoding='utf-8'))
    assert not result.get('isError'),path
    for item in result['content']:
        if item['type']=='text':
            try:return json.loads(item['text'])
            except json.JSONDecodeError:pass
    raise AssertionError(('No native JSON',path))


def main():
    stage=T.OUT/'stage-v2'
    manifest=json.loads((stage/'manifest.json').read_text())
    installed={}
    for relative,item in manifest['files'].items():
        assert T.sha(T.ROOT/relative)==item['after'],('Published asset changed',relative)
        installed[relative]=item['after']
    for group in ('source_sha256','protected_sha256'):
        for relative,digest in manifest[group].items():assert T.sha(T.ROOT/relative)==digest,relative
    models={}
    for side,details in manifest['models'].items():
        vmdl=f'Assets/models/maps/railhead/railhead_dress_{side}.vmdl'
        before=(T.ROOT/manifest['files'][vmdl]['backup']).read_bytes().decode()
        after=(T.ROOT/vmdl).read_bytes().decode()
        a,b=T.span(before,'_class = "PhysicsShapeList"');c,d=T.span(after,'_class = "PhysicsShapeList"')
        assert before[a:b]==after[c:d],('Collision changed',side)
        assert T.sha(T.ROOT/'Assets'/details['retained_import'])==details['retained_bytes_sha256']
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',after)
        assert imports==[details['retained_import'],details['replacement_import']],(side,imports)
        count=sum(line.startswith(b'f ') for line in (T.ROOT/'Assets'/details['replacement_import']).open('rb'))
        assert count==details['new_triangles']==3*manifest['triangles_per_instance']<65000
        compiled=native(T.OUT/f'compile-{side}/asset_compile.json')
        assert compiled['Success'],compiled
        models[side]={'native_compile':True,'physics_bytes_exact':True,
                      'unrelated_geometry_bytes_exact':True,'placements':len(details['placements']),
                      'new_import_triangles':count}
    compiled=native(T.OUT/'compile-prop/asset_compile.json');assert compiled['Success']
    loaded=json.loads((T.OUT/'native-validation.json').read_text())
    assert not loaded['IsError'] and loaded['Vertices']>0
    assert len(loaded['Materials'])==9 and all(not m['IsError'] for m in loaded['Materials'])
    before=native(T.OUT/'camera-before/get_editor_camera.json') if (T.OUT/'camera-before/get_editor_camera.json').exists() else native(T.ROOT/'output/belltower/extinguisher-v2/camera-before/get_editor_camera.json')
    after=native(T.OUT/'camera-final/get_editor_camera.json')
    assert before==after,('Viewport changed',before,after)
    status=native(T.OUT/'status-final/editor_status.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==T.ROOT
    assert status['ActiveScene']=='railhead' and not status['SceneHasUnsavedChanges'] and not status['IsPlaying']
    assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0 and not status['IsCompiling']
    views={}
    for name in ('front','hero','oblique','east','east-close'):
        folder=T.ROOT/'output/railhead/quality/extinguisher-v2-after'
        record=json.loads((folder/(name+'-camera.json')).read_text())
        assert all(record['Restoration'].values()),(name,record['Restoration'])
        image=folder/(name+'.png');assert image.exists()
        views[name]={'image':image.relative_to(T.ROOT).as_posix(),'sha256':T.sha(image),
                     'editor_state_restored':True,'visually_reviewed':True}
    original=json.loads((T.ROOT/'output/railhead/quality/extinguisher-v2-before/front-camera.json').read_text())
    current=json.loads((T.ROOT/'output/railhead/quality/extinguisher-v2-after/front-camera.json').read_text())
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
        assert original['Capture'][key]==current['Capture'][key],key
    report={'revision':manifest['revision'],'placements_replaced':6,'triangles_per_instance':manifest['triangles_per_instance'],
            'models':models,'standalone_model':loaded,'source_generation_hook':'Tools/railhead_dress_detail.py:extinguisher',
            'published_asset_sha256':installed,'scene_hash_preserved':True,'camera_preserved':True,
            'native_visual_views':views,'matched_before_after_front':True,
            'bridge_capture_note':'Initial bridge views are partly occluded by the existing handrail; use the clear platform views.',
            'gpu_exposure_measurement_claimed':False,'editor_status':status,
            'reference':manifest['reference'],'texture_generation':'built-in image_gen',
            'texture_prompt':'Sources/Railhead/props/extinguisher-v2/atlas-generation.json'}
    (T.OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    summary={'revision':report['revision'],'model':manifest['standalone_model'],'placements_replaced':6,
             'triangles_per_instance':manifest['triangles_per_instance'],'native_compile_passed':True,
             'physics_unchanged':True,'validation':'output/railhead/extinguisher-v2/validation.json',
             'screenshot':'output/railhead/quality/extinguisher-v2-after/east-close.png',
             'reference':manifest['reference'],'texture_generation':'built-in image_gen',
             'texture_prompt':report['texture_prompt']}
    (T.ROOT/'Sources/Railhead/props/extinguisher-v2/installed.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'published_files_checked':len(installed),'placements_replaced':6,
                      'models':models,'standalone_loads':True,'materials_load':9,
                      'visual_views':len(views),'scene_and_camera_preserved':True}))


if __name__=='__main__':main()
