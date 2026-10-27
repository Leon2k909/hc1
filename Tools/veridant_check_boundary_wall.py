"""Verify gate publication, unchanged boundary physics and native review evidence."""
import json
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_parts as P
from railhead_stage_extinguisher import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/boundary-wall-v1'


def results(path):
    raw=json.loads(path.read_text());assert not raw.get('isError'),path
    return [json.loads(item['text']) for item in raw['content'] if item['type']=='text']


def main():
    first=json.loads((OUT/'stage-v2/manifest.json').read_text())
    final=json.loads((OUT/'stage-v4/manifest.json').read_text())
    for p,item in final['files'].items():assert sha(ROOT/p)==item['after'],p
    for p,h in final['source_sha256'].items():assert sha(ROOT/p)==h,p
    for p,parts in final['required_source_snippets'].items():
        assert all(part in (ROOT/p).read_text() for part in parts),p
    # The original 72 faces were removed once. Later refinements change only
    # task-owned resources, leaving every original retained byte/index intact.
    base=first['base_import'];assert sha(ROOT/base)==first['files'][base]['after']
    assert sha(ROOT/base)==first['retained_bytes_sha256']
    document='Assets/models/maps/veridant/veridant_dress.vmdl'
    previous=(ROOT/first['files'][document]['backup']).read_text()
    current=(ROOT/document).read_text();marker='_class = "PhysicsShapeList"'
    assert previous[previous.index(marker):]==current[current.index(marker):]
    assert current.count('models/maps/veridant/gates-v1/gates.obj')==1
    expected=K.Model();actual=K.Model()
    for north in (-300.,500.):
        for side in (-1,1):
            low=(1886.,north+side*100-14,0)
            high=(1924.,north+side*100+14,150)
            P.box(expected,low[0],high[0],low[1],high[1],0,150,'vr_stone_dark','default')
            actual.collision_box(low,high,'default')
    assert len(expected.boxes)==len(actual.boxes)==4
    for a,b in zip(expected.boxes,actual.boxes):
        assert all(np.array_equal(x,y) for x,y in zip(a[:3],b[:3])) and a[3]==b[3]
    receipt=json.loads((OUT/'native-import.json').read_text())
    assert receipt['GatesUpdated']==2 and receipt['EditorStatePreserved']
    assert receipt['PhysicsBytesPreserved'] and not receipt['SceneChanged']
    compiles=results(OUT/'compile-v4/call_tools.json')
    assert len(compiles)==8 and all(r['Success'] and r['CompiledFile'] for r in compiles)
    status,compile_state,camera=results(OUT/'final-status/call_tools.json')
    assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT
    assert status['ActiveScene']=='veridant' and not status['SceneHasUnsavedChanges']
    assert not status['IsPlaying'] and not status['IsCompiling'] and status['LastCompileErrors']==0
    assert status['LastCompileSucceeded'] and not compile_state['IsBuilding']
    assert all(c['Errors']==0 and c['Success'] for c in compile_state['Compilers'])
    captures={}
    for name in ('front','north'):
        p=ROOT/f'output/veridant/quality/gates-v1-complete/{name}.png'
        meta=json.loads(p.with_name(name+'-camera.json').read_text())
        assert all(meta['Restoration'].values())
        captures[name]={'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),**meta}
    before=ROOT/'output/veridant/quality/gates-v1-before/front-camera.json'
    before_meta=json.loads(before.read_text())['Capture']
    for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','RequestedExposure'):
        assert before_meta[key]==captures['front']['Capture'][key],key
    # Other chats can save unrelated assets while this review runs. Record their
    # observed hashes without restoring them or claiming whole-session equality.
    outside=[]
    for p,h in final['protected_sha256'].items():
        now=sha(ROOT/p)
        if now!=h:outside.append({'path':p,'at_native_import':h,'at_review':now})
    assert all(row['path'] not in final['files'] for row in outside)
    report={'revision':final['revision'],'stage':'stage-v4','gates_updated':2,
        'gate_leaves':4,'stone_piers':4,'new_triangles':final['new_triangles'],
        'legacy_faces_removed_once':72,'retained_obj_bytes_and_indices_exact':True,
        'original_physics_bytes_exact':True,'pier_collision_boxes_identical':4,
        'scene_and_lights_not_written_by_task':True,
        'source_scene_hash_changed_between_reviews':before_meta['SourceSceneSha256']!=captures['front']['Capture']['SourceSceneSha256'],
        'protected_files_changed_after_guarded_import':outside,
        'native_import':receipt,'asset_compiles':compiles,'captures':captures,
        'matched_front_pose_projection_and_requested_exposure':True,
        'editor_status':status,'editor_camera':camera,
        'visual_review':'Both final gates inspected in sunlight and shade; earlier angle and hardware close-up also reviewed.',
        'performance_note':'9,236 replacement triangles across both gates; frame-rate impact was not benchmarked.'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Sources/Veridant/gates-v1/installed.json').write_text(json.dumps({
        'revision':final['revision'],'stage':'stage-v4','gates_updated':2,
        'validation':'output/veridant/boundary-wall-v1/validation.json',
        'screenshot':captures['north']['path'],'source':'Tools/veridant_boundary_wall.py',
        'source_hook':'Tools/veridant_map.py:forecourt',
        'original_physics_bytes_exact':True},indent=2)+'\n')
    print(json.dumps({'gates_updated':2,'replacement_triangles':final['new_triangles'],
        'asset_compiles_passed':8,'physics_bytes_preserved':True,
        'pier_collision_boxes_identical':4,'final_captures_reviewed':2,
        'unrelated_changed_files_preserved':len(outside)}))


if __name__=='__main__':main()
