// Fixed offscreen render+readback latency, not gameplay FPS. ABBA ordering
// controls drift; each arm warms caches before recording 24 samples.
var project=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(project,"output/lowtide/quality-pass");
var edited=Editor.SceneEditorSession.Active;
var userScene=Game.ActiveScene;
var qa=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("Hc1LowtideFinishQa")).First(t=>t!=null);
var binding=System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance;
if(qa.GetField("captureScene",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Static).GetValue(null) is Scene busy&&busy.IsValid())throw new Exception("Capture still running");
var source=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(project,"Assets/scenes/maps/Lowtide/lowtide.scene"))).AsObject();
var include=new System.Collections.Generic.HashSet<string>{"Sun","Sky","Fog","Look","Lowtide","Trees","Lights","Reflection Probes"};
var roots=new System.Text.Json.Nodes.JsonArray();
foreach(var item in source["GameObjects"].AsArray())if(include.Contains(item["Name"]?.GetValue<string>()))roots.Add(item.DeepClone());
source["GameObjects"]=roots;
source["SceneProperties"]["NavMesh"]["Enabled"]=false;
source["SceneProperties"]["WantsSystemScene"]=false;
var scene=Scene.CreateEditorScene();
scene.Name="Lowtide offscreen shadow benchmark";
var runs=new System.Collections.Generic.List<object>();
try
{
    CameraComponent camera;
    using(scene.Push())
    {
        scene.Deserialize(source);
        var go=new GameObject(true,"Fixed benchmark camera");
        camera=go.Components.Create<CameraComponent>();
        camera.WorldPosition=new Vector3(-300,-620,78);
        camera.WorldRotation=Rotation.LookAt(new Vector3(600,-620,155)-camera.WorldPosition);
        camera.FieldOfView=80;
        camera.CustomSize=new Vector2(1024,576);
        camera.ZNear=1;camera.ZFar=100000;
        camera.EnablePostProcessing=false;
    }
    using var bitmap=new Bitmap(1024,576);
    float elapsed=0;
    using(scene.Push()){scene.EditorTick(elapsed+=.016f,.016f);camera.RenderToBitmap(bitmap);}
    await Task.Delay(1200,cancellationToken);
    var renderProbe=typeof(EnvmapProbe).GetMethod("RenderCubemap",binding,null,Type.EmptyTypes,null);
    foreach(var probe in scene.GetAllComponents<EnvmapProbe>())
    {
        using(scene.Push())renderProbe.Invoke(probe,null);
        await Task.Delay(16,cancellationToken);
    }
    var models=scene.GetAllComponents<ModelRenderer>().Where(r=>r.GameObject.Parent?.Name=="Lowtide"&&r.GameObject.Name!="Glass"&&r.GameObject.Name!="Water").ToArray();
    var lamps=scene.GetAllComponents<Light>().Where(l=>l is PointLight||l is SpotLight).ToArray();
    foreach(var enabled in new[]{false,true,true,false})
    {
        using(scene.Push())
        {
            foreach(var model in models){model.GameObject.IsStatic=enabled;typeof(ModelRenderer).GetMethod("UpdateObject",binding).Invoke(model,null);}
            foreach(var lamp in lamps)lamp.GameObject.IsStatic=enabled;
        }
        var samples=new System.Collections.Generic.List<double>();
        for(int frame=0;frame<36;frame++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using(scene.Push())
            {
                scene.EditorTick(elapsed+=.016f,.016f);
                var watch=System.Diagnostics.Stopwatch.StartNew();
                camera.RenderToBitmap(bitmap);
                watch.Stop();
                if(frame>=12)samples.Add(watch.Elapsed.TotalMilliseconds);
            }
            await Task.Delay(16,cancellationToken);
        }
        var ordered=samples.OrderBy(v=>v).ToArray();
        runs.Add(new{staticCaching=enabled,medianMs=(ordered[11]+ordered[12])/2,p90Ms=ordered[21],minMs=ordered[0],maxMs=ordered[^1],samples});
    }
    var report=new{measurement="Offscreen camera RenderToBitmap wall-clock latency including GPU readback; not gameplay FPS",resolution="1024x576",order="ABBA",samplesPerRun=24,warmupFramesPerRun=12,postprocessing=false,models=models.Length,lamps=lamps.Length,runs,userScenePreserved=userScene==Game.ActiveScene,userEditorPreserved=edited==Editor.SceneEditorSession.Active};
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"static-shadow-offscreen-benchmark.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    return report;
}
finally{scene.Destroy();}
