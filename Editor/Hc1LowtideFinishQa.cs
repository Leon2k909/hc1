using Editor;
using Sandbox;
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Render Lowtide's finish and report missing assets in an isolated scene.</summary>
public static class Hc1LowtideFinishQa
{
    private static Scene captureScene;
    private static Transform? savedViewport;

    [ConCmd( "hc1_lowtide_view" )]
    public static void View( bool restore = false )
    {
        var viewport = SceneViewWidget.Current?.LastSelectedViewportWidget;
        if ( viewport is null ) return;
        if ( restore )
        {
            if ( savedViewport is not { } old ) return;
            viewport.State.CameraPosition = old.Position;
            viewport.State.CameraRotation = old.Rotation;
            savedViewport = null;
            return;
        }
        savedViewport ??= new Transform( viewport.State.CameraPosition, viewport.State.CameraRotation );
        viewport.State.CameraPosition = new Vector3( -1300, 0, 125 );
        viewport.State.CameraRotation = Rotation.LookAt( new Vector3( 530, 0, 205 ) - viewport.State.CameraPosition );
    }

    [ConCmd( "hc1_lowtide_finish_shot" )]
    public static async void Shot( string name = "detail", float ee = -910, float en = -1110, float ez = 205,
        float te = -620, float tn = -1475, float tz = 300, float fov = 56, float exposure = -999 )
    {
        // A hotload during an awaited capture can copy a busy bool into the new
        // assembly after the old method has started. Track the actual scene so
        // its destruction releases the guard across both assembly generations.
        if ( captureScene.IsValid() ) return;
        var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/quality-pass" );
        Directory.CreateDirectory( folder );
        File.WriteAllText( Path.Combine( folder, "capture-status.txt" ), $"Rendering {name}" );
        var scene = Scene.CreateEditorScene();
        captureScene = scene;
        SceneRenderingWidget livePreview = null;
        Texture reflectionTarget = null;
        var reflectionChecks = "not requested";
        try
        {
            var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Lowtide/lowtide.scene" ) ) ).AsObject();
            var visual = new HashSet<string>( StringComparer.OrdinalIgnoreCase )
            { "Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes" };
            var objects = new JsonArray();
            foreach ( var item in root["GameObjects"].AsArray() )
                if ( item["Name"] is { } label && visual.Contains( label.GetValue<string>() ) ) objects.Add( item.DeepClone() );
            root["GameObjects"] = objects;
            root["SceneProperties"]["NavMesh"]["Enabled"] = false;
            root["SceneProperties"]["WantsSystemScene"] = false;
            CameraComponent camera;
            Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
            using ( scene.Push() )
            {
                scene.Deserialize( root );
                if ( name.StartsWith( "live-spot-interior" ) )
                {
                    foreach ( var point in scene.GetAllComponents<PointLight>().Where( p =>
                        p.GameObject.Name.Contains( "Warehouse" ) || p.GameObject.Name.Contains( "Mezzanine" ) ).ToArray() )
                    {
                        var lamp = point.GameObject;
                        var spot = lamp.Components.Create<SpotLight>();
                        spot.WorldRotation = Rotation.LookAt( Vector3.Down );
                        spot.Radius = point.Radius;
                        spot.LightColor = point.LightColor;
                        spot.Attenuation = point.Attenuation;
                        spot.ConeOuter = 75;
                        spot.ConeInner = 45;
                        spot.Shadows = !lamp.Name.Contains( "Mezzanine" );
                        spot.ShadowHardness = .35f;
                        point.Enabled = false;
                    }
                }
                var holder = new GameObject( false, "Lowtide finish QA camera" );
                camera = holder.Components.Create<CameraComponent>();
                camera.WorldPosition = World( new( ee, en, ez ) );
                camera.WorldRotation = Rotation.LookAt( World( new( te, tn, tz ) ) - camera.WorldPosition );
                camera.FieldOfView = fov;
                camera.CustomSize = new Vector2( 1672, 941 );
                camera.ZNear = 1;
                camera.ZFar = 100000;
                camera.EnablePostProcessing = true;
                if ( exposure > -999 )
                {
                    foreach ( var tone in scene.GetAllComponents<Tonemapping>() )
                    {
                        tone.AutoExposureEnabled = true;
                        tone.MinimumExposure = 1;
                        tone.MaximumExposure = 1;
                        tone.Rate = 10;
                        tone.ExposureCompensation = exposure;
                    }
                }
                holder.Enabled = true;
            }
            using var bitmap = new Bitmap( 1672, 941 );
            float elapsed = 0;
            using ( scene.Push() )
            {
                scene.EditorTick( elapsed += .016f, .016f );
                camera.RenderToBitmap( bitmap );
            }
            await Task.Delay( 3500 );
            // Isolated scenes are outside the app render loop, so their dynamic
            // envmaps never render through EditorTick/RenderToBitmap alone.
            // This editor-only adapter fails explicitly if the engine API changes.
            var renderProbe = typeof( EnvmapProbe ).GetMethod( "RenderCubemap", BindingFlags.Instance | BindingFlags.NonPublic,
                null, Type.EmptyTypes, null ) ?? throw new MissingMethodException( "EnvmapProbe.RenderCubemap" );
            for ( var bounce = 0; bounce < 3; bounce++ )
                foreach ( var probe in scene.GetAllComponents<EnvmapProbe>() )
                {
                    using ( scene.Push() ) renderProbe.Invoke( probe, null );
                    await Task.Delay( 16 );
                }
            if ( name.StartsWith( "gi-debug" ) || name.StartsWith( "live-gi-interior" ) )
            {
                var editor = SceneEditorSession.Active;
                if ( editor?.Scene.Source?.ResourcePath?.Contains( "lowtide", StringComparison.OrdinalIgnoreCase ) != true )
                    throw new InvalidOperationException( "Open Lowtide before baking its lighting preview." );
                // Borrow only the saved scene's asset folder. All lighting and
                // geometry remain in this isolated preview scene.
                typeof( Scene ).GetProperty( "Editor" ).SetValue( scene, editor );
                GameObject indirectObject;
                IndirectLightVolume indirect;
                using ( scene.Push() )
                {
                    var interior = name.StartsWith( "live-gi-interior" );
                    indirectObject = new GameObject( true, interior ? "Warehouse Indirect Light Preview" : "Fleet Indirect Light" );
                    indirect = indirectObject.Components.Create<IndirectLightVolume>();
                    indirect.Bounds = interior
                        ? new BBox( new Vector3( -376, -975, 8 ), new Vector3( 1126, -265, 344 ) )
                        : new BBox( new Vector3( -1650, -255, -165 ), new Vector3( 1490, 255, 1050 ) );
                    indirect.ProbeDensity = interior ? 10 : 3;
                    indirect.NormalBias = 5;
                    indirect.RenderExcludeTags.Add( "water" );
                    File.WriteAllText( Path.Combine( folder, "capture-status.txt" ), $"Baking {name}: {indirect.ProbeCounts}" );
                    await indirect.BakeProbes();
                }
                File.WriteAllText( Path.Combine( folder, name + "-volume.json" ), indirectObject.Serialize().ToJsonString() );
            }
            if ( name.StartsWith( "live-" ) )
            {
                if ( name.StartsWith( "live-command" ) )
                {
                    using ( scene.Push() )
                    {
                        var water = scene.GetAllComponents<ModelRenderer>().First( r => r.GameObject.Name == "Water" );
                        var reflection = water.GameObject.Components.Get<Facepunch.LowtideWaterReflections>()
                            ?? water.GameObject.Components.Create<Facepunch.LowtideWaterReflections>();
                        var excludedObject = new GameObject( true, "QA intentionally excludes water" );
                        var excludedCamera = excludedObject.Components.Create<CameraComponent>();
                        excludedCamera.IsMainCamera = false;
                        excludedCamera.WorldPosition = camera.WorldPosition;
                        excludedCamera.RenderExcludeTags.Add( "water" );
                        reflection.PrepareViews();
                        if ( !camera.RenderExcludeTags.Has( "water" ) ) throw new Exception( "Reflection did not attach" );
                        var facing = camera.WorldRotation;
                        camera.WorldRotation = Rotation.LookAt( Vector3.Up );
                        camera.ComposeView();
                        reflection.PrepareViews();
                        if ( camera.RenderExcludeTags.Has( "water" ) ) throw new Exception( "Offscreen canal retained reflection view" );
                        camera.WorldRotation = facing;
                        camera.ComposeView();
                        reflection.PrepareViews();
                        if ( !camera.RenderExcludeTags.Has( "water" ) ) throw new Exception( "Reflection did not reattach after looking back" );
                        camera.Orthographic = true;
                        reflection.PrepareViews();
                        if ( camera.RenderExcludeTags.Has( "water" ) ) throw new Exception( "Orthographic camera retained water exclusion" );
                        camera.Orthographic = false;
                        reflection.PrepareViews();
                        reflection.Enabled = false;
                        if ( camera.RenderExcludeTags.Has( "water" ) ) throw new Exception( "Reflection did not clean up" );
                        if ( !excludedCamera.RenderExcludeTags.Has( "water" ) ) throw new Exception( "Authored camera exclusion was lost" );
                        excludedObject.Destroy();
                        reflection.Enabled = true;
                        reflection.PrepareViews();
                        reflectionChecks = "PASS: attach, offscreen removal, visible reattach, orthographic transition, disable cleanup, authored exclusions, re-enable";
                    }
                }
                if ( name.StartsWith( "live-planar" ) )
                {
                    using ( scene.Push() )
                    {
                        var reflectionObject = new GameObject( true, "Reflection preview" );
                        var reflectionCamera = reflectionObject.Components.Create<CameraComponent>();
                        reflectionCamera.IsMainCamera = false;
                        var position = camera.WorldPosition;
                        reflectionCamera.WorldPosition = position.WithZ( -274 - position.z );
                        var forward = camera.WorldRotation.Forward;
                        var up = camera.WorldRotation.Up;
                        reflectionCamera.WorldRotation = Rotation.LookAt( forward.WithZ( -forward.z ), new Vector3( -up.x, -up.y, up.z ) );
                        reflectionCamera.FieldOfView = camera.FieldOfView;
                        reflectionCamera.ZNear = 1;
                        reflectionCamera.ZFar = 100000;
                        reflectionCamera.EnablePostProcessing = false;
                        reflectionCamera.AutoExposure.Enabled = false;
                        reflectionCamera.RenderExcludeTags.Add( "water" );
                        reflectionCamera.CustomSize = new Vector2( 836, 470 );
                        typeof( CameraComponent ).GetMethod( "InitializeRendering", BindingFlags.Instance | BindingFlags.NonPublic ).Invoke( reflectionCamera, new object[] { false } );
                        reflectionCamera.CustomProjectionMatrix = reflectionCamera.CalculateObliqueMatrix( new Plane( new Vector3( 0, 0, -136.8f ), Vector3.Up ) );
                        reflectionTarget = Texture.CreateRenderTarget( "lowtide-planar-preview", ImageFormat.RGBA16161616F, new Vector2( 836, 470 ) );
                        reflectionCamera.RenderToTexture( reflectionTarget );
                        using var reflectionBitmap = reflectionTarget.GetBitmap();
                        File.WriteAllBytes( Path.Combine( folder, name + "-reflection.png" ), reflectionBitmap.ToPng() );
                        var water = scene.GetAllComponents<ModelRenderer>().First( r => r.GameObject.Name == "Water" );
                        water.SceneObject.Attributes.Set( "LowtideReflectionEnabled", true );
                        water.SceneObject.Attributes.Set( "LowtideReflectionFlip", true );
                        water.SceneObject.Attributes.Set( "LowtideReflectionPlane", -137f );
                        water.SceneObject.Attributes.Set( "LowtideReflection", reflectionTarget );
                    }
                }
                // The app's render loop updates temporal lighting/exposure.
                // Keep this opt-in and dispose the temporary preview in finally.
                livePreview = new SceneRenderingWidget
                {
                    Scene = scene,
                    Camera = camera,
                    Size = new Vector2( 1672, 941 ),
                    ShowWithoutActivating = true,
                    WindowFlags = WindowFlags.Tool | WindowFlags.WindowDoesNotAcceptFocus | WindowFlags.WindowStaysOnBottomHint
                };
                livePreview.OnPreFrame += () =>
                {
                    using ( scene.Push() ) scene.EditorTick( elapsed += .016f, .016f );
                };
                livePreview.Show();
                await Task.Delay( 4000 );
            }
            for ( var frame = 0; frame < 12; frame++ )
            {
                using ( scene.Push() )
                {
                    scene.EditorTick( elapsed += .016f, .016f );
                    camera.RenderToBitmap( bitmap );
                }
                await Task.Delay( 32 );
            }
            var diagnostics = new StringBuilder();
            diagnostics.AppendLine( $"Reflection lifecycle: {reflectionChecks}" );
            diagnostics.AppendLine( $"Lights: points={scene.GetAllComponents<PointLight>().Count( p => p.Enabled )}; spots={scene.GetAllComponents<SpotLight>().Count( p => p.Enabled )}" );
            foreach ( var lamp in scene.GetAllComponents<PointLight>().Where( p =>
                p.GameObject.Name.Contains( "Warehouse" ) || p.GameObject.Name.Contains( "Mezzanine" ) ) )
            {
                var start = lamp.WorldPosition;
                var obstruction = scene.Trace.Ray( start, start + Vector3.Down * 8 ).UseRenderMeshes().Run();
                diagnostics.AppendLine( $"Emitter {lamp.GameObject.Name}: downwardClear={!obstruction.Hit}" );
                if ( obstruction.Hit ) throw new Exception( $"Pendant blocks {lamp.GameObject.Name}" );
            }
            if ( name.StartsWith( "probe-debug" ) )
            {
                var probe = scene.GetAllComponents<EnvmapProbe>().First( p => p.GameObject.Name == "Probe Fleet South" );
                var texture = typeof( EnvmapProbe ).GetField( "_dynamicTexture", BindingFlags.Instance | BindingFlags.NonPublic ).GetValue( probe ) as Texture;
                for ( var face = 0; face < 6; face++ )
                {
                    using var faceBitmap = (Bitmap)typeof( Texture ).GetMethod( "GetFaceBitmap", BindingFlags.Instance | BindingFlags.NonPublic )
                        .Invoke( texture, new object[] { face, 0 } );
                    File.WriteAllBytes( Path.Combine( folder, name + $"-face-{face}.png" ), faceBitmap.ToPng() );
                }
            }
            diagnostics.AppendLine( $"Camera: sceneCamera={scene.Camera == camera}; exposure={camera.AutoExposure.Enabled}/{camera.AutoExposure.Compensation}/{camera.AutoExposure.MinimumExposure}/{camera.AutoExposure.MaximumExposure}; postprocessing={camera.EnablePostProcessing}; captureVersion=2" );
            foreach ( var probe in scene.GetAllComponents<EnvmapProbe>() )
                diagnostics.AppendLine( $"{probe.GameObject.Name}: mode={probe.Mode}; resolution={probe.Resolution}; possible-resolutions={string.Join(',', Enum.GetNames(probe.Resolution.GetType()))}; dynamic={probe.RenderDynamically}; range={probe.MaxDistance}; texture={probe.Texture}; baked={probe.BakedTexture}" );
            foreach ( var renderer in scene.GetAllComponents<ModelRenderer>() )
                diagnostics.AppendLine( $"{renderer.GameObject.Name}: modelError={renderer.Model?.IsError}; materialErrors={renderer.Model?.Materials.Count( m => m is null || m.IsError )}" );
            foreach ( var volume in scene.GetAllComponents<PostProcessVolume>() )
                diagnostics.AppendLine( $"{volume.GameObject.Name}: active={volume.Active}; infinite={volume.IsInfinite}" );
            foreach ( var tone in scene.GetAllComponents<Tonemapping>() )
                diagnostics.AppendLine( $"{tone.GameObject.Name}: exposure auto={tone.AutoExposureEnabled} min={tone.MinimumExposure} max={tone.MaximumExposure}" );
            File.WriteAllText( Path.Combine( folder, name + "-diagnostics.txt" ), diagnostics.ToString() );
            File.WriteAllBytes( Path.Combine( folder, name + ".png" ), bitmap.ToPng() );
            if ( name.StartsWith( "probe-debug" ) )
            {
                using var target = Texture.CreateRenderTarget( "lowtide-qa-target", ImageFormat.RGBA8888, new Vector2( 1672, 941 ) );
                camera.CustomSize = new Vector2( 1672, 941 );
                camera.RenderToTexture( target );
                using var targetBitmap = target.GetBitmap();
                File.WriteAllBytes( Path.Combine( folder, name + "-texture.png" ), targetBitmap.ToPng() );
            }
            File.WriteAllText( Path.Combine( folder, "capture-status.txt" ), $"Finished {name}" );
        }
        catch ( Exception e ) { File.WriteAllText( Path.Combine( folder, name + "-error.txt" ), e.ToString() ); }
        finally
        {
            livePreview?.Close();
            livePreview?.Destroy();
            scene.Destroy();
            reflectionTarget?.Dispose();
            if ( captureScene == scene ) captureScene = null;
        }
    }

}
