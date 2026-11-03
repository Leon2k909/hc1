from pathlib import Path
import json,sys
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
if '--capture-only' not in sys.argv:
 print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
 for name in ('blue','graphite','pipe'):
  result=call('asset_compile',dict(path=f'materials/reefhall/pump-v1/{name}.vmat',full=True));print(json.dumps(result),flush=True);assert result['Success']
 for name in (('circulation_pump',) if '--refresh-pump' in sys.argv else ('circulation_pump','filter_without_pump')):
  result=call('asset_compile',dict(path=f'models/maps/reefhall/pump-v1/{name}.vmdl',full=True));print(json.dumps(result),flush=True);assert result['Success']
src=(HERE/'runtime_before.cs.txt').read_text().replace('runtime-before','runtime-review')
src=src.replace('camera.IsMainCamera=false;', '''var gameplayCamera=scene.GetAllComponents<CameraComponent>().FirstOrDefault(c=>c!=camera&&c.IsMainCamera);
  if(gameplayCamera==null)throw new InvalidOperationException("No gameplay camera to match");
  void CopyEffect<T>() where T:Component,new() {
   var effect=gameplayCamera.GameObject.GetComponent<T>(true);if(effect==null)return;
   var copy=holder.Components.Create<T>();Facepunch.GameObjectExtensions.CopyPropertiesTo(effect,copy);
  }
  CopyEffect<Bloom>();CopyEffect<Tonemapping>();CopyEffect<Sharpen>();CopyEffect<AmbientOcclusion>();
  CopyEffect<Vignette>();CopyEffect<Facepunch.PhotographicResponse>();CopyEffect<ColorAdjustments>();
  var tone=holder.GetComponent<Tonemapping>();
  if(tone!=null&&tone.AutoExposureEnabled){tone.MinimumExposure=tone.MaximumExposure=(tone.MinimumExposure+tone.MaximumExposure)*.5f;tone.Rate=10;}
  System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"camera.json"),System.Text.Json.JsonSerializer.Serialize(new { Source=gameplayCamera.GameObject.Name, Effects=holder.Components.GetAll<Component>().Select(c=>c.GetType().Name).ToArray(), Tone=tone==null?null:new {tone.AutoExposureEnabled,tone.MinimumExposure,tone.MaximumExposure,tone.ExposureCompensation}}));
  foreach(var oldCamera in scene.GetAllComponents<CameraComponent>())oldCamera.IsMainCamera=false;
  camera.IsMainCamera=true;
  camera.BackgroundColor=gameplayCamera.BackgroundColor;''')
src=src.replace(' var views=new[]', ''' ModelRenderer architecture,replacement;Model originalModel;
 using(scene.Push()) {
  architecture=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/maps/reefhall/reefhall_filter.vmdl");originalModel=architecture.Model;
  var obj=new GameObject(false,"Reef Hall pump review");replacement=obj.Components.Create<ModelRenderer>();
  replacement.Model=Model.Load("models/maps/reefhall/pump-v1/circulation_pump.vmdl");
  if(replacement.Model.IsError)throw new InvalidOperationException("Candidate pump failed to load");
 }
 var views=new[]''')
src=src.replace(' foreach(var view in views) {', ''' foreach(var variant in new[]{"before","after"}) {
 architecture.Model=variant=="after"?Model.Load("models/maps/reefhall/pump-v1/filter_without_pump.vmdl"):originalModel;
 replacement.GameObject.Enabled=variant=="after";
 foreach(var view in views) {''')
src=src.replace('frame<120','frame<180').replace('view.Name+".png"','view.Name+"-"+variant+".png"')
src=src.replace(' var report=new { ActualPlayMode=', ' }\n var report=new { ActualPlayMode=')
(HERE/'runtime_review.cs.txt').write_text(src)
print(json.dumps(script(HERE/'runtime_review.cs.txt'),indent=2))
