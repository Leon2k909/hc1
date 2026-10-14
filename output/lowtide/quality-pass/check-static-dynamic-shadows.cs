var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass");
var userScene=Game.ActiveScene;
var userEditor=Editor.SceneEditorSession.Active;
var scene=Scene.CreateEditorScene();
scene.Name="Lowtide isolated static shadow check";
var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Static;
var mapper=typeof(SceneLight).Assembly.GetType("Sandbox.Rendering.ShadowMapper");
var evidence=new System.Collections.Generic.List<object>();
try
{
    CameraComponent camera;
    ModelRenderer floor,caster;
    SpotLight light;
    using(scene.Push())
    {
        var box=Model.Load("models/dev/box.vmdl");
        if(box.IsError) throw new Exception("Missing box model");
        ModelRenderer Box(string name,Vector3 size,Vector3 center,bool isStatic)
        {
            var go=new GameObject(true,name);
            go.IsStatic=isStatic;
            go.WorldScale=size/box.Bounds.Size;
            go.WorldPosition=center-box.Bounds.Center*go.WorldScale;
            var renderer=go.Components.Create<ModelRenderer>();
            renderer.Model=box;
            renderer.Tint=Color.White;
            return renderer;
        }
        floor=Box("Static floor",new Vector3(360,360,4),new Vector3(0,0,-2),true);
        caster=Box("Moving caster",new Vector3(24,24,60),new Vector3(0,0,30),false);
        var lamp=new GameObject(true,"Static spotlight");
        lamp.IsStatic=true;
        light=lamp.Components.Create<SpotLight>();
        light.WorldPosition=new Vector3(-50,-50,180);
        light.WorldRotation=Rotation.LookAt(Vector3.Down);
        light.Radius=500;
        light.LightColor=Color.White*3;
        light.ConeOuter=70;
        light.ConeInner=55;
        light.Shadows=true;
        var eye=new GameObject(true,"Diagnostic camera");
        camera=eye.Components.Create<CameraComponent>();
        camera.WorldPosition=new Vector3(260,-320,260);
        camera.WorldRotation=Rotation.LookAt(new Vector3(0,0,0)-camera.WorldPosition);
        camera.FieldOfView=60;
        camera.CustomSize=new Vector2(1024,768);
        camera.EnablePostProcessing=false;
        camera.ZNear=1;
        camera.ZFar=1000;
    }
    using var bitmap=new Bitmap(1024,768);
    float elapsed=0;
    foreach(var mode in new[]{"a-shadow","b-shadow","a-clear","b-clear"})
    {
        using(scene.Push())
        {
            caster.GameObject.WorldPosition=new Vector3(mode.StartsWith("a")?-40:40,0,0);
            light.Shadows=mode.EndsWith("shadow");
        }
        for(int frame=0;frame<20;frame++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using(scene.Push()) { scene.EditorTick(elapsed+=.016f,.016f); camera.RenderToBitmap(bitmap); }
            await Task.Delay(16,cancellationToken);
        }
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"static-dynamic-"+mode+".png"),bitmap.ToPng());
        object cache=null;
        foreach(var entry in (System.Collections.IEnumerable)mapper.GetField("Entries",flags).GetValue(null))
        {
            var type=entry.GetType();
            var reference=(WeakReference<object>)type.GetField("Light",flags).GetValue(entry);
            if(!reference.TryGetTarget(out var target)||target is not SceneLight native)continue;
            var owner=(GameObject)typeof(SceneObject).GetProperty("GameObject",flags).GetValue(native);
            if(owner?.Scene==scene) cache=type.GetField("StaticCache",flags).GetValue(entry);
        }
        evidence.Add(new{mode,staticFloor=floor.SceneObject.Flags.IsStatic,dynamicCaster=caster.SceneObject.Flags.IsStatic,cacheId=cache is null?0:System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(cache),casterPosition=caster.WorldPosition.ToString()});
    }
    var report=new{evidence,userScenePreserved=Game.ActiveScene==userScene,userEditorPreserved=Editor.SceneEditorSession.Active==userEditor};
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"static-dynamic-shadows.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    return report;
}
finally {scene.Destroy();}
