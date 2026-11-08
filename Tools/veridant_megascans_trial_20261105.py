"""Matched, isolated-scene material trial; never installs an override on the map."""
from pathlib import Path
import json,sys,hashlib,zipfile
sys.path.insert(0,'Sources/Belltower/terracotta-pot-v2')
import native
ROOT=Path.cwd(); OUT=ROOT/'output/veridant/megascans-concrete-trial-20261105'
OUT.mkdir(parents=True,exist_ok=True);native.OUT=OUT
phase=sys.argv[1]
scene=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if phase=='prepare':
    source=ROOT/'Sources/Veridant/megascans-concrete-trial-20261105'
    source.mkdir(parents=True,exist_ok=True)
    archive=Path('C:/Users/leon2/Downloads/smooth_concrete_sdijbcwb_2k.zip')
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            assert Path(item.filename).name==item.filename
            (source/item.filename).write_bytes(z.read(item))
    rel='materials/veridant/trials/megascans-concrete-20261105'
    material='''// Quixel Megascans Smooth Concrete sdijbcwb; 2x2 metre scan, original 2K maps.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "RELPATH/Smooth_Concrete_sdijbcwb_2K_BaseColor.jpg"
    TextureNormal "RELPATH/Smooth_Concrete_sdijbcwb_2K_Normal.jpg"
    TextureRoughness "RELPATH/Smooth_Concrete_sdijbcwb_2K_Roughness.jpg"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1.0"
    g_vTexCoordScale "[2.4384 2.4384]"
}
'''.replace('RELPATH',rel)
    (source/'concrete.vmat').write_text(material)
    names=['concrete.vmat']+[f'Smooth_Concrete_sdijbcwb_2K_{part}.jpg' for part in ('BaseColor','Normal','Roughness')]
    protected={str(p.relative_to(ROOT)):digest(p) for p in (scene,ROOT/'Assets/materials/veridant/vr_concrete.vmat',ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl',ROOT/'Assets/models/maps/veridant/veridant_dress.vmdl')}
    manifest={'source':str(source),'relative_asset_directory':rel,'files':{name:digest(source/name) for name in names},'protected':protected,'archive_sha256':digest(archive),'source_url':'https://www.fab.com/listings/68db59f6-f151-473b-aa47-48e64f47d8c3','asset_id':'sdijbcwb','scan_metres':[2,2],'texture_size':2048,'preview_only':True,'licence':'Fab Standard Licence','licence_acceptance':'Explicit user approval in this chat, 2026-11-05'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (source/'provenance.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'staged_files':len(names),'preview_only':True}))
elif phase=='import':
    print(json.dumps(native.script(ROOT/'Sources/Veridant/megascans-concrete-trial-20261105/import.cs.txt','import-receipt'),indent=2))
    print(json.dumps(native.call('asset_compile',{'path':'materials/veridant/trials/megascans-concrete-20261105/concrete.vmat'},'compile-receipt'),indent=2))
elif phase=='verify':
    manifest=json.loads((OUT/'manifest.json').read_text())
    for path,expected in manifest['protected'].items():
        assert digest(ROOT/path)==expected,('Shared file changed',path)
    target=ROOT/'Assets'/manifest['relative_asset_directory']
    for name,expected in manifest['files'].items():assert digest(target/name)==expected
    before=json.loads((OUT/'before-receipt.json').read_text())
    after=json.loads((OUT/'after-receipt.json').read_text())
    assert before['EditorStatePreserved'] and after['EditorStatePreserved']
    assert before['ErrorModels']==after['ErrorModels']==[]
    assert json.loads((OUT/'compile-receipt.json').read_text())['Success']
    report={'preview_only':True,'saved_scene_and_map_models_unchanged':True,'original_material_unchanged':True,'editor_state_preserved':True,'trial_material_valid':True,'overridden_material_slots':json.loads((OUT/'override-count.json').read_text()),'fixed_exposure':2.2,'field_of_view':65,'size':[1200,900],'position':'-512.7868,-230.7271,57','angles':'19.24,18.59,0'}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
elif phase in ('before','after'):
    config={'directory':'megascans-concrete-trial-20261105','name':phase,'exposure':2.2,'width':1200,'height':900,'fov':65,'position':'-512.7868,-230.7271,57','angles':'19.24,18.59,0','expected_scene_sha256':digest(scene)}
    (OUT/'capture-request.json').write_text(json.dumps(config))
    code=(ROOT/'Sources/Veridant/remove-cases-20261105/capture.cs.txt').read_text()
    code=code.replace('remove-cases-20261105/capture-request.json','megascans-concrete-trial-20261105/capture-request.json')
    code=code.replace('"UpdatePostProcessing"','"UpdateCamera"')
    if phase=='after':
        insert='''
        var replacement=Material.Load("materials/veridant/trials/megascans-concrete-20261105/concrete.vmat");
        if(replacement is null || replacement.IsError) throw new InvalidOperationException("Invalid trial material");
        var changed=0;
        foreach(var renderer in scene.GetAllComponents<ModelRenderer>())
            for(var slot=0;slot<renderer.Materials.Count;slot++)
                if(renderer.Materials.GetOriginal(slot)?.ResourcePath?.Equals("materials/veridant/vr_concrete.vmat",StringComparison.OrdinalIgnoreCase)==true) {
                    renderer.Materials.SetOverride(slot,replacement);changed++;
                }
        if(changed==0) throw new InvalidOperationException("No concrete slots matched");
        System.IO.File.WriteAllText(System.IO.Path.Combine(root,"output/veridant/megascans-concrete-trial-20261105/override-count.json"),changed.ToString());
'''
        code=code.replace('scene.Deserialize(data);','scene.Deserialize(data);'+insert)
    path=OUT/f'capture-{phase}.cs.txt';path.write_text(code)
    result=native.script(path,phase+'-receipt');assert digest(scene)==config['expected_scene_sha256']
    print(json.dumps(result,indent=2))
