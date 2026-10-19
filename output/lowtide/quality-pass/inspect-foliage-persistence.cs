if(Game.IsPlaying)throw new Exception("Preserve the running game");
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved edits");
var renderer=session.Scene.GetAllComponents<ModelRenderer>().First(r=>r.Model?.ResourcePath=="models/sbox_props/trees/oak/tree_oak_medium_a.vmdl");
int slot=Enumerable.Range(0,renderer.Materials.Count).Single(i=>renderer.Materials.GetOriginal(i)?.ResourcePath=="models/sbox_props/trees/oak/oak_branch.vmat");
var previous=renderer.Materials.GetOverride(slot);
var before=renderer.GameObject.Serialize(new GameObject.SerializeOptions());
System.Text.Json.Nodes.JsonObject after;
try
{
 renderer.Materials.SetOverride(slot,Material.Load("materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat"));
 renderer.Materials.Apply();
 after=renderer.GameObject.Serialize(new GameObject.SerializeOptions());
}
finally
{
 renderer.Materials.SetOverride(slot,previous);
 renderer.Materials.Apply();
}
var report=new{before,after,restored=renderer.Materials.GetOverride(slot)==previous,session.HasUnsavedChanges,
 sessionMethods=typeof(Editor.SceneEditorSession).GetMethods().Where(m=>m.Name.Contains("Save")||m.Name.Contains("Undo")||m.Name.Contains("Dirty")).Select(m=>m.ToString()).ToArray(),
 toolMethods=typeof(Editor.Mcp.SceneTools).GetMethods().Where(m=>m.Name.Contains("Save")).Select(m=>m.ToString()).ToArray()};
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/foliage/persistence-inspection.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
