var destination = System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "output/belltower/quality/before");
System.IO.Directory.CreateDirectory(destination);
var source = Editor.SceneEditorSession.Active.Scene;
var before = new { Game.IsPlaying, Scene = source.Name, SceneId = source.Id };
var visual = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase) {
    "Sun", "Sky", "Fog", "Town", "Trees and planting", "Lights", "Street Detail", "Ambient", "Reflections", "Indirect Light", "Look", "Volumetric Fog"
};
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "Assets/scenes/maps/Belltower/belltower.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
root["GameObjects"] = objects;
root["SceneProperties"]["NavMesh"]["Enabled"] = false;
root["SceneProperties"]["WantsSystemScene"] = false;
System.IO.File.WriteAllText(System.IO.Path.Combine(destination, "visual-scene.json"), root.ToJsonString());
var scene = new Scene();
try {
    CameraComponent camera;
    using (scene.Push()) {
        scene.Deserialize(root);
        var holder = new GameObject(false, "Belltower quality camera");
        camera = holder.Components.Create<CameraComponent>();
        camera.ZNear = 4; camera.ZFar = 100000;
        var tonemap = holder.Components.Create<Tonemapping>();
        tonemap.Mode = Tonemapping.TonemappingMode.ACES;
        tonemap.AutoExposureEnabled = false;
        tonemap.ExposureCompensation = 1f;
        var bloom = holder.Components.Create<Bloom>();
        bloom.Mode = SceneCamera.BloomAccessor.BloomMode.Additive;
        bloom.Strength = .15f; bloom.Threshold = 1.33f;
        holder.Enabled = true;
        scene.EditorTick(.016f, .016f);
    }
    Vector3 World(Vector3 plan) => new(plan.y, -plan.x, plan.z);
    var views = new[] {
        (Name: "square", Eye: new Vector3(-560,-320,64), Target: new Vector3(0,700,330), Fov: 85f),
        (Name: "market", Eye: new Vector3(-1760,1275,64), Target: new Vector3(0,1240,170), Fov: 80f),
        (Name: "west_street", Eye: new Vector3(-1800,125,64), Target: new Vector3(-400,160,130), Fov: 80f),
        (Name: "terrace", Eye: new Vector3(-1760,-950,64), Target: new Vector3(0,-950,110), Fov: 80f)
    };
    using var bitmap = new Bitmap(1600,900);
    foreach(var view in views) {
        cancellationToken.ThrowIfCancellationRequested();
        using(scene.Push()) {
            camera.WorldPosition = World(view.Eye);
            camera.WorldRotation = Rotation.LookAt(World(view.Target)-World(view.Eye));
            camera.FieldOfView = view.Fov;
            scene.EditorTick(.016f,.016f);
            camera.RenderToBitmap(bitmap);
        }
        await Task.Delay(1200,cancellationToken);
        using(scene.Push()) camera.RenderToBitmap(bitmap);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, view.Name+".png"),bitmap.ToPng());
    }
    return new { Before = before, Game.IsPlaying, SourceUnchanged = source.Id == before.SceneId, Directory = destination, VisualRoots = objects.Count };
} finally { scene.Destroy(); }
