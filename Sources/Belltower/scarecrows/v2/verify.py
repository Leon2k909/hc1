"""Verify the scoped render imports and their native compile/capture evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'output/belltower/scarecrow-v2'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def native(folder,tool):
    value=json.loads((OUT/folder/(tool+'.json')).read_text())
    assert not value.get('isError'),value
    rows=[json.loads(b['text']) for b in value['content'] if b['type']=='text']
    return rows[0] if len(rows)==1 else rows


def main():
    request=json.loads((OUT/'import-request.json').read_text())
    manifest=json.loads((OUT/request['stage']/'manifest.json').read_text())
    for path,item in manifest['files'].items():
        assert sha(ROOT/path)==item['after'],path
        assert sha(ROOT/item['backup'])==item['before'],path
        assert '/pending-garden-v1/' in path and '-scarecrow.' in path
    for path,digest in manifest['source_sha256'].items():assert sha(ROOT/path)==digest,path
    imported=native('import-final','run_csharp')
    assert imported['Stage']==request['stage']
    assert imported['SceneUnchanged'] and imported['ModelDocumentsPreserved']
    assert imported['EditorStatePreserved'] and imported['PublishedOnlyDedicatedRenderImports']
    compiled=native('compile-final','call_tools')
    assert len(compiled)==2 and all(v['Success'] for v in compiled)
    infos=native('info-final','call_tools')
    assert len(infos)==2 and all(v['IsCompiledAndUpToDate'] and not v['IsCompileFailed'] for v in infos)
    status=native('final-status','editor_status')
    assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
    captures={}
    for view in ('west','east','oblique'):
        base=ROOT/'output/belltower/quality/scarecrow-v2-installed'
        assert (base/(view+'.png')).is_file()
        receipt=json.loads((base/(view+'-camera.json')).read_text())
        assert receipt['Capture']['TrialModels']==0 and all(receipt['Restoration'].values())
        captures[view]=(base/(view+'.png')).relative_to(ROOT).as_posix()
    receipt={'revision':'scarecrow-v2','stage':request['stage'],'instances':2,
        'triangles_per_instance':manifest['triangles_per_instance'],
        'published_only_dedicated_render_imports':True,'scene_saved_by_this_task':False,
        'new_collision_shapes':0,'material_bindings_unchanged':True,
        'native_models_compiled_and_up_to_date':2,'captures':captures,
        'editor_state_preserved':True,'runtime_performance_measured':False}
    (Path(__file__).parent/'installed.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (OUT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
