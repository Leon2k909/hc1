"""Record the back-bar publication, matched captures and doorway checks."""
import json
from pathlib import Path
from railhead_stage_extinguisher import sha
from veridant_stage_backbar import units

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/backbar-v1'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    rows=[]
    for item in raw['content']:
        if item['type']=='text':
            try:rows.append(json.loads(item['text']))
            except json.JSONDecodeError:pass
    return rows


def main():
    manifest=json.loads((OUT/'stage-v1/manifest.json').read_text())
    for p,item in manifest['files'].items():assert sha(ROOT/p)==item['after'],p
    for group in ('source_sha256','protected_sha256'):
        for p,h in manifest[group].items():assert sha(ROOT/p)==h,p
    for p,parts in manifest['required_source_snippets'].items():
        text=(ROOT/p).read_text();assert all(part in text for part in parts),p
    expected=[{k:r[k] for k in ('lo','hi','z0','face')} for r in manifest['sections']]
    assert units()==expected
    assert sha(ROOT/manifest['base_import'])==manifest['retained_bytes_sha256']
    resource='Assets/models/maps/veridant/veridant_buildings.vmdl'
    before=(ROOT/manifest['files'][resource]['backup']).read_text();after=(ROOT/resource).read_text()
    marker='_class = "PhysicsShapeList"';assert before[before.index(marker):]==after[after.index(marker):]
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['SectionsUpdated']==3 and receipt['Bottles']==115 and receipt['EditorStatePreserved']
    assert receipt['PhysicsBytesPreserved'] and not receipt['SceneChanged']
    compiles=results(OUT/'compile-native/call_tools.json')
    assert len(compiles)==12 and all(r['Success'] for r in compiles)
    rays=results(OUT/'door-rays/call_tools.json')
    assert len(rays)==27 and all(not r['Hit'] and not r['StartedSolid'] for r in rays)
    status,camera=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0 and not status['IsCompiling']
    assert status['ActiveScene']=='veridant' and not status['IsPlaying'] and not status['SceneHasUnsavedChanges']
    captures={}
    for name in ('cafe','label-detail'):
        image=ROOT/f'output/veridant/quality/backbar-v1-after/{name}.png'
        meta=json.loads(image.with_name(name+'-camera.json').read_text())
        assert all(meta['Restoration'].values())
        captures[name]={'path':image.relative_to(ROOT).as_posix(),'sha256':sha(image),**meta}
    baseline=ROOT/'output/veridant/quality/backbar-v1-before/cafe.png'
    meta=json.loads(baseline.with_name('cafe-camera.json').read_text())
    for k in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure','SourceSceneSha256'):
        assert meta['Capture'][k]==captures['cafe']['Capture'][k],k
    assert sha(baseline)!=captures['cafe']['sha256']
    report={'revision':manifest['revision'],'stage':'stage-v1','sections_updated':3,'bottles':115,
            'published_files_verified':len(manifest['files']),'protected_files_unchanged':True,
            'physics_bytes_exact':True,'scene_unchanged':True,'unrelated_obj_bytes_exact':True,
            'original_obj_indices_preserved':True,'doorway_spans_preserved':True,'clear_doorway_rays':27,
            'native_compiles':compiles,'native_import':receipt,'sections':manifest['sections'],
            'matched_cafe_camera_and_exposure':True,'captures':captures,
            'editor_status':status,'editor_camera':camera,
            'visual_review':'Overall display and readable upright bottle labels inspected natively.',
            'performance_note':'Replacement geometry is 83,268 triangles; frame-rate impact was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/backbar-v1/installed.json').write_text(json.dumps({
        'revision':manifest['revision'],'sections_updated':3,'bottles':115,
        'validation':'output/veridant/backbar-v1/validation.json','screenshot':captures['cafe']['path'],
        'source_hook':'Tools/veridant_parts.py:counter_shelves','doorway_spans_preserved':True},indent=2)+'\n')
    print(json.dumps({'sections_updated':3,'bottles':115,'native_compiles_passed':12,
                      'doorway_rays_clear':27,'physics_and_scene_preserved':True,'captures_reviewed':2}))


if __name__=='__main__':main()
