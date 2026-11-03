// The new pallets beside the old slabs, drawn by s&box: run with sbox-cli --call run_csharp through compare.py. Loads Spillway's visual roots into an isolated editor scene, so the open scene and play state are
// never touched and nothing is saved. map_kit's plan (e, n, z) is engine (n, -e, z).
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "output/asset-improvement-20261030/spillway-cargo/pass2");
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
        var pallet = Model.Load("models/maps/spillway/pallet_v2/pallet.vmdl");
        if (pallet is null || pallet.IsError) throw new InvalidOperationException("The pallet hasn't compiled.");
        foreach (var (at, yaw) in new (Vector3, float)[] { (new Vector3(-745f, 255f, 0f), 92.0f), (new Vector3(-748f, 197f, 0f), 269.0f), (new Vector3(-747f, 196f, 4.75f), 94.5f), (new Vector3(-742f, 138f, 0f), 276.0f) })
        {
            var go = new GameObject(true, "New pallet");
            go.WorldPosition = at;
            go.WorldRotation = Rotation.FromYaw(yaw);
            go.Components.Create<ModelRenderer>().Model = pallet;
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
    var shots = new (string name, Vector3 eye, Vector3 target, float fov)[] { ("pair", new Vector3(-930f, 110f, 66f), new Vector3(-712f, 200f, 4f), 52f), ("pair_wide", new Vector3(-1060f, -60f, 120f), new Vector3(-705f, 190f, 10f), 50f), ("new_close", new Vector3(-835f, 205f, 42f), new Vector3(-745f, 197f, 4f), 50f), ("new_corner", new Vector3(-805f, 100f, 22f), new Vector3(-742f, 140f, 3f), 55f), ("new_top", new Vector3(-800f, 215f, 78f), new Vector3(-742f, 205f, 2f), 52f), ("old_close", new Vector3(-790f, 205f, 40f), new Vector3(-688f, 198f, 4f), 50f), ("far_12m", new Vector3(-1210f, 200f, 70f), new Vector3(-720f, 200f, 10f), 40f) };
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
    return new { Written = shots.Length, Renderers = scene.GetAllComponents<ModelRenderer>().Count() };
}
catch (Exception error)
{
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination, "capture-error.txt"), error.ToString());
    throw;
}
finally { scene.Destroy(); }
