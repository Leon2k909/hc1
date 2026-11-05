var output = System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "output/sewage/pipe-texture-v1");
var material = Material.Load("materials/sewage/pipe-texture-v1/pipe.vmat");
if (material is null || material.IsError) throw new Exception("Pipe material has not compiled successfully.");
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "Assets/scenes/maps/sewage/sewage.scene"))).AsObject();
var objects = root["GameObjects"].AsArray();
foreach (var item in objects.ToArray())
{
    var name = item["Name"]?.GetValue<string>() ?? "";
    if (name == "zombies" || name == "game_setup" || name.Contains("spawn", StringComparison.OrdinalIgnoreCase)) objects.Remove(item);
}
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject props)
{
    props["WantsSystemScene"] = false;
    if (props["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
}
var scene = Scene.CreateEditorScene();
try
{
    using (scene.Push()) scene.Deserialize(root);
    var renderer = scene.GetAllObjects(true).Single(x => x.Name == "Waterworks pipework").Components.Get<ModelRenderer>();
    var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
    var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
    var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
    CameraComponent camera;
    using (scene.Push())
    {
        var holder = new GameObject(false, "Pipe texture review camera");
        camera = holder.Components.Create<CameraComponent>();
        camera.IsMainCamera = false;
        camera.ZNear = 1;
        camera.ZFar = 20000;
        camera.WorldPosition = new Vector3(-638.180359f,661.684265f,159.773834f);
        camera.WorldRotation = Rotation.From(new Angles(-8.29982376f,91.0002441f,0));
        camera.FieldOfView = 80;
        holder.Enabled = true;
    }
    foreach (var variant in new[] { "before", "after" })
    {
        using (scene.Push()) renderer.MaterialOverride = variant == "after" ? material : null;
        using var bitmap = new Bitmap(1280,720);
        for (var frame = 0; frame < 24; frame++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using (scene.Push())
            {
                scene.EditorTick(.016f,.016f);
                preRender.Invoke(scene,null);
                preCameraRender.Invoke(scene,null);
                camera.RenderToBitmap(bitmap,false);
            }
            await Task.Delay(16,cancellationToken);
        }
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,variant+".png"),bitmap.ToPng());
    }
    return new { Success=true, Material=material.ResourcePath, ActiveScene=Editor.SceneEditorSession.Active.Scene.Name, Output=output };
}
finally { scene.Destroy(); }
