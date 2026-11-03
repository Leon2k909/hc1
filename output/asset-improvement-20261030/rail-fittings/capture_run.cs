// The fuel pool's rail, drawn by s&box: run with sbox-cli --call run_csharp through capture.py.
// Loads the reactor hall's models and the map's lights into an isolated editor scene, so the open scene and play state are never touched and nothing is saved.
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/rail-fittings/after");
System.IO.Directory.CreateDirectory(destination);
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes", "Indirect Light" }, StringComparer.OrdinalIgnoreCase);
var models = new System.Collections.Generic.HashSet<string>(new[] { "Reactor Hall", "Reactor Hall Dressing", "Reactor Hall Detail", "Reactor Hall Fine", "Fuel Pool", "Pool Water", "Glass" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Riverdale/riverdale.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
{
    var name = item["Name"]?.GetValue<string>() ?? "";
    if (!visual.Contains(name)) continue;
    var copy = item.DeepClone();
    if (name == "Riverdale")
    {
        var kept = new System.Text.Json.Nodes.JsonArray();
        foreach (var child in copy["Children"].AsArray())
            if (models.Contains(child["Name"]?.GetValue<string>() ?? "")) kept.Add(child.DeepClone());
        copy["Children"] = kept;
    }
    objects.Add(copy);
}
root["GameObjects"] = objects;
if (root["SceneProperties"]?["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject sceneProperties) sceneProperties["WantsSystemScene"] = false;
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    using (scene.Push())
    {
        scene.Deserialize(root);
        foreach (var tonemap in scene.GetAllComponents<Tonemapping>())
        {
            var hold = ( tonemap.MinimumExposure + tonemap.MaximumExposure ) / 2f;
            tonemap.AutoExposureEnabled = true;
            tonemap.MinimumExposure = tonemap.MaximumExposure = hold;
            tonemap.Rate = 10;
        }
        var holder = new GameObject(false, "Capture camera");
        camera = holder.Components.Create<CameraComponent>();
        camera.ZNear = 1;
        camera.ZFar = 30000;
        holder.Enabled = true;
        scene.EditorTick(.016f, .016f);
        preRender.Invoke(scene, null);
        preCameraRender.Invoke(scene, null);
    }
    var textureNames = new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "SkyTexture" };
    foreach (var material in scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is not null).SelectMany(r => r.Model.Materials).Distinct())
        foreach (var texture in textureNames.Select(material.GetTexture).Append(material.FirstTexture).Where(t => t is not null).Distinct())
            texture.MarkUsed(1024);
    for (var wait = 0; wait < 60; wait++)
    {
        using (scene.Push()) { scene.EditorTick(.016f, .016f); preRender.Invoke(scene, null); }
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target, float fov)[] { ("close", new Vector3(400.9638866299392f, 219.06153827749839f, 53.0f), new Vector3(410.343847769018f, 202.82221915349743f, 45.0f), 40f), ("closer", new Vector3(404.7683888425871f, 210.21334712722933f, 48.0f), new Vector3(410.343847769018f, 202.82221915349743f, 45.0f), 40f), ("from_inside", new Vector3(422.6502137776578f, 185.15177988203138f, 53.0f), new Vector3(410.343847769018f, 202.82221915349743f, 45.0f), 40f), ("run", new Vector3(417.4876701527455f, 284.2214832579943f, 71.0f), new Vector3(400.40000972114547f, 176.91763539389876f, 37.0f), 55f), ("low", new Vector3(404.78755983203314f, 215.32449721963314f, 33.0f), new Vector3(410.343847769018f, 202.82221915349743f, 45.0f), 45f), ("corner", new Vector3(556f, 540f, 342f), new Vector3(580f, 560f, 328f), 45f) };
    foreach (var shot in shots)
    {
        cancellationToken.ThrowIfCancellationRequested();
        using var bitmap = new Bitmap(1280, 720);
        for (var frame = 0; frame < 12; frame++)
        {
            using (scene.Push())
            {
                camera.WorldPosition = shot.eye;
                camera.WorldRotation = Rotation.LookAt(shot.target - shot.eye);
                camera.FieldOfView = shot.fov;
                scene.EditorTick(.016f, .016f);
                preRender.Invoke(scene, null);
                preCameraRender.Invoke(scene, null);
                camera.RenderToBitmap(bitmap);
            }
            await Task.Delay(16, cancellationToken);
        }
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, shot.name + ".png"), bitmap.ToPng());
    }
    return new { Written = shots.Length, Renderers = scene.GetAllComponents<ModelRenderer>().Count(), ErrorModels = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is null || r.Model.IsError).Select(r => r.GameObject.Name).Take(6).ToArray() };
}
catch (Exception error)
{
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination, "capture-error.txt"), error.ToString());
    throw;
}
finally { scene.Destroy(); }
