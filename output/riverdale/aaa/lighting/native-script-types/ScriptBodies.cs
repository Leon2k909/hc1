using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Sandbox;
using static Sandbox.Internal.GlobalGameNamespace;
using static Sandbox.Internal.GlobalToolsNamespace;
public static class RiverdaleScript0
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Riverdale/editor/prepare-lighting.cs.txt"
// Riverdale: puts the lighting plan of Sources/Riverdale/lighting/config.json into the open, saved Riverdale editor
// document and saves it. Run with the native MCP's run_csharp before bake-lighting.cs.txt. Safe to run again: it only
// adds what's missing and refuses when something differs from the plan.
// - Indirect light: an "Indirect Light" group with one IndirectLightVolume per configured volume (bounds in world space,
//   probe density, biases, blend distance, runtime strength). A volume that already exists must match the plan's
//   bounds and density, so a bake is never silently resized.
// - Reflections: every probe under "Reflection Probes" becomes static (CustomTexture). Realtime probes run the
//   engine's envmap filtering at load, which faulted envmap_filtering_cs on this workstation. Until
//   capture-reflections.cs.txt and apply-reflections.cs.txt give a probe its own cube, it shows a copy of the sky's
//   compiled cube (lighting/riverdale/<revision>/sky_fallback_<hash>.vtex), dimmed indoors by its fallback tint. Each
//   probe moves to its capture position with its world box kept; probes the plan no longer has (the old single
//   "Probe Yard") are removed.
// It never bakes, never captures and never runs envmap filtering.
if(Game.IsPlaying) throw new InvalidOperationException("Stop play before preparing Riverdale lighting.");
var root = Sandbox.Project.Current.GetRootPath();
var config = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Sources/Riverdale/lighting/config.json")));
var revision = config["revision"].GetValue<string>();
if(!System.Text.RegularExpressions.Regex.IsMatch(revision,"^daylight-v[0-9]+$")) throw new InvalidOperationException("Invalid lighting revision.");
var session = Editor.SceneEditorSession.Active;
if(session?.Scene?.Source?.ResourcePath?.Equals("scenes/maps/riverdale/riverdale.scene",StringComparison.OrdinalIgnoreCase)!=true)
    throw new InvalidOperationException("Riverdale must own the editor window.");
if(session.HasUnsavedChanges) throw new InvalidOperationException("Riverdale has unsaved edits; inspect them before preparing its lighting.");
var scene = session.Scene;
var beforeGameId = Game.ActiveScene?.Id;
var resourceDirectory = "lighting/riverdale/"+revision;
var nativeDirectory = System.IO.Path.Combine(root,"Assets",resourceDirectory);
string Hash(byte[] data) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(data)).ToLowerInvariant();

// The sky's compiled cube, copied under a name taken from its content, so a running editor never shows a cached older
// cube under the same name (Orion's lesson).
var skyCubes = new System.IO.DirectoryInfo(System.IO.Path.Combine(root,"Assets/materials/riverdale/sky"))
    .GetFiles("riverdale_sky_exr_*.generated.vtex_c").OrderBy(f => f.LastWriteTimeUtc).ToArray();
if(skyCubes.Length==0) throw new InvalidOperationException("Compile materials/riverdale/sky/riverdale_sky.vmat first: its cube is the probes' fallback.");
var skyBytes = System.IO.File.ReadAllBytes(skyCubes[^1].FullName);
var fallbackPath = $"{resourceDirectory}/sky_fallback_{Hash(skyBytes)[..8]}.vtex";
var fallbackFile = System.IO.Path.Combine(root,"Assets",fallbackPath+"_c");
if(!System.IO.File.Exists(fallbackFile))
{
    System.IO.Directory.CreateDirectory(nativeDirectory);
    System.IO.File.WriteAllBytes(fallbackFile+".riverdale-pending",skyBytes);
    System.IO.File.Move(fallbackFile+".riverdale-pending",fallbackFile,false);
}
var fallback = Texture.Load(fallbackPath,false);
if(fallback is null || fallback.IsError) throw new InvalidOperationException("The fallback sky cube did not load: "+fallbackPath);

GameObject Group(string name)
{
    var found = scene.Children.Where(g => g.Name==name).ToArray();
    if(found.Length>1) throw new InvalidOperationException("More than one group named "+name);
    if(found.Length==1) return found[0];
    return new GameObject(scene){ Name=name };
}
void SetEnum(object target,string property,string value)
{
    var info = target.GetType().GetProperty(property) ?? throw new MissingMemberException(target.GetType().Name+"."+property);
    info.SetValue(target,Enum.Parse(info.PropertyType,value));
}
var report = new System.Collections.Generic.List<object>();
var changed = false;
using(scene.Push())
{
    // Indirect light.
    var indirectRoot = Group("Indirect Light");
    var entries = config["volumes"].AsArray().Select(n => n.AsObject()).ToArray();
    var names = entries.Select(e => e["name"].GetValue<string>()).ToHashSet();
    var strays = scene.GetAllComponents<IndirectLightVolume>().Where(v => !names.Contains(v.GameObject.Name)).ToArray();
    if(strays.Length>0) throw new InvalidOperationException("Unplanned indirect-light volume: "+strays[0].GameObject.Name+"; inspect it first.");
    foreach(var entry in entries)
    {
        var name = entry["name"].GetValue<string>();
        var bounds = new BBox(Vector3.Parse(entry["bounds_min"].GetValue<string>()),Vector3.Parse(entry["bounds_max"].GetValue<string>()));
        var volume = scene.GetAllComponents<IndirectLightVolume>().SingleOrDefault(v => v.GameObject.Name==name);
        var created = volume is null;
        if(created)
        {
            var holder = new GameObject(indirectRoot){ Name=name };
            holder.NetworkMode = NetworkMode.Snapshot;
            holder.WorldPosition = Vector3.Zero;
            holder.WorldRotation = Rotation.Identity;
            volume = holder.Components.Create<IndirectLightVolume>();
            volume.Bounds = bounds;
            volume.ProbeDensity = entry["probe_density"].GetValue<int>();
            SetEnum(volume,"InsideGeometry","Relocate");
            changed = true;
        }
        else if((volume.Bounds.Mins-bounds.Mins).Length>0.5f || (volume.Bounds.Maxs-bounds.Maxs).Length>0.5f
                || volume.ProbeDensity!=entry["probe_density"].GetValue<int>() || volume.WorldPosition.Length>0.5f)
            throw new InvalidOperationException($"{name} differs from the plan; inspect it (and its bake) before changing either.");
        // Shading-time settings: none of them is captured by a bake, so they're always taken from the plan.
        volume.NormalBias = entry["normal_bias"].GetValue<float>();
        volume.ViewBias = entry["view_bias"].GetValue<float>();
        volume.BlendDistance = entry["blend_distance"].GetValue<float>();
        volume.RuntimeIntensity = entry["runtime_intensity"].GetValue<float>();
        volume.RuntimeContrast = entry["runtime_contrast"].GetValue<float>();
        volume.RuntimeSaturation = entry["runtime_saturation"].GetValue<float>();
        if(volume.ProbeCounts.ToString()!=entry["expected_counts"].GetValue<string>())
            throw new InvalidOperationException($"{name}: the engine makes a {volume.ProbeCounts} grid, the plan {entry["expected_counts"]}.");
        report.Add(new { Volume=name, Created=created, Grid=volume.ProbeCounts.ToString(), Baked=volume.BakeVersion==1 && volume.IrradianceTexture is not null });
    }

    // Reflections.
    var probeRoot = Group("Reflection Probes");
    var planned = config["reflections"].AsArray().Select(n => n.AsObject()).ToArray();
    var plannedNames = planned.Select(p => p["name"].GetValue<string>()).ToHashSet();
    // Destroy is deferred until the next scene tick. Exclude exactly these retired probes from the
    // final mode check; otherwise the first preparation aborts with "Probe Yard" still enumerated.
    var removedProbes = new System.Collections.Generic.HashSet<EnvmapProbe>();
    foreach(var stale in probeRoot.Children.Where(g => g.Components.Get<EnvmapProbe>() is not null && !plannedNames.Contains(g.Name)).ToArray())
    {
        removedProbes.Add(stale.Components.Get<EnvmapProbe>());
        report.Add(new { Removed=stale.Name });
        stale.Destroy();
        changed = true;
    }
    foreach(var entry in planned)
    {
        var name = entry["name"].GetValue<string>();
        var holder = probeRoot.Children.SingleOrDefault(g => g.Name==name);
        var created = holder is null;
        if(created) { holder = new GameObject(probeRoot){ Name=name }; holder.NetworkMode = NetworkMode.Snapshot; changed = true; }
        var probe = holder.Components.Get<EnvmapProbe>() ?? holder.Components.Create<EnvmapProbe>();
        var capture = Vector3.Parse(entry["capture_world"].GetValue<string>());
        var box = new BBox(Vector3.Parse(entry["bounds_min"].GetValue<string>()),Vector3.Parse(entry["bounds_max"].GetValue<string>()));
        var captured = probe.Texture?.ResourcePath?.StartsWith(resourceDirectory+"/reflection_",StringComparison.OrdinalIgnoreCase)==true;
        if(!captured)
        {
            // The world box stays where the plan puts it; only the cube's origin moves to where it'll be captured.
            holder.WorldPosition = capture;
            holder.WorldRotation = Rotation.Identity;
            probe.Bounds = new BBox(box.Mins-capture,box.Maxs-capture);
            probe.Priority = entry["priority"].GetValue<int>();
            probe.Feathering = entry["feathering"].GetValue<float>();
            SetEnum(probe,"Projection","Box");
            probe.Texture = fallback;
            var tint = entry["fallback_tint"].GetValue<float>();
            probe.TintColor = new Color(tint,tint,tint,1);
            SetEnum(probe,"Mode","CustomTexture");
            changed = true;
        }
        else if(probe.Mode.ToString()!="CustomTexture")
        {
            SetEnum(probe,"Mode","CustomTexture");
            changed = true;
        }
        report.Add(new { Probe=name, Created=created, Captured=captured, Texture=probe.Texture?.ResourcePath, Mode=probe.Mode.ToString() });
    }
    var realtime = scene.GetAllComponents<EnvmapProbe>().Where(p => p.Mode.ToString()!="CustomTexture" && !removedProbes.Contains(p))
        .Select(p => p.GameObject.Name).ToArray();
    if(realtime.Length>0) throw new InvalidOperationException("Probes outside Reflection Probes are still not static: "+string.Join(", ",realtime));
}
if(changed)
{
    typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);
    session.Save(false);
    if(session.HasUnsavedChanges) throw new InvalidOperationException("Riverdale was not saved.");
}
var output = System.IO.Path.Combine(root,"output/riverdale/lighting",revision);
System.IO.Directory.CreateDirectory(output);
var result = new { Revision=revision, Changed=changed, Saved=changed, Fallback=fallbackPath, Items=report, GamePreserved=!Game.IsPlaying && Game.ActiveScene?.Id==beforeGameId };
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"prepared.json"),System.Text.Json.JsonSerializer.Serialize(result));
return result;

#line default
}
}
public static class RiverdaleScript1
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Riverdale/editor/bake-lighting.cs.txt"
// Riverdale: bakes the next unbaked indirect-light (DDGI) volume of Sources/Riverdale/lighting/config.json's revision
// into the open, saved Riverdale editor document, saves its textures to Assets/lighting/riverdale/<revision>/ and saves
// the scene. Run with the native MCP's run_csharp once per volume, in the config's order (the yard, the hall, the pool),
// until it returns AllBaked = true. Each later volume sees the earlier ones' light. Results go to
// output/riverdale/lighting/<revision>/<volume>-<utc>/; Sources/Riverdale/lighting/riverdale_lighting.py preserve keeps
// them for scene regeneration.
// Mirrors Collider's and Cerro Blanco's accepted bakes:
// - Bake into the persistent editor scene. Never create or destroy an isolated world.
// - Relocation stays serial, on the main thread: engine 26.10.13's parallel ComputeProbeRelocation can race
//   ResourceSystem.RegisterWeak and break rendering in the whole process. Never call it.
// - The native cubemapper owns both lighting passes. It replaces GeneratedIrradianceTexture for its second pass, so the
//   texture is fetched again after RunAsync before it's saved.
// - Scene.Push changes the process-wide Game.ActiveScene: no Push scope is held across an await.
// - Reflections are left alone: the GPU Quality GGX bake faulted envmap_filtering_cs on this workstation.
// - It refuses to start during play, and cancels (adopting nothing) if play starts or the document changes meanwhile.
if(Game.IsPlaying) throw new InvalidOperationException("Stop play before baking Riverdale lighting.");
var root = Sandbox.Project.Current.GetRootPath();
var config = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Sources/Riverdale/lighting/config.json")));
var revision = config["revision"].GetValue<string>();
if(!System.Text.RegularExpressions.Regex.IsMatch(revision,"^daylight-v[0-9]+$")) throw new InvalidOperationException("Invalid lighting revision.");
var resourceDirectory = "lighting/riverdale/"+revision;
var nativeDirectory = System.IO.Path.Combine(root,"Assets",resourceDirectory);
var session = Editor.SceneEditorSession.All.SingleOrDefault(s => s.Scene.IsEditor && s.Scene.Source?.ResourcePath?.Equals("scenes/maps/riverdale/riverdale.scene",StringComparison.OrdinalIgnoreCase)==true)
    ?? throw new InvalidOperationException("Open Riverdale in the editor first.");
if(Editor.SceneEditorSession.Active!=session) throw new InvalidOperationException("Riverdale must own the editor window.");
if(session.HasUnsavedChanges) throw new InvalidOperationException("Riverdale has unsaved edits; inspect them before baking.");
var scene = session.Scene;

// Every configured volume must be in the scene as configured (prepare-lighting.cs.txt or the generator puts them there),
// and nothing else: an unplanned volume would change what the others capture.
var entries = config["volumes"].AsArray().Select(n => n.AsObject()).ToArray();
var volumes = scene.GetAllComponents<IndirectLightVolume>().ToArray();
if(volumes.Length != entries.Length) throw new InvalidOperationException($"Expected {entries.Length} indirect-light volumes, found {volumes.Length}; run prepare-lighting.cs.txt.");
var planned = new System.Collections.Generic.List<(string Key, IndirectLightVolume Volume, System.Text.Json.Nodes.JsonObject Entry)>();
foreach(var entry in entries)
{
    var key = entry["key"].GetValue<string>();
    if(!System.Text.RegularExpressions.Regex.IsMatch(key,"^[a-z][a-z0-9]*$")) throw new InvalidOperationException("Invalid volume key.");
    var name = entry["name"].GetValue<string>();
    var volume = volumes.SingleOrDefault(v => v.GameObject.Name==name) ?? throw new InvalidOperationException("Missing volume: "+name);
    var bounds = new BBox(Vector3.Parse(entry["bounds_min"].GetValue<string>()),Vector3.Parse(entry["bounds_max"].GetValue<string>()));
    if((volume.Bounds.Mins-bounds.Mins).Length>0.5f || (volume.Bounds.Maxs-bounds.Maxs).Length>0.5f || volume.WorldPosition.Length>0.5f
        || volume.WorldRotation!=Rotation.Identity || (volume.WorldScale-Vector3.One).Length>0.001f)
        throw new InvalidOperationException("Volume moved or resized since the plan: "+name);
    if(volume.ProbeDensity != entry["probe_density"].GetValue<int>() || volume.ProbeCounts.ToString() != entry["expected_counts"].GetValue<string>())
        throw new InvalidOperationException($"Unexpected probe grid for {name}: {volume.ProbeCounts}");
    if(volume.InsideGeometry.ToString()!="Relocate") throw new InvalidOperationException("Inside-geometry probes must relocate: "+name);
    planned.Add((key,volume,entry));
}
string TexturePath(string key,string kind) => $"{resourceDirectory}/{key}_{kind}.vtex";
bool IsBaked((string Key, IndirectLightVolume Volume, System.Text.Json.Nodes.JsonObject Entry) p) =>
    p.Volume.BakeVersion==1 && p.Volume.IrradianceTexture?.ResourcePath==TexturePath(p.Key,"irradiance")
    && p.Volume.DistanceTexture?.ResourcePath==TexturePath(p.Key,"distance") && p.Volume.RelocationTexture?.ResourcePath==TexturePath(p.Key,"relocation");
var next = planned.FirstOrDefault(p => !IsBaked(p));
if(next.Volume is null) return new { AllBaked=true, Revision=revision, Volumes=planned.Select(p => new { p.Key, Grid=p.Volume.ProbeCounts.ToString() }).ToArray() };
var bakeKey = next.Key;
var indirect = next.Volume;
foreach(var kind in new[]{"irradiance","distance","relocation"})
    if(System.IO.File.Exists(System.IO.Path.Combine(nativeDirectory,$"{bakeKey}_{kind}.vtex_c")))
        throw new InvalidOperationException($"{bakeKey} already has {kind} output in {resourceDirectory}; inspect it instead of overwriting it, or start a new revision.");
var reflections = scene.GetAllComponents<EnvmapProbe>().ToArray();
if(reflections.Any(p => p.Mode.ToString()!="CustomTexture"))
    throw new InvalidOperationException("Every reflection probe must be static (CustomTexture) before a bake: realtime probes run envmap filtering.");

var beforeGameId = Game.ActiveScene?.Id;
var beforePlaying = Game.IsPlaying;
// Another tab being selected meanwhile doesn't change this scene (the updater renders its own world), so only play, the
// game scene and edits to this document stop the bake, as in Collider's.
bool ContextUnchanged() => Game.ActiveScene?.Id==beforeGameId && Game.IsPlaying==beforePlaying && !session.HasUnsavedChanges;
void RequireContext()
{
    if(!ContextUnchanged()) throw new InvalidOperationException("Editor or game state changed during the bake; its result must not be adopted.");
}
string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var scenePath = System.IO.Path.Combine(root,"Assets/scenes/maps/Riverdale/riverdale.scene");
var inputs = System.IO.Directory.EnumerateFiles(System.IO.Path.Combine(root,"Assets/models/maps/riverdale"))
    .Concat(System.IO.Directory.EnumerateFiles(System.IO.Path.Combine(root,"Assets/materials/riverdale")))
    .Concat(System.IO.Directory.EnumerateFiles(System.IO.Path.Combine(root,"Assets/materials/riverdale/sky")))
    .Where(p => !p.EndsWith("_c") && !p.EndsWith(".meta") && !p.Contains(".riverdale-"))
    .Append(scenePath)
    .ToDictionary(p => p, p => Hash(p));
var attempt = DateTime.UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'");
var destination = System.IO.Path.Combine(root,"output/riverdale/lighting",revision,bakeKey+"-"+attempt);
System.IO.Directory.CreateDirectory(destination);
System.IO.Directory.CreateDirectory(nativeDirectory);
System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"input-assets.json"),System.Text.Json.JsonSerializer.Serialize(
    inputs.ToDictionary(p => System.IO.Path.GetRelativePath(root,p.Key).Replace('\\','/'), p => p.Value)));
System.IO.File.Copy(scenePath,System.IO.Path.Combine(destination,"visual-scene.json"),false);
void Status(string value) => System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"bake-status.txt"),value);

var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var type = typeof(IndirectLightVolume);
var probesProperty = type.GetProperty("Probes",flags) ?? throw new MissingMemberException("IndirectLightVolume.Probes");
var generatedProperty = type.GetProperty("GeneratedRelocationTexture",flags) ?? throw new MissingMemberException("IndirectLightVolume.GeneratedRelocationTexture");
var previewField = type.GetField("_bakePreview",flags) ?? throw new MissingMemberException("IndirectLightVolume._bakePreview");
var dirty = type.GetMethod("MarkDirty",flags) ?? throw new MissingMemberException("IndirectLightVolume.MarkDirty");
var originalProbes = probesProperty.GetValue(indirect);
var originalGenerated = (Texture)generatedProperty.GetValue(indirect);
var originalTextures = (indirect.IrradianceTexture,indirect.DistanceTexture,indirect.RelocationTexture,indirect.BakeVersion);
using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
timeout.CancelAfter(TimeSpan.FromSeconds(next.Entry["timeout_seconds"]?.GetValue<int>() ?? config["timeout_seconds"]?.GetValue<int>() ?? 900));
var token = timeout.Token;
object updater = null;
Texture relocation = null;
bool completed = false;
bool appliedTextures = false;
var started = DateTime.UtcNow;
try
{
    var counts = indirect.ProbeCounts;
    var spacing = (Vector3)type.GetMethod("ComputeSpacing",flags).Invoke(indirect,new object[]{counts}) * indirect.WorldScale.Abs();
    var directions = (Vector3[])type.GetMethod("GenerateSphericalDirections",flags | System.Reflection.BindingFlags.Static).Invoke(null,new object[]{128});
    var trace = type.GetMethod("TraceProbeRays",flags);
    var relocate = type.GetMethod("ComputeRelocationOffset",flags);
    var position = type.GetMethod("GetProbeWorldPosition",flags);
    var ratio = trace.ReturnType.GetProperty("BackfaceRatio",flags);
    var minSpacing = MathF.Min(spacing.x,MathF.Min(spacing.y,spacing.z));
    var probes = new IndirectLightVolume.Probe[counts.x*counts.y*counts.z];
    for(var index=0;index<probes.Length;index++) probes[index] = new IndirectLightVolume.Probe();
    probesProperty.SetValue(indirect,probes);
    for(var z=0;z<counts.z;z++)
    for(var y=0;y<counts.y;y++)
    {
        token.ThrowIfCancellationRequested();
        RequireContext();
        if(!ThreadSafe.IsMainThread) throw new InvalidOperationException("Relocation left the main thread.");
        using(scene.Push())
        for(var x=0;x<counts.x;x++)
        {
            var world = (Vector3)position.Invoke(indirect,new object[]{new Vector3Int(x,y,z)});
            var offset = Vector3.Zero;
            var active = true;
            for(var iteration=0;iteration<12 && active;iteration++)
            {
                var hit = trace.Invoke(indirect,new object[]{world+offset,spacing.Length,directions});
                var move = ((Vector3,bool))relocate.Invoke(indirect,new object[]{offset,hit,spacing,minSpacing,minSpacing*.2f,directions});
                if(move.Item2) { active=false; break; }
                offset = move.Item1;
            }
            if(active && indirect.InsideGeometry.ToString()=="Relocate")
                active = (float)ratio.GetValue(trace.Invoke(indirect,new object[]{world+offset,spacing.Length,directions})) < .25f;
            probes[x+y*counts.x+z*counts.x*counts.y] = new IndirectLightVolume.Probe { Offset=offset, Active=active };
        }
        Status($"{bakeKey}: relocating on the main thread, row {z*counts.y+y+1}/{counts.z*counts.y}");
        await Task.Yield();
    }
    using(scene.Push())
    {
        type.GetMethod("UpdateRelocationTexture",flags).Invoke(indirect,null);
        dirty.Invoke(indirect,null);
    }
    relocation = (Texture)generatedProperty.GetValue(indirect);
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"relocation-status.json"),System.Text.Json.JsonSerializer.Serialize(
        new { Volume=bakeKey, Mode="Main thread; native trace and relocation functions", Grid=counts.ToString(), Active=probes.Count(p => p.Active), Total=probes.Length,
              Seconds=(DateTime.UtcNow-started).TotalSeconds }));
    var updaterType = type.Assembly.GetType("Sandbox.DDGIProbeUpdaterCubemapper") ?? throw new MissingMemberException("Sandbox.DDGIProbeUpdaterCubemapper");
    using(scene.Push()) updater = Activator.CreateInstance(updaterType,new object[]{indirect});
    var irradiance = (Texture)updaterType.GetProperty("GeneratedIrradianceTexture").GetValue(updater);
    var distance = (Texture)updaterType.GetProperty("GeneratedDistanceTexture").GetValue(updater);
    previewField.SetValue(indirect,(irradiance,distance,relocation));
    dirty.Invoke(indirect,null);
    var passField = updaterType.GetField("_pass",flags);
    var indexField = updaterType.GetField("_renderedIndex",flags);
    // The updater keeps its own world: only starting it needs the scene pushed, never the awaits after.
    Task<bool> task;
    using(scene.Push()) task = (Task<bool>)updaterType.GetMethod("RunAsync").Invoke(updater,new object[]{token});
    while(!task.IsCompleted)
    {
        await Task.WhenAny(task,Task.Delay(1000));
        // Cancel, then let the updater drain before its GPU textures are disposed. A timed-out observation or a changed
        // scene is never a reason to start it again.
        if(!ContextUnchanged()) timeout.Cancel();
        if(!task.IsCompleted) Status($"{bakeKey}: baking pass {(int)passField.GetValue(updater)+1}/2, probe {indexField.GetValue(updater)}, grid {counts}");
    }
    if(!await task) throw new InvalidOperationException("The native lighting bake did not complete.");
    RequireContext();
    if(inputs.Any(p => !System.IO.File.Exists(p.Key) || Hash(p.Key)!=p.Value))
        throw new InvalidOperationException("Riverdale's source assets changed during the bake; its result must not be adopted.");
    var firstPass = irradiance;
    irradiance = (Texture)updaterType.GetProperty("GeneratedIrradianceTexture").GetValue(updater);
    distance = (Texture)updaterType.GetProperty("GeneratedDistanceTexture").GetValue(updater);
    token.ThrowIfCancellationRequested();
    Graphics.FlushGPU();
    Texture Save(Texture texture,string kind,ImageFormat? format=null)
    {
        if(texture is null || texture.IsError) throw new InvalidOperationException("Invalid capture: "+kind);
        var target = System.IO.Path.Combine(nativeDirectory,$"{bakeKey}_{kind}.vtex_c");
        var pending = target+".riverdale-pending";
        // Written whole, then moved into place: the file watcher never sees half a texture.
        System.IO.File.WriteAllBytes(pending,texture.SaveToVtex(format));
        System.IO.File.Move(pending,target,false);
        var saved = Texture.Load(TexturePath(bakeKey,kind),false);
        if(saved is null || saved.IsError) throw new InvalidOperationException("Could not reload capture: "+kind);
        return saved;
    }
    appliedTextures = true;
    indirect.IrradianceTexture = Save(irradiance,"irradiance");
    indirect.DistanceTexture = Save(distance,"distance",(ImageFormat)85);
    indirect.RelocationTexture = Save(relocation,"relocation",(ImageFormat)24);
    indirect.BakeVersion = 1;
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"indirect-result.json"),System.Text.Json.JsonSerializer.Serialize(
        new { Volume=bakeKey, Passes=2, SavedFinalIrradiance=true, IrradianceReplacedAfterFirstPass=!ReferenceEquals(firstPass,irradiance), Grid=counts.ToString() }));
    previewField.SetValue(indirect,null);
    dirty.Invoke(indirect,null);
    using(scene.Push())
    {
        var systemType = typeof(Scene).Assembly.GetType("Sandbox.DDGIVolumeSystem");
        var getter = typeof(Scene).GetMethods().Single(m => m.Name=="GetSystem" && m.IsGenericMethodDefinition && m.GetParameters().Length==0);
        var system = getter.MakeGenericMethod(systemType).Invoke(scene,null);
        systemType.GetMethod("MarkDirty",flags).Invoke(system,null);
        systemType.GetMethod("UpdateVolumes",flags).Invoke(system,null);
    }
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"indirect-light.json"),indirect.GameObject.Serialize().ToJsonString());
    typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);
    session.Save(false);
    if(session.HasUnsavedChanges) throw new InvalidOperationException("Riverdale's lighting was not saved.");
    var remaining = planned.Where(p => !IsBaked(p)).Select(p => p.Key).ToArray();
    var result = new { Volume=bakeKey, Revision=revision, Passes=2, SavedFinalIrradiance=true, IrradianceReplacedAfterFirstPass=!ReferenceEquals(firstPass,irradiance),
        Grid=counts.ToString(), ActiveProbes=probes.Count(p => p.Active), TotalProbes=probes.Length, Seconds=(DateTime.UtcNow-started).TotalSeconds,
        PersistentEditorScene=true, SceneId=scene.Id, SavedScene=true, InputAssetsUnchanged=true,
        Textures=new[]{TexturePath(bakeKey,"irradiance"),TexturePath(bakeKey,"distance"),TexturePath(bakeKey,"relocation")},
        StaticReflections=reflections.Length, Remaining=remaining, AllBaked=remaining.Length==0,
        GamePreserved=Game.ActiveScene?.Id==beforeGameId && Game.IsPlaying==beforePlaying };
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"bake-result.json"),System.Text.Json.JsonSerializer.Serialize(result));
    completed = true;
    Status("Complete "+counts);
    return result;
}
catch(Exception error)
{
    Status("Failed: "+error);
    throw;
}
finally
{
    previewField.SetValue(indirect,null);
    if(!completed)
    {
        if(appliedTextures)
        {
            indirect.IrradianceTexture=originalTextures.Item1;
            indirect.DistanceTexture=originalTextures.Item2;
            indirect.RelocationTexture=originalTextures.Item3;
            indirect.BakeVersion=originalTextures.Item4;
        }
        probesProperty.SetValue(indirect,originalProbes);
    }
    (updater as IDisposable)?.Dispose();
    if(relocation is not null && !ReferenceEquals(relocation,originalGenerated)) relocation.Dispose();
    generatedProperty.SetValue(indirect,originalGenerated);
    dirty.Invoke(indirect,null);
}

#line default
}
}
public static class RiverdaleScript2
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Riverdale/editor/capture-reflections.cs.txt"
// Riverdale: captures the six faces of each planned reflection probe (Sources/Riverdale/lighting/config.json's
// "reflections") as ordinary camera views of the open Riverdale document, to
// output/riverdale/lighting/reflections/<revision>/<key>/face-0..5.png with faces.json. Run with the native MCP's
// run_csharp after the indirect light is baked (so the cubes hold the bounced light). A probe whose faces.json exists is
// skipped: delete its folder to capture it again. Sources/Riverdale/lighting/riverdale_reflections.py turns the faces
// into linear panoramas, and import-reflections.cs.txt and apply-reflections.cs.txt give them to the probes.
// Cerro Blanco's accepted method:
// - Ordinary camera faces, never EnvmapProbe.Bake, RenderCubemap or CubemapRendering.Filter: those run the GPU GGX
//   filter that faulted envmap_filtering_cs on this workstation's driver.
// - ACES at a fixed exposure (the probe's "exposure", 1 outdoors, more indoors so dark rooms keep their levels in 8 bits);
//   the converter inverts the curve and calibrates against the sky. The bitmap path rejects float readback.
// - Colour grading, vignette, bloom, screen-space AO and SSR are off while it captures: they're display effects or
//   differ from face to face, and would leave seams. The haze stays: it's part of the room.
// - The viewport overwrites the editor camera between frames, so the whole view is set again right before each render.
// - Scene.Push is never held across an await. Everything it changes is put back.
if(Game.IsPlaying) throw new InvalidOperationException("Stop play before capturing reflections.");
var session = Editor.SceneEditorSession.Active;
var scene = session?.Scene;
if(scene?.Source?.ResourcePath?.Equals("scenes/maps/riverdale/riverdale.scene",StringComparison.OrdinalIgnoreCase)!=true)
    throw new InvalidOperationException("Riverdale must own the editor window.");
var root = Sandbox.Project.Current.GetRootPath();
var config = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Sources/Riverdale/lighting/config.json")));
var revision = config["revision"].GetValue<string>();
if(!System.Text.RegularExpressions.Regex.IsMatch(revision,"^daylight-v[0-9]+$")) throw new InvalidOperationException("Invalid lighting revision.");
var size = config["reflection_capture_size"]?.GetValue<int>() ?? 512;
if(size!=512 && size!=256) throw new InvalidOperationException("Capture faces at 512 or 256.");
var beforeGameId = Game.ActiveScene?.Id;
var beforeDirty = session.HasUnsavedChanges;
var camera = scene.GetAllComponents<CameraComponent>().Single(c => c.GameObject.Name=="editor_camera" && c.GameObject.Flags.HasFlag(GameObjectFlags.EditorOnly));
var oldPosition = camera.WorldPosition; var oldRotation = camera.WorldRotation; var oldFov = camera.FieldOfView;
var oldSize = camera.CustomSize; var oldAxis = camera.FovAxis; var oldOrtho = camera.Orthographic;
var tone = scene.GetAllComponents<Tonemapping>().Single();
var oldTone = (tone.Mode,tone.AutoExposureEnabled,tone.MinimumExposure,tone.MaximumExposure,tone.ExposureCompensation);
var displayEffects = new System.Collections.Generic.HashSet<string>{ "ColorGrading","ColorAdjustments","Vignette","Bloom","AmbientOcclusion","ScreenSpaceReflections",
    "ChromaticAberration","FilmGrain","Sharpen","DepthOfField","MotionBlur","Highlight" };
var switched = scene.GetAllObjects(true).SelectMany(g => g.Components.GetAll()).Where(c => displayEffects.Contains(c.GetType().Name))
    .Select(c => (Component:c,Enabled:c.Enabled)).ToArray();
var skyTint = scene.GetAllComponents<SkyBox2D>().FirstOrDefault()?.Tint ?? Color.White;
var flags = System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Public;
var post = scene.GetSystem<PostProcessSystem>();
var updatePost = typeof(PostProcessSystem).GetMethod("UpdateCamera",flags);
var composeView = typeof(CameraComponent).GetMethod("ComposeView",flags,null,Type.EmptyTypes,null);
var preRender = typeof(Scene).GetMethod("PreRender",flags,null,Type.EmptyTypes,null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender",flags,null,Type.EmptyTypes,null);
void RefreshPostProcessing()
{
    // RenderToBitmap starts editor captures from the map's main camera: refresh both so the fixed exposure reaches the view.
    foreach(var other in scene.GetAllComponents<CameraComponent>().Where(c => c!=camera)) updatePost.Invoke(post,new object[]{other});
    updatePost.Invoke(post,new object[]{camera});
}
// Ask for useful mips before rendering (1024 is plenty for 512 faces; 4096 across a whole map ran the editor out of video
// memory once), and bring the baked indirect light up to date. No scope is held over the wait.
var marked = 0;
using(scene.Push())
{
    var keys = new[]{ "g_tColor","g_tNormal","g_tRoughness","g_tSelfIllumMask","g_tAmbientOcclusion","g_tTransmissiveColor" };
    foreach(var material in scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is not null && !r.Model.IsError).SelectMany(r => r.Model.Materials).Where(m => m is not null).Distinct())
    foreach(var texture in keys.Select(material.GetTexture).Append(material.FirstTexture).Where(t => t is not null && !t.IsError).Distinct())
    { texture.MarkUsed(1024); marked++; }
    foreach(var volume in scene.GetAllComponents<IndirectLightVolume>())
    foreach(var texture in new[]{volume.IrradianceTexture,volume.DistanceTexture,volume.RelocationTexture})
        if(texture is not null && !texture.IsError) texture.MarkUsed(Math.Max(texture.Width,texture.Height));
    var ddgiType = typeof(Scene).Assembly.GetType("Sandbox.DDGIVolumeSystem");
    var getter = typeof(Scene).GetMethods().Single(m => m.Name=="GetSystem" && m.IsGenericMethodDefinition && m.GetParameters().Length==0);
    var ddgi = getter.MakeGenericMethod(ddgiType).Invoke(scene,null);
    ddgiType.GetMethod("MarkDirty",flags).Invoke(ddgi,null);
    ddgiType.GetMethod("UpdateVolumes",flags).Invoke(ddgi,null);
}
await Task.Delay(2000,cancellationToken);
var rotations = new[]{ new Angles(0,0,0),new Angles(0,90,0),new Angles(0,180,0),new Angles(0,-90,0),new Angles(-90,0,0),new Angles(90,0,0) };
var captured = new System.Collections.Generic.List<object>();
var skipped = new System.Collections.Generic.List<string>();
try
{
    tone.Mode = Tonemapping.TonemappingMode.ACES; tone.AutoExposureEnabled = true; tone.ExposureCompensation = 0;
    foreach(var entry in switched) entry.Component.Enabled = false;
    foreach(var item in config["reflections"].AsArray())
    {
        var key = item["key"].GetValue<string>();
        if(!System.Text.RegularExpressions.Regex.IsMatch(key,"^[a-z][a-z0-9_]*$")) throw new InvalidOperationException("Invalid probe key.");
        var directory = System.IO.Path.Combine(root,"output/riverdale/lighting/reflections",revision,key);
        if(System.IO.File.Exists(System.IO.Path.Combine(directory,"faces.json"))) { skipped.Add(key); continue; }
        System.IO.Directory.CreateDirectory(directory);
        var position = Vector3.Parse(item["capture_world"].GetValue<string>());
        var exposure = item["exposure"]?.GetValue<float>() ?? 1f;
        var faces = new System.Collections.Generic.List<object>();
        for(var face=0;face<rotations.Length;face++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if(Game.IsPlaying || Editor.SceneEditorSession.Active!=session) throw new InvalidOperationException("Play started or the document changed during the capture.");
            using(scene.Push())
            {
                tone.MinimumExposure = exposure; tone.MaximumExposure = exposure;
                preRender.Invoke(scene,null);
                preCameraRender.Invoke(scene,null);
                using var bitmap = new Bitmap(size,size);
                float renderedFov = 0; string renderedSize = null; Vector3 renderedPosition = default; Rotation renderedRotation = default;
                for(var warmup=0;warmup<3;warmup++)
                {
                    camera.WorldPosition = position;
                    camera.WorldRotation = Rotation.From(rotations[face]);
                    camera.FieldOfView = 90; camera.CustomSize = new Vector2(size,size);
                    camera.FovAxis = CameraComponent.Axis.Horizontal; camera.Orthographic = false;
                    composeView.Invoke(camera,null);
                    RefreshPostProcessing();
                    if(Math.Abs(camera.View.FieldOfView-90)>0.01f) throw new InvalidOperationException("The reflection camera lost its 90-degree projection.");
                    renderedFov = camera.View.FieldOfView; renderedSize = camera.CustomSize.Value.ToString();
                    renderedPosition = camera.WorldPosition; renderedRotation = camera.WorldRotation;
                    camera.RenderToBitmap(bitmap,false);
                }
                var file = $"face-{face}.png";
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(directory,file),bitmap.ToPng());
                faces.Add(new { File=file, Face=face, FieldOfView=renderedFov, Position=renderedPosition.ToString(), CaptureSize=renderedSize,
                                Forward=renderedRotation.Forward.ToString(), Right=renderedRotation.Right.ToString(), Up=renderedRotation.Up.ToString() });
            }
            await Task.Yield();
        }
        var report = new { Key=key, Name=item["name"].GetValue<string>(), Revision=revision, Position=position.ToString(), Exposure=exposure,
            Encoding="sRGB; ACES tonemapper; native bitmap capture", ScreenSpaceOcclusion=false, DisplayEffects=false,
            SkyTint=$"{skyTint.r},{skyTint.g},{skyTint.b}", CaptureSize=$"{size},{size}", Faces=faces };
        System.IO.File.WriteAllText(System.IO.Path.Combine(directory,"faces.json"),System.Text.Json.JsonSerializer.Serialize(report));
        captured.Add(new { Key=key, Faces=faces.Count });
    }
}
finally
{
    camera.WorldPosition = oldPosition; camera.WorldRotation = oldRotation; camera.FieldOfView = oldFov;
    camera.CustomSize = oldSize; camera.FovAxis = oldAxis; camera.Orthographic = oldOrtho;
    tone.Mode = oldTone.Item1; tone.AutoExposureEnabled = oldTone.Item2; tone.MinimumExposure = oldTone.Item3; tone.MaximumExposure = oldTone.Item4; tone.ExposureCompensation = oldTone.Item5;
    foreach(var entry in switched) entry.Component.Enabled = entry.Enabled;
    using(scene.Push()) { composeView.Invoke(camera,null); RefreshPostProcessing(); }
}
return new { Revision=revision, Captured=captured, Skipped=skipped, MarkedTextures=marked,
    GamePreserved=!Game.IsPlaying && Game.ActiveScene?.Id==beforeGameId, DirtyStatePreserved=beforeDirty==session.HasUnsavedChanges };

#line default
}
}
public static class RiverdaleScript3
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Riverdale/editor/import-reflections.cs.txt"
// Riverdale: imports the reflection panoramas Sources/Riverdale/lighting/riverdale_reflections.py staged under
// output/riverdale/lighting/stage/ (EXRs and their sky.shader vmats, listed with their hashes in
// output/riverdale/lighting/reflection-manifest.json) into Assets/materials/riverdale/reflections/<revision>/, and
// compiles each vmat. The sky asset compiler turns each panorama into a cube
// (reflection_<key>_exr_<hash>.generated.vtex_c) without the runtime GGX filter that faulted envmap_filtering_cs here.
// Then run apply-reflections.cs.txt. Run with the native MCP's run_csharp; it refuses during play (compiling stalls the
// editor's frame, and a match with it).
if(Game.IsPlaying) throw new InvalidOperationException("Stop play before importing reflections.");
var root = Sandbox.Project.Current.GetRootPath();
var config = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Sources/Riverdale/lighting/config.json")));
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/riverdale/lighting/reflection-manifest.json")));
var revision = manifest["revision"].GetValue<string>();
if(revision!=config["revision"].GetValue<string>() || !System.Text.RegularExpressions.Regex.IsMatch(revision,"^daylight-v[0-9]+$"))
    throw new InvalidOperationException("The staged reflections are for another revision.");
var keys = config["reflections"].AsArray().Select(n => n["key"].GetValue<string>()).ToArray();
var files = manifest["files"].AsArray();
if(manifest["capture_encoding"]?.GetValue<string>()!="ACES inverse with sky calibration" || files.Count!=keys.Length*2)
    throw new InvalidOperationException("Convert every planned probe's capture (an EXR and a vmat each) before importing.");
string Hash(byte[] data) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(data)).ToLowerInvariant();
var stage = System.IO.Path.Combine(root,"output/riverdale/lighting/stage");
var imported = new System.Collections.Generic.List<string>();
var pattern = "^materials/riverdale/reflections/"+revision+"/reflection_([a-z][a-z0-9_]*)\\.(exr|vmat)$";
foreach(var item in files.OrderBy(i => i["path"].GetValue<string>().EndsWith(".vmat") ? 1 : 0))
{
    cancellationToken.ThrowIfCancellationRequested();
    var relative = item["path"].GetValue<string>();
    var match = System.Text.RegularExpressions.Regex.Match(relative,pattern);
    if(!match.Success || !keys.Contains(match.Groups[1].Value)) throw new InvalidOperationException("Unexpected reflection file: "+relative);
    var bytes = System.IO.File.ReadAllBytes(System.IO.Path.Combine(stage,relative));
    if(Hash(bytes)!=item["sha256"].GetValue<string>().ToLowerInvariant()) throw new InvalidOperationException("Staged file changed since conversion: "+relative);
    var target = System.IO.Path.Combine(root,"Assets",relative);
    if(System.IO.File.Exists(target) && System.IO.File.ReadAllBytes(target).SequenceEqual(bytes)) continue;
    System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
    System.IO.File.WriteAllBytes(target+".riverdale-import",bytes);
    System.IO.File.Move(target+".riverdale-import",target,true);
    Editor.AssetSystem.RegisterFile(target);
    imported.Add(relative);
}
var results = new System.Collections.Generic.List<object>();
var failed = new System.Collections.Generic.List<string>();
foreach(var key in keys)
{
    cancellationToken.ThrowIfCancellationRequested();
    var file = System.IO.Path.Combine(root,"Assets/materials/riverdale/reflections",revision,$"reflection_{key}.vmat");
    var asset = Editor.AssetSystem.FindByPath(file) ?? Editor.AssetSystem.RegisterFile(file);
    if(asset is null) { failed.Add(key); continue; }
    var ok = false; string error = null;
    try { ok = asset.Compile(true); } catch(Exception e) { error = e.Message; }
    await Task.Delay(1,cancellationToken);
    var cubes = System.IO.Directory.GetFiles(System.IO.Path.GetDirectoryName(file),$"reflection_{key}_exr_*.generated.vtex_c");
    if(!ok || asset.IsCompileFailed || cubes.Length!=1) failed.Add(key);
    results.Add(new { Key=key, Ok=ok, asset.IsCompiled, asset.IsCompileFailed, Cubes=cubes.Length, Error=error });
}
return new { Revision=revision, Imported=imported, Failed=failed, Results=results };

#line default
}
}
public static class RiverdaleScript4
{
public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)
{
#line 1 "D:/Documents/s&box projects/hc1/forked-shooter-main/Sources/Riverdale/editor/apply-reflections.cs.txt"
// Riverdale: gives each planned reflection probe its captured cube and saves the scene. Run with the native MCP's
// run_csharp after import-reflections.cs.txt. Each compiled cube (materials/riverdale/reflections/<revision>/
// reflection_<key>_exr_*.generated.vtex_c) is copied to lighting/riverdale/<revision>/reflection_<key>.vtex_c, a name
// that stays put when the panorama is recompiled. The probe moves to where its faces were captured (the cube's origin,
// for box projection) with its world box kept, and stays static (CustomTexture). Then
// Sources/Riverdale/lighting/riverdale_lighting.py preserve keeps the probes and the indirect light for regeneration.
if(Game.IsPlaying) throw new InvalidOperationException("Stop play before assigning reflections.");
var root = Sandbox.Project.Current.GetRootPath();
var config = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Sources/Riverdale/lighting/config.json")));
var revision = config["revision"].GetValue<string>();
if(!System.Text.RegularExpressions.Regex.IsMatch(revision,"^daylight-v[0-9]+$")) throw new InvalidOperationException("Invalid lighting revision.");
var session = Editor.SceneEditorSession.Active;
if(session?.Scene?.Source?.ResourcePath?.Equals("scenes/maps/riverdale/riverdale.scene",StringComparison.OrdinalIgnoreCase)!=true)
    throw new InvalidOperationException("Riverdale must own the editor window.");
if(session.HasUnsavedChanges) throw new InvalidOperationException("Riverdale has unsaved edits; inspect them before assigning reflections.");
var scene = session.Scene;
var beforeGameId = Game.ActiveScene?.Id;
var source = System.IO.Path.Combine(root,"Assets/materials/riverdale/reflections",revision);
var probeRoot = scene.Children.Single(g => g.Name=="Reflection Probes");
string Hash(byte[] data) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(data)).ToLowerInvariant();
var prepared = new System.Collections.Generic.List<(EnvmapProbe Probe, Texture Texture, Vector3 Position, BBox World, System.Text.Json.Nodes.JsonObject Entry)>();
var result = new System.Collections.Generic.List<object>();
// Everything is checked and loaded before the first probe changes, so a failure leaves the scene as it was.
foreach(var entry in config["reflections"].AsArray().Select(n => n.AsObject()))
{
    var key = entry["key"].GetValue<string>();
    var cubes = System.IO.Directory.GetFiles(source,$"reflection_{key}_exr_*.generated.vtex_c");
    if(cubes.Length!=1) throw new InvalidOperationException("Expected one compiled reflection cube for "+key);
    var path = $"lighting/riverdale/{revision}/reflection_{key}.vtex";
    var target = System.IO.Path.Combine(root,"Assets",path+"_c");
    var bytes = System.IO.File.ReadAllBytes(cubes[0]);
    if(System.IO.File.Exists(target))
    {
        if(Hash(System.IO.File.ReadAllBytes(target))!=Hash(bytes))
            throw new InvalidOperationException($"{path} already holds another cube; a running editor keeps the old one under that name. Start a new revision.");
    }
    else
    {
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
        System.IO.File.WriteAllBytes(target+".riverdale-pending",bytes);
        System.IO.File.Move(target+".riverdale-pending",target,false);
    }
    var texture = Texture.Load(path,false);
    if(texture is null || texture.IsError) throw new InvalidOperationException("The reflection cube did not load: "+path);
    var faces = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/riverdale/lighting/reflections",revision,key,"faces.json")));
    var position = Vector3.Parse(faces["Position"].GetValue<string>());
    if((position-Vector3.Parse(entry["capture_world"].GetValue<string>())).Length>0.5f) throw new InvalidOperationException("Captured somewhere else than the plan: "+key);
    var holder = probeRoot.Children.SingleOrDefault(g => g.Name==entry["name"].GetValue<string>()) ?? throw new InvalidOperationException("Run prepare-lighting.cs.txt first: no "+entry["name"]);
    var probe = holder.Components.Get<EnvmapProbe>() ?? throw new InvalidOperationException("No probe on "+holder.Name);
    var world = new BBox(Vector3.Parse(entry["bounds_min"].GetValue<string>()),Vector3.Parse(entry["bounds_max"].GetValue<string>()));
    prepared.Add((probe,texture,position,world,entry));
    result.Add(new { Key=key, Probe=holder.Name, Texture=texture.ResourcePath, texture.Width, texture.Height, texture.Mips });
}
void SetEnum(object target,string property,string value)
{
    var info = target.GetType().GetProperty(property) ?? throw new MissingMemberException(target.GetType().Name+"."+property);
    info.SetValue(target,Enum.Parse(info.PropertyType,value));
}
foreach(var item in prepared)
{
    item.Probe.GameObject.WorldPosition = item.Position;
    item.Probe.GameObject.WorldRotation = Rotation.Identity;
    item.Probe.GameObject.NetworkMode = NetworkMode.Snapshot;
    item.Probe.Bounds = new BBox(item.World.Mins-item.Position,item.World.Maxs-item.Position);
    item.Probe.Priority = item.Entry["priority"].GetValue<int>();
    item.Probe.Feathering = item.Entry["feathering"].GetValue<float>();
    var tint = item.Entry["tint"].GetValue<float>();
    item.Probe.TintColor = new Color(tint,tint,tint,1);
    SetEnum(item.Probe,"Projection","Box");
    item.Probe.Texture = item.Texture;
    SetEnum(item.Probe,"Mode","CustomTexture");
}
typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);
session.Save(false);
if(session.HasUnsavedChanges) throw new InvalidOperationException("Riverdale's reflections were not saved.");
var output = System.IO.Path.Combine(root,"output/riverdale/lighting/reflections",revision);
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"reflections-applied.json"),probeRoot.Serialize().ToJsonString());
var report = new { Revision=revision, Applied=result, SavedScene=true, GamePreserved=!Game.IsPlaying && Game.ActiveScene?.Id==beforeGameId };
System.IO.File.WriteAllText(System.IO.Path.Combine(output,"applied.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;

#line default
}
}
