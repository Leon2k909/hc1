// Spillway's cargo yard props as the game draws them, to choose which to rebuild: run with sbox-cli --call run_csharp
// through candidates.py. Loads Spillway's visual roots into an isolated editor scene, so the open scene and play state are
// never touched and nothing is saved. map_kit's plan (e, n, z) is engine (n, -e, z).
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/spillway-cargo/candidates");
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
    // 1024 at most: the editor is shared, and a whole map's textures at full size have run it out of video memory.
    var textureNames = new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "SkyTexture" };
    var textures = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is not null).SelectMany(r => r.Model.Materials).Distinct()
        .SelectMany(m => textureNames.Select(m.GetTexture).Append(m.FirstTexture)).Where(t => t is not null).Distinct().ToArray();
    for (var wait = 0; wait < 120; wait++)
    {
        foreach (var texture in textures) texture.MarkUsed(1024);
        using (scene.Push()) { scene.EditorTick(.016f, .016f); preRender.Invoke(scene, null); }
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target, float fov)[] { ("turbine_tanks", new Vector3(560f, 1650f, 110f), new Vector3(700f, 2200f, 90f), 62f), ("pump_tanks", new Vector3(1310f, -1900f, 90f), new Vector3(1310f, -2260f, 80f), 72f), ("canvas_cover", new Vector3(-1470f, -1560f, 200f), new Vector3(-1705f, -1550f, 165f), 60f), ("container_03", new Vector3(-1330f, 1240f, 80f), new Vector3(-1560f, 1380f, 60f), 62f), ("jersey", new Vector3(770f, 960f, 62f), new Vector3(840f, 1100f, 20f), 60f), ("wall_unit", new Vector3(300f, 1170f, 70f), new Vector3(220f, 1320f, 70f), 60f), ("case_stack_east", new Vector3(520f, -1180f, 80f), new Vector3(650f, -1300f, 40f), 60f) };
    foreach (var shot in shots)
    {
        cancellationToken.ThrowIfCancellationRequested();
        using var bitmap = new Bitmap(1400, 860);
        for (var frame = 0; frame < 20; frame++)
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
    return new { Written = shots.Length, Renderers = scene.GetAllComponents<ModelRenderer>().Count() };
}
catch (Exception error)
{
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination, "capture-error.txt"), error.ToString());
    throw;
}
finally { scene.Destroy(); }
