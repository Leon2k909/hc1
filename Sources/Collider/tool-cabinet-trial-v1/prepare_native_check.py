from pathlib import Path
HERE=Path(__file__).parent
s=(HERE/'native-collision.cs.txt').read_text()
a=s.index('var checks=');b=s.index('Probe("original case solid base"')
s=s[a:b].replace('World(go,a)','World(a)').replace('World(go,b)','World(b)').replace('.WithTag(tag)','')
s=s.replace('GameObject go,','').replace('proposed,tag,','tag,').replace('World(b)).Run()','World(b)).WithTag(tag).Run()')
header='''var root=Sandbox.Project.Current.GetRootPath();
var scene=new Scene();
var originalScene=Game.ActiveScene;
var folder=System.IO.Path.Combine(root,"output/collider-tool-cabinet-accepted-20261031");
try
{
var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Assets/scenes/maps/Collider/collider.scene")));
var objects=new System.Text.Json.Nodes.JsonArray();
var visual=new[]{"Look","Ambient","Collider","Lights","Reflection Probes","Collider indirect lighting"};
foreach(var item in data["GameObjects"].AsArray())
    if(visual.Contains(item["Name"]?.GetValue<string>()))objects.Add(item.DeepClone());
data["GameObjects"]=objects;data["SceneProperties"]["NavMesh"]["Enabled"]=false;
data["SceneProperties"]["WantsSystemScene"]=false;
CameraComponent camera;
using(scene.Push())
{
scene.Deserialize(data.AsObject());
var holder=scene.CreateObject(false);holder.Name="Installation verification camera";
camera=holder.Components.Create<CameraComponent>();camera.IsMainCamera=false;camera.ZNear=4;camera.ZFar=20000;
var source=originalScene.GetAllComponents<CameraComponent>().Where(c=>c.IsMainCamera).FirstOrDefault();
void Copy<T>() where T:Component,new()
{
var effect=source?.GameObject.GetComponent<T>(true);
if(effect.IsValid())Facepunch.GameObjectExtensions.CopyPropertiesTo(effect,holder.Components.Create<T>());
}
Copy<Tonemapping>();Copy<Bloom>();Copy<AmbientOcclusion>();Copy<Vignette>();Copy<Sharpen>();Copy<Facepunch.PhotographicResponse>();
holder.Enabled=true;scene.EditorTick(.016f,.016f);
var detail=scene.GetAllComponents<ModelCollider>().Single(c=>c.Model?.ResourcePath=="models/maps/collider/collider_detail.vmdl");
detail.GameObject.Tags.Add("cabinet-review-after");
}
await Task.Delay(1000,cancellationToken);
using(scene.Push())
using(Editor.EditorUtility.DisableTextureStreaming())
{
Vector3 World(Vector3 plan)=>new Vector3(plan.y+160,-plan.x+650,plan.z);
'''
footer='''
var result=new {NativePhysics=true,InstalledPackedModel=true,Count=checks.Count,Passed=failures.Count==0,Failures=failures,Checks=checks,
    IsolatedVerificationScene=true,OriginalRuntimeSceneName=originalScene.Name};
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"native-collision.json"),System.Text.Json.JsonSerializer.Serialize(result,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
if(failures.Count>0)throw new InvalidOperationException("Collision checks failed: "+string.Join(",",failures));
var flags=System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic;
camera.WorldPosition=new Vector3(110,590,66);camera.WorldRotation=Rotation.LookAt(new Vector3(160,650,27)-camera.WorldPosition);
typeof(Scene).GetMethod("PreRender",flags,null,Type.EmptyTypes,null).Invoke(scene,null);
typeof(Scene).GetMethod("PreCameraRender",flags,null,Type.EmptyTypes,null).Invoke(scene,null);
typeof(PostProcessSystem).GetMethod("UpdateCamera",flags).Invoke(scene.GetSystem<PostProcessSystem>(),new object[]{camera});
using var bitmap=new Bitmap(3840,2160);
for(var frame=0;frame<4;frame++)
{
camera.WorldPosition=new Vector3(110,590,66);camera.WorldRotation=Rotation.LookAt(new Vector3(160,650,27)-camera.WorldPosition);
camera.FieldOfView=80;camera.FovAxis=CameraComponent.Axis.Horizontal;camera.CustomSize=new Vector2(3840,2160);
camera.RenderToBitmap(bitmap,false);
}
System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"installed-native.png"),bitmap.ToPng());
using(var resolved=bitmap.Resize(1920,1080,true))System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"installed.png"),resolved.ToPng());
return result;
}
}
finally{scene.Destroy();}
'''
(HERE/'check-installed.cs.txt').write_text(header+s+footer)
