var material=Material.Load("materials/lowtide/foliage/lt_oak_branch.vmat");
var textures=new[]{"g_tColor","g_tNormal","g_tRma","g_tTransmissiveColor"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray();
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/foliage");
using(var bitmap=material.GetTexture("g_tColor").GetBitmap(0))System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"compiled-candidate-atlas.png"),bitmap.ToPng());
var report=new{material.IsError,material.ShaderName,textures,
 features=new[]{"F_ALPHA_TEST","F_RENDER_BACKFACES","F_FOLIAGE_ANIMATION","F_TRANSMISSIVE","F_GRAZING_FADE"}.Select(name=>new{name,value=material.GetFeature(name)}).ToArray(),
 parameters=new[]{"g_flTintColor","g_flTransmissionScale","g_flRimStrength","g_flSwayStrength","g_flAlphaTestReference"}.Select(name=>new{name,value=material.GetVector4(name)}).ToArray()};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"candidate-bindings.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
