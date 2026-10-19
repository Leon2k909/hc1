using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Sandbox;
using static Sandbox.Internal.GlobalGameNamespace;
using static Sandbox.Internal.GlobalToolsNamespace;
public static class BelltowerScript0
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/capture-viewport.cs.txt"
// Capture the existing Belltower editor scene. No temporary scene or frame callbacks.
// Use its existing editor camera directly without changing the selected tab.
// Apply post-process and DDGI explicitly because hidden tabs skip normal updates.
var root = Sandbox.Project.Current.GetRootPath();
var config = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/viewport-capture.json")));
var folder = config["directory"].GetValue<string>();
var name = config["name"].GetValue<string>();
if (!System.Text.RegularExpressions.Regex.IsMatch(folder,"^[a-z0-9-]+$") || !System.Text.RegularExpressions.Regex.IsMatch(name,"^[a-z0-9-]+$"))
    throw new InvalidOperationException("Invalid capture name");
var destination = System.IO.Path.Combine(root,"output/belltower/quality",folder);
System.IO.Directory.CreateDirectory(destination);
var previous = Editor.SceneEditorSession.Active;
var gameId = Game.ActiveScene?.Id;
var playing = Game.IsPlaying;
var session = Editor.SceneEditorSession.All.Single(s => s.Scene.IsEditor && s.Scene.Source?.ResourcePath?.Equals("scenes/maps/belltower/belltower.scene",StringComparison.OrdinalIgnoreCase)==true);
var scene = session.Scene;
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
Vector3 oldPosition = default;
Rotation oldRotation = default;
CameraComponent camera = null;
float oldFov = 80;
Action restoreProjection = null;
var trialOverrides = new System.Collections.Generic.List<(ModelRenderer Renderer,int Slot,Material Original)>();
var trialSnapshots = new System.Collections.Generic.Dictionary<ModelRenderer,string>();
var plasterTrialSlots = 0;
var weatheredPlasterTrial = config["weathered_plaster_trial"]?.GetValue<bool>()==true;
var canopyTrialSlots = 0;
var farfieldTrialSlots = 0;
var streetTrialSlots = 0;
var streetTrial = config["street_trial"]?.GetValue<bool>()==true;
Material streetTrialMaterial = null;
var canopyTrial = config["canopy_trial"]?.GetValue<bool>()==true;
var farfieldTrial = config["farfield_trial"]?.GetValue<bool>()==true;
if(canopyTrial && farfieldTrial) throw new InvalidOperationException("Choose only one landscape trial.");
var landscapeTrial = canopyTrial || farfieldTrial;
System.Collections.Generic.Dictionary<string,Material> canopyMaterials = null;
GameObject trialForest = null;
var originalObjects = scene.GetAllObjects(true).Select(o=>o.Id).ToHashSet();
var forestTrial = config["forest_trial"]?.GetValue<bool>()==true;
var forestBrightness = config["forest_brightness"]?.GetValue<float>();
var lookTrial = config["look_trial"]?.AsObject();
var syncMainPostprocess = config["sync_main_postprocess"]?.GetValue<bool>()==true;
var mainCamera = scene.Camera;
var mainExposureSnapshot = mainCamera.IsValid() ? new {
    mainCamera.AutoExposure.Enabled, mainCamera.AutoExposure.MinimumExposure,
    mainCamera.AutoExposure.MaximumExposure, mainCamera.AutoExposure.Compensation, mainCamera.AutoExposure.Rate
} : null;
var tone = scene.GetAllComponents<Tonemapping>().Single(c=>c.GameObject.Name=="Look");
var oldToneMinimum = tone.MinimumExposure;
var oldToneMaximum = tone.MaximumExposure;
var oldToneCompensation = tone.ExposureCompensation;
var oldToneMode = tone.Mode;
var toneSnapshot = tone.Serialize().ToJsonString();
if(lookTrial is not null)
{
    var minimum=lookTrial["minimum_exposure"].GetValue<float>();
    var maximum=lookTrial["maximum_exposure"].GetValue<float>();
    if(minimum<.2f || maximum>3 || maximum<minimum
        || !Enum.TryParse<Tonemapping.TonemappingMode>(lookTrial["mode"].GetValue<string>(),out _))
        throw new InvalidOperationException("Invalid tone mapping comparison.");
}
if(forestBrightness is float brightness && (!forestTrial || brightness<.05f || brightness>1.5f))
    throw new InvalidOperationException("Forest brightness requires a trial and a value from .05 to 1.5.");
// Request useful mip levels before the atomic capture. This await never holds
// a scene scope, camera change, material override or selected-document change.
var captureMaterials = new System.Collections.Generic.HashSet<Material>();
using(scene.Push())
{
    foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("models/maps/belltower/",StringComparison.OrdinalIgnoreCase)==true))
    for(var slot=0;slot<renderer.Materials.Count;slot++)
        captureMaterials.Add(renderer.Materials.GetOverride(slot) ?? renderer.Materials.GetOriginal(slot));
    if(config["plaster_trial"]?.GetValue<bool>()==true)
    {
        var records=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/plaster-v1-materials.json"))).AsArray();
        foreach(var record in records) captureMaterials.Add(Material.Load(record["path"].GetValue<string>()));
    }
    if(weatheredPlasterTrial)
    {
        var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/plaster-weathered-v2/manifest.json")));
        if(manifest["revision"].GetValue<string>()!="plaster-weathered-v2") throw new InvalidOperationException("Wrong plaster trial");
        foreach(var entry in manifest["records"].AsArray()) captureMaterials.Add(Material.Load(entry["path"].GetValue<string>()));
    }
    if(streetTrial)
    {
        var stage=System.IO.Path.Combine(root,"output/belltower/quality/streetwear-v1/manifest.json");
        var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(stage));
        string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
        if(manifest["revision"].GetValue<string>()!="streetwear-v1")
            throw new InvalidOperationException("Unexpected street trial revision");
        foreach(var asset in manifest["trial"].AsArray())
        {
            var resource=asset["resource"].GetValue<string>();
            if(resource!="shaders/belltower_streetwear_trial.shader" && resource!="materials/belltower/trials/street_cobbles_aaa.vmat")
                throw new InvalidOperationException("Unexpected street trial resource");
            if(Hash(System.IO.Path.Combine(root,"Assets",resource))!=asset["sha256"].GetValue<string>())
                throw new InvalidOperationException("Street trial resource differs from staged source");
        }
        streetTrialMaterial=Material.Load("materials/belltower/trials/street_cobbles_aaa.vmat");
        if(streetTrialMaterial is null || streetTrialMaterial.IsError)
            throw new InvalidOperationException("Street trial material is not compiled");
        captureMaterials.Add(streetTrialMaterial);
    }
    if(forestTrial) captureMaterials.Add(Material.Load("materials/belltower/forest/forest_trees.vmat"));
    if(landscapeTrial)
    {
        var stage=System.IO.Path.Combine(root,canopyTrial ? "output/belltower/quality/canopy-photo-v2-full" : "output/belltower/quality/farfield-v3");
        var manifestPath=System.IO.Path.Combine(stage,canopyTrial ? "native-import.json" : "manifest.json");
        var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(manifestPath));
        var imported=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage,"native-import-result.json")));
        string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
        if(manifest["revision"].GetValue<string>()!=(canopyTrial ? "canopy-photo-v2" : "farfield-v3") || imported["ManifestSha256"].GetValue<string>()!=Hash(manifestPath))
            throw new InvalidOperationException("The landscape trial has not completed its checked native import.");
        foreach(var file in manifest[canopyTrial ? "files" : "resources"].AsArray())
            if(Hash(System.IO.Path.Combine(root,"Assets",file["path"].GetValue<string>()))!=file["sha256"].GetValue<string>())
                throw new InvalidOperationException("An installed landscape trial file changed.");
        canopyMaterials=manifest["material_overrides"].AsObject().ToDictionary(x=>x.Key,x=>Material.Load(x.Value.GetValue<string>()),StringComparer.OrdinalIgnoreCase);
        if(canopyMaterials.Count!=2 || canopyMaterials.Values.Any(m=>m is null || m.IsError))
            throw new InvalidOperationException("A landscape trial material failed to load.");
        foreach(var material in canopyMaterials.Values) captureMaterials.Add(material);
    }
    foreach(var material in captureMaterials.Where(m=>m is not null && !m.IsError))
    {
    foreach(var key in new[]{"g_tColor","g_tNormal","g_tRma","g_tHeight","g_tPlants","g_tWearColor","g_tWearNormal","g_tWearData","g_tCanopyColorB","g_tCanopyNormalB","g_tCanopyColorC","g_tCanopyNormalC","g_tCanopyColorD","g_tCanopyNormalD"})
        material.GetTexture(key)?.MarkUsed(2048);
    foreach(var key in new[]{"g_tColorA","g_tColorB","g_tColorC","g_tColorD","g_tCanopyColorB","g_tCanopyColorC","g_tCanopyColorD"})
        material.GetTexture(key)?.MarkUsed(4096);
    foreach(var key in new[]{"g_tNormalA","g_tNormalB","g_tNormalC","g_tNormalD"})
        material.GetTexture(key)?.MarkUsed(2048);
    }
    foreach(var volume in scene.GetAllComponents<IndirectLightVolume>())
    foreach(var texture in new[]{volume.IrradianceTexture,volume.DistanceTexture,volume.RelocationTexture})
        if(texture is not null && !texture.IsError) texture.MarkUsed(Math.Max(texture.Width,texture.Height));
}
await Task.Delay(1000,cancellationToken);
try
{
    cancellationToken.ThrowIfCancellationRequested();
    camera = scene.GetAllComponents<CameraComponent>().Single(c => c.GameObject.Name=="editor_camera" && c.GameObject.Flags.HasFlag(GameObjectFlags.EditorOnly));
    oldPosition = camera.WorldPosition;
    oldRotation = camera.WorldRotation;
    oldFov = camera.FieldOfView;
    var oldFovAxis = camera.FovAxis;
    var oldCustomSize = camera.CustomSize;
    restoreProjection = () => { camera.FovAxis=oldFovAxis; camera.CustomSize=oldCustomSize; };
    object captureResult;
    object captureProjection;
    object nativeExposure;
    using (scene.Push())
    {
        if(lookTrial is not null)
        {
            tone.MinimumExposure=lookTrial["minimum_exposure"].GetValue<float>();
            tone.MaximumExposure=lookTrial["maximum_exposure"].GetValue<float>();
            tone.ExposureCompensation=lookTrial["compensation"]?.GetValue<float>() ?? 0;
            tone.Mode=Enum.Parse<Tonemapping.TonemappingMode>(lookTrial["mode"].GetValue<string>());
        }
        if(forestTrial)
        {
            if(scene.GetAllObjects(true).Any(o=>o.Name=="Distant woodland"))
                throw new InvalidOperationException("A saved woodland group is already present; use a saved-scene capture.");
            var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/forest-v1-staging/forest.json"))).AsObject();
            trialForest=scene.CreateObject(false);
            trialForest.Deserialize(data);
            trialForest.Flags |= GameObjectFlags.EditorOnly;
            if(forestBrightness is float canopyBrightness)
            {
                var material=Material.Load("materials/belltower/forest/forest_trees.vmat").CreateCopy("forest-canopy-trial-"+Guid.NewGuid());
                material.Set("g_flCanopyBrightness",canopyBrightness);
                foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.StartsWith("models/maps/belltower/forest/",StringComparison.OrdinalIgnoreCase)==true))
                    renderer.Materials.SetOverride(0,material);
            }
        }
        if(config["plaster_trial"]?.GetValue<bool>()==true || weatheredPlasterTrial)
        {
            var records=weatheredPlasterTrial
                ? System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/plaster-weathered-v2/manifest.json")))["records"].AsArray()
                : System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/plaster-v1-materials.json"))).AsArray();
            var trials=records.ToDictionary(x=>x["target"].GetValue<string>(),x=>Material.Load(x["path"].GetValue<string>()),StringComparer.OrdinalIgnoreCase);
            if(trials.Values.Any(m=>m is null || m.IsError)) throw new InvalidOperationException("A plaster trial material failed to load");
            foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("models/maps/belltower/",StringComparison.OrdinalIgnoreCase)==true))
            for(var slot=0;slot<renderer.Materials.Count;slot++)
            {
                var path=renderer.Materials.GetOriginal(slot)?.ResourcePath;
                if(path is null || !trials.TryGetValue(path,out var material)) continue;
                if(!trialSnapshots.ContainsKey(renderer)) trialSnapshots.Add(renderer,renderer.Serialize().ToJsonString());
                trialOverrides.Add((renderer,slot,renderer.Materials.GetOverride(slot)));
                renderer.Materials.SetOverride(slot,material);
            }
            if(trialOverrides.Count==0) throw new InvalidOperationException("No plaster material slots matched");
            plasterTrialSlots=trialOverrides.Count;
        }
        if(streetTrial)
        {
            foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("models/maps/belltower/",StringComparison.OrdinalIgnoreCase)==true))
            for(var slot=0;slot<renderer.Materials.Count;slot++)
            {
                var path=renderer.Materials.GetOriginal(slot)?.ResourcePath;
                if(!string.Equals(path,"materials/belltower/street_cobbles.vmat",StringComparison.OrdinalIgnoreCase)) continue;
                if(!trialSnapshots.ContainsKey(renderer)) trialSnapshots.Add(renderer,renderer.Serialize().ToJsonString());
                trialOverrides.Add((renderer,slot,renderer.Materials.GetOverride(slot)));
                renderer.Materials.SetOverride(slot,streetTrialMaterial);
                streetTrialSlots++;
            }
            if(streetTrialSlots==0) throw new InvalidOperationException("No cobblestone slots matched the Belltower models");
        }
        if(landscapeTrial)
        {
            var matched=new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("models/maps/belltower/",StringComparison.OrdinalIgnoreCase)==true))
            for(var slot=0;slot<renderer.Materials.Count;slot++)
            {
                var path=renderer.Materials.GetOriginal(slot)?.ResourcePath;
                if(path is null || !canopyMaterials.TryGetValue(path,out var material)) continue;
                if(!trialSnapshots.ContainsKey(renderer)) trialSnapshots.Add(renderer,renderer.Serialize().ToJsonString());
                trialOverrides.Add((renderer,slot,renderer.Materials.GetOverride(slot)));
                renderer.Materials.SetOverride(slot,material);
                matched.Add(path);
                if(canopyTrial) canopyTrialSlots++; else farfieldTrialSlots++;
            }
            if(matched.Count!=2) throw new InvalidOperationException("Both the landscape and forest material must match for a landscape comparison.");
        }
        camera.WorldPosition = Vector3.Parse(config["position"].GetValue<string>());
        camera.WorldRotation = Rotation.From(Angles.Parse(config["angles"].GetValue<string>()));
        camera.FieldOfView = config["fov"]?.GetValue<float>() ?? 80;
        // SceneViewportWidget resets projection on editor frames. Configure it
        // after the streaming wait, immediately before this synchronous render.
        camera.FovAxis = CameraComponent.Axis.Horizontal;
        camera.CustomSize = new Vector2(config["width"]?.GetValue<int>() ?? 1920,config["height"]?.GetValue<int>() ?? 1080);
        typeof(Scene).GetMethod("PreRender",flags,null,Type.EmptyTypes,null).Invoke(scene,null);
        typeof(Scene).GetMethod("PreCameraRender",flags,null,Type.EmptyTypes,null).Invoke(scene,null);
        var post = scene.GetSystem<PostProcessSystem>();
        typeof(PostProcessSystem).GetMethod("UpdateCamera",flags).Invoke(post,new object[]{camera});
        if(syncMainPostprocess && mainCamera.IsValid() && !ReferenceEquals(mainCamera,camera))
            typeof(PostProcessSystem).GetMethod("UpdateCamera",flags).Invoke(post,new object[]{mainCamera});
        // Hidden documents can miss FinishUpdate after resource hotloads. Refresh
        // the native DDGI buffer so its bindless indices match the loaded textures.
        var ddgiType = typeof(Scene).Assembly.GetType("Sandbox.DDGIVolumeSystem");
        var getSystem = typeof(Scene).GetMethods().Single(m => m.Name=="GetSystem" && m.IsGenericMethodDefinition && m.GetParameters().Length==0);
        var ddgi = getSystem.MakeGenericMethod(ddgiType).Invoke(scene,null);
        ddgiType.GetMethod("MarkDirty",flags).Invoke(ddgi,null);
        ddgiType.GetMethod("UpdateVolumes",flags).Invoke(ddgi,null);
        if (!camera.AutoExposure.Enabled || MathF.Abs(camera.AutoExposure.MinimumExposure-tone.MinimumExposure)>.001f || MathF.Abs(camera.AutoExposure.MaximumExposure-tone.MaximumExposure)>.001f)
            throw new InvalidOperationException("Belltower's saved tone mapping did not reach the viewport camera");
        using var bitmap = new Bitmap(config["width"]?.GetValue<int>() ?? 1920,config["height"]?.GetValue<int>() ?? 1080);
        camera.RenderToBitmap(bitmap,false);
        var nativeCamera=typeof(CameraComponent).GetField("sceneCamera",flags).GetValue(camera);
        var nativeTone=nativeCamera.GetType().GetProperty("Tonemap",flags).GetValue(nativeCamera);
        object NativeToneValue(string property) => nativeTone.GetType().GetProperty(property,flags).GetValue(nativeTone);
        var main=scene.Camera;
        nativeExposure=new {
            Enabled=NativeToneValue("Enabled"), MinExposure=NativeToneValue("MinExposure"), MaxExposure=NativeToneValue("MaxExposure"),
            ExposureCompensation=NativeToneValue("ExposureCompensation"), Rate=NativeToneValue("Rate"),
            MainCamera=main?.GameObject.Name, MainCameraIsViewport=ReferenceEquals(main,camera),
            MainAutoExposureEnabled=main?.AutoExposure.Enabled,
            MainMinimumExposure=main?.AutoExposure.MinimumExposure,
            MainMaximumExposure=main?.AutoExposure.MaximumExposure,
            MainCompensation=main?.AutoExposure.Compensation
        };
        System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination,name+".png"),bitmap.ToPng());
        captureProjection = new { FovAxis=camera.FovAxis.ToString(), CustomSize=camera.CustomSize.ToString(), Width=bitmap.Width, Height=bitmap.Height };
        captureResult = new { Scene=scene.Name, CameraScene=camera.Scene.Name, Position=camera.WorldPosition.ToString(), Angles=camera.WorldRotation.Angles().ToString(), camera.FieldOfView,
            camera.EnablePostProcessing, camera.AutoExposure.Enabled, camera.AutoExposure.MinimumExposure, camera.AutoExposure.MaximumExposure,
            camera.AutoExposure.Compensation, camera.AutoExposure.Rate };
    }
    var result = new { Capture=captureResult, Projection=captureProjection, TrialPlasterSlots=plasterTrialSlots, TrialCanopySlots=canopyTrialSlots, TrialFarfieldSlots=farfieldTrialSlots, TrialStreetSlots=streetTrialSlots,
        TrialForestSectors=trialForest is null ? 0 : trialForest.Children.Count,
        Lighting=scene.GetAllComponents<IndirectLightVolume>().Select(v=>new {
            v.GameObject.Name, v.BakeVersion,
            Irradiance=v.IrradianceTexture?.ResourcePath, Distance=v.DistanceTexture?.ResourcePath, Relocation=v.RelocationTexture?.ResourcePath,
            TexturesValid=v.IrradianceTexture is not null && !v.IrradianceTexture.IsError && v.DistanceTexture is not null && !v.DistanceTexture.IsError && v.RelocationTexture is not null && !v.RelocationTexture.IsError }).ToArray(),
        TrialForestBrightness=forestBrightness,
        TrialLook=lookTrial,
        NativeExposureAfterRender=nativeExposure,
        MainPostprocessSynced=syncMainPostprocess,
        SourceScene=scene.Source?.ResourcePath, SceneHasUnsavedChanges=session.HasUnsavedChanges,
        GamePreserved=Game.ActiveScene?.Id==gameId && Game.IsPlaying==playing, SelectedDocumentPreserved=ReferenceEquals(previous,Editor.SceneEditorSession.Active) };
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,name+"-camera.json"),System.Text.Json.JsonSerializer.Serialize(result));
    return result;
}
finally
{
    var toneRestored=true;
    if(lookTrial is not null)
    {
        tone.MinimumExposure=oldToneMinimum;
        tone.MaximumExposure=oldToneMaximum;
        tone.ExposureCompensation=oldToneCompensation;
        tone.Mode=oldToneMode;
        toneRestored=tone.Serialize().ToJsonString()==toneSnapshot;
        if(camera.IsValid())
        {
            using(scene.Push())
                typeof(PostProcessSystem).GetMethod("UpdateCamera",flags).Invoke(scene.GetSystem<PostProcessSystem>(),new object[]{camera});
        }
        System.IO.File.WriteAllText(System.IO.Path.Combine(destination,name+"-look-restore.json"),System.Text.Json.JsonSerializer.Serialize(new{ToneRestored=toneRestored}));
    }
    if(syncMainPostprocess && mainCamera.IsValid() && !ReferenceEquals(mainCamera,camera))
    {
        using(scene.Push())
            typeof(PostProcessSystem).GetMethod("UpdateCamera",flags).Invoke(scene.GetSystem<PostProcessSystem>(),new object[]{mainCamera});
        mainCamera.AutoExposure.Enabled=mainExposureSnapshot.Enabled;
        mainCamera.AutoExposure.MinimumExposure=mainExposureSnapshot.MinimumExposure;
        mainCamera.AutoExposure.MaximumExposure=mainExposureSnapshot.MaximumExposure;
        mainCamera.AutoExposure.Compensation=mainExposureSnapshot.Compensation;
        mainCamera.AutoExposure.Rate=mainExposureSnapshot.Rate;
    }
    if(trialForest.IsValid())
    {
        using(scene.Push()) { trialForest.Destroy(); scene.ProcessDeletes(); }
        var forestRestored=scene.GetAllObjects(true).Select(o=>o.Id).ToHashSet().SetEquals(originalObjects);
        System.IO.File.WriteAllText(System.IO.Path.Combine(destination,name+"-forest-restore.json"),System.Text.Json.JsonSerializer.Serialize(new{ForestRestored=forestRestored}));
        if(!forestRestored) throw new InvalidOperationException("Forest preview cleanup differs; inspect before continuing.");
    }
    foreach(var item in trialOverrides) if(item.Renderer.IsValid()) item.Renderer.Materials.SetOverride(item.Slot,item.Original);
    var materialsRestored=trialSnapshots.All(x=>x.Key.IsValid() && x.Key.Serialize().ToJsonString()==x.Value);
    if(trialOverrides.Count>0) System.IO.File.WriteAllText(System.IO.Path.Combine(destination,name+"-restore.json"),System.Text.Json.JsonSerializer.Serialize(new{MaterialsRestored=materialsRestored,Slots=trialOverrides.Count}));
    if (camera.IsValid()) { camera.WorldPosition=oldPosition; camera.WorldRotation=oldRotation; camera.FieldOfView=oldFov; restoreProjection?.Invoke(); }
    if(!toneRestored) throw new InvalidOperationException("Tone mapping comparison did not restore; inspect before continuing.");
    if(!materialsRestored) throw new InvalidOperationException("Material trial restoration differs; inspect the editor before further work");
}

#line default
}
}
public static class BelltowerScript1
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/inspect-capture-cameras.cs.txt"
// Read existing camera state only. Do not initialize, select or render a camera.
var root=Sandbox.Project.Current.GetRootPath();
var flags=System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic;
var previous=Editor.SceneEditorSession.Active;
var gameId=Game.ActiveScene?.Id;
var playing=Game.IsPlaying;
var session=Editor.SceneEditorSession.All.SingleOrDefault(s=>s.Scene.IsEditor && s.Scene.Source?.ResourcePath?.Equals("scenes/maps/belltower/belltower.scene",StringComparison.OrdinalIgnoreCase)==true);
if(session is null)
    return new {
        ScenePresent=false, ActiveDocument=previous?.Scene.Source?.ResourcePath, Playing=playing,
        OpenDocuments=Editor.SceneEditorSession.All.Select(s=>s.Scene.Source?.ResourcePath).ToArray(),
        GamePreserved=Game.ActiveScene?.Id==gameId && Game.IsPlaying==playing,
        SelectedDocumentPreserved=ReferenceEquals(previous,Editor.SceneEditorSession.Active)
    };
var scene=session.Scene;
object ReadCamera(CameraComponent camera)
{
    if(!camera.IsValid()) return null;
    var native=typeof(CameraComponent).GetField("sceneCamera",flags).GetValue(camera);
    var tone=native?.GetType().GetProperty("Tonemap",flags)?.GetValue(native);
    object ToneValue(string property) => tone?.GetType().GetProperty(property,flags)?.GetValue(tone);
    var system=tone?.GetType().GetField("System",flags)?.GetValue(tone);
    return new {
        camera.Id, Name=camera.GameObject.Name, camera.Enabled,
        EditorCamera=typeof(CameraComponent).GetField("IsSceneEditorCamera",flags)?.GetValue(camera),
        camera.EnablePostProcessing,
        Requested=new{camera.AutoExposure.Enabled,camera.AutoExposure.MinimumExposure,camera.AutoExposure.MaximumExposure,camera.AutoExposure.Compensation,camera.AutoExposure.Rate},
        Native=tone is null ? null : new {
            Enabled=ToneValue("Enabled"),MinimumExposure=ToneValue("MinExposure"),MaximumExposure=ToneValue("MaxExposure"),
            Compensation=ToneValue("ExposureCompensation"),Rate=ToneValue("Rate"),
            SystemValid=system?.GetType().GetProperty("IsValid",flags)?.GetValue(system)
        }
    };
}
var result=new {
    ScenePresent=true,
    Scene=scene.Source.ResourcePath, ActiveDocument=previous?.Scene.Source?.ResourcePath, Playing=playing,
    MainCamera=ReadCamera(scene.Camera),
    Cameras=scene.GetAllComponents<CameraComponent>().Select(ReadCamera).ToArray(),
    GamePreserved=Game.ActiveScene?.Id==gameId && Game.IsPlaying==playing,
    SelectedDocumentPreserved=ReferenceEquals(previous,Editor.SceneEditorSession.Active)
};
var output=System.IO.Path.Combine(root,"output/belltower/quality/capture-camera-state.json");
System.IO.File.WriteAllText(output,System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
public static class BelltowerScript2
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/import-canopy-trial.cs.txt"
// Import a separate reviewed texture candidate. Accepted materials stay intact.
var root=Sandbox.Project.Current.GetRootPath();
var stage=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"output/belltower/quality/canopy-photo-v2-full"));
var assets=System.IO.Path.GetFullPath(System.IO.Path.Combine(root,"Assets"));
var manifestPath=System.IO.Path.Combine(stage,"native-import.json");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(manifestPath));
if(manifest["revision"].GetValue<string>()!="canopy-photo-v2") throw new InvalidOperationException("Unexpected canopy revision.");
string Hash(string path)
{
    using var stream=System.IO.File.OpenRead(path);
    return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).ToLowerInvariant();
}
foreach(var group in new[]{"source_hashes","base_inputs"})
    foreach(var dependency in manifest[group].AsObject())
        if(Hash(System.IO.Path.Combine(root,dependency.Key))!=dependency.Value.GetValue<string>())
            throw new InvalidOperationException("Checked canopy dependency changed: "+dependency.Key);
var accepted=manifest["accepted_manifest"];
if(Hash(System.IO.Path.Combine(root,accepted["path"].GetValue<string>()))!=accepted["sha256"].GetValue<string>())
    throw new InvalidOperationException("The accepted landscape changed after staging.");
var allowed=new System.Collections.Generic.HashSet<string>{"vista_land.vmat","forest_trees.vmat"};
foreach(var zone in new[]{"a","b","c","d"})
    foreach(var suffix in new[]{"color.jpg","kind.png"}) allowed.Add("vista_"+zone+"_"+suffix);
var files=manifest["files"].AsArray();
if(files.Count!=allowed.Count) throw new InvalidOperationException("Unexpected canopy trial file count.");
var checkedNames=new System.Collections.Generic.HashSet<string>();
foreach(var file in files)
{
    var relative=file["path"].GetValue<string>();
    var name=System.IO.Path.GetFileName(relative);
    if(!allowed.Contains(name) || !checkedNames.Add(name)
        || relative!="materials/belltower/vista/canopy-photo-v2/"+name
        || file["source"].GetValue<string>()!="output/belltower/quality/canopy-photo-v2-full/"+name)
        throw new InvalidOperationException("Unexpected canopy trial path.");
    var destination=System.IO.Path.Combine(assets,relative);
    var source=System.IO.Path.Combine(stage,name);
    var digest=file["sha256"].GetValue<string>();
    if(Hash(source)!=digest || (System.IO.File.Exists(destination) && Hash(destination)!=digest))
        throw new InvalidOperationException("Canopy trial input or destination changed: "+name);
}
var game=Game.ActiveScene?.Id;
var playing=Game.IsPlaying;
var selected=Editor.SceneEditorSession.Active;
var incomingDirectory=System.IO.Path.Combine(stage,"native-incoming");
System.IO.Directory.CreateDirectory(incomingDirectory);
foreach(var file in files)
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative=file["path"].GetValue<string>();
    var name=System.IO.Path.GetFileName(relative);
    var destination=System.IO.Path.Combine(assets,relative);
    if(System.IO.File.Exists(destination)) continue; // Complete batch checked above.
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    var incoming=System.IO.Path.Combine(incomingDirectory,name);
    if(!System.IO.File.Exists(incoming)) System.IO.File.Copy(System.IO.Path.Combine(stage,name),incoming);
    if(Hash(incoming)!=file["sha256"].GetValue<string>()) throw new InvalidOperationException("Incoming canopy asset changed.");
    System.IO.File.Move(incoming,destination); // A trial never overwrites an existing different asset.
    if(Hash(destination)!=file["sha256"].GetValue<string>()) throw new InvalidOperationException("Published canopy asset differs.");
}
foreach(var material in manifest["material_overrides"].AsObject())
    Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(assets,material.Value.GetValue<string>()));
var result=new {Imported=files.Count, ManifestSha256=Hash(manifestPath), AcceptedAssetsReplaced=false,
    GamePreserved=Game.ActiveScene?.Id==game && Game.IsPlaying==playing,
    SelectedDocumentPreserved=ReferenceEquals(selected,Editor.SceneEditorSession.Active)};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-import-result.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
public static class BelltowerScript3
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/verify-canopy-trial.cs.txt"
// Verify imported sources and loaded trial materials without selecting a scene.
var root=Sandbox.Project.Current.GetRootPath();
var stage=System.IO.Path.Combine(root,"output/belltower/quality/canopy-photo-v2-full");
var manifestPath=System.IO.Path.Combine(stage,"native-import.json");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(manifestPath));
var imported=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(stage,"native-import-result.json")));
string Hash(string path)
{
    using var stream=System.IO.File.OpenRead(path);
    return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).ToLowerInvariant();
}
var digest=Hash(manifestPath);
if(imported["ManifestSha256"].GetValue<string>()!=digest) throw new InvalidOperationException("Canopy import manifest differs.");
foreach(var file in manifest["files"].AsArray())
    if(Hash(System.IO.Path.Combine(root,"Assets",file["path"].GetValue<string>()))!=file["sha256"].GetValue<string>())
        throw new InvalidOperationException("Installed canopy trial file differs.");
foreach(var dependency in manifest["base_inputs"].AsObject())
    if(Hash(System.IO.Path.Combine(root,dependency.Key))!=dependency.Value.GetValue<string>())
        throw new InvalidOperationException("An accepted landscape input changed.");
var game=Game.ActiveScene?.Id;
var playing=Game.IsPlaying;
var selected=Editor.SceneEditorSession.Active;
var materials=new System.Collections.Generic.List<object>();
foreach(var entry in manifest["material_overrides"].AsObject())
{
    var path=entry.Value.GetValue<string>();
    var material=Material.Load(path);
    if(material is null || material.IsError) throw new InvalidOperationException("Canopy material failed to load: "+path);
    var forest=path.EndsWith("/forest_trees.vmat",StringComparison.Ordinal);
    var textures=new System.Collections.Generic.List<object>();
    foreach(var zone in forest ? new[]{"B","C","D"} : new[]{"A","B","C","D"})
    foreach(var kind in new[]{"Color","Normal"})
    {
        var key="g_t"+(forest ? "Canopy" : "")+kind+zone;
        var texture=material.GetTexture(key);
        var size=kind=="Color" ? 4096 : 2048;
        if(texture is null || texture.IsError || texture.Width!=size || texture.Height!=size)
            throw new InvalidOperationException("Canopy texture failed or has unexpected dimensions: "+key);
        textures.Add(new {Key=key,texture.Width,texture.Height,Path=texture.ResourcePath});
    }
    materials.Add(new {Path=path,Textures=textures});
}
var result=new {ManifestSha256=digest,Materials=materials,AcceptedInputsUnchanged=true,
    GamePreserved=Game.ActiveScene?.Id==game && Game.IsPlaying==playing,
    SelectedDocumentPreserved=ReferenceEquals(selected,Editor.SceneEditorSession.Active)};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-resources.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
public static class BelltowerScript4
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/import-gardens.cs.txt"
// The model files may also hotload while an unrelated map is running. Preserve
// that session, and refuse a live map that uses any Belltower model.
var playing=Game.IsPlaying;
var runtimePath=Game.ActiveScene?.Source?.ResourcePath?.ToLowerInvariant();
if(playing && (runtimePath!="scenes/maps/collider/collider.scene" && runtimePath!="scenes/maps/sewage/sewage.scene"
    || Game.ActiveScene.GetAllComponents<ModelRenderer>().Any(r=>r.Model?.ResourcePath?.StartsWith("models/maps/belltower/",StringComparison.OrdinalIgnoreCase)==true)))
    throw new InvalidOperationException("The current play session cannot safely hotload Belltower's models.");
var root=Sandbox.Project.Current.GetRootPath();
var request=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/garden-import-request.json")));
var revision=request["revision"].GetValue<string>();
if(revision!="garden-v1" && revision!="garden-v2" && revision!="garden-v3") throw new InvalidOperationException("Unknown garden revision.");
var stage=System.IO.Path.Combine(root,"output/belltower/quality/models",revision);
var manifestPath=System.IO.Path.Combine(stage,"native-import.json");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(manifestPath));
if(manifest["revision"].GetValue<string>()!=revision) throw new InvalidOperationException("Garden revision mismatch.");
if(manifest["spots"].GetValue<int>()!=94 || manifest["invalid_spots"].GetValue<int>()!=0 || manifest["unreachable_spots"].GetValue<int>()!=0)
    throw new InvalidOperationException("Gameplay validation did not pass.");
if(manifest["geometry_checks"]["checks"].GetValue<int>()!=11
    || !manifest["geometry_checks"]["garden_collision_preserved"].GetValue<bool>()
    || !manifest["geometry_checks"]["shared_random_sequence_preserved"].GetValue<bool>())
    throw new InvalidOperationException("Garden geometry validation did not pass.");
string Hash(string path)
{
    using var stream=System.IO.File.OpenRead(path);
    return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).ToLowerInvariant();
}
string PhysicsHash(string path)
{
    var text=System.IO.File.ReadAllText(path).Replace("\r\n","\n");
    var marker="_class = \"PhysicsShapeList\"";
    var start=text.IndexOf(marker,StringComparison.Ordinal);
    if(start<0) throw new InvalidOperationException("Physics list is missing.");
    var rest=text.Substring(start+marker.Length);
    var end=rest.IndexOf("\n\t\t]\n",StringComparison.Ordinal);
    if(end<0) throw new InvalidOperationException("Physics list is incomplete.");
    return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(rest.Substring(0,end)))).ToLowerInvariant();
}
foreach(var source in manifest["source_hashes"].AsObject())
    if(Hash(System.IO.Path.Combine(root,source.Key))!=source.Value.GetValue<string>())
        throw new InvalidOperationException("Generator changed since validation: "+source.Key);
foreach(var key in new[]{"collision_inputs","existing_material_dependencies","unchanged_model_inputs"})
    foreach(var dependency in manifest[key].AsArray())
        if(Hash(System.IO.Path.Combine(root,dependency["path"].GetValue<string>()))!=dependency["sha256"].GetValue<string>())
            throw new InvalidOperationException("A checked dependency changed: "+dependency["path"].GetValue<string>());
var files=manifest["files"].AsArray();
var allowed=new System.Collections.Generic.HashSet<string>();
foreach(var side in new[]{"west","east"})
    foreach(var extension in revision=="garden-v1" ? new[]{"obj","mtl","vmdl"} : new[]{"obj"}) allowed.Add("belltower_"+side+"."+extension);
if(files.Count!=allowed.Count) throw new InvalidOperationException("Garden source file count differs from the revision allowlist.");
var checkedNames=new System.Collections.Generic.HashSet<string>();
foreach(var file in files)
{
    var relative=file["path"].GetValue<string>();
    var name=System.IO.Path.GetFileName(relative);
    if(!allowed.Contains(name) || !checkedNames.Add(name) || relative!="models/maps/belltower/"+name
        || file["source"].GetValue<string>()!="output/belltower/quality/models/"+revision+"/"+name)
        throw new InvalidOperationException("Unexpected garden asset path.");
    var current=Hash(System.IO.Path.Combine(root,"Assets",relative));
    if(Hash(System.IO.Path.Combine(stage,name))!=file["sha256"].GetValue<string>()
        || (current!=file["expected_sha256"].GetValue<string>() && current!=file["sha256"].GetValue<string>()))
        throw new InvalidOperationException("A source or destination changed: "+name);
}
foreach(var model in manifest["models"].AsArray())
{
    var name=model["name"].GetValue<string>()+".vmdl";
    var expected=model["physics_sha256"].GetValue<string>();
    if(PhysicsHash(System.IO.Path.Combine(stage,name))!=expected
        || PhysicsHash(System.IO.Path.Combine(root,"Assets/models/maps/belltower",name))!=expected)
        throw new InvalidOperationException("Model physics differs: "+name);
}
var game=Game.ActiveScene?.Id;
var active=Editor.SceneEditorSession.Active;
var incomingDirectory=System.IO.Path.Combine(stage,"native-incoming");
System.IO.Directory.CreateDirectory(incomingDirectory);
foreach(var file in files)
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative=file["path"].GetValue<string>();
    var name=System.IO.Path.GetFileName(relative);
    var destination=System.IO.Path.Combine(root,"Assets",relative);
    var backup=System.IO.Path.Combine(root,"output/belltower/quality",revision+"-before/assets",relative);
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(backup));
    if(!System.IO.File.Exists(backup))
    {
        if(Hash(destination)!=file["expected_sha256"].GetValue<string>()) throw new InvalidOperationException("Original backup missing: "+name);
        System.IO.File.Copy(destination,backup);
    }
    if(Hash(backup)!=file["expected_sha256"].GetValue<string>()) throw new InvalidOperationException("Backup differs: "+name);
    if(Hash(destination)==file["sha256"].GetValue<string>()) continue;
    var incoming=System.IO.Path.Combine(incomingDirectory,name);
    if(!System.IO.File.Exists(incoming)) System.IO.File.Copy(System.IO.Path.Combine(stage,name),incoming);
    if(Hash(incoming)!=file["sha256"].GetValue<string>()) throw new InvalidOperationException("Incoming source differs: "+name);
    // Atomic publication; an external Git scan can briefly deny replacement.
    // Preserve the checked incoming file and inspect state before resuming.
    try { System.IO.File.Move(incoming,destination,true); }
    catch(Exception error) { throw new System.IO.IOException("Could not publish "+name+"; inspect its source and destination hashes before resuming.",error); }
    if(Hash(destination)!=file["sha256"].GetValue<string>()) throw new InvalidOperationException("Published source differs: "+name);
}
foreach(var side in new[]{"west","east"})
    Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(root,"Assets/models/maps/belltower/belltower_"+side+".vmdl"));
var result=new {Imported=files.Count,ManifestSha256=Hash(manifestPath),GameplaySpots=94,CollisionDefinitionsReplaced=false,
    GamePreserved=Game.ActiveScene?.Id==game && Game.IsPlaying==playing,Playing=playing,RuntimePath=runtimePath,
    SelectedDocumentPreserved=ReferenceEquals(active,Editor.SceneEditorSession.Active)};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-import-result.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
public static class BelltowerScript5
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/verify-gardens.cs.txt"
var root=Sandbox.Project.Current.GetRootPath();
var request=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/garden-import-request.json")));
var revision=request["revision"].GetValue<string>();
if(revision!="garden-v1" && revision!="garden-v2" && revision!="garden-v3") throw new InvalidOperationException("Unknown garden revision.");
var stage=System.IO.Path.Combine(root,"output/belltower/quality/models",revision);
var manifestPath=System.IO.Path.Combine(stage,"native-import.json");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(manifestPath));
string Hash(string path)
{
    using var stream=System.IO.File.OpenRead(path);
    return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).ToLowerInvariant();
}
foreach(var file in manifest["files"].AsArray())
    if(Hash(System.IO.Path.Combine(root,"Assets",file["path"].GetValue<string>()))!=file["sha256"].GetValue<string>())
        throw new InvalidOperationException("Installed garden source differs from the checked candidate.");
foreach(var dependency in manifest["collision_inputs"].AsArray())
    if(Hash(System.IO.Path.Combine(root,dependency["path"].GetValue<string>()))!=dependency["sha256"].GetValue<string>())
        throw new InvalidOperationException("Collision source changed during import.");
var loaded=new System.Collections.Generic.List<object>();
foreach(var record in manifest["models"].AsArray())
{
    var name=record["name"].GetValue<string>();
    var resource="models/maps/belltower/"+name+".vmdl";
    var source=System.IO.Path.Combine(root,"Assets",resource);
    var compiled=source+"_c";
    var newestSource=new[]{source,System.IO.Path.ChangeExtension(source,".obj"),System.IO.Path.ChangeExtension(source,".mtl")}
        .Max(path=>System.IO.File.GetLastWriteTimeUtc(path));
    if(!System.IO.File.Exists(compiled) || System.IO.File.GetLastWriteTimeUtc(compiled)<newestSource)
        throw new InvalidOperationException("Model has not compiled since the garden import: "+name);
    var model=Model.Load(resource);
    if(model is null || model.IsError || model.Materials.Any(m=>m is null || m.IsError))
        throw new InvalidOperationException("Model or material did not load: "+name);
    if(!model.Materials.Any(m=>m.ResourcePath==record["new_material"].GetValue<string>()))
        throw new InvalidOperationException("Loaded model is missing the new firewood material: "+name);
    var nativeFirstMaterialTriangles=model.GetIndexCountForLod(0)/3;
    if(model.Materials[0].ResourcePath!=record["first_material"].GetValue<string>()
        || nativeFirstMaterialTriangles!=record["first_material_triangles"].GetValue<int>())
        throw new InvalidOperationException("Loaded first-material geometry differs: "+name);
    loaded.Add(new{Model=resource,AuthoredTriangles=record["triangles"].GetValue<int>(),NativeFirstMaterialTriangles=nativeFirstMaterialTriangles,
        NativeTotalTrianglesVerified=false,model.MeshCount,Materials=model.Materials.Length,NewMaterialLoaded=true});
}
var result=new {ManifestSha256=Hash(manifestPath),Models=loaded.ToArray()};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-resources.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
public static class BelltowerScript6
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Belltower/editor/import-farfield-v3.cs.txt"
// Add only isolated Belltower far-field trial resources. Original landscape,
// forest materials, collision and any running game stay untouched.
var root=Sandbox.Project.Current.GetRootPath();
var stage=System.IO.Path.Combine(root,"output/belltower/quality/farfield-v3");
var assets=System.IO.Path.Combine(root,"Assets");
var manifestPath=System.IO.Path.Combine(stage,"manifest.json");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(manifestPath));
if(manifest["revision"].GetValue<string>()!="farfield-v3")
    throw new InvalidOperationException("Unexpected farfield trial revision");
string Hash(string path)
{
    using var source=System.IO.File.OpenRead(path);
    return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(source)).ToLowerInvariant();
}
foreach(var item in manifest["accepted_inputs"].AsObject())
    if(Hash(System.IO.Path.Combine(root,item.Key))!=item.Value.GetValue<string>())
        throw new InvalidOperationException("Accepted farfield dependency changed: "+item.Key);
var expectedNames=new System.Collections.Generic.HashSet<string>{"vista_c_color.jpg","vista_d_color.jpg","vista_land.vmat","forest_trees.vmat"};
var seen=new System.Collections.Generic.HashSet<string>();
var files=manifest["resources"].AsArray();
if(files.Count!=4) throw new InvalidOperationException("Expected four separate terrain trial resources");
foreach(var item in files)
{
    var relative=item["path"].GetValue<string>();
    var name=System.IO.Path.GetFileName(relative);
    if(!expectedNames.Contains(name) || !seen.Add(name)
        || relative!="materials/belltower/vista/farfield-v3/"+name
        || item["source"].GetValue<string>()!="output/belltower/quality/farfield-v3/"+name)
        throw new InvalidOperationException("Unexpected terrain candidate asset: "+relative);
    var source=System.IO.Path.Combine(stage,name);
    var destination=System.IO.Path.Combine(assets,relative);
    if(Hash(source)!=item["sha256"].GetValue<string>()
        || System.IO.File.Exists(destination) && Hash(destination)!=item["sha256"].GetValue<string>())
        throw new InvalidOperationException("Terrain candidate source or destination differs: "+name);
}
var gameId=Game.ActiveScene?.Id;
var playing=Game.IsPlaying;
var selected=Editor.SceneEditorSession.Active;
var imported=0;
foreach(var item in files)
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative=item["path"].GetValue<string>();
    var name=System.IO.Path.GetFileName(relative);
    var destination=System.IO.Path.Combine(assets,relative);
    if(System.IO.File.Exists(destination)) continue;
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
    System.IO.File.Copy(System.IO.Path.Combine(stage,name),destination);
    if(Hash(destination)!=item["sha256"].GetValue<string>())
        throw new InvalidOperationException("Imported terrain resource hash differs: "+name);
    Editor.AssetSystem.RegisterFile(destination);
    imported++;
}
foreach(var filename in new[]{"vista_land.vmat","forest_trees.vmat"})
    Editor.AssetSystem.RegisterFile(System.IO.Path.Combine(assets,"materials/belltower/vista/farfield-v3",filename));
var result=new {Imported=imported,ManifestSha256=Hash(manifestPath),AcceptedAssetsReplaced=false,
    GamePreserved=Game.ActiveScene?.Id==gameId && Game.IsPlaying==playing,
    SelectedDocumentPreserved=ReferenceEquals(selected,Editor.SceneEditorSession.Active)};
System.IO.File.WriteAllText(System.IO.Path.Combine(stage,"native-import-result.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
