var project=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(project,"output/lowtide/quality-pass");
var scenePath=System.IO.Path.Combine(project,"Assets/scenes/maps/Lowtide/lowtide.scene");
var before=System.IO.File.ReadAllBytes(scenePath);
var backup=System.IO.Path.Combine(folder,"static-shadow-before.scene");
if(System.IO.File.Exists(backup)&&!before.SequenceEqual(System.IO.File.ReadAllBytes(backup))) throw new Exception("Static baseline already exists and differs; inspect before re-staging");
var root=System.Text.Json.Nodes.JsonNode.Parse(before).AsObject();
var meshNames=new System.Collections.Generic.HashSet<string>{"Fleet","East","West","Dressing East","Dressing West","Backdrop","Masonry Details","Tidal Details","Harbour Details"};
var meshes=root["GameObjects"].AsArray().Single(o=>o["Name"]?.GetValue<string>()=="Lowtide")["Children"].AsArray().Where(o=>meshNames.Contains(o["Name"]?.GetValue<string>())).ToArray();
var lamps=root["GameObjects"].AsArray().Single(o=>o["Name"]?.GetValue<string>()=="Lights")["Children"].AsArray().Where(o=>o["Components"].AsArray().Any(c=>new[]{"Sandbox.PointLight","Sandbox.SpotLight"}.Contains(c["__type"]?.GetValue<string>()))).ToArray();
if(meshes.Length!=9||lamps.Length!=24)throw new Exception("Unexpected fixed geometry or lamp count");
var stage=Scene.CreateEditorScene();
stage.Name="Lowtide static flag serialization preview";
try
{
    using(stage.Push())
    {
        foreach(var source in meshes.Concat(lamps))
        {
            var go=new GameObject(false,"Static serialization");
            go.Deserialize(source.AsObject());
            go.IsStatic=true;
            var native=go.Serialize();
            source["Flags"]=native["Flags"].DeepClone();
            if(source["Flags"].GetValue<long>()!=32768)throw new Exception("Unexpected native flags");
            go.Destroy();
        }
    }
    System.IO.File.WriteAllBytes(backup,before);
    System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"static-shadow-candidate.scene"),root.ToJsonString(new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
    return new {meshes=meshes.Length,lamps=lamps.Length,productionSceneChanged=false};
}
finally {stage.Destroy();}
