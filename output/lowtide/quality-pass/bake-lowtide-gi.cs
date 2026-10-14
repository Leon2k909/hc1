var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output/lowtide/quality-pass");
var request = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "gi-bake-request.json")));
var name = request["name"].GetValue<string>();
var side = request["side"]?.GetValue<string>() ?? "east";
if (side != "east" && side != "west") throw new ArgumentException("Expected east or west warehouse");
if (Scene.All.Any(s => s.IsValid() && s.Name == "Lowtide GI bake preview")) throw new Exception("A lighting bake is already running. Inspect it before retrying.");
var scene = Scene.CreateEditorScene();
scene.Name = "Lowtide GI bake preview";
var flags = System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var updaterType = typeof(IndirectLightVolume).Assembly.GetType("Sandbox.DDGIProbeUpdaterCubemapper") ?? throw new Exception("Engine probe baker unavailable");
object updater = null;
IndirectLightVolume volume = null;
CancellationTokenSource bakeCancellation = null;
var output = System.IO.Path.Combine(folder, name);
System.IO.Directory.CreateDirectory(output);
System.IO.File.WriteAllText(System.IO.Path.Combine(output, "request.json"), request.ToJsonString());
var statusPath = System.IO.Path.Combine(output, "status.txt");
try
{
    var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(project, "Assets/scenes/maps/Lowtide/lowtide.scene"))).AsObject();
    var keep = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase) { "Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes" };
    var objects = new System.Text.Json.Nodes.JsonArray();
    foreach (var node in root["GameObjects"].AsArray()) if (node["Name"] is { } label && keep.Contains(label.GetValue<string>())) objects.Add(node.DeepClone());
    root["GameObjects"] = objects;
    root["SceneProperties"]["NavMesh"]["Enabled"] = false;
    root["SceneProperties"]["WantsSystemScene"] = false;
    CameraComponent camera;
    using (scene.Push())
    {
        scene.Deserialize(root);
        scene.Name = "Lowtide GI bake preview";
        foreach (var old in scene.GetAllComponents<IndirectLightVolume>().ToArray()) old.Destroy();
        foreach (var old in scene.GetAllComponents<SpotLight>().Where(p=>p.GameObject.Name.Contains("Warehouse")||p.GameObject.Name.Contains("Mezzanine")).ToArray()) old.Destroy();
        foreach (var sun in scene.GetAllComponents<DirectionalLight>()) sun.SkyColor *= request["skyFactor"].GetValue<float>();
        foreach (var point in scene.GetAllComponents<PointLight>().Where(p => p.GameObject.Name.Contains("Warehouse") || p.GameObject.Name.Contains("Mezzanine")).ToArray())
        {
            var spot = point.GameObject.Components.Create<SpotLight>();
            spot.WorldRotation = Rotation.LookAt(Vector3.Down);
            spot.Radius = point.Radius;
            spot.LightColor = point.LightColor * request["lampFactor"].GetValue<float>();
            spot.Attenuation = point.Attenuation;
            spot.ConeOuter = request["coneOuter"].GetValue<float>();
            spot.ConeInner = request["coneInner"].GetValue<float>();
            spot.Shadows = true;
            spot.ShadowHardness = .25f;
            point.Enabled = false;
        }
        var cameraObject = new GameObject(true, "GI bake warmup camera");
        camera = cameraObject.Components.Create<CameraComponent>();
        camera.WorldPosition = new Vector3(-300,-620,78);
        camera.WorldRotation = Rotation.LookAt(new Vector3(900,0,77));
        camera.CustomSize = new Vector2(640,360);
        scene.EditorTick(.016f,.016f);
        using var warmup = new Bitmap(640,360);
        camera.RenderToBitmap(warmup);
    }
    System.IO.File.WriteAllText(statusPath, "Loading preview resources");
    await Task.Delay(3500, cancellationToken);
    var renderProbe = typeof(EnvmapProbe).GetMethod("RenderCubemap", flags, null, Type.EmptyTypes, null);
    for (int bounce=0;bounce<3;bounce++)
        foreach (var probe in scene.GetAllComponents<EnvmapProbe>())
        {
            using (scene.Push()) renderProbe.Invoke(probe,null);
            await Task.Delay(16,cancellationToken);
        }
    using (scene.Push())
    {
        var holder = new GameObject(true, side == "east" ? "Warehouse East Bounced Light" : "Warehouse West Bounced Light");
        volume = holder.Components.Create<IndirectLightVolume>();
        // Cover the receiving floor, inner wall faces and ceiling. A volume
        // inset into the free room air excludes those receivers entirely.
        volume.Bounds = side == "east"
            ? new BBox(new Vector3(-402,-1002,-8),new Vector3(1152,-238,360))
            : new BBox(new Vector3(-402,238,-8),new Vector3(1152,1002,360));
        volume.BlendDistance = 24;
        volume.ProbeDensity = request["density"].GetValue<int>();
        volume.NormalBias = 3;
        volume.ViewBias = 4;
        volume.RenderExcludeTags.Add("water");
        bakeCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, holder.EnabledToken);
        typeof(IndirectLightVolume).GetField("_bakeCts",flags).SetValue(volume,bakeCancellation);
        var previous = typeof(IndirectLightVolume).GetProperty("Probes",flags).GetValue(volume);
        typeof(IndirectLightVolume).GetMethod("ComputeProbeRelocation",flags).Invoke(volume,null);
        var probeArray = (Array)typeof(IndirectLightVolume).GetProperty("Probes",flags).GetValue(volume);
        System.IO.File.WriteAllText(System.IO.Path.Combine(output,"probe-count.txt"), $"Counts={volume.ProbeCounts}; Probes={probeArray?.Length}");
        updater = Activator.CreateInstance(updaterType,flags,null,new object[]{volume},null);
        var irradiance = (Texture)updaterType.GetProperty("GeneratedIrradianceTexture",flags).GetValue(updater);
        var distance = (Texture)updaterType.GetProperty("GeneratedDistanceTexture",flags).GetValue(updater);
        var relocation = (Texture)typeof(IndirectLightVolume).GetProperty("GeneratedRelocationTexture",flags).GetValue(volume);
        typeof(IndirectLightVolume).GetField("_bakePreview",flags).SetValue(volume,new ValueTuple<Texture,Texture,Texture>(irradiance,distance,relocation));
        typeof(IndirectLightVolume).GetMethod("MarkDirty",flags).Invoke(volume,null);
        System.IO.File.WriteAllText(statusPath,$"Baking direct and bounced light: {volume.ProbeCounts}");
        var completed = await (Task<bool>)updaterType.GetMethod("RunAsync",flags).Invoke(updater,new object[]{bakeCancellation.Token});
        if (!completed) throw new OperationCanceledException("Engine probe bake did not complete");
        Graphics.FlushGPU();
        var identifier = Guid.NewGuid().ToString("N");
        var relativeFolder = $"scenes/maps/lowtide/lowtide_scene_data/ddgi/{name}";
        System.IO.Directory.CreateDirectory(System.IO.Path.Combine(project,"Assets",relativeFolder));
        foreach (var item in new[] { ("IrradianceTexture",irradiance), ("DistanceTexture",distance), ("RelocationTexture",relocation) })
        {
            var relative = $"{relativeFolder}/{side}_{item.Item1.ToLowerInvariant()}_{identifier}.vtex";
            var bytes = item.Item2.SaveToVtex();
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(project,"Assets",relative+"_c"),bytes);
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,item.Item1+".vtex.bin"),bytes);
            var loaded = Texture.Load(relative);
            if (loaded is null || loaded.IsError) throw new Exception($"Baked texture failed to load: {relative}");
            typeof(IndirectLightVolume).GetProperty(item.Item1,flags).SetValue(volume,loaded);
        }
        typeof(IndirectLightVolume).GetProperty("BakeVersion",flags).SetValue(volume,1);
        typeof(IndirectLightVolume).GetField("_bakePreview",flags).SetValue(volume,null);
        volume.RuntimeIntensity = 4;
        volume.RuntimeContrast = .85f;
        typeof(IndirectLightVolume).GetMethod("MarkDirty",flags).Invoke(volume,null);
        System.IO.File.WriteAllText(System.IO.Path.Combine(output,"volume.json"),holder.Serialize().ToJsonString());
        System.IO.File.WriteAllText(statusPath,"Finished");
        return new { name, volume.ProbeCounts, probes=((Array)typeof(IndirectLightVolume).GetProperty("Probes",flags).GetValue(volume)).Length, status="Finished", sceneSaved=false };
    }
}
catch(Exception ex)
{
    System.IO.File.WriteAllText(statusPath,"Failed: "+ex.ToString());
    throw;
}
finally
{
    if (updater is IDisposable disposable) disposable.Dispose();
    if (volume.IsValid())
    {
        typeof(IndirectLightVolume).GetField("_bakePreview",flags).SetValue(volume,null);
        typeof(IndirectLightVolume).GetField("_bakeCts",flags).SetValue(volume,null);
        var relocation = (Texture)typeof(IndirectLightVolume).GetProperty("GeneratedRelocationTexture",flags).GetValue(volume);
        relocation?.Dispose();
        typeof(IndirectLightVolume).GetProperty("GeneratedRelocationTexture",flags).SetValue(volume,null);
    }
    bakeCancellation?.Dispose();
    scene.Destroy();
}
