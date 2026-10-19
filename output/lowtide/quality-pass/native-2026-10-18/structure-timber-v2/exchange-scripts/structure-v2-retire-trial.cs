var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
var assets=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"Assets"))+System.IO.Path.DirectorySeparatorChar;
var relative="materials/lowtide/structure/lt_cast_paint_trial.vmat";
var production="materials/lowtide/structure/lt_cast_iron_v2.vmat";
var source=System.IO.Path.GetFullPath(System.IO.Path.Combine(assets,relative));
if(System.IO.File.ReadAllText(source)!=System.IO.File.ReadAllText(System.IO.Path.Combine(assets,production)))throw new Exception("Trial differs from the selected production material");
foreach(var s in Editor.SceneEditorSession.All)
foreach(var r in s.Scene.GetAllComponents<ModelRenderer>())
for(int i=0;i<r.Materials.Count;i++)
if(r.Materials.GetOriginal(i)?.ResourcePath==relative||r.Materials.GetOverride(i)?.ResourcePath==relative)throw new Exception("Trial still bound");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/structure-timber-v2/retired-trial");
System.IO.Directory.CreateDirectory(folder);
var deleted=new System.Collections.Generic.List<string>();
foreach(var suffix in new[]{"",".meta"})
{
    var file=System.IO.Path.GetFullPath(source+suffix);
    if(!file.StartsWith(assets,StringComparison.OrdinalIgnoreCase))throw new Exception("Outside Assets");
    if(!System.IO.File.Exists(file))continue;
    var target=System.IO.Path.Combine(folder,System.IO.Path.GetFileName(file));
    System.IO.File.Copy(file,target,false);
    if(!System.IO.File.ReadAllBytes(file).SequenceEqual(System.IO.File.ReadAllBytes(target)))throw new Exception("Archive differs");
    System.IO.File.Delete(file);deleted.Add(relative+suffix);
}
var report=new{Deleted=deleted,CompiledCachesPreserved=true,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"cleanup.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
