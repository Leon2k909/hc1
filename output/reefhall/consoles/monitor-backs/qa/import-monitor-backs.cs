var root = Project.Current.GetRootPath();
if (!System.IO.Path.GetFullPath(root).TrimEnd('\\').Equals(@"D:\Documents\s&box projects\hc1\forked-shooter-main", StringComparison.OrdinalIgnoreCase))
    throw new Exception("Wrong project.");
var work = System.IO.Path.Combine(root,"output/reefhall/consoles/monitor-backs");
var stage = System.IO.Path.Combine(work,"staging");
var backup = System.IO.Path.Combine(work,"before-assets");
System.IO.Directory.CreateDirectory(backup);
var modelDir = System.IO.Path.Combine(root,"Assets/models/maps/reefhall");
var materials = System.IO.Path.Combine(root,"Assets/materials/reefhall/consoles");
string Hash(string p) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p)));
var names = new[] {"reefhall_control.obj","reefhall_control.mtl","reefhall_control.vmdl"};
foreach (var name in names)
{
    var target = System.IO.Path.Combine(modelDir,name);
    var baseline = System.IO.Path.Combine(work,"before",name);
    if (Hash(target)!=Hash(baseline)) throw new Exception("Source changed since baseline: "+name);
}
var copied = new System.Collections.Generic.List<string>();
var registered = new System.Collections.Generic.List<string>();
foreach (var file in System.IO.Directory.GetFiles(System.IO.Path.Combine(stage,"materials"),"rh_monitor_*").OrderBy(p=>p.EndsWith(".vmat")?1:0))
{
    cancellationToken.ThrowIfCancellationRequested();
    var target = System.IO.Path.Combine(materials,System.IO.Path.GetFileName(file));
    if (System.IO.File.Exists(target))
    {
        var saved = System.IO.Path.Combine(backup,System.IO.Path.GetFileName(file));
        if (!System.IO.File.Exists(saved)) System.IO.File.Copy(target,saved);
    }
    System.IO.File.Copy(file,target,true);
    copied.Add(target);
    if (target.EndsWith(".vmat"))
    {
        var asset = Editor.AssetSystem.RegisterFile(target);
        if (asset is null) throw new Exception("Registration failed: "+target);
        registered.Add(asset.Path);
    }
}
foreach (var name in names)
{
    cancellationToken.ThrowIfCancellationRequested();
    var target = System.IO.Path.Combine(modelDir,name);
    var saved = System.IO.Path.Combine(backup,name);
    if (!System.IO.File.Exists(saved)) System.IO.File.Copy(target,saved);
    System.IO.File.Copy(System.IO.Path.Combine(stage,name),target,true);
    copied.Add(target);
}
var model = Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(modelDir,"reefhall_control.vmdl"));
if (model is null) throw new Exception("Model registration failed.");
return new {Model=model.Path,Materials=registered,Files=copied,Backup=backup,ActiveScene=Editor.SceneEditorSession.Active?.Scene?.Name};

