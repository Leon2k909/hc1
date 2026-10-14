var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project,"output/lowtide/quality-pass");
var scenePath = System.IO.Path.Combine(project,"Assets/scenes/maps/Lowtide/lowtide.scene");
var baseline = System.IO.File.ReadAllBytes(System.IO.Path.Combine(folder,"warehouse-lighting-before/lowtide.scene"));
if (!baseline.SequenceEqual(System.IO.File.ReadAllBytes(scenePath))) throw new Exception("Saved scene changed since lighting baseline; inspect it first");
var root = System.Text.Json.Nodes.JsonNode.Parse(baseline).AsObject();
var lights = root["GameObjects"].AsArray().Single(n=>n["Name"]?.GetValue<string>()=="Lights").AsObject();
var stage = Scene.CreateEditorScene();
stage.Name = "Lowtide lighting serialization preview";
try
{
    var serialized = new System.Text.Json.Nodes.JsonObject();
    var stagedLights = new System.Text.Json.Nodes.JsonArray();
    using(stage.Push())
    {
        var parent = new GameObject(false,"Lights");
        parent.Deserialize(lights);
        foreach (var point in stage.GetAllComponents<PointLight>().Where(p=>p.GameObject.Name.Contains("Warehouse")||p.GameObject.Name.Contains("Mezzanine")).ToArray())
        {
            var go = point.GameObject;
            var spot = go.Components.Create<SpotLight>();
            spot.WorldRotation = Rotation.LookAt(Vector3.Down);
            spot.Radius = point.Radius;
            spot.LightColor = point.LightColor * .85f;
            spot.Attenuation = point.Attenuation;
            spot.ConeOuter = 55;
            spot.ConeInner = 30;
            spot.Shadows = true;
            spot.ShadowHardness = .25f;
            point.Enabled = false;
            var native = go.Serialize();
            var source = lights["Children"].AsArray().Single(n=>n["Name"]?.GetValue<string>()==go.Name);
            source["Rotation"] = native["Rotation"].DeepClone();
            var oldPoint = source["Components"].AsArray().Single(c=>c["__type"]?.GetValue<string>()=="Sandbox.PointLight");
            oldPoint["__enabled"] = false;
            var spotData = native["Components"].AsArray().Single(c=>c["__type"]?.GetValue<string>()=="Sandbox.SpotLight");
            source["Components"].AsArray().Add(spotData.DeepClone());
            stagedLights.Add(new System.Text.Json.Nodes.JsonObject {
                ["name"] = go.Name, ["rotation"] = native["Rotation"].DeepClone(),
                ["pointGuid"] = oldPoint["__guid"].DeepClone(), ["spot"] = spotData.DeepClone()
            });
        }
        if (stagedLights.Count!=18) throw new Exception("Expected eighteen pendant conversions");
    }
    var volumes = new System.Text.Json.Nodes.JsonArray();
    foreach (var side in new[]{"east","west"})
    {
        var data = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,$"warehouse-{side}-v3/volume.json"))).AsObject();
        var gi = data["Components"].AsArray().Single();
        foreach(var key in new[]{"IrradianceTexture","DistanceTexture","RelocationTexture"})
        {
            var texture=Texture.Load(gi[key].GetValue<string>());
            if(texture is null || texture.IsError) throw new Exception($"Missing baked texture {key}");
        }
        lights["Children"].AsArray().Add(data.DeepClone());
        volumes.Add(data.DeepClone());
    }
    serialized["lights"]=stagedLights;
    serialized["volumes"]=volumes;
    serialized["engineVersion"]="26.10.13";
    serialized["notes"]="Baked direct light plus one bounce. Re-bake after changing static warehouse geometry, fixtures or daylight. Runtime intensity 4 and contrast 0.85 compensate for the limited bounce count.";
    var sourceFolder=System.IO.Path.Combine(project,"Sources/Lowtide/lighting");
    System.IO.Directory.CreateDirectory(sourceFolder);
    System.IO.File.WriteAllText(System.IO.Path.Combine(sourceFolder,"warehouse-lighting.json"),serialized.ToJsonString(new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"warehouse-lighting-candidate.scene"),root.ToJsonString(new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    return new {stage="Ready",spots=stagedLights.Count,volumes=volumes.Count,productionSceneChanged=false};
}
finally { stage.Destroy(); }
