var scene=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene").Scene;
var trees=scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("trees/oak/")==true).ToArray();
var materials=trees.SelectMany(r=>Enumerable.Range(0,r.Materials.Count).Select(i=>r.Materials.GetOverride(i)??r.Materials.GetOriginal(i))).Distinct().ToArray();
var report=new{
 trees=trees.Select(r=>new{r.GameObject.Name,r.GameObject.Id,position=r.GameObject.WorldPosition,scale=r.GameObject.WorldScale,model=r.Model.ResourcePath,slots=r.Materials.Count}).ToArray(),
 materials=materials.Select(m=>new{path=m.ResourcePath,m.ShaderName,m.IsError,
  features=new[]{"F_ALPHA_TEST","F_TRANSLUCENT","F_RENDER_BACKFACES","F_VERTEX_COLOR","F_WIND"}.Select(name=>new{name,value=m.GetFeature(name)}).ToArray(),
  parameters=new[]{"g_flAlphaTestReference","g_flRoughnessScaleFactor","g_flTransmissionAmount","g_flModelTintAmount","g_vColorTint"}.Select(name=>new{name,value=m.GetVector4(name)}).ToArray(),
  textures=new[]{"g_tColor","g_tNormal","g_tRma","g_tTintMask","g_tTranslucency"}.Select(name=>new{name,path=m.GetTexture(name)?.ResourcePath,width=m.GetTexture(name)?.Width,height=m.GetTexture(name)?.Height}).ToArray()}).ToArray()
};
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/foliage");
System.IO.Directory.CreateDirectory(folder);
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"inspection.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
