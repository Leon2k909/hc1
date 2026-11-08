var root=Sandbox.Project.Current.GetRootPath();
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/veridant/breakable-rails-v1/stage/plan.json")));
var session=Editor.SceneEditorSession.All.Single(x=>x.Scene.IsEditor && x.Scene.Name=="veridant");
if(session.HasUnsavedChanges) throw new Exception("Veridant has unsaved changes");
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in plan["imports"].AsArray())
    if(Hash(item["source"].GetValue<string>())!=item["sha256"].GetValue<string>()) throw new Exception("Source changed: "+item["source"]);
var invalid=plan["models"].AsArray().Select(n=>n.GetValue<string>()).Where(p=>Model.Load(p) is not {IsError:false}).ToArray();
if(invalid.Length>0) throw new Exception("Invalid models: "+string.Join(",",invalid));
var backup=System.IO.Path.Combine(root,"output/veridant/breakable-rails-v1/install-before");
System.IO.Directory.CreateDirectory(backup);
System.IO.File.Copy(System.IO.Path.Combine(root,"Assets/scenes/maps/veridant/veridant.scene"),System.IO.Path.Combine(backup,"veridant.scene"),true);
using(session.Scene.Push()) {
    if(session.Scene.GetAllObjects(true).Any(g=>g.Name=="Breakable Railing Glass")) throw new Exception("Already installed");
    var group=new GameObject(false,"Breakable Railing Glass");
    group.Deserialize(plan["group"].DeepClone().AsObject());
    group.Parent=session.Scene.GetAllObjects(true).Single(g=>g.Name=="Veridant");
    var panes=group.GetComponentsInChildren<Facepunch.BreakableGlass>().ToArray();
    if(panes.Length!=147 || group.GetComponentsInChildren<ModelCollider>().Count()!=147) throw new Exception("Unexpected pane count");
    session.HasUnsavedChanges=true;
    session.Save(false);
}
foreach(var item in plan["imports"].AsArray()) {
    var source=item["source"].GetValue<string>();
    System.IO.File.Copy(source,System.IO.Path.Combine(backup,System.IO.Path.GetFileName(source)),true);
    var temporary=source+".rail-update";
    System.IO.File.Copy(item["staged"].GetValue<string>(),temporary,true);
    System.IO.File.Move(temporary,source,true);
}
return new {Installed=147,Saved=!session.HasUnsavedChanges,Game.IsPlaying};
