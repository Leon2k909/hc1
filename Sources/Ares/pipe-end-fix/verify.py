"""Verify the installed cap migration against its source and native evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/ares/pipe-end-fix'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def native(folder,tool):
    result=json.loads((OUT/folder/(tool+'.json')).read_text())
    assert not result.get('isError'),result
    rows=[json.loads(block['text']) for block in result['content'] if block['type']=='text']
    return rows[0] if len(rows)==1 else rows


def main():
    m=json.loads((OUT/'stage-v1/manifest.json').read_text())
    assert sha(ROOT/m['target'])==m['after']
    assert sha(ROOT/m['backup'])==m['before']
    with (ROOT/m['target']).open('rb') as stream:
        assert hashlib.sha256(stream.read(m['original_bytes'])).hexdigest()==m['before']
    for group in ('source_sha256','protected_sha256'):
        for path,digest in m[group].items():assert sha(ROOT/path)==digest,path
    for path,snippets in m['required_source_snippets'].items():
        for snippet in snippets:assert snippet in (ROOT/path).read_text(),path
    assert m['caps']==32 and m['open_rim_edges_before']==1344
    assert m['open_rim_edges_after']==0 and m['cap_internal_edges_manifold']
    imported=native('import-installed','run_csharp')
    assert imported['Caps']==32 and imported['OriginalGeometryBytesPreserved']
    assert imported['ModelDocAndPhysicsPreserved'] and imported['EditorStatePreserved']
    assert native('compile-installed','asset_compile')['Success']
    info=native('info-installed','asset_info')
    assert info['IsCompiledAndUpToDate'] and not info['IsCompileFailed']
    before=native('traces-before','call_tools');after=native('traces-installed','call_tools')
    assert len(before)==27 and before==after
    state=native('final-status','call_tools')[0]
    assert state['ActiveScene']=='ares' and not state['IsCompiling']
    assert state['LastCompileSucceeded'] and state['LastCompileErrors']==0
    captures={}
    for view in ('cargo-east','cargo-west'):
        folder=ROOT/'output/ares/quality/pipe-end-fix-installed'
        assert (folder/(view+'.png')).is_file()
        receipt=json.loads((folder/(view+'-camera.json')).read_text())
        assert receipt['Capture']['TrialModels']==0 and all(receipt['Restoration'].values())
        captures[view]=(folder/(view+'.png')).relative_to(ROOT).as_posix()
    receipt={'revision':m['revision'],'caps':m['caps'],'added_triangles':m['added_triangles'],
        'closed_rim_edges':m['open_rim_edges_before'],'all_original_geometry_bytes_preserved':True,
        'modeldoc_materials_scene_and_collision_preserved':True,'native_compiled_and_up_to_date':True,
        'identical_collision_rays':len(after),'captures':captures,'scene_saved_by_task':False}
    (OUT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (Path(__file__).parent/'installed.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
