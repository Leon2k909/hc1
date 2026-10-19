var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene?.IsEditor!=true || session.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || Editor.SceneViewWidget.Current?.Session!=session) throw new Exception("Expected Lowtide edit viewport");
var folder=System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/construction-recomposed/native-review");
var requests=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"views.json"))).AsArray();
var names=new[]{"lowtide_east","lowtide_west","lowtide_backdrop","lowtide_finish"};
var renderers=session.Scene.GetAllObjects(true).Select(go=>go.Components.Get<ModelRenderer>()).Where(r=>r!=null && names.Any(n=>r.Model?.ResourcePath=="models/maps/lowtide/"+n+".vmdl")).ToArray();
if(renderers.Length!=4)throw new Exception("Expected four production renderers, got "+renderers.Length);
var originals=renderers.ToDictionary(r=>r,r=>r.Model);
var candidates=originals.ToDictionary(p=>p.Key,p=>Model.Load(p.Value.ResourcePath.Replace("models/maps/lowtide/","models/maps/lowtide/construction_review/")));
var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var position=viewport.State.CameraPosition;
var rotation=viewport.State.CameraRotation;
var dirtyBefore=session.HasUnsavedChanges;
var results=new System.Collections.Generic.List<object>();
void Guard(){cancellationToken.ThrowIfCancellationRequested();if(Game.IsPlaying || Editor.SceneEditorSession.Active!=session || Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport state changed");}
try
{
    foreach(var candidate in new[]{false,true})
    {
        Guard();
        foreach(var item in (candidate?candidates:originals))item.Key.Model=item.Value;
        await Task.Delay(500,cancellationToken);
        foreach(var request in requests)
        {
            Guard();
            var name=request["name"].GetValue<string>();
            if(System.IO.Path.GetFileName(name)!=name)throw new Exception("Invalid screenshot name");
            var p=request["position"].GetValue<string>();var a=request["angles"].GetValue<string>();
            Editor.Mcp.SceneTools.SetEditorCamera(p,a);
            await Task.Delay(250,cancellationToken);
            Guard();
            Editor.Mcp.SceneTools.SetEditorCamera(p,a);
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var path=System.IO.Path.Combine(folder,name+(candidate?"-candidate":"-before")+".png");
            System.IO.File.WriteAllBytes(path,bitmap.ToPng());
            results.Add(new{name,candidate,path,camera=Editor.Mcp.SceneTools.GetEditorCamera()});
        }
    }
}
finally
{
    foreach(var item in originals)if(item.Key.IsValid())item.Key.Model=item.Value;
    if(!Game.IsPlaying && Editor.SceneEditorSession.Active==session && Editor.SceneViewWidget.Current?.Session==session)
    {
        var a=rotation.Angles();
        Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{position.x:R},{position.y:R},{position.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
    }
}
var record=new{results,dirtyBefore,dirtyAfter=session.HasUnsavedChanges,RestoredModels=originals.All(p=>p.Key.Model==p.Value),scene=session.Scene.Source.ResourcePath,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"capture.json"),System.Text.Json.JsonSerializer.Serialize(record,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return new{Count=results.Count,record.dirtyBefore,record.dirtyAfter,record.RestoredModels,folder};
