var m=Material.Load("models/sbox_props/trees/oak/oak_branch.vmat");
var names=new[]{"g_flEdgeFrequency","g_flEdgeAmplitude","g_flBranchFrequency","g_flBranchAmplitude","g_flSwayStrength","g_flSwaySpeed","g_flTintColor","g_flSelfIllumScale","g_flDetailFadeDistance","g_flRimStrength","g_flRimPower"};
var report=new{parameters=names.Select(name=>new{name,value=m.GetVector4(name)}).ToArray(),bitmapToTexture=typeof(Bitmap).GetMethod("ToTexture")?.GetParameters().Select(p=>new{p.Name,type=p.ParameterType.ToString(),p.DefaultValue}).ToArray()};
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/foliage/animation.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
