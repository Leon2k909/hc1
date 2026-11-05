"""Native import and isolated review; no writes to the saved map."""
from pathlib import Path
import json,sys,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
OUT=ROOT/'output/riverside/fluorescent-v1';mode=sys.argv[1]
with Editor() as e:
    if mode=='import':
        m=json.loads((OUT/'manifest.json').read_text())
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        scene='Assets/scenes/maps/Riverside/riverside.scene'
        # Other chats may save unrelated scene work. This import never writes the scene; geometry guards stay strict.
        assert all(sha(ROOT/p)==h for p,h in m['protected'].items() if p!=scene),'Store source changed; rebuild the review.'
        m['protected'][scene]=sha(ROOT/scene)
        (OUT/'manifest.json').write_text(json.dumps(m,indent=2))
        r=e.script((HERE/'import.cs.txt').read_text(),'import-fluorescent.cs')
        (OUT/'native-import.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
        m=json.loads((OUT/'manifest.json').read_text())
        paths=[p[7:] for p in m['files'] if p.endswith('.vmat')]+[m['resource'],m['background'],'models/props/riverside/fluorescent_v1/legacy_fixture.vmdl']
        results=[dict(path=p,result=e.call('asset_compile',dict(path=p))) for p in paths]
        (OUT/'native-compile.json').write_text(json.dumps(results,indent=2))
        assert all(i['result']['Success'] for i in results)
        print(json.dumps(dict(Compiled=len(results),Success=True)))
    elif mode=='isolated':
        code=r'''
var session=Editor.SceneEditorSession.Active;var before=new{Id=session.Scene.Id,Dirty=session.HasUnsavedChanges,Game.IsPlaying};
var output=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/fluorescent-v1");
var paths=new System.Collections.Generic.List<string>();
foreach(var variant in new[]{"before","after"})
{
    var model=Model.Load("models/props/riverside/fluorescent_v1/"+(variant=="before"?"legacy_fixture.vmdl":"fixture.vmdl"));
    if(model.IsError)throw new Exception("Fixture failed to load");
    var world=new SceneWorld();
    try
    {
        var item=new SceneObject(world,model,Transform.Zero);
        var key=new SceneLight(world,new Vector3(10,-20,-35),200,Color.White*.85f);
        var fill=new SceneLight(world,new Vector3(-35,20,-20),200,new Color(.75f,.85f,1f)*.45f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(47,-34,-26)),("underside",new Vector3(8,-15,-56))})
        {
            var camera=new SceneCamera("Fluorescent fixture review") { World=world,Position=eye,Rotation=Rotation.LookAt(new Vector3(0,0,1)-eye),
                FieldOfView=45,ZNear=.1f,ZFar=300,Size=new Vector2(1200,700),AmbientLightColor=Color.White*.12f,
                BackgroundColor=new Color(.06f,.07f,.075f),AntiAliasing=true,EnablePostProcessing=true};
            var pixmap=new Editor.Pixmap(1200,700);Sandbox.SandboxToolExtensions.RenderToPixmap(camera,pixmap,false);
            var path=System.IO.Path.Combine(output,name+"-"+variant+".png");pixmap.SavePng(path);paths.Add(path);
        }
    }
    finally{world.Delete();}
}
return new{PreviewOnly=true,UserStatePreserved=session.Scene.Id==before.Id&&session.HasUnsavedChanges==before.Dirty&&Game.IsPlaying==before.IsPlaying,Images=paths};
'''
        r=e.script(code,'capture-fluorescent-isolated.cs')
        assert r['UserStatePreserved'];(OUT/'isolated-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
    elif mode in ('context','installed'):
        code=(ROOT/'Sources/Zombies/cooler-v2/capture_engine.cs.txt').read_text()
        code=code.replace('output/asset-improvement-20261030/cooler/engine','output/riverside/fluorescent-v1/context')
        code=code.replace('models/zombies/cooler_v2/cooler.vmdl','models/props/riverside/fluorescent_v1/fixture.vmdl')
        code=code.replace('models/compare_old/old_cooler.vmdl','models/props/riverside/fluorescent_v1/legacy_fixture.vmdl')
        a=code.index('var views = ');b=code.index('\nvar scene = ',a)
        code=code[:a]+'''var at=new Vector3(760f,-150f,145.4f);
var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("close",at+new Vector3(-42,-30,-40),at+Vector3.Up,50f,true),
    ("room",at+new Vector3(-100,-65,-56),at+Vector3.Up,60f,true)
};
'''+code[b:]
        code=code.replace('"Volumetric Fog"','"Volumetric Fog", "Roof Air Conditioners"')
        code=code.replace('newObject = scene.GetAllObjects(false).Single(g => g.Name == "Cooler");','''var store=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath?.Equals("models/maps/riverside/riverside_store.vmdl",StringComparison.OrdinalIgnoreCase)==true);
        store.Model=Model.Load("models/props/riverside/fluorescent_v1/store_without_fixture.vmdl");
        newObject=new GameObject(false,"Fluorescent fixture review");newObject.WorldPosition=at;
        newObject.Components.Create<ModelRenderer>().Model=cooler;''')
        code=code.replace('wait < 90','wait < 30').replace('new Bitmap(1536, 1024)','new Bitmap(1280,840)')
        if mode=='installed':
            begin=code.index('var store=scene.GetAllComponents<ModelRenderer>()');end=code.index('        oldObject = ',begin)
            code=code[:begin]+'newObject=scene.GetAllObjects(false).Single(g=>g.Name=="Store Fluorescent 1");\n'+code[end:]
            code=code.replace('"Roof Air Conditioners"','"Roof Air Conditioners", "Store Ceiling Lights"')
            code=code.replace('models/props/riverside/fluorescent_v1/legacy_fixture.vmdl','models/props/riverside/fluorescent_v1/fixture.vmdl')
            code=code.replace('new[] { "before", "after" }','new[] { "after" }')
            code=code.replace('output/riverside/fluorescent-v1/context','output/riverside/fluorescent-v1/installed')
        r=e.script(code,'capture-fluorescent-context.cs')
        assert r['SourceUnchanged'] and not r['ErrorModels']
        (OUT/(mode+'-capture.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
