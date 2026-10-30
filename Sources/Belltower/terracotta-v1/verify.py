"""Check installed material sources and native rendering/compile receipts."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/belltower/terracotta-v1'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def native(folder,tool):
    result=json.loads((OUT/folder/(tool+'.json')).read_text())
    assert not result.get('isError'),result
    rows=[json.loads(c['text']) for c in result['content'] if c['type']=='text']
    assert len(rows)==1
    return rows[0]


def main():
    m=json.loads((OUT/'stage-v2/manifest.json').read_text())
    for path,item in m['files'].items():assert sha(ROOT/path)==item['after'],path
    for group in ('source_sha256','protected_sha256'):
        for path,digest in m[group].items():assert sha(ROOT/path)==digest,path
    assert json.loads((OUT/'shader-compile.json').read_text())['ShaderCompiled']
    assert native('compile-pot-v2','asset_compile')['Success']
    info=native('info-installed','asset_info')
    assert info['IsCompiledAndUpToDate'] and not info['IsCompileFailed']
    texture_info=native('verify-material','run_csharp')
    assert texture_info['MaterialValid'] and all(t['Valid'] for t in texture_info['Textures'])
    sys.path.insert(0,str(ROOT/'Tools'))
    import building_textures as B
    import belltower_terracotta as T
    assert B.vmat('clay_pot','render',0)==T.material()==(ROOT/'Assets/materials/buildings/clay_pot.vmat').read_text()
    source_hashes=set();captures=[]
    for phase,name in (('before','street-pot'),('installed-v2','street-pot'),('installed-v2','sunlit-pot')):
        directory=ROOT/'output/belltower/quality'/('terracotta-v1-'+phase)
        receipt=json.loads((directory/(name+'-camera.json')).read_text())
        assert all(receipt['Restoration'][k] for k in ('CameraRestored','ToneRestored','EditorStatePreserved','ObjectsPreserved'))
        assert receipt['Restoration']['InitialUnsavedState']
        source_hashes.add(receipt['Capture']['SourceSceneSha256'])
        assert (directory/(name+'.png')).exists()
        captures.append((directory/(name+'.png')).relative_to(ROOT).as_posix())
    assert len(source_hashes)==1
    state=native('final-status','editor_status')
    assert state['SceneHasUnsavedChanges'] and not state['IsPlaying'] and not state['IsCompiling'] and state['LastCompileErrors']==0
    result={'revision':'belltower-terracotta-v1','stage':'stage-v2','native_material_compiled_and_current':True,
        'shader_compiled':True,'dedicated_textures':texture_info['Textures'],'geometry_and_collision_changed':False,
        'shared_editor_unsaved_work_preserved':True,'scene_saved_by_task':False,'captures':captures,
        'generator_delegates_material':True,'generated_colour_source':'Sources/Belltower/terracotta-v1/clay-albedo-v1.png',
        'source_prompt':'Sources/Belltower/terracotta-v1/generation.json','provider':'built-in ImageGen'}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
