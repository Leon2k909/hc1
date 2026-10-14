var folder = System.IO.Path.Combine(Project.Current.GetRootPath(), "output/lowtide/quality-pass");
var request = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "lighting-preview-request.json")));
var name = request["name"].GetValue<string>();
var skyFactor = request["skyFactor"].GetValue<float>();
var useGi = request["useGi"].GetValue<bool>();
var qa = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("Hc1LowtideFinishQa")).First(t => t != null);
var field = qa.GetField("captureScene", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
if (field.GetValue(null) is Scene busy && busy.IsValid()) throw new InvalidOperationException("Existing QA capture is still active.");
var editedScene = Editor.SceneEditorSession.Active?.Scene;
var gameScene = Game.ActiveScene;
var gameCameraPosition = gameScene?.Camera?.WorldPosition.ToString();
var gameCameraRotation = gameScene?.Camera?.WorldRotation.ToString();
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, name + "-request.json"), request.ToJsonString());
var view = request["camera"]?.AsArray().Select(v => v.GetValue<float>()).ToArray() ?? new[] { 620f, -300f, 78f, 620f, 600f, 155f, 80f };
qa.GetMethod("Shot").Invoke(null, new object[] { name, view[0], view[1], view[2], view[3], view[4], view[5], view[6], -999f });
var preview = field.GetValue(null) as Scene;
if (!preview.IsValid()) throw new InvalidOperationException("QA scene was not created.");
using (preview.Push())
{
    if (request["staticWorld"] is { } staticWorld)
    {
        foreach (var renderer in preview.GetAllComponents<ModelRenderer>().Where(r=>r.GameObject.Parent?.Name=="Lowtide" && r.GameObject.Name!="Water" && r.GameObject.Name!="Glass"))
        {
            renderer.GameObject.IsStatic=staticWorld.GetValue<bool>();
            // The helper already created render objects before this override.
            // Refresh their flags as a fresh load from the saved scene would.
            typeof(ModelRenderer).GetMethod("UpdateObject",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).Invoke(renderer,null);
        }
        foreach (var light in preview.GetAllComponents<Light>().Where(l=>l is PointLight || l is SpotLight))
            light.GameObject.IsStatic=staticWorld.GetValue<bool>();
    }
    if (request["contactStrength"] is { } contactStrength)
    {
        var original = Material.Load("materials/lowtide/interior/lt_concrete.vmat");
        var copy = original.CreateCopy("Lowtide floor comparison " + name);
        copy.Set("g_flFloorContact", contactStrength.GetValue<float>());
        var count = 0;
        foreach (var renderer in preview.GetAllComponents<ModelRenderer>().Where(r => r.GameObject.Name == "East" || r.GameObject.Name == "West"))
        {
            for (var i=0; i<renderer.Materials.Count; i++)
                if (renderer.Materials.GetOriginal(i) == original)
                {
                    renderer.Materials.SetOverride(i, copy);
                    count++;
                }
            renderer.Materials.Apply();
        }
        if (count != 2) throw new Exception($"Expected two floor material slots, found {count}");
    }
    foreach (var sun in preview.GetAllComponents<DirectionalLight>()) sun.SkyColor *= skyFactor;
    foreach (var point in preview.GetAllComponents<PointLight>().Where(p => p.GameObject.Name.Contains("Warehouse") || p.GameObject.Name.Contains("Mezzanine")).ToArray())
    {
        var strength = request["lampFactor"]?.GetValue<float>() ?? 1f;
        point.LightColor *= strength;
        if (request["spots"]?.GetValue<bool>() == true)
        {
            var lamp = point.GameObject;
            var spot = lamp.Components.Create<SpotLight>();
            spot.WorldRotation = Rotation.LookAt(Vector3.Down);
            spot.Radius = point.Radius;
            spot.LightColor = point.LightColor;
            spot.Attenuation = point.Attenuation;
            spot.ConeOuter = request["coneOuter"]?.GetValue<float>() ?? 85;
            spot.ConeInner = request["coneInner"]?.GetValue<float>() ?? 50;
            spot.Shadows = true;
            spot.ShadowHardness = .25f;
            point.Enabled = false;
        }
    }
    if (useGi)
    {
        var volumeFiles = request["giVolumeFiles"]?.AsArray().Select(v=>v.GetValue<string>()).ToArray()
            ?? new[] { request["giVolumeFile"]?.GetValue<string>() ?? "live-gi-interior-test-volume.json" };
        foreach (var volumeFile in volumeFiles)
        {
            var source = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, volumeFile))).AsObject();
            var holder = new GameObject(false, "Lighting comparison GI");
            holder.Deserialize(source);
            var gi = holder.Components.Get<IndirectLightVolume>();
            gi.RuntimeIntensity = request["giIntensity"].GetValue<float>();
            gi.RuntimeContrast = request["giContrast"].GetValue<float>();
        }
    }
}
for (int n=0; n<120 && preview.IsValid(); n++)
{
    await Task.Delay(250, cancellationToken);
    if(n==24 && preview.IsValid() && request["staticWorld"] is not null)
    {
        var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Static;
        var mapper=typeof(SceneLight).Assembly.GetType("Sandbox.Rendering.ShadowMapper");
        var entries=(System.Collections.IEnumerable)mapper.GetField("Entries",flags).GetValue(null);
        var cache=new System.Collections.Generic.List<object>();
        foreach(var entry in entries)
        {
            var type=entry.GetType();
            var reference=(WeakReference<object>)type.GetField("Light",flags).GetValue(entry);
            if(!reference.TryGetTarget(out var target)||target is not SceneLight light) continue;
            var owner=(GameObject)typeof(SceneObject).GetProperty("GameObject",flags).GetValue(light);
            if(owner?.Scene!=preview) continue;
            cache.Add(new{name=owner.Name,owner.IsStatic,cached=type.GetField("StaticCache",flags).GetValue(entry)!=null,resolution=type.GetField("CurrentResolution",flags).GetValue(entry)});
        }
        var evidence=new{scene=preview.Name,userScene=gameScene?.Name,userCameraPosition=gameCameraPosition,userCameraRotation=gameCameraRotation,
            models=preview.GetAllComponents<ModelRenderer>().Where(r=>r.GameObject.Parent?.Name=="Lowtide").Select(r=>new{r.GameObject.Name,r.GameObject.IsStatic,nativeStatic=r.SceneObject?.Flags.IsStatic}).ToArray(),cache};
        System.IO.File.WriteAllText(System.IO.Path.Combine(folder,name+"-static-cache.json"),System.Text.Json.JsonSerializer.Serialize(evidence,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    }
}
if (preview.IsValid()) throw new TimeoutException("QA capture still running. Inspect before retrying.");
if (Editor.SceneEditorSession.Active?.Scene != editedScene || Game.ActiveScene != gameScene) throw new Exception("User scene changed during comparison.");
return new { name, skyFactor, useGi, userScenePreserved = true, cameraStayedFixed=gameCameraPosition==gameScene?.Camera?.WorldPosition.ToString() && gameCameraRotation==gameScene?.Camera?.WorldRotation.ToString(), status = System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "capture-status.txt")) };
