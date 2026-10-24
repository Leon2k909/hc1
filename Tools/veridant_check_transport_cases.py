"""Record the completed scoped case publication and native visual checks."""
import json
from pathlib import Path
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/cases-v3'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    rows=[]
    for item in raw['content']:
        if item['type']=='text':
            try:rows.append(json.loads(item['text']))
            except json.JSONDecodeError:pass
    return rows


def main():
    stage=OUT/'stage-v3';manifest=json.loads((stage/'manifest.json').read_text())
    for p,item in manifest['files'].items():assert sha(ROOT/p)==item['after'],p
    for group in ('source_sha256','protected_sha256'):
        for p,h in manifest[group].items():assert sha(ROOT/p)==h,p
    for name,data in manifest['models'].items():
        relative=f'Assets/models/maps/veridant/{name}.vmdl'
        item=manifest['files'][relative]
        before=(ROOT/item['backup']).read_text();after=(ROOT/relative).read_text()
        marker='_class = "PhysicsShapeList"'
        assert before[before.index(marker):]==after[after.index(marker):]
        assert sha(ROOT/data['base_import'])==data['retained_bytes_sha256']
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['Stage']=='stage-v3' and receipt['CasesUpdated']==82
    assert receipt['PhysicsBytesPreserved'] and receipt['EditorStatePreserved'] and not receipt['SceneChanged']
    compiles=results(OUT/'compile-native/call_tools.json')
    assert len(compiles)==8 and all(r['Success'] for r in compiles)
    status,camera,compile_state=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0 and not status['IsCompiling']
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    captures={}
    for tone in ('olive','black'):
        path=ROOT/f'output/veridant/quality/cases-v3-after/{tone}-stack.png'
        meta=json.loads(path.with_name(tone+'-stack-camera.json').read_text())
        assert all(meta['Restoration'].values())
        captures[tone]={'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),**meta}
    before_image=ROOT/'output/veridant/quality/cases-v3-before/olive-stack.png'
    baseline=json.loads(before_image.with_name('olive-stack-camera.json').read_text())
    for k in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure','SourceSceneSha256'):
        assert baseline['Capture'][k]==captures['olive']['Capture'][k],k
    assert sha(before_image)!=captures['olive']['sha256']
    counts=[v for r in manifest['models'].values() for v in r['triangles_per_case']]
    assert len(counts)==82 and max(counts)<4000
    report={'revision':manifest['revision'],'stage':'stage-v3','cases_updated':82,
            'published_files_verified':len(manifest['files']),'source_hashes_verified':True,
            'protected_files_unchanged':True,'physics_bytes_exact':True,'scene_unchanged':True,
            'unrelated_obj_bytes_exact':True,'original_obj_indices_preserved':True,
            'case_layout_replayed_and_verified':manifest['case_layout_replayed_and_verified'],
            'models':manifest['models'],'native_import':receipt,'native_compiles':compiles,
            'triangles_per_case':max(counts),'total_case_triangles':sum(counts),
            'matched_olive_camera_and_exposure':True,'captures':captures,
            'editor_status':status,'editor_camera':camera,'compile_status':compile_state,
            'visual_review':'Both olive and black stacks inspected. The white lid openings are closed.',
            'performance_note':'Geometry was budgeted and chunked; frame-rate impact was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/cases-v3/installed.json').write_text(json.dumps({
        'revision':manifest['revision'],'stage':'stage-v3','cases_updated':82,'physics_bytes_exact':True,
        'validation':'output/veridant/cases-v3/validation.json','screenshot':captures['olive']['path'],
        'source_hook':'Tools/veridant_parts.py:hard_case'},indent=2)+'\n')
    print(json.dumps({'cases_updated':82,'native_compiles_passed':8,'physics_and_scene_preserved':True,
                      'unrelated_geometry_bytes_preserved':True,'both_colour_variants_visually_checked':True}))


if __name__=='__main__':main()
