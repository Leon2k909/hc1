
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/propane");
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Moon", "Sky", "Fog", "Look", "Riverside", "Lights", "Fires", "Burn Drums", "Reflection Probes", "Volumetric Fog" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Riverside/riverside.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
root["GameObjects"] = objects;
if (root["SceneProperties"]?["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject sceneProperties) sceneProperties["WantsSystemScene"] = false;
var news = new (string path, Vector3 offset, float yaw)[] { ("models/props/riverside/propane_v2/propane_100.vmdl", new Vector3(0.0f, 18.0f, 0.0f), 23.0f), ("models/props/riverside/propane_v2/propane_100.vmdl", new Vector3(0.0f, 0.0f, 0.0f), 141.0f), ("models/props/riverside/propane_v2/propane_100.vmdl", new Vector3(0.0f, -18.0f, 0.0f), 278.0f) };
var models = new System.Collections.Generic.List<Model>();
if (true) foreach (var n in news) models.Add(Model.Load(n.path));
Model model = models.FirstOrDefault();
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    GameObject board = null;
    var exposures = new System.Collections.Generic.List<string>();
    var frame = Rotation.FromYaw(0.0f);
    var origin = new Vector3(-560.0f, 362.0f, 96.0f);
    var originNew = new Vector3(-560.0f, 282.0f, 96.0f);
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
            board = new GameObject(false, "New propane");
            board.WorldPosition = originNew;
            for (var k = 0; k < news.Length; k++)
            {
                var piece = new GameObject(board, true, "Bottle");
                piece.LocalPosition = news[k].offset;
                piece.LocalRotation = Rotation.FromYaw(news[k].yaw);
                piece.Components.Create<ModelRenderer>().Model = models[k];
            }
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
        foreach (var m in models)
            foreach (var material in m.Materials)
                foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                    texture.MarkUsed(4096);
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target)[] { ("front", new Vector3(80f, 0f, 40f), new Vector3(0f, 0f, 24f)), ("angle", new Vector3(50f, 45f, 50f), new Vector3(0f, 0f, 22f)), ("close", new Vector3(24f, -10f, 50f), new Vector3(0f, 0f, 42f)), ("eye", new Vector3(140f, -40f, 64f), new Vector3(0f, 0f, 24f)) };
    foreach (var variant in new[] { "settling", "old", "new" })
    {
        if (variant == "new" && board is null) break;
        using (scene.Push()) { if (board is not null) board.Enabled = variant != "old"; }
        var at = variant == "new" ? originNew : origin;
        foreach (var shot in shots)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var bitmap = new Bitmap(1600, 900);
            for (var f = 0; f < 12; f++)
            {
                using (scene.Push())
                {
                    camera.WorldPosition = at + frame * shot.eye;
                    camera.WorldRotation = Rotation.LookAt(frame * shot.target - frame * shot.eye);
                    camera.FieldOfView = 75;
                    scene.EditorTick(.016f, .016f);
                    preRender.Invoke(scene, null);
                    preCameraRender.Invoke(scene, null);
                    camera.RenderToBitmap(bitmap);
                }
                foreach (var m in models)
                    foreach (var material in m.Materials)
                        foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                            texture.MarkUsed(4096);
                await Task.Delay(16, cancellationToken);
            }
            if (variant != "settling") System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, variant + "_" + shot.name + ".png"), bitmap.ToPng());
        }
    }
    return new { Renderers = scene.GetAllComponents<ModelRenderer>().Count(), Exposures = exposures, Models = models.Select(m => m.ResourcePath + (m.IsError ? " ERROR" : "")).ToArray() };
}
finally { scene.Destroy(); }
