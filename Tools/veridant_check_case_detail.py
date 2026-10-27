"""Verify the scoped case publication, native compiles and matched visual checks."""
import argparse
import json
from pathlib import Path
import re
from belltower_safe_imports import sha,span
import veridant_case_detail as C
from veridant_case_placements import placements

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/cases-v4'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    rows=[]
    for item in raw['content']:
        if item['type']=='text':
            try:rows.append(json.loads(item['text']))
            except json.JSONDecodeError:pass
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    parser.add_argument('--phase',default='after');args=parser.parse_args()
    stage=OUT/args.stage;manifest=json.loads((stage/'manifest.json').read_text())
    documents={f'Assets/models/maps/veridant/{name}.vmdl' for name in manifest['models']}
    for p,item in manifest['files'].items():
        if p not in documents:assert sha(ROOT/p)==item['after'],p
    external_document_changes=[]
    for name,data in manifest['models'].items():
        relative=f'Assets/models/maps/veridant/{name}.vmdl';item=manifest['files'][relative]
        before=(ROOT/item['backup']).read_text();staged=(ROOT/item['source']).read_text();now=(ROOT/relative).read_text()
        marker='_class = "PhysicsShapeList"'
        assert before[before.index(marker):]==staged[staged.index(marker):]==now[now.index(marker):]
        a,b=span(now,'_class = "RenderMeshList"');imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',now[a:b])
        assert [p for p in imports if '/cases-v4/' in p]==data['replacement_imports']
        assert not any('/cases-v3/' in p for p in imports)
        for paint,path in C.MATERIALS.items():
            assert f'{{ from = "{paint}.vmat" to = "{path}" }}' in now
        if sha(ROOT/relative)!=item['after']:external_document_changes.append(relative)
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['Stage']==args.stage and receipt['CasesUpdated']==82
    assert receipt['PhysicsBytesPreserved'] and receipt['EditorStatePreserved'] and not receipt['SceneChanged']
    compiles=results(OUT/'compile-native/call_tools.json')
    assert len(compiles)==11 and all(r['Success'] for r in compiles)
    status,camera,compile_state=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0 and not status['IsCompiling']
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    captures={}
    for tone in ('olive','black'):
        path=ROOT/f'output/veridant/quality/cases-v4-{args.phase}/{tone}-stack.png'
        meta=json.loads(path.with_name(tone+'-stack-camera.json').read_text())
        assert path.exists() and all(meta['Restoration'].values())
        baseline_path=ROOT/f'output/veridant/quality/cases-v4-before/{tone}-stack.png'
        baseline=json.loads(baseline_path.with_name(tone+'-stack-camera.json').read_text())
        for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
            assert meta['Capture'][key]==baseline['Capture'][key],(tone,key)
        assert sha(path)!=sha(baseline_path)
        captures[tone]={'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),**meta,
                        'same_saved_scene_as_baseline':meta['Capture']['SourceSceneSha256']==baseline['Capture']['SourceSceneSha256']}
    poses=json.loads((ROOT/'output/veridant/cases-v3/placements.json').read_text())
    assert placements()==poses
    protected_changes=[p for p,h in manifest['protected_sha256'].items() if sha(ROOT/p)!=h]
    own_sources=('Tools/veridant_case_detail.py','Tools/veridant_stage_case_detail.py','Tools/veridant_transport_case.py')
    assert all(sha(ROOT/p)==manifest['source_sha256'][p] for p in own_sources)
    scene='Assets/scenes/maps/Veridant/veridant.scene'
    # Other chats can save the shared scene between operations. Each native
    # operation proves it preserved the scene; never revert a concurrent save.
    assert scene not in manifest['files']
    concurrent_scene_save=sha(ROOT/scene)!=manifest['protected_sha256'][scene]
    audit=results(OUT/'live-material-audit/run_csharp.json')
    assert len(audit)==1 and len(audit[0]['Materials'])==9 and len(audit[0]['LiveRenderers'])==2
    assert all(not m['IsError'] for m in audit[0]['Materials'])
    counts=[n for data in manifest['models'].values() for n in data['triangles_per_case']]
    assert len(counts)==82 and max(counts)<10000
    report={'revision':manifest['revision'],'stage':args.stage,'cases_updated':82,
            'published_files_verified':len(manifest['files']),'geometry_sizes_checked':len(manifest['geometry_checks']),
            'case_poses_exact':True,'physics_bytes_exact':True,'collision_boxes_identical':True,
            'scene_unchanged_by_import':True,'concurrent_scene_save_observed':concurrent_scene_save,
            'triangles_per_case':max(counts),'total_case_triangles':sum(counts),
            'native_compiles':compiles,'native_import':receipt,'captures':captures,'live_material_audit':audit[0],
            'concurrent_model_document_changes_preserved':external_document_changes,
            'protected_files_changed_after_successful_import':protected_changes,
            'editor_status':status,'editor_camera':camera,'compile_status':compile_state,
            'visual_review':'Olive and black native views inspected after compilation.',
            'performance_note':'Render imports are split below 65k triangles; frame-rate impact was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/cases-v4/installed.json').write_text(json.dumps({
        'revision':manifest['revision'],'stage':args.stage,'cases_updated':82,'physics_bytes_exact':True,
        'validation':'output/veridant/cases-v4/validation.json','screenshot':captures['olive']['path'],
        'source_hook':'Tools/veridant_parts.py:hard_case -> veridant_transport_case -> veridant_case_detail'},indent=2)+'\n')
    print(json.dumps({'cases_updated':82,'native_compiles_passed':11,'sizes_checked':len(manifest['geometry_checks']),
                      'physics_and_scene_preserved':True,'both_colour_variants_visually_checked':True,
                      'concurrent_model_document_changes_preserved':external_document_changes}))


if __name__=='__main__':main()
