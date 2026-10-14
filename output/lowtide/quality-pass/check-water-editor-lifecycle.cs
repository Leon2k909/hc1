var session=Editor.SceneEditorSession.Active;
if(Game.IsPlaying || session?.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || session.HasUnsavedChanges)throw new Exception("Expected saved Lowtide edit viewport");
var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
var pos=viewport.State.CameraPosition;
var rot=viewport.State.CameraRotation;
var reflection=session.Scene.GetAllComponents<Facepunch.LowtideWaterReflections>().Single();
if(!reflection.Enabled)throw new Exception("Expected enabled reflection component");
var camera=Editor.Application.Editor.Camera;
var owner=session.Scene.Camera;
var originalOrtho=owner.Orthographic;
var viewsField=reflection.GetType().GetField("views",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);
var commandField=typeof(CameraComponent).GetField("commandlists",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic);
var checks=new System.Collections.Generic.List<string>();
int Views()=>((System.Collections.IDictionary)viewsField.GetValue(reflection)).Count;
int Commands()
{
 var dictionary=(System.Collections.IDictionary)commandField.GetValue(owner);
 var count=0;
 foreach(System.Collections.IEnumerable entries in dictionary.Values)
 foreach(var entry in entries)
 {
  var field=entry.GetType().GetProperty("List",System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
  var list=(Sandbox.Rendering.CommandList)field.GetValue(entry);
  if(list.DebugName=="Lowtide planar reflection")count++;
 }
 return count;
}
void Check(string name,bool condition) { if(!condition)throw new Exception(name); checks.Add(name); }
void Overview() { Editor.Mcp.SceneTools.SetEditorCamera("-1300,0,125","-2.503,0,0"); reflection.PrepareViews(); }
try
{
 Overview();
 Check("one editor reflection command on main camera",Views()==1&&Commands()==1&&camera.RenderExcludeTags.Has("water"));
 Editor.Mcp.SceneTools.SetEditorCamera("-2000,0,500","0,180,0"); reflection.PrepareViews();
 Check("looking away releases command and water exclusion",Views()==0&&Commands()==0&&!camera.RenderExcludeTags.Has("water"));
 Overview();
 Check("returning reacquires exactly one command",Views()==1&&Commands()==1);
 reflection.Enabled=false;
 Check("disable restores ordinary water",Views()==0&&Commands()==0&&!camera.RenderExcludeTags.Has("water"));
 camera.RenderExcludeTags.Add("water");
 reflection.Enabled=true; reflection.PrepareViews();
 Check("preexisting intentional exclusion is respected",Views()==0&&Commands()==0&&camera.RenderExcludeTags.Has("water"));
 camera.RenderExcludeTags.Remove("water"); Overview();
 owner.Orthographic=false; reflection.PrepareViews();
 Check("shared editor views retain fallback without duplicate draws",Views()==0&&Commands()==0&&!camera.RenderExcludeTags.Has("water"));
 owner.Orthographic=originalOrtho; Overview();
 Check("single viewport reflection recovers",Views()==1&&Commands()==1);
}
finally
{
 owner.Orthographic=originalOrtho;
 reflection.Enabled=true;
 var a=rot.Angles();
 Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
 reflection.PrepareViews();
}
Check("scene remains saved",!session.HasUnsavedChanges);
var result=new {checks,session.HasUnsavedChanges,restored=Editor.Mcp.SceneTools.GetEditorCamera()};
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/water-editor-lifecycle.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
