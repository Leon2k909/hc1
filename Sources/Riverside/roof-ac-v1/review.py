"""Import private review resources and render them without modifying the user's scene or play state."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3]
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
OUT=ROOT/'output/riverside/roof-ac-v1'
mode=sys.argv[1]
with Editor() as e:
    if mode=='import':
        code=r'''
var project=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(project,"output/riverside/roof-ac-v1");
var stage=System.IO.Path.Combine(folder,"stage");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var pair in manifest["protected"].AsObject())
    if(Hash(System.IO.Path.Combine(project,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Source changed: regenerate the review before importing: "+pair.Key);
var session=Editor.SceneEditorSession.Active;
var before=new {Id=session.Scene.Id,Dirty=session.HasUnsavedChanges,Playing=Game.IsPlaying};
var files=manifest["files"].AsObject();
int Priority(string p)=>p.EndsWith(".png")?0:p.EndsWith(".vmat")?1:p.EndsWith(".mtl")?2:p.EndsWith(".obj")?3:4;
foreach(var pair in files)
{
    if(pair.Key.Contains("..") || !(pair.Key.StartsWith("Assets/models/props/riverside/roof_ac_v1/") || pair.Key.StartsWith("Assets/materials/riverside/roof_ac_v1/")))throw new Exception("Unexpected target");
    if(Hash(System.IO.Path.Combine(stage,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Staged input changed");
}
foreach(var pair in files.OrderBy(p=>Priority(p.Key)))
{
    var target=System.IO.Path.Combine(project,pair.Key);
    if(System.IO.File.Exists(target)&&Hash(target)==pair.Value.GetValue<string>())continue;
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
    System.IO.File.Copy(System.IO.Path.Combine(stage,pair.Key),target,true);
    Editor.AssetSystem.RegisterFile(target);
}
return new {PreviewOnly=true,Files=files.Count,UserStatePreserved=session.Scene.Id==before.Id&&session.HasUnsavedChanges==before.Dirty&&Game.IsPlaying==before.Playing};
'''
        result=e.script(code,'import-roof-ac.cs')
        print(json.dumps(result,indent=2),flush=True)
        (OUT/'native-import.json').write_text(json.dumps(result,indent=2))
        catalog=e.call('search_tools',dict(query='asset_compile'))
        print(json.dumps([t for t in catalog['tools'] if t['name']=='asset_compile'],indent=2),flush=True)
        manifest=json.loads((OUT/'manifest.json').read_text())
        resources=[p[7:] for p in manifest['files'] if p.endswith('.vmat')]+[manifest['resource'],'models/props/riverside/roof_ac_v1/legacy_ac.vmdl',manifest['background']]
        results=[]
        for p in resources:
            r=e.call('asset_compile',dict(path=p));results.append(dict(path=p,result=r))
        (OUT/'native-compile.json').write_text(json.dumps(results,indent=2))
        print(json.dumps(results,indent=2),flush=True)
    elif mode=='isolated':
        code=r'''
var session=Editor.SceneEditorSession.Active;
var before=new {Id=session.Scene.Id,Dirty=session.HasUnsavedChanges,Playing=Game.IsPlaying};
var output=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/roof-ac-v1");
var images=new System.Collections.Generic.List<string>();
var views=new[]{("three-quarter",new Vector3(-48,-52,43)),("top",new Vector3(-12,-27,68)),("side",new Vector3(-55,16,21))};
foreach(var variant in new[]{"before","after"})
{
    var model=Model.Load("models/props/riverside/roof_ac_v1/"+(variant=="before"?"legacy_ac.vmdl":"roof_ac.vmdl"));
    if(model.IsError)throw new Exception("Model did not compile");
    var world=new SceneWorld();
    try
    {
        var item=new SceneObject(world,model,Transform.Zero);
        var key=new SceneLight(world,new Vector3(-40,-35,65),250,new Color(1,.93f,.81f)*1.3f);
        var fill=new SceneLight(world,new Vector3(35,30,42),200,new Color(.69f,.8f,1f)*.5f);
        foreach(var (name,eye) in views)
        {
            var camera=new SceneCamera("Rooftop AC review") { World=world,Position=eye,Rotation=Rotation.LookAt(new Vector3(0,0,6)-eye),
                FieldOfView=42,ZNear=.1f,ZFar=300,Size=new Vector2(1000,800),AmbientLightColor=Color.White*.12f,
                BackgroundColor=new Color(.075f,.085f,.09f),AntiAliasing=true,EnablePostProcessing=true };
            var pixmap=new Editor.Pixmap(1000,800);
            Sandbox.SandboxToolExtensions.RenderToPixmap(camera,pixmap,false);
            var path=System.IO.Path.Combine(output,name+"-"+variant+".png");pixmap.SavePng(path);images.Add(path);
        }
    }
    finally{world.Delete();}
}
return new {PreviewOnly=true,UserStatePreserved=session.Scene.Id==before.Id&&session.HasUnsavedChanges==before.Dirty&&Game.IsPlaying==before.Playing,Images=images};
'''
        result=e.script(code,'capture-roof-ac-isolated.cs')
        (OUT/'isolated-capture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    elif mode in ('context','installed'):
        code=(ROOT/'Sources/Zombies/cooler-v2/capture_engine.cs.txt').read_text()
        code=code.replace('output/asset-improvement-20261030/cooler/engine','output/riverside/roof-ac-v1/context')
        code=code.replace('models/zombies/cooler_v2/cooler.vmdl','models/props/riverside/roof_ac_v1/roof_ac.vmdl')
        code=code.replace('models/compare_old/old_cooler.vmdl','models/props/riverside/roof_ac_v1/legacy_ac.vmdl')
        a=code.index('var views = ');b=code.index('\nvar scene = ',a)
        code=code[:a]+'''var ac=new Vector3(-640f,524.23195f,219.5f);
var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("close",ac+new Vector3(-44,-50,40),ac+Vector3.Up*6,50f,true),
    ("roof",ac+new Vector3(-120,-125,90),ac+Vector3.Up*4,54f,true)
};
'''+code[b:]
        code=code.replace('newObject = scene.GetAllObjects(false).Single(g => g.Name == "Cooler");','''var pad=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath?.Equals("models/maps/riverside/riverside_pad.vmdl",StringComparison.OrdinalIgnoreCase)==true);
        pad.Model=Model.Load("models/props/riverside/roof_ac_v1/pad_without_ac.vmdl");
        newObject=new GameObject(false,"Roof AC review");newObject.WorldPosition=ac;
        newObject.Components.Create<ModelRenderer>().Model=cooler;''')
        code=code.replace('wait < 90','wait < 30').replace('new Bitmap(1536, 1024)','new Bitmap(1280,840)')
        if mode=='installed':
            begin=code.index('var pad=scene.GetAllComponents<ModelRenderer>()')
            end=code.index('        oldObject = ',begin)
            code=code[:begin]+'newObject=scene.GetAllObjects(false).Single(g=>g.Name=="Office Rooftop AC");\n'+code[end:]
            code=code.replace('"Volumetric Fog"','"Volumetric Fog", "Roof Air Conditioners"')
            code=code.replace('models/props/riverside/roof_ac_v1/legacy_ac.vmdl','models/props/riverside/roof_ac_v1/roof_ac.vmdl')
            code=code.replace('new[] { "before", "after" }','new[] { "after" }')
            code=code.replace('output/riverside/roof-ac-v1/context','output/riverside/roof-ac-v1/installed')
        result=e.script(code,'capture-roof-ac-context.cs')
        assert result['SourceUnchanged'] and not result['ErrorModels']
        (OUT/(mode+'-capture.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
