// Matched before and after shots of the pallet, drawn by s&box: run with sbox-cli --call run_csharp through compare2.py, once per setup.
// Each setup places its models and can hide the map's own slabs (the cargo model's rv_desk slot). Same cameras and held exposure every time. Loads Spillway's visual roots into an isolated editor scene, so the open scene and play state are
// never touched and nothing is saved. map_kit's plan (e, n, z) is engine (n, -e, z).
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/spillway-cargo/matched");
System.IO.Directory.CreateDirectory(destination);
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Sun", "Sky", "Fog", "Look", "Spillway", "Lights", "Reflection Probes", "Volumetric Fog" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/spillway/spillway.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
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
    var hiddenSlots = 0;
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
        foreach (var (path, at, yaw) in new (string, Vector3, float)[] {  })
        {
            var model = Model.Load(path);
            if (model is null || model.IsError) throw new InvalidOperationException($"{path} hasn't compiled.");
            var go = new GameObject(true, "Compared");
            go.WorldPosition = at;
            go.WorldRotation = Rotation.FromYaw(yaw);
            go.Components.Create<ModelRenderer>().Model = model;
        }
        if (false)
        {
            var hidden = Material.Load("models/compare_old/hidden.vmat");
            foreach (var renderer in scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath?.Contains("spillway_cargo") == true))
                for (var slot = 0; slot < renderer.Model.Materials.Length; slot++)
                    if (renderer.Model.Materials[slot]?.ResourcePath?.Contains("rv_desk") == true) { renderer.Materials.SetOverride(slot, hidden); hiddenSlots++; }
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
    // 1024 at most: the editor is shared, and a whole map's textures at full size have run it out of video memory.
    var textureNames = new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "SkyTexture" };
    var textures = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is not null).SelectMany(r => r.Model.Materials).Distinct()
        .SelectMany(m => textureNames.Select(m.GetTexture).Append(m.FirstTexture)).Where(t => t is not null).Distinct().ToArray();
    var palletModel = Model.Load("models/maps/spillway/pallet_v2/pallet.vmdl");
    var sharp = palletModel.Materials.Distinct().SelectMany(m => textureNames.Select(m.GetTexture).Append(m.FirstTexture)).Where(t => t is not null).Distinct().ToArray();
    for (var wait = 0; wait < 120; wait++)
    {
        foreach (var texture in textures) texture.MarkUsed(1024);
        foreach (var texture in sharp) texture.MarkUsed(2048);
        using (scene.Push()) { scene.EditorTick(.016f, .016f); preRender.Invoke(scene, null); }
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target, float fov)[] { ("place_before_standing", new Vector3(-878.0f, 127.0f, 66f), new Vector3(-688.0f, 197.0f, 3f), 50f), ("place_before_close", new Vector3(-793.0f, 187.0f, 44f), new Vector3(-686.0f, 197.0f, 4f), 52f), ("place_before_low", new Vector3(-773.0f, 82.0f, 20f), new Vector3(-688.0f, 157.0f, 3f), 55f), ("place_before_above", new Vector3(-763.0f, 202.0f, 100f), new Vector3(-688.0f, 197.0f, 0f), 62f) };
    foreach (var shot in shots)
    {
        cancellationToken.ThrowIfCancellationRequested();
        using var bitmap = new Bitmap(1400, 860);
        for (var frame = 0; frame < 20; frame++)
        {
            foreach (var texture in sharp) texture.MarkUsed(2048);
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
    return new { Written = shots.Length, HiddenSlots = hiddenSlots, Renderers = scene.GetAllComponents<ModelRenderer>().Count() };
}
catch (Exception error)
{
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination, "capture-error.txt"), error.ToString());
    throw;
}
finally { scene.Destroy(); }
