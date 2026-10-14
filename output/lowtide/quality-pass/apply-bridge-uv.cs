var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor && s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
if(session?.Scene?.IsEditor!=true || session.Scene.Source?.ResourcePath!="scenes/maps/lowtide/lowtide.scene" || session.HasUnsavedChanges)throw new Exception("Expected saved Lowtide editor");
var root=Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"bridge-uv-manifest.json")));
string Hash(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var live=System.IO.Path.Combine(root,"Assets/models/maps/lowtide/lowtide_fleet.obj");
if(Hash(live)!=manifest["before"].GetValue<string>())throw new Exception("Fleet changed since staging");
foreach(var p in manifest["protected"].AsObject())
 if(Hash(System.IO.Path.Combine(root,p.Key))!=p.Value.GetValue<string>())throw new Exception("Protected source changed: "+p.Key);
var stage=System.IO.Path.Combine(folder,"bridge-uv-stage/lowtide_fleet.obj");
if(Hash(stage)!=manifest["after"].GetValue<string>())throw new Exception("Staged UV repair changed");
var temporary=stage+".replace";
System.IO.File.Copy(stage,temporary,true);
System.IO.File.Replace(temporary,live,null);
var compiled=Editor.AssetSystem.FindByPath("models/maps/lowtide/lowtide_fleet.vmdl").Compile(true);
if(!compiled)throw new Exception("Fleet compile failed");
await Task.Delay(500,cancellationToken);
var model=Model.Load("models/maps/lowtide/lowtide_fleet.vmdl");
var material=Material.Load("materials/lowtide/lt_bridge_deck.vmat");
var report=new{compiled,modelError=model.IsError,materialError=material.IsError,
 installedHash=Hash(live),session.HasUnsavedChanges,Game.IsPlaying};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"bridge-uv-native-compile.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
