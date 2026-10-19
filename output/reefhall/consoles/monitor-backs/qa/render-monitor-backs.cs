var scene = new Scene();
var folder = System.IO.Path.Combine(exchangeDirectory,"monitor-backs");
System.IO.Directory.CreateDirectory(folder);
try
{
    var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(
        System.IO.Path.Combine(Project.Current.GetRootPath(),"Assets/scenes/maps/ReefHall/reefhall.scene"))).AsObject();
    var objects = new System.Text.Json.Nodes.JsonArray();
    foreach (var item in root["GameObjects"].AsArray())
        if (new[] {"Ambient","Fog","Aquarium","Lights","Reflection Probes"}.Contains(item["Name"]?.GetValue<string>()))
            objects.Add(item.DeepClone());
    root["GameObjects"] = objects;
    root["SceneProperties"]["NavMesh"]["Enabled"] = false;
    root["SceneProperties"]["WantsSystemScene"] = false;
    CameraComponent camera;
    using (scene.Push())
    {
        scene.Deserialize(root);
        var holder = new GameObject(false,"Monitor inspection camera");
        camera = holder.Components.Create<CameraComponent>();
        camera.IsMainCamera = true;
        camera.ZNear = 2;
        camera.ZFar = 20000;
        var tone = holder.Components.Create<Tonemapping>();
        tone.Mode = Tonemapping.TonemappingMode.ACES;
        tone.AutoExposureEnabled = false;
        tone.ExposureCompensation = 1;
        holder.Enabled = true;
        scene.EditorTick(.016f,.016f);
    }
    Vector3 World(Vector3 p) => new(p.y,-p.x,p.z);
    var views = new (string name,Vector3 eye,Vector3 target,float fov)[] {
        ("engine-mixed-backs",new(2675,330,67),new(2612,307,51),88),
        ("engine-charcoal",new(2662,330,61),new(2612,330,52),60),
        ("engine-aluminium",new(2662,283.3333f,61),new(2612,283.3333f,52),60),
        ("engine-overview",new(2720,70,75),new(2600,260,43),72)
    };
    using var bitmap = new Bitmap(1600,1000);
    foreach (var view in views)
    {
        cancellationToken.ThrowIfCancellationRequested();
        using (scene.Push())
        {
            camera.WorldPosition = World(view.eye);
            camera.WorldRotation = Rotation.LookAt(World(view.target)-camera.WorldPosition);
            camera.FieldOfView = view.fov;
            scene.EditorTick(.016f,.016f);
            camera.RenderToBitmap(bitmap);
        }
        await Task.Delay(800,cancellationToken);
        using (scene.Push()) camera.RenderToBitmap(bitmap);
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,view.name+".png"),bitmap.ToPng());
    }
    return new {Folder=folder,ActiveScene=Editor.SceneEditorSession.Active?.Scene?.Name,Views=views.Select(v=>v.name).ToArray()};
}
finally { scene.Destroy(); }

