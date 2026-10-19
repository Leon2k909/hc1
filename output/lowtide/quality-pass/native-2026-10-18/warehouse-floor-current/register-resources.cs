var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/warehouse-floor-current");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
var paths=data["assets"].AsObject().Where(p=>p.Key.EndsWith(".vmat")||p.Key.EndsWith(".png")).Select(p=>p.Key).OrderBy(p=>p.EndsWith(".png")?0:1).ToArray();
var results=paths.Select(path=>new{path,Registered=Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(root,"Assets",path))!=null}).ToArray();
return results;
