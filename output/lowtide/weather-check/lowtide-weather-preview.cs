var active = Game.ActiveScene;
var scene = Scene.CreateEditorScene();
var folder = System.IO.Path.Combine(@"D:\Documents\s&box projects\hc1\forked-shooter-main", "output", "lowtide", "weather-check");
System.IO.Directory.CreateDirectory(folder);
try
{
    var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(@"D:\Documents\s&box projects\hc1\forked-shooter-main\Assets\scenes\maps\Lowtide\lowtide.scene")).AsObject();
    var visuals = new[] { "Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes" };
    var objects = new System.Text.Json.Nodes.JsonArray();
    foreach (var go in root["GameObjects"].AsArray())
        if (visuals.Contains(go["Name"]?.GetValue<string>())) objects.Add(go.DeepClone());
    root["GameObjects"] = objects;
    root["SceneProperties"]["NavMesh"]["Enabled"] = false;
    root["SceneProperties"]["WantsSystemScene"] = false;
    using (scene.Push()) scene.Deserialize(root);
    CameraComponent camera;
    Facepunch.Weather weather;
    using (scene.Push())
    {
        var holder = new GameObject(scene, true, "Weather QA camera");
        camera = holder.Components.Create<CameraComponent>();
        camera.WorldPosition = new Vector3(-1300, 0, 125);
        camera.WorldRotation = Rotation.LookAt(new Vector3(530, 0, 205) - camera.WorldPosition);
        camera.FieldOfView = 72;
        camera.CustomSize = new Vector2(1280, 720);
        camera.ZNear = 1;
        camera.ZFar = 100000;
        camera.EnablePostProcessing = true;
        var weatherObject = new GameObject(scene, true, "Weather QA");
        weatherObject.NetworkMode = NetworkMode.Never;
        weather = weatherObject.Components.Create<Facepunch.Weather>();
        scene.EditorTick(.016f, .016f);
    }
    using var bitmap = new Bitmap(1280, 720);
    using (scene.Push()) camera.RenderToBitmap(bitmap);
    await Task.Delay(2000, cancellationToken);
    using (scene.Push())
    {
        camera.RenderToBitmap(bitmap);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder, "clear.png"), bitmap.ToPng());
    }
    var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
    var hasSky = (bool)typeof(Facepunch.Weather).GetMethod("HasSky", flags).Invoke(weather, null);
    var lookType = typeof(Facepunch.RainView).GetNestedType("RainLook", System.Reflection.BindingFlags.NonPublic);
    var look = Activator.CreateInstance(lookType, true);
    var sky = scene.GetAllComponents<SkyBox2D>().Single();
    var sun = scene.GetAllComponents<DirectionalLight>().Single();
    var originalMaterial = sky.SkyMaterial;
    var originalTint = sky.Tint;
    var originalLight = sun.LightColor;
    object rainy;
    var stages = new System.Collections.Generic.List<object>();
    using (scene.Push())
    {
        lookType.GetMethod("Apply", flags).Invoke(look, new object[] {scene, 1f, 5f, 0f, .6f});
        scene.EditorTick(.032f, .016f);
        camera.RenderToBitmap(bitmap);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder, "steady.png"), bitmap.ToPng());
        rainy = new {Material = sky.SkyMaterial?.ResourcePath, Error = sky.SkyMaterial?.IsError, PrivateSky = sky.SkyMaterial != originalMaterial, sun.LightColor, sun.SkyColor};
        lookType.GetMethod("Restore", flags).Invoke(look, null);
        foreach (var stage in new[] {0f, .49f, .51f, 1f})
        {
            lookType.GetMethod("Apply", flags).Invoke(look, new object[] {scene, stage, 5f * stage, 0f, .6f});
            scene.EditorTick(.1f + stage, .016f);
            camera.RenderToBitmap(bitmap);
            var path = System.IO.Path.Combine(folder, $"front-{stage:0.00}.png");
            System.IO.File.WriteAllBytes(path, bitmap.ToPng());
            stages.Add(new {Stage = stage, Path = path, sun.LightColor});
        }
        lookType.GetMethod("Restore", flags).Invoke(look, null);
    }
    return new
    {
        HasSky = hasSky, Rainy = rainy,
        Stages = stages,
        Restored = sky.SkyMaterial == originalMaterial && sky.Tint == originalTint && sun.LightColor == originalLight,
        RuntimeUnchanged = Game.ActiveScene == active,
        PreviewDirectory = folder
    };
}
finally { scene.Destroy(); }
