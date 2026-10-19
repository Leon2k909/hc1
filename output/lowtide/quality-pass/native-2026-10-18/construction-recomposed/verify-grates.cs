var root = System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if (!string.Equals(root.TrimEnd('\\'), @"C:\sbox-projects\hc1\forked-shooter-main", StringComparison.OrdinalIgnoreCase)) throw new Exception("Wrong project");
var folder = System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed");
var targets = new System.Collections.Generic.List<(float E,float N,float W,float L)>();
foreach(var side in new[]{-1,1})
{
    foreach(var e in new[]{390,770,1160,1420,1880,2110}) targets.Add((side*e,-1540,23,32));
    foreach(var n in new[]{-870,-505,-170,180,540,920}) targets.Add((side*1030,n,16,26));
}
var meshData = new System.Collections.Generic.Dictionary<string,System.Collections.Generic.List<(Vector3 A,Vector3 B,Vector3 C)>>();
var reports = new System.Collections.Generic.List<object>();
foreach(var name in new[]{"lowtide_finish","lowtide_east","lowtide_west"})
{
    cancellationToken.ThrowIfCancellationRequested();
    var model=Model.Load("models/maps/lowtide/"+name+".vmdl");
    var triangles=new System.Collections.Generic.List<(Vector3 A,Vector3 B,Vector3 C)>();
    var vertices=model.GetVertices();
    var indices=model.GetIndices();
    {
        for(var i=0;i<indices.Length;i+=3)
        {
            var a=vertices[indices[i]].Position; var b=vertices[indices[i+1]].Position; var c=vertices[indices[i+2]].Position;
            if(Math.Max(a.z,Math.Max(b.z,c.z))>1 || Math.Min(a.z,Math.Min(b.z,c.z))<-11)continue;
            triangles.Add((a,b,c));
        }
    }
    meshData[name]=triangles;
    reports.Add(new { name, ReadbackTriangles=indices.Length/3,
        Materials=model.Materials.Select(m=>m.ResourcePath).ToArray(),NearGroundTriangles=triangles.Count });
}
float RayZ(System.Collections.Generic.List<(Vector3 A,Vector3 B,Vector3 C)> triangles,float x,float y)
{
    float result=float.NegativeInfinity;
    foreach(var t in triangles)
    {
        float ux=t.B.x-t.A.x,uy=t.B.y-t.A.y,vx=t.C.x-t.A.x,vy=t.C.y-t.A.y;
        var det=ux*vy-uy*vx;
        if(Math.Abs(det)<1e-7)continue;
        var px=x-t.A.x; var py=y-t.A.y;
        var u=(px*vy-py*vx)/det; var v=(ux*py-uy*px)/det;
        if(u<-.000001 || v<-.000001 || u+v>1.000001)continue;
        result=Math.Max(result,t.A.z+u*(t.B.z-t.A.z)+v*(t.C.z-t.A.z));
    }
    return result;
}
var checks=new System.Collections.Generic.List<object>();
foreach(var t in targets)
{
    var usable=t.W-.7f-1.48f; var count=Math.Max(5,(int)Math.Round(usable/2.05f));
    var slotE=t.E-usable/2+usable/count;
    var barE=t.E-usable/2+.5f*usable/count;
    var slot=RayZ(meshData["lowtide_finish"],t.N+1,-slotE);
    var bar=RayZ(meshData["lowtide_finish"],t.N+1,-barE);
    var paving=RayZ(meshData[t.E>0?"lowtide_east":"lowtide_west"],t.N+1,-slotE);
    checks.Add(new{t.E,t.N,Slot=slot,Bar=bar,PavementOccludes=paving>=-.01,
        Passed=Math.Abs(slot+10)<.02 && Math.Abs(bar-.07)<.02 && paving<-.01});
}
var report=new{models=reports,grates=checks,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"grate-verification.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
var summary=System.Text.Json.Nodes.JsonNode.Parse(System.Text.Json.JsonSerializer.Serialize(checks)).AsArray();
var passed=summary.Count(x=>x["Passed"].GetValue<bool>());
return new{CheckedGrates=checks.Count,PassedGrates=passed,AllPassed=passed==checks.Count,models=reports,Game.IsPlaying};
