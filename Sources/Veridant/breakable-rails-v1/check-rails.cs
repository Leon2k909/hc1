var scene=Editor.SceneEditorSession.All.Single(x=>x.Scene.IsEditor && x.Scene.Name=="veridant").Scene;
var panes=scene.GetAllComponents<Facepunch.BreakableGlass>().Where(x=>x.GameObject.Name.StartsWith("Breakable Rail Glass ")).ToArray();
var issues=new System.Collections.Generic.List<string>();
var setBroken=typeof(Facepunch.BreakableGlass).GetMethod("SetBroken",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
var hitCount=0;
using(scene.Push()) {
    scene.EditorTick(.016f,.016f);
    foreach(var pane in panes) {
        var renderer=pane.GetComponent<ModelRenderer>();
        var collider=pane.GetComponent<ModelCollider>();
        if(renderer?.Model is not {IsError:false} || !renderer.Enabled || collider?.Model is not {IsError:false} || !collider.Enabled || !pane.ShardEffect.IsValid() || pane.BreakSound is null || pane.IntactModel is null || !pane.GameObject.Tags.Has("glass")) issues.Add("Invalid pane "+pane.GameObject.Name);
        var from=pane.WorldPosition-pane.WorldRotation.Forward*2f;
        var to=pane.WorldPosition+pane.WorldRotation.Forward*2f;
        if(scene.Trace.Ray(from,to).WithTag("glass").Run().GameObject==pane.GameObject) hitCount++;
        try {
            setBroken.Invoke(pane,new object[]{true});
            if(!pane.IsBroken || renderer.Enabled || collider.Enabled) issues.Add("Break failed "+pane.GameObject.Name);
        } finally {setBroken.Invoke(pane,new object[]{false});}
        if(pane.IsBroken || !renderer.Enabled || !collider.Enabled || renderer.Model!=pane.IntactModel) issues.Add("Restore failed "+pane.GameObject.Name);
    }
}
var report=new {Panes=panes.Length,TraceHits=hitCount,BreakAndRestore=panes.Length,Issues=issues};
System.IO.File.WriteAllText(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/veridant/breakable-rails-v1/verification.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
