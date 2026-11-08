from pathlib import Path
import json
OUT=Path('C:/sbox-projects/hc1/forked-shooter-main/output/veridant/stair-geometry-fix')
EX=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/1d09b2f423ab4564983b1b6933715a6a')
script='''var scene=Editor.SceneEditorSession.All.Single(s=>s.Scene?.Name=="veridant").Scene;
var renderer=scene.GetAllComponents<ModelRenderer>().Single(x=>x.Id==Guid.Parse("71d2be30-1656-5001-be4e-c4d181072a22"));
var original=renderer.Model;if(original.ResourcePath!="models/maps/veridant/veridant_buildings.vmdl")throw new Exception("Model changed");
var baseline=Model.Load("models/maps/veridant/reception-stair-closure-v1/review-before.vmdl");if(baseline.IsError)throw new Exception("Baseline error");
var t=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("Sandbox.ScreenshotService")).First(x=>x!=null);
var method=t.GetMethod("RequestCapture",System.Reflection.BindingFlags.Static|System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic);
string before=null;string after=null;
var engine="C:/Program Files (x86)/Steam/steamapps/common/sbox";
try {renderer.Model=baseline;await Task.Delay(800,cancellationToken);before=(string)method.Invoke(null,null);
for(var i=0;i<60&&!System.IO.File.Exists(System.IO.Path.Combine(engine,before));i++)await Task.Delay(100,cancellationToken);
if(!System.IO.File.Exists(System.IO.Path.Combine(engine,before)))throw new Exception("Before frame not displayed");}
finally {renderer.Model=original;}
await Task.Delay(800,cancellationToken);after=(string)method.Invoke(null,null);
for(var i=0;i<60&&!System.IO.File.Exists(System.IO.Path.Combine(engine,after));i++)await Task.Delay(100,cancellationToken);
if(!System.IO.File.Exists(System.IO.Path.Combine(engine,after)))throw new Exception("After frame not displayed");
var output=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/veridant/stair-geometry-fix");
System.IO.File.Copy(System.IO.Path.Combine(engine,before),System.IO.Path.Combine(output,"before.png"),true);
System.IO.File.Copy(System.IO.Path.Combine(engine,after),System.IO.Path.Combine(output,"after.png"),true);
return new{Before=before,After=after,Restored=renderer.Model.ResourcePath};'''
p=EX/'stair-comparison.cs';p.write_text(script);(OUT/'pair.json').write_text(json.dumps({'path':str(p)}))
