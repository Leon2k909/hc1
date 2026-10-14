var project=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(project,"output/lowtide/quality-pass");
var stage=System.IO.Path.Combine(folder,"weathering-stage/Assets");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"weathering-before/manifest.json")));
foreach(var pair in manifest.AsObject())
{
    var hash=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(System.IO.Path.Combine(project,pair.Key)))).ToLowerInvariant();
    if(hash!=pair.Value.GetValue<string>())throw new Exception("Source changed since staging: "+pair.Key);
}
foreach(var source in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories).OrderBy(p=>p.EndsWith(".meta")?0:p.EndsWith(".png")?1:2))
{
    var destination=System.IO.Path.Combine(project,"Assets",System.IO.Path.GetRelativePath(stage,source));
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.Copy(source,destination,true);
    if(!source.EndsWith(".meta"))Editor.AssetSystem.RegisterFile(destination);
}
var shader=await Editor.EditorUtility.CompileShader("shaders/hc1_brick.shader",new Sandbox.Engine.Shaders.ShaderCompileOptions(),cancellationToken);
if(!shader.Success)throw new Exception("Biofilm shader compile failed; inspect diagnostics");
var materials=new System.Collections.Generic.List<object>();
foreach(var source in System.IO.Directory.GetFiles(stage,"*.vmat",System.IO.SearchOption.AllDirectories))
{
    var relative=System.IO.Path.GetRelativePath(stage,source).Replace('\\','/');
    var asset=Editor.AssetSystem.FindByPath(relative);
    materials.Add(new{path=relative,success=asset.Compile(false)});
}
var report=new{shader=shader.Success,materials,userScene=Game.ActiveScene?.Name};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"weathering-compile.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
