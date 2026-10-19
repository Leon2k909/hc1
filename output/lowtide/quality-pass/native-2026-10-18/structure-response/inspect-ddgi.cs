var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance;
object Probes(IndirectLightVolume v)
{
    var probes=typeof(IndirectLightVolume).GetProperty("Probes",flags)?.GetValue(v) as System.Collections.IEnumerable;
    var array=probes?.Cast<object>().ToArray();
    return new {Total=array?.Length,Active=array?.Count(p=>(p.GetType().GetProperty("Active",flags)?.GetValue(p) as bool?)==true)};
}
object Describe(Texture t)
{
    if(t==null)return null;
    return new {t.ResourcePath,t.IsError,Properties=t.GetType().GetProperties(System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Public).Where(p=>p.CanRead&&p.GetIndexParameters().Length==0&&(p.PropertyType.IsPrimitive||p.PropertyType.IsEnum||p.PropertyType==typeof(string))).Select(p=>new {p.Name,Value=p.GetValue(t)?.ToString()}).ToArray()};
}
var data=new {Scene=session.Scene.Source.ResourcePath,session.HasUnsavedChanges,Game.IsPlaying,
    Volumes=session.Scene.GetAllComponents<IndirectLightVolume>().Select(v=>new {v.GameObject.Name,v.Enabled,v.Active,v.BakeVersion,v.ProbeCounts,ProbeData=Probes(v),Irradiance=Describe(v.IrradianceTexture),Distance=Describe(v.DistanceTexture),Relocation=Describe(v.RelocationTexture)}).ToArray(),
    BuildData=typeof(IndirectLightVolume).GetMethods(flags).Where(m=>m.Name=="BuildData").Select(m=>new {m.IsPublic,Return=m.ReturnType.FullName,Parameters=m.GetParameters().Select(p=>new {p.Name,Type=p.ParameterType.FullName}).ToArray()}).ToArray(),
    Fields=typeof(IndirectLightVolume).GetFields(flags).Select(f=>new {f.Name,Type=f.FieldType.FullName}).ToArray()};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-response");
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"ddgi-inspection.json"),System.Text.Json.JsonSerializer.Serialize(data,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return data;
