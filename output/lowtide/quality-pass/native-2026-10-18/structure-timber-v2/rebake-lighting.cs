if(Game.IsPlaying)throw new Exception("Preserve the running match");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2");
var output=System.IO.Path.Combine(folder,"lighting");
System.IO.Directory.CreateDirectory(output);
var volumes=session.Scene.GetAllComponents<IndirectLightVolume>().OrderBy(v=>v.GameObject.Name).ToArray();
if(volumes.Length!=2||volumes.Any(v=>!v.GameObject.Name.StartsWith("Warehouse ")||v.ProbeCounts.ToString()!="20,10,6"))throw new Exception("Unexpected lighting scope");
var before=new System.Text.Json.Nodes.JsonArray();
foreach(var v in volumes)before.Add(v.GameObject.Serialize());
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"volumes-before.json"),before.ToJsonString());
var records=new System.Collections.Generic.List<object>();
try
{
    session.MakeActive(true);
    await Task.Delay(350,cancellationToken);
    foreach(var volume in volumes)
    {
        if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session)throw new Exception("Editor state changed");
        cancellationToken.ThrowIfCancellationRequested();
        var old=volume.IrradianceTexture?.ResourcePath;
        System.IO.File.WriteAllText(System.IO.Path.Combine(output,"status.txt"),"Baking "+volume.GameObject.Name);
        using(session.Scene.Push())await volume.BakeProbes(cancellationToken);
        if(volume.IrradianceTexture==null||volume.IrradianceTexture.IsError||volume.DistanceTexture==null||volume.DistanceTexture.IsError||volume.RelocationTexture==null||volume.RelocationTexture.IsError||volume.IrradianceTexture.ResourcePath==old)throw new Exception("Bake did not produce valid new textures");
        var serialized=volume.GameObject.Serialize();
        System.IO.File.WriteAllText(System.IO.Path.Combine(output,volume.GameObject.Name.Contains("East")?"east.json":"west.json"),serialized.ToJsonString());
        records.Add(new{volume.GameObject.Name,volume.ProbeCounts,Irradiance=volume.IrradianceTexture.ResourcePath,Distance=volume.DistanceTexture.ResourcePath,Relocation=volume.RelocationTexture.ResourcePath});
        System.IO.File.WriteAllText(System.IO.Path.Combine(output,"progress.json"),System.Text.Json.JsonSerializer.Serialize(records));
    }
    System.IO.File.WriteAllText(System.IO.Path.Combine(output,"status.txt"),"Finished");
}
catch(Exception ex)
{
    System.IO.File.WriteAllText(System.IO.Path.Combine(output,"status.txt"),"Failed: "+ex);
    throw;
}
finally
{
    if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
return new{records,session.HasUnsavedChanges,TabRestored=Editor.SceneEditorSession.Active==previous,TimeUtc=DateTime.UtcNow};
