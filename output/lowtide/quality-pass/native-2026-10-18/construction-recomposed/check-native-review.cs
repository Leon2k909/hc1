var result=new System.Collections.Generic.List<object>();
foreach(var name in new[]{"lowtide_east","lowtide_west","lowtide_backdrop","lowtide_finish"})
{
    cancellationToken.ThrowIfCancellationRequested();
    var current=Model.Load("models/maps/lowtide/"+name+".vmdl");
    var candidate=Model.Load("models/maps/lowtide/construction_review/"+name+".vmdl");
    var before=current.GetIndices().Length/3;
    var after=candidate.GetIndices().Length/3;
    if(after<=before)throw new Exception("Candidate geometry has not loaded: "+name);
    result.Add(new{name,CurrentTriangles=before,CandidateTriangles=after,Delta=after-before,Materials=candidate.Materials.Select(x=>x.ResourcePath).ToArray()});
}
var path=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed/native-review/readback.json");
System.IO.File.WriteAllText(path,System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return new{models=result,Game.IsPlaying};
