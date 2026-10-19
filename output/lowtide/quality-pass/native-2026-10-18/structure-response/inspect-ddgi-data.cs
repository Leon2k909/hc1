var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance;
var method=typeof(IndirectLightVolume).GetMethod("BuildData",flags);
var dataType=method.GetParameters()[0].ParameterType.GetElementType();
var rows=new System.Collections.Generic.List<object>();
foreach(var v in session.Scene.GetAllComponents<IndirectLightVolume>())
foreach(var preview in new[]{false,true})
{
    var args=new object[]{Activator.CreateInstance(dataType),preview,true};
    var success=method.Invoke(v,args);
    rows.Add(new {v.GameObject.Name,Preview=preview,Success=success,PreviewPresent=typeof(IndirectLightVolume).GetField("_bakePreview",flags).GetValue(v)!=null,Data=dataType.GetFields(flags).Select(f=>new {f.Name,Value=f.GetValue(args[0])?.ToString()}).ToArray()});
}
var text=System.Text.Json.JsonSerializer.Serialize(rows,new System.Text.Json.JsonSerializerOptions{WriteIndented=true});
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-response/ddgi-gpu-data.json"),text);
return rows;
