if(Game.IsPlaying)throw new Exception("Preserve the running match");
var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/paving-contact");
var previous=Editor.SceneEditorSession.Active;
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session.HasUnsavedChanges)throw new Exception("Lowtide has unsaved changes");
var slots=session.Scene.GetAllComponents<ModelRenderer>().SelectMany(r=>Enumerable.Range(0,r.Materials.Count).Where(i=>r.Materials.GetOriginal(i)?.ResourcePath=="materials/lowtide/lt_setts.vmat").Select(i=>(renderer:r,index:i))).ToArray();
if(slots.Length!=3)throw new Exception("Unexpected paving slot count");
var readback=slots.Select(s=>new{Name=s.renderer.GameObject.Name,Index=s.index,Material=s.renderer.Materials.GetOriginal(s.index),Override=s.renderer.Materials.GetOverride(s.index)}).ToArray();
if(readback.Any(s=>s.Override!=null||s.Material.IsError||!s.Material.ShaderName.Contains("hc1_lowtide_paving_use")||s.Material.GetTexture("g_tPavingUse")?.Width!=2048))throw new Exception("Paving not bound to production shader");
System.IO.Directory.CreateDirectory(System.IO.Path.Combine(folder,"production"));
var captures=new System.Collections.Generic.List<string>();
try
{
    session.MakeActive(true);
    await Task.Delay(350,cancellationToken);
    if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
    var viewport=Editor.SceneViewWidget.Current.LastSelectedViewportWidget;
    var position=viewport.State.CameraPosition;var rotation=viewport.State.CameraRotation;
    try
    {
        foreach(var camera in new[]{("pipe-outlet","230,-1060,30","17.566221,113.860175,0"),("shed-foot","-1125,-1290,28","21.56,-20.56,0")})
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            await Task.Delay(400,cancellationToken);
            if(Game.IsPlaying||Editor.SceneEditorSession.Active!=session||Editor.SceneViewWidget.Current?.Session!=session)throw new Exception("Viewport changed");
            Editor.Mcp.SceneTools.SetEditorCamera(camera.Item2,camera.Item3);
            using var bitmap=(Bitmap)Editor.Mcp.SceneTools.EditorCameraScreenshot(1440,1000);
            var name=camera.Item1+".png";
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"production",name),bitmap.ToPng());captures.Add(name);
        }
    }
    finally
    {
        if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&Editor.SceneViewWidget.Current?.Session==session)
        {
            var a=rotation.Angles();
            Editor.Mcp.SceneTools.SetEditorCamera(FormattableString.Invariant($"{position.x:R},{position.y:R},{position.z:R}"),FormattableString.Invariant($"{a.pitch:R},{a.yaw:R},{a.roll:R}"));
        }
    }
}
finally
{
    if(!Game.IsPlaying&&Editor.SceneEditorSession.Active==session&&previous!=null)previous.MakeActive(true);
}
var report=new{captures,Slots=readback.Select(r=>new{r.Name,r.Index,r.Material.ShaderName,MaskWidth=r.Material.GetTexture("g_tPavingUse").Width,HasOverride=r.Override!=null}).ToArray(),TabRestored=Editor.SceneEditorSession.Active==previous,RestoreTab=previous?.Scene.Source?.ResourcePath,session.HasUnsavedChanges,Game.IsPlaying,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production/verification.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
var reviewPath=System.IO.Path.Combine(root,"Assets/materials/lowtide/paving-use/lt_setts_review.vmat");
var expected=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")))["staged_files"]["materials/lowtide/lt_setts.vmat"].GetValue<string>();
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
if(Hash(reviewPath)!=expected)throw new Exception("Review source changed; keep it");
foreach(var suffix in new[]{"",".meta","_c"})
{
    var path=reviewPath+suffix;
    if(!System.IO.File.Exists(path))continue;
    var backup=System.IO.Path.Combine(folder,"retired-review",System.IO.Path.GetFileName(path));
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    System.IO.File.Copy(path,backup,true);
    if(Hash(backup)!=Hash(path))throw new Exception("Archive failed");
    System.IO.File.Delete(path);
}
return report;
