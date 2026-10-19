var scene=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene").Scene;
var model=Model.Load("models/sbox_props/trees/oak/tree_oak_medium_a.vmdl");
var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Instance;
return new{
 modelMethods=typeof(Model).GetMethods(flags).Where(m=>m.Name.Contains("Lod")||m.Name.Contains("DrawCall")||m.Name=="GetVertices"||m.Name=="GetIndices").Select(m=>m.ToString()).ToArray(),
 modelProperties=typeof(Model).GetProperties(flags).Where(p=>p.Name.Contains("Lod")||p.Name=="Bounds").Select(p=>p.ToString()).ToArray(),
 rendererLodProperty=typeof(ModelRenderer).GetProperty("LodOverride")?.ToString(),
 renderers=scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("trees/oak/")==true).Select(r=>new{r.GameObject.Id,lod=typeof(ModelRenderer).GetProperty("LodOverride")?.GetValue(r)}).ToArray()
};
