"""Check the published plaza lamp move against source bytes and native evidence."""
from pathlib import Path
import ast
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/lamp-placement'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def native(folder,tool):
    result=json.loads((OUT/folder/(tool+'.json')).read_text())
    assert not result.get('isError'),result
    return [json.loads(c['text']) for c in result['content'] if c['type']=='text']


def render_bytes(before,after,row):
    # Compare streams independently of the stager: only new positions and the
    # selected faces' position indices may differ. All UV/normal tokens stay exact.
    changed=0;vertices=0;old_positions={};new_positions={};inserted=False
    with before.open('rb') as original,after.open('rb') as target:
        for old in original:
            if old.startswith(b'v '):
                vertices+=1;old_positions[vertices]=tuple(map(float,old.split()[1:]))
            if not inserted and old.startswith((b'usemtl ',b'f ')):
                for i in range(row['new_position_entries']):
                    line=next(target);assert line.startswith(b'v ')
                    new_positions[vertices+i+1]=tuple(map(float,line.split()[1:]))
                inserted=True
            new=next(target)
            if old==new:continue
            assert old.startswith(b'f ') and new.startswith(b'f ')
            old_tokens=[t.split(b'/') for t in old.split()[1:]]
            new_tokens=[t.split(b'/') for t in new.split()[1:]]
            assert len(old_tokens)==len(new_tokens)==3
            for a,b in zip(old_tokens,new_tokens):
                assert a[1:]==b[1:]
                p=old_positions[int(a[0])];q=new_positions[int(b[0])]
                assert all(abs(v-w)<.00001 for v,w in zip(q,(p[0],p[1],p[2]+190)))
            changed+=1
        assert next(target,None) is None
    assert changed==row['translated_faces']


def main():
    manifest=json.loads((OUT/'stage-v1/manifest.json').read_text())
    render_rows=[(p,row) for p,row in manifest['files'].items() if 'translated_faces' in row]
    assert sum(row['translated_faces'] for p,row in render_rows if '/compiler-safe/' not in p)==2960
    assert sum(row['translated_faces'] for p,row in render_rows if '/compiler-safe/' in p)==2960
    for path,row in manifest['files'].items():
        assert sha(ROOT/path)==row['after'] and sha(ROOT/row['backup'])==row['before'],path
        if 'translated_faces' in row:render_bytes(ROOT/row['backup'],ROOT/path,row)
        else:
            changed=0
            with (ROOT/row['backup']).open('rb') as a,(ROOT/path).open('rb') as b:
                for old,new in zip(a,b,strict=True):
                    if old==new:continue
                    assert old.startswith(b'v ') and new.startswith(b'v ')
                    p=list(map(float,old.split()[1:]));q=list(map(float,new.split()[1:]))
                    assert all(abs(v-w)<.00001 for v,w in zip(q,(p[0],p[1],p[2]+190)))
                    changed+=1
            assert changed==28
    imported=native('import-installed','run_csharp')[0]
    assert imported['ImportedFiles']==12 and imported['LampsMoved']==2 and imported['CollisionHullsMoved']==4
    assert imported['OtherGeometryAndPhysicsPreserved'] and imported['SceneUnchanged'] and imported['EditorStatePreserved']
    # The native importer verified every protected hash immediately before and
    # after publication. Other chats can subsequently update unrelated assets.
    # Keep final assertions on our 12 targets, the model descriptions and the
    # generator's lamp placement; record other concurrent edits separately.
    concurrent={}
    for group in ('protected_sha256','source_sha256'):
        for p,h in manifest[group].items():
            actual=sha(ROOT/p)
            if actual!=h:concurrent[p]={'at_publication':h,'current':actual}
    for side in ('west','east'):
        p=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        assert sha(ROOT/p)==manifest['protected_sha256'][p]
    current=(ROOT/'Tools/belltower_map.py').read_text()
    assert '( ( -420, 520 ), ( -420, -150 ) )' in current
    original=(OUT/'before-source/belltower_map.py').read_text()
    def lamp_function(source):
        return ast.dump(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='lamp_post'),include_attributes=False)
    assert lamp_function(current)==lamp_function(original)
    assert sha(ROOT/'Tools/belltower_move_square_lamps.py')==manifest['source_sha256']['Tools/belltower_move_square_lamps.py']
    assert all(r['Success'] for r in native('compile-installed','call_tools'))
    assert all(r['IsCompiledAndUpToDate'] and not r['IsCompileFailed'] for r in native('info-final','call_tools'))
    before=native('traces-before','call_tools');after=native('traces-installed','call_tools')
    assert len(before)==len(after)==8
    for offset in (0,4):
        for height in (0,1):
            a,b=offset+height,offset+2+height
            assert before[a]['Hit'] and not after[a]['Hit']
            assert not before[b]['Hit'] and after[b]['Hit'] and not after[b]['StartedSolid']
            assert before[a]['GameObject']==after[b]['GameObject']
            p=list(map(float,before[a]['EndPosition'].split(',')));q=list(map(float,after[b]['EndPosition'].split(',')))
            assert all(abs(v-w)<.001 for v,w in zip(q,(p[0]+190,p[1],p[2])))
    state=native('final-status','editor_status')[0]
    assert state['ActiveScene']=='belltower' and not state['IsCompiling'] and state['LastCompileSucceeded'] and state['LastCompileErrors']==0
    captures={}
    for side in ('east','west'):
        folder=ROOT/'output/belltower/quality/lamp-placement-installed';name='square-'+side
        c=json.loads((folder/(name+'-camera.json')).read_text())
        assert c['GamePreserved'] and c['SelectedDocumentPreserved']
        assert c['SourceSceneSha256']==manifest['protected_sha256']['Assets/scenes/maps/Belltower/belltower.scene']
        assert (folder/(name+'.png')).is_file()
        captures[side]=(folder/(name+'.png')).relative_to(ROOT).as_posix()
    result={'revision':manifest['revision'],'lamps_moved':2,'collision_hulls_moved':4,
        'old_plan_centres':manifest['old_plan_centres'],'new_plan_centres':manifest['new_plan_centres'],
        'translated_lamp_triangles':2960,'other_render_bytes_uvs_normals_and_physics_exact':True,
        'compiled_models':2,'old_collision_positions_clear':True,'new_collision_positions_solid':True,
        'native_collision_rays':8,'scene_source_unchanged':True,'captures':captures,
        'other_changes_after_guarded_publication':concurrent}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'Sources/Belltower/props/lamp-placement-v1.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
