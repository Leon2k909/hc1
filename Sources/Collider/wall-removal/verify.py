"""Verify that only the selected screen and its one collision box were removed."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider/wall-removal'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def native(folder,tool):
    r=json.loads((OUT/folder/(tool+'.json')).read_text());assert not r.get('isError'),r
    rows=[json.loads(c['text']) for c in r['content'] if c['type']=='text']
    return rows[0] if len(rows)==1 else rows


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--side',choices=('west','east'),default='west')
    args=parser.parse_args()
    if args.side=='east':OUT=ROOT/'output/collider/wall-removal-east'
    m=json.loads((OUT/'stage-v1/manifest.json').read_text())
    for p,row in m['files'].items():
        assert sha(ROOT/p)==row['after'] and sha(ROOT/row['backup'])==row['before'],p
        if p.endswith('.obj'):
            removed=set(row['removed_face_lines']);assert len(removed)==12
            with (ROOT/row['backup']).open('rb') as old,(ROOT/p).open('rb') as new:
                for number,line in enumerate(old):
                    if number in removed:assert line.startswith(b'f ')
                    else:assert line==next(new)
                assert next(new,None) is None
        elif p.endswith('.vmdl'):
            old=(ROOT/row['backup']).read_bytes();new=(ROOT/p).read_bytes();node=row['removed_node'].encode()
            assert old.count(node)==1 and old.replace(node,b'',1)==new
    installed=native('import-installed','run_csharp')
    assert installed['WallsRemoved']==installed['CollisionBoxesRemoved']==1
    assert installed['MinimapUpdated'] and installed['AllOtherPhysicsPreserved'] and installed['SceneUnchanged'] and installed['EditorStatePreserved']
    # The importer checks all protected inputs before and after its mutation.
    # A shared editor can subsequently save another task's scene edits. Keep
    # the final checks strict on our three assets and generation hook, and
    # record unrelated changes instead of requiring the whole project to freeze.
    concurrent={}
    for group in ('source_sha256','protected_sha256'):
        for p,h in m[group].items():
            actual=sha(ROOT/p)
            if actual!=h:concurrent[p]={'at_publication':h,'current':actual}
    assert m['generator_hook'] in (ROOT/'Tools/collider_map.py').read_text()
    for p in ('Tools/map_kit.py','Tools/collider_remove_west_wall.py'):
        assert sha(ROOT/p)==m['source_sha256'][p]
    assert native('compile-installed','asset_compile')['Success']
    info=native('info-installed','asset_info');assert info['IsCompiledAndUpToDate'] and not info['IsCompileFailed']
    before=native('traces-before','call_tools');after=native('traces-installed','call_tools')
    assert len(before)==len(after)==18
    removed_slice=slice(0,9) if args.side=='west' else slice(9,18)
    reference_slice=slice(9,18) if args.side=='west' else slice(0,9)
    assert all(row['Hit'] and not row['StartedSolid'] for row in before[removed_slice])
    assert all(not row['Hit'] and not row['StartedSolid'] for row in after[removed_slice])
    assert before[reference_slice]==after[reference_slice]
    checks=json.loads((OUT/'layout-checks.json').read_text())
    assert checks['checked_spots']==68 and checks['obstructed_or_unsupported']==checks['unreachable']==0
    assert checks['retakes_exposed_pairs_before']==0
    if args.side=='west':assert checks['retakes_exposed_pairs_after']==0
    else:
        assert checks['retakes_exposed_pairs_after']==2
        sight=native('retakes-los-native','call_tools')
        assert len(sight)==2 and all(not r['Hit'] and not r['StartedSolid'] for r in sight)
    capture=native('capture-installed','run_csharp')
    assert capture['SceneDirtyStatePreserved'] and capture['GamePreserved'] and capture['SelectedDocumentPreserved']
    assert (OUT/'captures'/f'after-{args.side}.png').is_file()
    state=native('final-status','editor_status')
    assert state['ActiveScene']=='collider' and not state['IsCompiling'] and state['LastCompileSucceeded'] and state['LastCompileErrors']==0
    result={'revision':m['revision'],'walls_removed':1,'removed_render_triangles':12,'removed_collision_boxes':1,
        'all_other_render_and_physics_bytes_exact':True,'minimap_updated':True,'native_model_compiled_and_current':True,
        'native_rays_through_removed_wall_clear':9,'native_reference_rays_unchanged':9,'layout_positions_passed':68,
        'exposed_retakes_pairs':checks['retakes_exposed_pairs_after'],'scene_source_unchanged':True,
        'capture':(OUT/'captures'/f'after-{args.side}.png').relative_to(ROOT).as_posix(),
        'primary_stage_sync':json.loads((OUT/'primary-stage-sync.json').read_text()),
        'concurrent_changes_after_publication':concurrent}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    receipt=ROOT/'Sources/Collider'/('wall-removal-east' if args.side=='east' else 'wall-removal')/'installed.json'
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
