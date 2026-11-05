"""Create review scripts from the project's proven isolated capture workflow."""
from pathlib import Path
HERE=Path(__file__).absolute().parent;ROOT=HERE.parents[2]
old=HERE.parent/'fluorescent-v1'
(HERE/'import.cs.txt').write_text((old/'import.cs.txt').read_text().replace('fluorescent-v1','tv-aerial-v1').replace('fluorescent_v1','tv_aerial_v1'))
(HERE/'verify.py').write_text((old/'verify.py').read_text().replace('fluorescent-v1','tv-aerial-v1').replace('fluorescent_v1','tv_aerial_v1').replace('fixture_lod','aerial_lod').replace('<4000','<6500'))
t=(old/'review.py').read_text().replace('fluorescent-v1','tv-aerial-v1').replace('fluorescent_v1','tv_aerial_v1').replace('legacy_fixture','legacy_aerial').replace('fixture.vmdl','aerial.vmdl').replace('capture-fluorescent','capture-aerial').replace('import-fluorescent','import-aerial')
a=t.index('var key=new SceneLight');b=t.index('            var pixmap=',a)
t=t[:a]+'''var key=new SceneLight(world,new Vector3(50,-70,110),350,Color.White*1.8f);
        var fill=new SceneLight(world,new Vector3(-60,40,60),300,new Color(.75f,.85f,1f)*.8f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(82,-100,84)),("detail",new Vector3(57,-68,99))})
        {
            var aim=name=="detail"?new Vector3(0,0,62):new Vector3(0,0,37);
            var camera=new SceneCamera("TV aerial review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=name=="detail"?40:43,ZNear=.1f,ZFar=500,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.2f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
'''+t[b:]
t=t.replace('new Editor.Pixmap(1200,700)','new Editor.Pixmap(1200,900)')
a=t.index('    elif mode in')
t=t[:a]+'''    elif mode=='context':
        r=e.script((HERE/'context.cs.txt').read_text(),'capture-aerial-context.cs')
        assert r['SourceUnchanged'] and not r['ErrorModels']
        (OUT/'context-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
'''
(HERE/'review.py').write_text(t)
code=(ROOT/'Sources/Zombies/cooler-v2/capture_engine.cs.txt').read_text().replace('output/asset-improvement-20261030/cooler/engine','output/riverside/tv-aerial-v1/context').replace('models/zombies/cooler_v2/cooler.vmdl','models/props/riverside/tv_aerial_v1/aerial.vmdl').replace('models/compare_old/old_cooler.vmdl','models/props/riverside/tv_aerial_v1/legacy_aerial.vmdl')
code=code.replace('"Volumetric Fog"','"Volumetric Fog", "Roof Air Conditioners", "Store Ceiling Lights", "Pole Insulators", "Street Lights"')
a=code.index('var views = ');b=code.index('\nvar scene = ',a)
code=code[:a]+'''var at=new Vector3(1033.5f,794.7722f,123f);
var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("close",at+new Vector3(85,-85,85),at+Vector3.Up*58,46f,true),
    ("roof",at+new Vector3(155,-175,98),at+Vector3.Up*35,52f,true)
};
'''+code[b:]
code=code.replace('newObject = scene.GetAllObjects(false).Single(g => g.Name == "Cooler");','''var low=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath?.Equals("models/maps/riverside/riverside_low.vmdl",StringComparison.OrdinalIgnoreCase)==true);
        low.Model=Model.Load("models/props/riverside/tv_aerial_v1/low_without_aerial.vmdl");
        newObject=new GameObject(false,"TV aerial review");newObject.WorldPosition=at;
        newObject.Components.Create<ModelRenderer>().Model=cooler;''')
code=code.replace('wait < 90','wait < 30').replace('new Bitmap(1536, 1024)','new Bitmap(1280,840)')
(HERE/'context.cs.txt').write_text(code)
print('Review scripts ready')
