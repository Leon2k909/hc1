"""Audit the installed 3D ivy, guarded preservation, generator hook and native review."""
from pathlib import Path
import ast
import hashlib
import json
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_ivy as I
import belltower_stage_ivy as S

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/ivy-3d-v1'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    phases=[]
    for name in ('final','refined'):
        manifest=json.loads((OUT/name/'stage/manifest.json').read_text())
        native=json.loads((OUT/name/'native-import.json').read_text())
        assert native['SceneUnchanged'] and native['CollisionUnchanged'] and native['OtherTownArtPreserved']
        for relative,row in manifest['files'].items():
            assert sha(ROOT/row['source'])==row['after']
            if row['backup']:assert sha(ROOT/row['backup'])==row['before']
            if name=='refined':assert sha(ROOT/relative)==row['after'],relative
        assert all(row['collision_blocks_and_bounded_import_list_exact'] for row in manifest['models'].values())
        assert all(row['all_non_ivy_obj_bytes_preserved'] for row in manifest['models'].values())
        phases.append(manifest)
    before=phases[0]
    final=phases[1]
    assert sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')==before['scene_sha256_at_stage']==final['scene_sha256_at_stage']
    for relative,row in final['files'].items():
        assert row['before']==before['files'][relative]['after'],relative
    for path,digest in final['source_sha256'].items():assert sha(ROOT/path)==digest,path
    # Restore must remove just these two remaps, leaving all physics and import
    # paths byte-identical to the pre-task VMDL, including other chats' assets.
    for side in ('west','east'):
        relative=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        original=(OUT/'final/before'/relative).read_bytes()
        installed=(ROOT/relative).read_bytes()
        kept=b''.join(line for line in installed.splitlines(keepends=True) if not any(f'from = "{p}.vmat"'.encode() in line for p in I.MATERIALS))
        assert kept==original
    old_source=ast.parse((OUT/'before-source/belltower_map.py').read_text())
    source=ast.parse((ROOT/'Tools/belltower_map.py').read_text())
    definitions=lambda tree:{n.name:ast.dump(n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    a,b=definitions(old_source),definitions(source)
    shared=json.loads((OUT/'shared-source-revision.json').read_text())
    assert sha(ROOT/shared['source_snapshot'])==shared['source_snapshot_sha256']
    extra=shared['extra_functions']
    assert set(k for k in a if a[k]!=b.get(k))=={'ivy',*extra}
    for name,row in extra.items():
        assert hashlib.sha256(a[name].encode()).hexdigest()==row['before_ast_sha256']
        assert hashlib.sha256(b[name].encode()).hexdigest()==row['after_ast_sha256']
    # Exercise the canonical map hook at an installed, photographed patch.
    model=K.Model()
    wall=K.Wall('n',(1400,1560),(-2380,-2300),(0,240),'+e')
    assert B.ivy(model,wall,1480,0,1.5,out=1.2)
    reference=K.Model()
    path=next((OUT/'final/before/Assets/models/maps/belltower/compiler-safe/west').glob('*ivy_climb.obj'))
    pts,n=next((p,n) for p,n in S.patches(path) if np.allclose(np.mean(p,axis=0),(-2298.8,1480,72)))
    I.build(reference,pts,n)
    def geometry(m):
        return {p:[([np.round(v,9).tolist() for v in points],np.round(n,9).tolist(),m.polygon_uvs.get((p,k)))
            for k,(points,n) in enumerate(polygons)] for p,polygons in m.polygons.items()}
    assert geometry(model)==geometry(reference)
    assert not model.boxes and not model.hulls and not model.props
    resources=json.loads((OUT/'native-resources.json').read_text())
    assert not resources['LeafMaterialError'] and not resources['Texture']['IsError']
    assert all(not m['IsError'] and I.MATERIALS[I.LEAF] in m['Materials'] for m in resources['Models'])
    compile_result=json.loads((OUT/'final-compile-check/call_tools.json').read_text())
    compiled=[json.loads(item['text']) for item in compile_result['content'] if item['type']=='text']
    assets=[row for row in compiled if 'IsCompiled' in row]
    assert len(assets)==3 and all(row['IsCompiledAndUpToDate'] and not row['IsCompileFailed'] for row in assets)
    play=json.loads((OUT/'restart-play/play_start.json').read_text())
    play=json.loads(next(item['text'] for item in play['content'] if item['type']=='text'))
    assert play['IsPlaying'] and play['Scene']=='belltower' and not play['IsPaused']
    captures=[]
    for name in ('wall-front','wall-oblique','hanging','east-context'):
        base=ROOT/'output/belltower/quality/ivy-3d-v2-after'
        record=json.loads((base/(name+'-camera.json')).read_text())
        assert all(record['Restoration'].values())
        assert (base/(name+'.png')).is_file()
        assert record['Capture']['SourceSceneSha256']==final['scene_sha256_at_stage']
        captures.append((base/(name+'.png')).relative_to(ROOT).as_posix())
    result={'passed':True,'patches':50,'leaves':2*sum(p['leaves'] for p in final['patches_per_half']),
        'triangles_per_half':final['models']['west']['new_ivy_triangles'],
        'old_flat_patch_triangles_removed':100,'non_ivy_model_bytes_preserved':True,
        'original_scene_and_collision_exact':True,'generator_hook_matches_installed_patch':True,
        'native_resources_valid':True,'native_compilation_passed':True,'authorized_play_test_restarted':True,
        'native_views_reviewed':captures,'runtime_performance_measured':False}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
