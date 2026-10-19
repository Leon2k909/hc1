var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2/lighting");
var ddgi=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"Assets/scenes/maps/lowtide/lowtide_scene_data/ddgi"))+System.IO.Path.DirectorySeparatorChar;
var rows=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"stored.json"))).AsArray();
if(rows.Count!=6)throw new Exception("Expected six retained texture copies");
var allVolumes=Editor.SceneEditorSession.All.SelectMany(s=>s.Scene.GetAllComponents<IndirectLightVolume>()).ToArray();
var sceneText=System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Assets/scenes/maps/Lowtide/lowtide.scene"));
var archives=new System.Collections.Generic.List<(string source,string target,string hash)>();
foreach(var row in rows)
{
    var source=row["Source"].GetValue<string>();
    var target=row["Target"].GetValue<string>();
    var hash=row["Hash"].GetValue<string>();
    if(allVolumes.Any(v=>new[]{v.IrradianceTexture?.ResourcePath,v.DistanceTexture?.ResourcePath,v.RelocationTexture?.ResourcePath}.Any(p=>string.Equals(p,source,StringComparison.OrdinalIgnoreCase))))throw new Exception("Generated source still referenced by a volume");
    if(sceneText.Contains(source,StringComparison.OrdinalIgnoreCase))throw new Exception("Generated source still referenced by saved scene");
    var sourceFile=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"Assets",source+"_c"));
    var stableFile=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"Assets",target+"_c"));
    if(!sourceFile.StartsWith(ddgi,StringComparison.OrdinalIgnoreCase)||!stableFile.StartsWith(ddgi,StringComparison.OrdinalIgnoreCase)||System.IO.Path.GetDirectoryName(sourceFile).TrimEnd('\\')!=ddgi.TrimEnd('\\'))throw new Exception("Source outside expected bake directory");
    string Digest(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
    if(Digest(sourceFile)!=hash||Digest(stableFile)!=hash)throw new Exception("Texture copy no longer matches reviewed bake");
    var archive=System.IO.Path.Combine(folder,"retired-generated",System.IO.Path.GetFileName(sourceFile));
    if(System.IO.File.Exists(archive))throw new Exception("Archive already exists; inspect before retry");
    archives.Add((sourceFile,archive,hash));
}
System.IO.Directory.CreateDirectory(System.IO.Path.Combine(folder,"retired-generated"));
foreach(var entry in archives)
{
    System.IO.File.Copy(entry.source,entry.target,false);
    var digest=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(entry.target))).ToLowerInvariant();
    if(digest!=entry.hash)throw new Exception("Archive mismatch");
    System.IO.File.Delete(entry.source);
}
var report=new {Status="archived_six_unreferenced_generated_bake_files",Count=archives.Count,PreservedStableV5=true,Game.IsPlaying,Files=archives.Select(x=>new {Source=x.source,Archive=x.target,Hash=x.hash}).ToArray()};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"cleanup.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
