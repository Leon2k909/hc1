if(Game.IsPlaying)throw new Exception("Stop play for the bounded comparison");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved work");
var root=Project.Current.GetRootPath();
var floor=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
var output=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-response/lighting-diagnostic");
System.IO.Directory.CreateDirectory(output);
var old=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(floor,"lighting-before/warehouse-lighting.json")))["volumes"].AsArray();
var vols=session.Scene.GetAllComponents<IndirectLightVolume>().ToArray();
var saved=vols.Select(v=>(v,irr:v.IrradianceTexture,dist:v.DistanceTexture,rel:v.RelocationTexture)).ToArray();
void Guard(){if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");}
var captures=new System.Collections.Generic.List<object>();
try
{
    session.MakeActive(true);await Task.Delay(500,cancellationToken);Guard();
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var pos=viewport.State.CameraPosition;var rot=viewport.State.CameraRotation;
    try
    {
        foreach(var variant in new[]{"v4-baseline","v4-reactivated","v3","v4-restored"})
        {
            if(variant!="v4-baseline")
            foreach(var s in saved)
            {
                s.v.Enabled=false;
                var source=old.Single(o=>o["Name"].GetValue<string>()==s.v.GameObject.Name)["Components"][0];
                s.v.IrradianceTexture=variant=="v3"?Texture.Load(source["IrradianceTexture"].GetValue<string>()):s.irr;
                s.v.DistanceTexture=variant=="v3"?Texture.Load(source["DistanceTexture"].GetValue<string>()):s.dist;
                s.v.RelocationTexture=variant=="v3"?Texture.Load(source["RelocationTexture"].GetValue<string>()):s.rel;
                s.v.Enabled=true;
            }
            Editor.Mcp.SceneTools.SetEditorCamera("440,-700,240","12,30,0");
            await Task.Delay(700,cancellationToken);Guard();
            Editor.Mcp.SceneTools.SetEditorCamera("440,-700,240","12,30,0");
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(output,variant+".png"),bitmap.ToPng());
            captures.Add(new{variant,Textures=vols.Select(v=>new{v.GameObject.Name,Path=v.IrradianceTexture.ResourcePath,Error=v.IrradianceTexture.IsError}).ToArray()});
        }
    }
    finally
    {
        foreach(var s in saved){s.v.IrradianceTexture=s.irr;s.v.DistanceTexture=s.dist;s.v.RelocationTexture=s.rel;s.v.Enabled=true;}
        if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
        {var a=rot.Angles();Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{pos.x:R},{pos.y:R},{pos.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));}
    }
}
finally{if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);}
var report=new{captures,session.HasUnsavedChanges,TabRestored=Editor.SceneEditorSession.Active==previous,TexturesRestored=saved.All(s=>s.v.IrradianceTexture==s.irr&&s.v.DistanceTexture==s.dist&&s.v.RelocationTexture==s.rel)};
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"readback.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
