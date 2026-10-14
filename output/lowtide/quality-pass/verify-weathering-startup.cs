var names=new[]{"materials/lowtide/lt_brick.vmat","materials/lowtide/lt_brick_soot.vmat","materials/lowtide/lt_brick_glazed.vmat","materials/lowtide/lt_brick_slime.vmat","materials/lowtide/finish/lt_quay_stone.vmat","materials/lowtide/masonry/lt_granite_trim.vmat"};
var results=new System.Collections.Generic.List<object>();
foreach(var name in names)
{
    var material=Material.Load(name);
    var texture=material.GetTexture("g_tCanalBiofilm");
    if(material.IsError||texture is null||texture.IsError||texture.Width<1024)throw new Exception("Missing biofilm binding: "+name);
    results.Add(new{name,material.IsError,texture=texture.ToString(),texture.Width,texture.Height});
}
var report=new {userScene=Game.ActiveScene?.Name,editorScene=Editor.SceneEditorSession.Active?.Scene?.Name,results};
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/weathering-bindings.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
