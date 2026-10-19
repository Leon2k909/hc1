var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current/lighting");
var rows=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"progress.json"))).AsArray();
var copies=new System.Collections.Generic.List<(string source,string target)>();
foreach(var row in rows)
{
    var side=row["Name"].GetValue<string>().Contains("East")?"east":"west";
    foreach(var field in new[]{"Irradiance","Distance","Relocation"})
    {
        var source=row[field].GetValue<string>();
        var target=$"scenes/maps/lowtide/lowtide_scene_data/ddgi/warehouse-{side}-v4/{field.ToLowerInvariant()}.vtex";
        if(System.IO.File.Exists(System.IO.Path.Combine(root,"Assets",target+"_c")))throw new Exception("Target exists: "+target);
        if(Texture.Load(source).IsError)throw new Exception("Invalid bake source");
        copies.Add((source,target));
    }
}
var report=new System.Collections.Generic.List<object>();
foreach(var pair in copies)
{
    var source=System.IO.Path.Combine(root,"Assets",pair.source+"_c");
    var target=System.IO.Path.Combine(root,"Assets",pair.target+"_c");
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
    System.IO.File.Copy(source,target,false);
    var texture=Texture.Load(pair.target);
    if(texture==null||texture.IsError)throw new Exception("Stored bake did not load");
    report.Add(new{Source=pair.source,Target=pair.target,Hash=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(target))).ToLowerInvariant(),texture.Width,texture.Height,texture.Depth});
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"stored.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
