
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/notice-board");
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes", "Indirect Light" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Riverdale/riverdale.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
root["GameObjects"] = objects;
if (root["SceneProperties"]?["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject sceneProperties) sceneProperties["WantsSystemScene"] = false;
var model = Model.Load("models/maps/riverdale/notice_board_v2/notice_board.vmdl");
if (model is null || model.IsError) throw new InvalidOperationException("The new board hasn't compiled.");
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    GameObject board;
    var exposures = new System.Collections.Generic.List<string>();
    var frame = Rotation.FromYaw(0f);
    var origin = new Vector3(1200f, 670f, 346f);
    using (scene.Push())
    {
        scene.Deserialize(root);
        foreach (var tonemap in scene.GetAllComponents<Tonemapping>())
        {
            // The top of the map's range: the exposure this dim corner settles at when a player looks at it.
            var hold = tonemap.MaximumExposure;
            exposures.Add( tonemap.Mode + " " + tonemap.MinimumExposure + ".." + tonemap.MaximumExposure );
            tonemap.AutoExposureEnabled = true;
            tonemap.MinimumExposure = tonemap.MaximumExposure = hold;
            tonemap.Rate = 10;
        }
        board = new GameObject(false, "New board");
        board.WorldPosition = origin + frame * new Vector3(1.3f, 0, 0);
        board.WorldRotation = frame;
        board.Components.Create<ModelRenderer>().Model = model;
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
        foreach (var material in model.Materials)
            foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                texture.MarkUsed(4096);
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target)[] { ("front", new Vector3(120f, 0f, 18f), new Vector3(0f, 0f, 12f)), ("close", new Vector3(34f, -6f, 15f), new Vector3(0f, -6f, 12f)), ("angle", new Vector3(46f, 62f, 20f), new Vector3(0f, 2f, 12f)), ("detail", new Vector3(15f, 9f, 9f), new Vector3(0.5f, 9f, 7f)), ("far", new Vector3(500f, 0f, 18f), new Vector3(0f, 0f, 12f)), ("further", new Vector3(780f, 40f, 40f), new Vector3(0f, 0f, 12f)) };
    foreach (var variant in new[] { "settling", "old", "new" })
    {
        using (scene.Push()) { board.Enabled = variant != "old"; }
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
                    camera.FieldOfView = 70;
                    scene.EditorTick(.016f, .016f);
                    preRender.Invoke(scene, null);
                    preCameraRender.Invoke(scene, null);
                    camera.RenderToBitmap(bitmap);
                }
                foreach (var material in model.Materials)
                    foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                        texture.MarkUsed(4096);
                await Task.Delay(16, cancellationToken);
            }
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, variant + "_" + shot.name + ".png"), bitmap.ToPng());
        }
    }
    return new { Renderers = scene.GetAllComponents<ModelRenderer>().Count(), Exposures = exposures, Materials = model.Materials.Select(m => m.ResourcePath + " " + m.GetTexture("g_tColor")?.Width).ToArray() };
}
finally { scene.Destroy(); }
