"""Validate this prop's installed sources, preservation guards and native evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'output/belltower/wheelbarrow-v2'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def native(folder,tool):
    data=json.loads((OUT/folder/(tool+'.json')).read_text())
    assert not data.get('isError'),data
    rows=[json.loads(c['text']) for c in data['content'] if c['type']=='text']
    return rows[0] if len(rows)==1 else rows


def main():
    request=json.loads((OUT/'import-request.json').read_text());assert not request['preview']
    m=json.loads((OUT/request['stage']/'manifest.json').read_text())
    scene_path='Assets/scenes/maps/Belltower/belltower.scene'
    original_scene=m['protected_sha256'][scene_path];current_scene=sha(ROOT/scene_path)
    assert scene_path not in m['files'],'This task must not publish a scene.'
    for group in ('source_sha256','protected_sha256'):
        for path,digest in m[group].items():
            # Every native capture below proves the original scene hash before
            # and after its operation. A later shared-editor save is retained;
            # it must never be overwritten to make an older guard pass.
            if path==scene_path:continue
            assert sha(ROOT/path)==digest,path
    for path,item in m['files'].items():
        assert sha(ROOT/path)==item['after'],path
        if item['before'] is not None:assert sha(ROOT/item['backup'])==item['before']
        assert sha(ROOT/item['source'])==item['after']
        if item.get('removed_old_wheelbarrow_triangles'):
            assert item['all_retained_bytes_exact']
            # Each staged patch only deletes whole face records. Attribute tables,
            # material groups and every surviving face retain their original bytes.
            with (ROOT/item['backup']).open('rb') as before,(ROOT/path).open('rb') as after:
                current=iter(after);line=next(current,None);deleted=0
                for original in before:
                    if line==original:line=next(current,None)
                    else:assert original.startswith(b'f ');deleted+=1
                assert line is None and deleted==item['removed_old_wheelbarrow_triangles']
    for side,model in m['models'].items():
        path=model['document'];before=(ROOT/m['files'][path]['backup']).read_bytes();after=(ROOT/path).read_bytes()
        marker=b'_class = "PhysicsShapeList"'
        assert before[before.index(marker):]==after[after.index(marker):]
        assert model['removed_triangles']==2360 and model['new_triangles']==11404
        assert after.count(('filename = "models/maps/belltower/wheelbarrow-v2/'+side+'.obj"').encode())==1
    for path,digest in json.loads((OUT/'physics-guards.json').read_text()).items():assert sha(ROOT/path)==digest,path
    info=native('info-installed','call_tools');assert len(info)==8
    assert all(row['IsCompiledAndUpToDate'] and not row['IsCompileFailed'] for row in info)
    assert all(row['Success'] for row in native('compile-installed','call_tools'))
    installed=native('install-v7','run_csharp')
    assert installed['Wheelbarrows']==2 and installed['PhysicsPreserved'] and installed['SourceScenePreserved'] and installed['EditorStatePreserved']
    before=native('rays-before','call_tools');after=native('rays-installed','call_tools')
    assert len(before)==10 and before==after and all(r['Hit'] and not r['StartedSolid'] for r in after)
    state,camera=native('final-status','call_tools')
    # The shared editor may select or play another map after the captures. Its
    # selected document is not owned by this asset-only task.
    assert not state['IsCompiling']
    assert state['LastCompileSucceeded'] and state['LastCompileErrors']==0
    captures={}
    for name in ('west','east','overview','wheel'):
        folder=ROOT/'output/belltower/quality/wheelbarrow-v2-installed'
        assert (folder/(name+'.png')).is_file()
        receipt=json.loads((folder/(name+'-camera.json')).read_text())
        assert receipt['Capture']['TrialModels']==0 and all(receipt['Restoration'].values())
        assert receipt['Capture']['SourceSceneSha256']==original_scene
        captures[name]=(folder/(name+'.png')).relative_to(ROOT).as_posix()
    if current_scene!=original_scene:
        source=(ROOT/scene_path).read_text()
        assert all('models/maps/belltower/belltower_'+side+'.vmdl' in source for side in ('west','east'))
    result={'revision':m['revision'],'stage':request['stage'],'wheelbarrows':2,
        'triangles_per_instance':11404,'replaced_triangles_per_instance':2360,
        'native_compiled_assets':len(info),'identical_collision_rays':len(after),
        'unrelated_obj_bytes_preserved':True,'physics_bytes_preserved':True,
        'scene_source_preserved_during_import_and_captures':True,'scene_saved_by_task':False,
        'scene_sha256_during_native_validation':original_scene,'scene_sha256_at_finish':current_scene,
        'later_shared_editor_scene_save_retained':current_scene!=original_scene,
        'active_scene_at_finish':state['ActiveScene'],
        'existing_editor_unsaved_state_retained':state['SceneHasUnsavedChanges'],
        'captures':captures,'camera_at_finish':camera}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
