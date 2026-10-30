"""Check the scoped installed plinth and the native compilation/capture evidence."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/belltower/market-steps-v2'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def native(folder,tool):
    result=json.loads((OUT/folder/(tool+'.json')).read_text())
    assert not result.get('isError'),result
    values=[json.loads(item['text']) for item in result['content'] if item['type']=='text']
    return values[0] if len(values)==1 else values


def main():
    m=json.loads((OUT/'stage-v1/manifest.json').read_text())
    for path,item in m['files'].items():
        assert sha(ROOT/path)==item['after'],path
        if item['before']:assert sha(ROOT/item['backup'])==item['before'],path
    for group in ('protected_sha256','source_sha256'):
        for path,digest in m[group].items():assert sha(ROOT/path)==digest,path
    doc='Assets/models/maps/belltower/belltower_centre.vmdl'
    a=(ROOT/m['files'][doc]['backup']).read_bytes();b=(ROOT/doc).read_bytes()
    marker=b'_class = "PhysicsShapeList"'
    assert a[a.index(marker):]==b[b.index(marker):]
    assert all(p['unrelated_obj_bytes_exact'] for p in m['geometry_preservation'].values())
    assert m['geometry']['blocks']==m['geometry']['closed_blocks']==80
    assert m['original_collision_hulls_exact'] and m['column_and_capital_preserved']
    installed=native('install','run_csharp')
    assert installed['EditorStatePreserved'] and installed['InitialUnsavedChangesPreserved']
    assert native('compile-material','asset_compile')['Success']
    assert native('compile-centre','asset_compile')['Success']
    checks=native('native-checks','call_tools')
    assert all(r['IsCompiledAndUpToDate'] and not r['IsCompileFailed'] for r in checks[:2])
    for row,height in zip(checks[2:],(12.,24.,36.)):
        assert row['Hit'] and not row['StartedSolid'] and row['Component']=='ModelCollider'
        assert abs(float(row['EndPosition'].split(',')[2])-height)<.001
    state=native('final-status','editor_status')
    assert not state['IsCompiling'] and state['LastCompileSucceeded'] and state['LastCompileErrors']==0
    captures={}
    for view in ('steps','steps-low'):
        folder=ROOT/'output/belltower/quality/market-steps-v2-installed'
        receipt=json.loads((folder/(view+'-camera.json')).read_text())
        assert all(receipt['Restoration'].values()) and receipt['Capture']['TrialModels']==0
        assert (folder/(view+'.png')).is_file()
        captures[view]=(folder/(view+'.png')).relative_to(ROOT).as_posix()
    result={'revision':m['revision'],'blocks':80,'closed_stones_at_obj_precision':True,
        'new_step_triangles':m['new_step_triangles'],'removed_step_triangles':m['removed_step_triangles'],
        'only_market_base_geometry_replaced':True,'physics_bytes_exact':True,'original_step_heights':[12,24,36],
        'native_compiled_and_up_to_date':True,'captures':captures,'scene_saved_by_task':False,
        'preexisting_unsaved_editor_state_preserved':True}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
