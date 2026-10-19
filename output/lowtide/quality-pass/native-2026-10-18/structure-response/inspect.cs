var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var paths=new[]{"materials/lowtide/lt_timber.vmat","materials/buildings/iron_black.vmat","materials/railhead/rw_wood.vmat"};
var materials=paths.Select(path=>
{
    var m=Material.Load(path);
    return new{Path=path,m.IsError,m.ShaderName,Tint=m.GetVector4("g_vColorTint").ToString(),
        Features=new[]{"F_SPECULAR","F_DIFFUSE_DIRECT","F_DIFFUSE_INDIRECT","F_FULLBRIGHT","F_VERTEX_COLOR","F_MODEL_TINT"}.Select(f=>new{Name=f,Value=m.GetFeature(f)}).ToArray(),
        Textures=new[]{"g_tColor","g_tNormal","g_tRoughness","g_tAmbientOcclusion"}.Select(n=>{var t=m.GetTexture(n);return new{Name=n,Path=t?.ResourcePath,Error=t?.IsError,Width=t?.Width,Height=t?.Height};}).ToArray()};
}).ToArray();
var bindings=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_west.vmdl").Select(r=>new{r.GameObject.Name,Slots=r.Model.Materials.Select((m,i)=>new{Index=i,m.ResourcePath,m.ShaderName,m.IsError,Override=r.Materials.GetOverride(i)?.ResourcePath}).Where(m=>paths.Contains(m.ResourcePath)).ToArray()}).ToArray();
var result=new {TimeUtc=DateTime.UtcNow,Game.IsPlaying,ActiveScene=Editor.SceneEditorSession.Active?.Scene.Source?.ResourcePath,session.HasUnsavedChanges,materials,bindings};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/structure-response");
System.IO.Directory.CreateDirectory(folder);
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-before.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
