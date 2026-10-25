"""Check installed native stone assets, collision, imports and capture restoration."""
import hashlib
import json
from pathlib import Path
import re
import belltower_stage_stone_wear as S


def native(path):
    result = json.loads(path.read_text(encoding='utf-8'))
    assert not result.get('isError'), path
    for item in result['content']:
        if item['type'] == 'text':
            try: return json.loads(item['text'])
            except json.JSONDecodeError: pass
    raise AssertionError(('No native result', path))


def main():
    stages = ('props-rebase-v6','props-syntax-v7','props-chips-v8','props-chips-v9')
    manifests = [json.loads((S.OUT/stage/'manifest.json').read_text()) for stage in stages]
    installed = {}
    for report in manifests: installed.update(report['files'])
    for relative, item in installed.items():
        assert S.sha(S.ROOT/relative) == item['after'], ('Installed file changed',relative)
    final = manifests[-1]
    for group in ('source_sha256','protected_sha256'):
        for relative,digest in final[group].items():
            assert S.sha(S.ROOT/relative) == digest, ('Input changed',relative)
    models = {}
    for side in ('west','east','centre'):
        relative = f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        before = (S.ROOT/manifests[0]['files'][relative]['backup']).read_bytes().decode()
        after = (S.ROOT/relative).read_bytes().decode()
        a,b = S.span(before,'_class = "PhysicsShapeList"')
        c,d = S.span(after,'_class = "PhysicsShapeList"')
        assert before[a:b] == after[c:d], ('Collision changed',side)
        pattern = r'filename\s*=\s*"([^"]+\.obj)"'
        old_imports,new_imports = re.findall(pattern,before),re.findall(pattern,after)
        expected = f'models/maps/belltower/edge-realism-v1/{side}.obj'
        assert new_imports == old_imports+[expected], ('Prior imports changed',side)
        leaf = S.ROOT/'Assets'/expected
        triangles = sum(line.startswith(b'f ') for line in leaf.open('rb'))
        assert triangles == final['models'][side]['new_triangles'] < 65000
        compiled = native(S.OUT/f'compile-{side}-reviewed/asset_compile.json')
        assert compiled['Success'] is True, compiled
        models[side] = {'physics_bytes_exact':True,'all_prior_imports_retained':True,
                        'new_import_triangles':triangles,'native_compile':compiled}
    views = ('street-trough','spawn-trough','east-trough','church-tomb','gate-corner',
             'fountain-rim','fountain-overview','market-steps-street')
    captures = {}
    quality = S.ROOT/'output/belltower/quality'
    for view in views:
        path = quality/'edge-realism-v1-after-reviewed'/f'{view}-camera.json'
        capture = json.loads(path.read_text())
        assert all(capture['Restoration'].values()), (view,capture['Restoration'])
        png = path.with_name(view+'.png')
        assert png.exists() and png.stat().st_size > 10000
        item = {'image':png.relative_to(S.ROOT).as_posix(),
                'sha256':S.sha(png),'restoration':capture['Restoration']}
        before = quality/'edge-realism-v1-before'/f'{view}-camera.json'
        if before.exists():
            previous = json.loads(before.read_text())
            keys = ('Position','Angles','FieldOfView','FovAxis','Width','Height',
                    'RequestedExposure','NativeMinimum','NativeMaximum','NativeCompensation')
            assert all(previous['Capture'][k] == capture['Capture'][k] for k in keys), ('Capture settings differ',view)
            item['matched_camera_and_requested_exposure'] = True
        captures[view] = item
    status = native(S.OUT/'status-final/editor_status.json')
    assert Path(status['Paths']['ProjectRoot']).resolve() == S.ROOT.resolve()
    assert status['ActiveScene'] == 'belltower' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0
    report = {'revision':'belltower-stone-wear-v1','accepted_stage':stages[-1],
              'scope':final['scope'],'installed_files_checked':len(installed),
              'installed_file_sha256':{p:item['after'] for p,item in installed.items()},
              'models':models,'captures':captures,'editor_status':status,
              'publication_receipts':[f'output/belltower/edge-realism-v1/import-{stage}/run_csharp.json' for stage in ('props-syntax-v7','props-chips-v8','props-chips-v9')],
              'native_write_types':['.obj','.mtl','.vmdl'],
              'scene_not_written_by_importers':True,
              'external_saved_scene_revision_observed':manifests[0]['protected_sha256']['Assets/scenes/maps/Belltower/belltower.scene'] != final['protected_sha256']['Assets/scenes/maps/Belltower/belltower.scene'],
              'trough_water_recess_inches':2.7,'capture_gpu_exposure_measurement_claimed':False,
              'visual_review':'Inspect the eight recorded native images before accepting this report.'}
    (S.OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    installed_record = S.ROOT/'Sources/Belltower/props/stone-wear-v1/installed.json'
    installed_record.parent.mkdir(parents=True,exist_ok=True)
    installed_record.write_text(json.dumps({'revision':report['revision'],'scope':report['scope'],
        'validation':'output/belltower/edge-realism-v1/validation.json',
        'final_manifest':f'output/belltower/edge-realism-v1/{stages[-1]}/manifest.json',
        'capture_directory':'output/belltower/quality/edge-realism-v1-after-reviewed',
        'source_helpers':['Tools/belltower_stone_wear.py','Tools/belltower_stone_chips.py','Tools/belltower_wall_edges.py'],
        'physics_bytes_exact':True,'all_prior_imports_retained':True,
        'maximum_new_import_triangles':max(m['new_import_triangles'] for m in models.values())},indent=2)+'\n')
    print(json.dumps({'installed_files_checked':len(installed),'scope':report['scope'],
                      'models':models,'native_views':len(captures),'editor_preserved':True}))


if __name__ == '__main__': main()
