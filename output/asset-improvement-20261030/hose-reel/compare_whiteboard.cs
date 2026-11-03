
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/hose-reel");
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes", "Indirect Light" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Riverdale/riverdale.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
root["GameObjects"] = objects;
if (root["SceneProperties"]?["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject sceneProperties) sceneProperties["WantsSystemScene"] = false;
Model model = null;
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    GameObject board = null;
    var exposures = new System.Collections.Generic.List<string>();
    var frame = Rotation.FromYaw(180.0f);
    var origin = new Vector3(2000.0f, -680.0f, 28.5f);
    using (scene.Push())
    {
        scene.Deserialize(root);
        foreach (var tonemap in scene.GetAllComponents<Tonemapping>())
        {
            var hold = ( tonemap.MinimumExposure + tonemap.MaximumExposure ) / 2f;
            exposures.Add( tonemap.Mode + " " + tonemap.MinimumExposure + ".." + tonemap.MaximumExposure );
            tonemap.AutoExposureEnabled = true;
            tonemap.MinimumExposure = tonemap.MaximumExposure = hold;
            tonemap.Rate = 10;
        }
        if (model is not null)
        {
            board = new GameObject(false, "New whiteboard");
            board.WorldPosition = origin;
            board.WorldRotation = frame;
            board.Components.Create<ModelRenderer>().Model = model;
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
    for (var wait = 0; wait < 240; wait++)
    {
        using (scene.Push()) { scene.EditorTick(.016f, .016f); preRender.Invoke(scene, null); }
        if (model is not null)
            foreach (var material in model.Materials)
                foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                    texture.MarkUsed(4096);
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target)[] { ("front", new Vector3(70f, 0f, 34f), new Vector3(0f, 0f, 17f)), ("angle", new Vector3(36f, 40f, 30f), new Vector3(2f, 0f, 16f)), ("close", new Vector3(20f, -6f, 26f), new Vector3(2f, 0f, 16f)), ("eye", new Vector3(110f, -30f, 36f), new Vector3(0f, 0f, 18f)) };
    foreach (var variant in new[] { "settling", "old", "new" })
    {
        if (variant == "new" && board is null) break;
        using (scene.Push()) { if (board is not null) board.Enabled = variant != "old"; }
        foreach (var shot in shots)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var bitmap = new Bitmap(1600, 900);
            for (var f = 0; f < 12; f++)
            {
                using (scene.Push())
                {
                    camera.WorldPosition = origin + frame * shot.eye;
                    camera.WorldRotation = Rotation.LookAt((origin + frame * shot.target) - (origin + frame * shot.eye));
                    camera.FieldOfView = 75;
                    scene.EditorTick(.016f, .016f);
                    preRender.Invoke(scene, null);
                    preCameraRender.Invoke(scene, null);
                    camera.RenderToBitmap(bitmap);
                }
                if (model is not null)
                    foreach (var material in model.Materials)
                        foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                            texture.MarkUsed(4096);
                await Task.Delay(16, cancellationToken);
            }
            if (variant != "settling") System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, variant + "_" + shot.name + ".png"), bitmap.ToPng());
        }
    }
    return new { Renderers = scene.GetAllComponents<ModelRenderer>().Count(), Exposures = exposures, Model = model?.ResourcePath, Error = model?.IsError };
}
finally { scene.Destroy(); }
