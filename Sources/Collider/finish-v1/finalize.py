"""Finish derived caches from the native-saved scene when the editor is closed.

Never rewrites a scene, model or material. The native import/bake/capture records
and current content hashes must agree before the cache or menu picture is saved.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import shutil
import subprocess
import winreg

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/depot-finish-20261027'
STAGE=OUT/'stage-v8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def verify_scene_changes(scene):
    original=json.loads((ROOT/'output/collider/lighting-v5/visual-scene.json').read_text())
    before=copy.deepcopy(original);after=copy.deepcopy(scene)
    normalization=[v for v in json.loads((OUT/'scene-bake-diff.json').read_text()) if '/__PrefabIdToInstanceId/' in v[0]]
    assert len(normalization)==4
    for pointer,old,new in normalization:
        parts=pointer.split('/')[1:]
        assert parts[:2] in [['GameObjects','16'],['GameObjects','17']]
        assert parts[2]=='__PrefabIdToInstanceId' and len(parts)==4
        left=before['GameObjects'][int(parts[1])][parts[2]]
        right=after['GameObjects'][int(parts[1])][parts[2]]
        assert left.get(parts[3])==old and right.get(parts[3])==new
        left.pop(parts[3],None);right.pop(parts[3],None)
    find=lambda data,name:next(o for o in data['GameObjects'] if o.get('Name')==name)
    left=find(before,'Collider indirect lighting')['Components'][0]
    right=find(after,'Collider indirect lighting')['Components'][0]
    resource=lambda value:value['Path'] if isinstance(value,dict) else value
    for key,stem in [('IrradianceTexture','irradiance'),('DistanceTexture','distance'),('RelocationTexture','relocation')]:
        assert resource(left.pop(key))==f'lighting/collider/lighting-v4/{stem}.vtex'
        assert resource(right.pop(key))==f'lighting/collider/lighting-v6/{stem}.vtex'
    left=find(before,'Reflection Probes')['Children'];right=find(after,'Reflection Probes')['Children']
    assert len(left)==len(right)==4
    for a,b in zip(left,right):
        old=resource(a['Components'][0].pop('Texture'))
        new=resource(b['Components'][0].pop('Texture'))
        assert old.endswith('_v3.vtex') and new==old.replace('_v3.vtex','_v4.vtex')
    assert before==after,'Unexpected scene changes beyond lighting references and recorded native prefab normalization.'
    report={'other_scene_content_preserved':True,'indirect_texture_changes':3,
        'reflection_texture_changes':4,'native_prefab_mapping_deltas':normalization,
        'baseline':'output/collider/lighting-v5/visual-scene.json','final_scene_sha256':sha(ROOT/'Assets/scenes/maps/Collider/collider.scene')}
    write_json(OUT/'scene-owned-changes.json',report)
    return report


def main():
    engine=os.environ.get('FACEPUNCH_ENGINE') or winreg.QueryValueEx(
        winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment'),'FACEPUNCH_ENGINE')[0]
    running=json.loads(subprocess.check_output([str(Path(engine)/'bin/managed/sbox-cli.exe'),'--list'],cwd=ROOT,text=True))
    assert not running,'Use the native editor for publication while an editor is open.'
    manifest=json.loads((STAGE/'manifest.json').read_text())
    for entry in manifest['files']:
        assert sha(ROOT/'Assets'/entry['relative'])==entry['after'],entry['relative']
    for relative,value in manifest['sources'].items():assert sha(ROOT/relative)==value,relative
    for relative,value in manifest['protected'].items():
        if relative!='scenes/maps/Collider/collider.scene':assert sha(ROOT/'Assets'/relative)==value,relative
    scene_path=ROOT/'Assets/scenes/maps/Collider/collider.scene'
    scene=json.loads(scene_path.read_text())
    capture=json.loads((OUT/'captures/capture-report.json').read_text())
    assert sha(scene_path)==capture['SavedSceneSha256']
    assert capture['SceneDirtyStatePreserved'] and capture['GamePreserved'] and capture['SelectedDocumentPreserved']
    native=json.loads((OUT/'native-validation.json').read_text())
    assert native['SceneSha256']==sha(scene_path) and native['Checked']==68 and not native['Failed']
    assert not native['MissingModels'] and not native['MissingMaterials']
    scene_changes=verify_scene_changes(scene)
    indirect=next(o for o in scene['GameObjects'] if o.get('Name')=='Collider indirect lighting')
    reflections=next(o for o in scene['GameObjects'] if o.get('Name')=='Reflection Probes')['Children']
    path=lambda value:value['Path'] if isinstance(value,dict) else value
    volume=indirect['Components'][0]
    assert path(volume['IrradianceTexture'])=='lighting/collider/lighting-v6/irradiance.vtex'
    textures=[path(volume[k]) for k in ['IrradianceTexture','DistanceTexture','RelocationTexture']]
    for obj in reflections:
        component=obj['Components'][0]
        assert component['Mode']=='CustomTexture'
        assert path(component['Texture']).endswith('_v4.vtex')
        textures.append(path(component['Texture']))
    assert len(textures)==7
    for texture in textures:assert (ROOT/'Assets'/(texture+'_c')).is_file(),texture
    bake=json.loads((ROOT/'output/collider/lighting-v6/bake-result.json').read_text())
    assert bake['InputAssetsUnchanged'] and bake['SavedScene'] and bake['GamePreserved']
    assert bake['Passes']==2 and bake['SavedFinalIrradiance']
    inputs=json.loads((ROOT/'output/collider/lighting-v6/input-assets.json').read_text())
    for relative,value in inputs.items():
        if relative!='Assets/scenes/maps/Collider/collider.scene':assert sha(ROOT/relative)==value,relative
    cache=ROOT/'Sources/Collider/lighting';backup=OUT/'lighting-cache-before'
    backup.mkdir(exist_ok=True)
    for name in ['indirect-light.json','reflections.json','bake-result.json']:
        if (cache/name).exists() and not (backup/name).exists():shutil.copyfile(cache/name,backup/name)
    write_json(cache/'indirect-light.json',indirect)
    write_json(cache/'reflections.json',reflections)
    bake.update(AcceptedRevision='lighting-v6',SavedSceneSha256=sha(scene_path))
    write_json(cache/'bake-result.json',bake)
    art=OUT/'captures/art.png';art_target=ROOT/'Assets/ui/maps/collider.png'
    if not (OUT/'map-art-before.png').exists():shutil.copyfile(art_target,OUT/'map-art-before.png')
    assert art.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    shutil.copyfile(art,art_target)
    reflection_stage=json.loads((OUT/'reflection-stage/manifest.json').read_text())
    for entry in reflection_stage['files']:
        assert sha(ROOT/'Assets'/entry['relative'])==entry['sha256']
    files=[e['relative'] for e in manifest['files']]+[e['relative'] for e in reflection_stage['files']]
    files += [t+'_c' for t in textures]+['ui/maps/collider.png']
    primary=ROOT/'output/collider/stage';synchronized=[]
    by_relative={e['relative']:e for e in manifest['files']}
    for relative in files:
        source=ROOT/'Assets'/relative;target=primary/relative
        current=sha(target);entry=by_relative.get(relative,{})
        accepted={None,sha(source),sha(OUT/'stage-v4/before'/relative),entry.get('before')}
        if relative=='ui/maps/collider.png':accepted.add(sha(OUT/'map-art-before.png'))
        safe=current in accepted
        if safe:
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
        synchronized.append({'relative':relative,'synchronized':safe,'sha256':sha(source)})
    # A differently staged scene may belong to another task. Retain it and export
    # the actual saved scene separately for the next package/rebuild operation.
    shutil.copyfile(scene_path,OUT/'reviewed-collider.scene.json')
    primary_scene=primary/'collider.scene.json'
    scene_synchronized=sha(primary_scene) in {None,sha(scene_path),manifest['protected']['scenes/maps/Collider/collider.scene']}
    if scene_synchronized:shutil.copyfile(scene_path,primary_scene)
    result={'revision':manifest['revision'],'installed_stage':manifest['stage'],
        'scene_sha256':sha(scene_path),'lighting':'lighting-v6','static_reflections':'v4',
        'native_positions_passed':68,'missing_models':0,'missing_materials':0,
        'bake_input_assets_verified':len(inputs)-1,'protected_assets_verified':len(manifest['protected'])-1,
        'map_art_sha256':sha(art_target),'derived_caches_saved':True,
        'source_scene_rewritten':False,'editor_open_at_finalization':False,
        'other_scene_content_preserved':scene_changes['other_scene_content_preserved'],
        'primary_stage_scene_synchronized':scene_synchronized,
        'primary_stage_files':synchronized,'disk_free_bytes':shutil.disk_usage(ROOT).free}
    write_json(OUT/'published.json',result)
    assert sha(scene_path)==capture['SavedSceneSha256']
    print(json.dumps({'published':str(OUT/'published.json'),'native_positions_passed':68,
        'primary_files_synchronized':sum(v['synchronized'] for v in synchronized),
        'primary_scene_synchronized':scene_synchronized,'scene_unchanged':True}))


if __name__=='__main__':main()
