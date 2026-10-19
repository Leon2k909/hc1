var rows=new System.Collections.Generic.List<object>();
foreach(var side in new[]{"east","west"})
{
    var model=Model.Load($"models/maps/lowtide/lowtide_dress_{side}.vmdl");
    var vertices=model.GetVertices();
    var min=new Vector3(float.PositiveInfinity);var max=new Vector3(float.NegativeInfinity);int bad=0;
    foreach(var vertex in vertices)
    {
        var p=vertex.Position;
        if(!float.IsFinite(p.x)||!float.IsFinite(p.y)||!float.IsFinite(p.z)||Math.Abs(p.x)>10000||Math.Abs(p.y)>10000||Math.Abs(p.z)>10000)bad++;
        min=new Vector3(Math.Min(min.x,p.x),Math.Min(min.y,p.y),Math.Min(min.z,p.z));
        max=new Vector3(Math.Max(max.x,p.x),Math.Max(max.y,p.y),Math.Max(max.z,p.z));
    }
    rows.Add(new{side,model.IsError,Bounds=model.Bounds.ToString(),PhysicsBounds=model.PhysicsBounds.ToString(),Vertices=vertices.Length,Minimum=min.ToString(),Maximum=max.ToString(),Bad=bad});
}
var report=new{TimeUtc=DateTime.UtcNow,rows,Game.IsPlaying};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"model-bounds-readback.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
