var project=Project.Current.GetRootPath();
var stage=System.IO.Path.Combine(project,"output/lowtide/quality-pass/weathering-stage/Assets");
var results=new System.Collections.Generic.List<object>();
foreach(var path in System.IO.Directory.GetFiles(stage,"*.vmat",System.IO.SearchOption.AllDirectories))
{
    var relative=System.IO.Path.GetRelativePath(stage,path).Replace('\\','/');
    var asset=Editor.AssetSystem.FindByPath(relative);
    System.IO.File.WriteAllText(asset.AbsolutePath,"// Biofilm binding compiled after shader schema update.\n"+System.IO.File.ReadAllText(path));
    results.Add(new{path=relative,success=asset.Compile(true)});
}
return results;
