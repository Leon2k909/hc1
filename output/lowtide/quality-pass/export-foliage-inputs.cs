var root=Project.Current.GetRootPath();
if(!root.Replace('\\','/').TrimEnd('/').EndsWith("/hc1/forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var material=Material.Load("models/sbox_props/trees/oak/oak_branch.vmat");
if(material.IsError)throw new Exception("Original oak material unavailable");
var folder=System.IO.Path.Combine(root,"Sources/Lowtide/foliage/native-inputs");
System.IO.Directory.CreateDirectory(folder);
var report=new System.Collections.Generic.Dictionary<string,object>();
var pending=new System.Collections.Generic.Dictionary<string,byte[]>();
foreach(var input in new[]{("g_tColor","coverage.png"),("g_tNormal","normal.png"),("g_tRma","surface.png"),("g_tTransmissiveColor","transmission.png")})
{
 cancellationToken.ThrowIfCancellationRequested();
 var texture=material.GetTexture(input.Item1);
 if(texture==null||texture.Width<4||texture.Height<4)throw new Exception("Missing original texture "+input.Item1);
 var path=System.IO.Path.Combine(folder,input.Item2);
 if(System.IO.File.Exists(path))throw new Exception("Readback already exists; inspect before retrying: "+path);
 using var bitmap=texture.GetBitmap(0);
 var bytes=bitmap.ToPng();
 pending[path]=bytes;
 report[input.Item1]=new{file=input.Item2,texture.Width,texture.Height,sha256=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant()};
}
foreach(var item in pending)System.IO.File.WriteAllBytes(item.Key,item.Value);
var result=new{source=material.ResourcePath,material.ShaderName,textures=report,note="Unchanged native GPU texture readbacks for private Lowtide material evaluation. No scene, resource or game state changed."};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"provenance.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return result;
