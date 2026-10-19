var root=System.IO.Path.GetFullPath(Project.Current.GetRootPath());
if(!root.TrimEnd('\\','/').Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong checkout");
var folder=System.IO.Path.Combine(root,"output/lowtide/quality-pass/native-2026-10-18/water-reflection");
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var key in new[]{"Assets/materials/lowtide/lt_water.vmat","Assets/shaders/hc1_lowtide_water.shader","Assets/models/maps/lowtide/lowtide_water.vmdl","Assets/models/maps/lowtide/lowtide_water.obj","Assets/scenes/maps/Lowtide/lowtide.scene"})
    if(Hash(System.IO.Path.Combine(root,key))!=data["sources"][key].GetValue<string>())throw new Exception("Source changed: "+key);
if(Hash(System.IO.Path.Combine(root,"Code/Map/LowtideWaterReflections.cs"))!=data["capture_code_sha256"].GetValue<string>())throw new Exception("Capture code changed");
foreach(var key in new[]{"Assets/shaders/hc1_lowtide_water_filtered.shader","Assets/shaders/hc1_lowtide_water_filtered.shader.meta"})
    if(Hash(System.IO.Path.Combine(root,key))!=data["files"][key].GetValue<string>())throw new Exception("Review shader changed");
var source=System.IO.Path.Combine(root,data["production_material_source"].GetValue<string>());
if(Hash(source)!=data["production_material_sha256"].GetValue<string>())throw new Exception("Material stage changed");
if(Game.IsPlaying&&Game.ActiveScene?.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene")throw new Exception("Wait for the Lowtide match to finish");
var scene=Editor.SceneEditorSession.Active;var playing=Game.IsPlaying;
var target=System.IO.Path.Combine(root,"Assets/materials/lowtide/lt_water.vmat");
var backup=System.IO.Path.Combine(folder,"before/Assets/materials/lowtide/lt_water.vmat");
System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
if(System.IO.File.Exists(backup))throw new Exception("Material backup already exists");
System.IO.File.Copy(target,backup);
System.IO.File.WriteAllBytes(target+".native-stage",System.IO.File.ReadAllBytes(source));
System.IO.File.Move(target+".native-stage",target,true);
var report=new{Material="materials/lowtide/lt_water.vmat",Hash=Hash(target),ScenePreserved=Editor.SceneEditorSession.Active==scene,PlayStatePreserved=Game.IsPlaying==playing,TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"production-import.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
