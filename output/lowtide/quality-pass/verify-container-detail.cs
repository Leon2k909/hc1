var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying||session?.Scene?.IsEditor!=true||session.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene")throw new Exception("Expected Lowtide editor");
var renderers=session.Scene.GetAllComponents<ModelRenderer>().ToArray();
var modelErrors=renderers.Where(r=>r.Model==null||r.Model.IsError).Select(r=>r.GameObject.Name).ToArray();
var materialErrors=renderers.SelectMany(r=>Enumerable.Range(0,r.Materials.Count).Where(i=>r.Materials.GetOriginal(i)?.IsError==true).Select(i=>r.GameObject.Name+":"+i)).ToArray();
var targets=renderers.Where(r=>r.Model?.ResourcePath=="models/maps/lowtide/lowtide_dress_east.vmdl"||r.Model?.ResourcePath=="models/maps/lowtide/lowtide_dress_west.vmdl")
 .Select(r=>new{r.GameObject.Name,path=r.Model.ResourcePath,materialSlots=r.Materials.Count}).ToArray();
if(modelErrors.Length!=0||materialErrors.Length!=0||targets.Length!=2)throw new Exception("Loaded model/material failure or missing targets");
var report=new{modelErrors,materialErrors,targets,session.HasUnsavedChanges,Game.IsPlaying,camera=Editor.Mcp.SceneTools.GetEditorCamera()};
var path=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/container-detail/native-verify.json");
System.IO.File.WriteAllText(path,System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
