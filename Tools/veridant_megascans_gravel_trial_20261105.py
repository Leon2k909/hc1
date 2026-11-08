"""Stage and capture a reversible Quixel garden-path trial through the native editor."""
from pathlib import Path
import json,sys,hashlib,zipfile
sys.path.insert(0,'Sources/Belltower/terracotta-pot-v2')
import native
ROOT=Path.cwd(); TAG='megascans-gravel-trial-20261105'
OUT=ROOT/'output/veridant'/TAG;OUT.mkdir(parents=True,exist_ok=True);native.OUT=OUT
SOURCE=ROOT/'Sources/Veridant'/TAG
REL='materials/veridant/trials/'+TAG
SCENE=ROOT/'Assets/scenes/maps/Veridant/veridant.scene'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
phase=sys.argv[1]
if phase=='prepare':
    SOURCE.mkdir(parents=True,exist_ok=True)
    archive=Path('C:/Users/leon2/Downloads/gravel_ground_vi0maebg_2k.zip')
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            assert Path(item.filename).name==item.filename
            (SOURCE/item.filename).write_bytes(z.read(item))
    maps={kind:next(SOURCE.glob('*_'+kind+'.jpg')).name for kind in ('BaseColor','Normal','Roughness','AO')}
    template=(ROOT/'Sources/Veridant/megascans-concrete-trial-20261105/concrete.vmat').read_text()
    import re
    template=re.sub(r'//[^\n]*','// Quixel Megascans Gravel Ground vi0maebg, 2x2 metre original 2K scan.',template,count=1)
    for param,kind in [('TextureColor','BaseColor'),('TextureNormal','Normal'),('TextureRoughness','Roughness'),('TextureAmbientOcclusion','AO')]:
        template=re.sub(param+r' "[^"]+"',param+' "'+REL+'/'+maps[kind]+'"',template)
    template=template.replace('[2.4384 2.4384]','[1.2192 1.2192]')
    (SOURCE/'gravel.vmat').write_text(template)
    names=['gravel.vmat',*maps.values()]
    protected={str(p.relative_to(ROOT)):digest(p) for p in (SCENE,ROOT/'Assets/materials/veridant/vr_concrete.vmat',ROOT/'Assets/materials/veridant/vr_gravel.vmat',ROOT/'Assets/models/maps/veridant/veridant_ground.vmdl')}
    manifest={'source':str(SOURCE),'relative_asset_directory':REL,'files':{name:digest(SOURCE/name) for name in names},'protected':protected,'archive_sha256':digest(archive),'source_url':'https://www.fab.com/listings/c19d425f-4957-4238-b1d7-34c984e9867f','asset_id':'vi0maebg','scan_metres':[2,2],'texture_size':2048,'preview_only':True,'licence':'Fab Standard Licence'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(SOURCE/'provenance.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'staged_files':len(names),'preview_only':True}))
elif phase=='import':
    SOURCE.mkdir(parents=True,exist_ok=True)
    code=(ROOT/'Sources/Veridant/megascans-concrete-trial-20261105/import.cs.txt').read_text().replace('megascans-concrete-trial-20261105',TAG)
    script=SOURCE/'import.cs.txt';script.write_text(code)
    print(json.dumps(native.script(script,'import-receipt'),indent=2))
    print(json.dumps(native.call('asset_compile',{'path':REL+'/gravel.vmat'},'compile-receipt'),indent=2))
elif phase in ('before','after','after-streamed','installed'):
    config={'directory':TAG,'name':phase,'exposure':2.2,'width':1200,'height':900,'fov':65,'position':'-850,150,64','angles':'25,-90,0','expected_scene_sha256':digest(SCENE)}
    (OUT/'capture-request.json').write_text(json.dumps(config))
    code=(ROOT/'Sources/Veridant/remove-cases-20261105/capture.cs.txt').read_text()
    code=code.replace('remove-cases-20261105/capture-request.json',TAG+'/capture-request.json').replace('"UpdatePostProcessing"','"UpdateCamera"')
    if phase.startswith('after'):
        insert='''
        var replacement=Material.Load("RELPATH/gravel.vmat");
        if(replacement is null || replacement.IsError) throw new InvalidOperationException("Invalid trial material");
        var changed=0;
        foreach(var renderer in scene.GetAllComponents<ModelRenderer>())
            for(var slot=0;slot<renderer.Materials.Count;slot++)
                if(renderer.Materials.GetOriginal(slot)?.ResourcePath?.Equals("materials/veridant/vr_gravel.vmat",StringComparison.OrdinalIgnoreCase)==true) {
                    renderer.Materials.SetOverride(slot,replacement);changed++;
                }
        if(changed==0) throw new InvalidOperationException("No gravel slots matched");
        System.IO.File.WriteAllText(System.IO.Path.Combine(root,"output/veridant/TAG/override-count.json"),changed.ToString());
'''.replace('RELPATH',REL).replace('TAG',TAG)
        code=code.replace('scene.Deserialize(data);','scene.Deserialize(data);'+insert)
    path=OUT/f'capture-{phase}.cs.txt';path.write_text(code)
    if phase=='after-streamed':
        warmup='''
    var trialMaterial=Material.Load("RELPATH/gravel.vmat");
    var sampled=new[] {"g_tColor","g_tNormal","g_tRoughness","g_tAmbientOcclusion"}.Select(key=>new {Key=key, Texture=trialMaterial.GetTexture(key)}).Where(x=>x.Texture is not null).ToArray();
    foreach(var sample in sampled) sample.Texture.MarkUsed(2048);
    for(var wait=0;wait<60;wait++) {
        using(scene.Push()) scene.EditorTick(.016f,.016f);
        foreach(var sample in sampled) sample.Texture.MarkUsed(2048);
        await Task.Delay(33,cancellationToken);
    }
    System.IO.File.WriteAllText(System.IO.Path.Combine(root,"output/veridant/TAG/texture-audit.json"),System.Text.Json.JsonSerializer.Serialize(sampled.Select(x=>new {x.Key,x.Texture.Width,x.Texture.Height,x.Texture.Mips}).ToArray()));
'''.replace('RELPATH',REL).replace('TAG',TAG)
        code=code.replace('using var bitmap = new Bitmap',warmup+'\n    using var bitmap = new Bitmap')
        path.write_text(code)
    result=native.script(path,phase+'-receipt');assert digest(SCENE)==config['expected_scene_sha256']
    print(json.dumps(result,indent=2))
elif phase=='verify':
    manifest=json.loads((OUT/'manifest.json').read_text())
    for path,expected in manifest['protected'].items():assert digest(ROOT/path)==expected,path
    for name,expected in manifest['files'].items():assert digest(ROOT/'Assets'/REL/name)==expected
    for capture in ('before','after'):
        receipt=json.loads((OUT/(capture+'-receipt.json')).read_text());assert receipt['EditorStatePreserved'] and receipt['ErrorModels']==[]
    assert json.loads((OUT/'compile-receipt.json').read_text())['Success']
    report={'preview_only':True,'saved_scene_original_materials_and_ground_model_unchanged':True,'editor_state_preserved':True,'trial_material_valid':True,'overridden_slots':json.loads((OUT/'override-count.json').read_text())}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
