var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed");
var results=new System.Collections.Generic.List<object>();
foreach(var name in new[]{"lowtide_east","lowtide_west","lowtide_backdrop","lowtide_finish"})
{
    cancellationToken.ThrowIfCancellationRequested();
    var current=Model.Load("models/maps/lowtide/"+name+".vmdl");
    var candidate=Model.Load("models/maps/lowtide/construction_review/"+name+".vmdl");
    var a=current.GetVertices();var b=candidate.GetVertices();
    var ai=current.GetIndices();var bi=candidate.GetIndices();
    var verticesMatch=a.Length==b.Length && Enumerable.Range(0,a.Length).All(i=>a[i].Position==b[i].Position);
    var indicesMatch=ai.SequenceEqual(bi);
    var materials=current.Materials.Select(m=>m.ResourcePath).ToArray();
    var expected=candidate.Materials.Select(m=>m.ResourcePath.Replace("/construction_review/","/")).ToArray();
    if(!verticesMatch || !indicesMatch || !materials.SequenceEqual(expected))throw new Exception("Production differs from reviewed model: "+name);
    results.Add(new{name,Triangles=ai.Length/3,Vertices=a.Length,verticesMatch,indicesMatch,Materials=materials});
}
var result=new{models=results,AllMatch=true,Game.IsPlaying,Scene=Editor.SceneEditorSession.Active?.Scene?.Source?.ResourcePath,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-readback.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return new{AllMatch=true,Models=results.Count,Game.IsPlaying};
