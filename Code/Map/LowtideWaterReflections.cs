using Sandbox.Rendering;

namespace Facepunch;

/// <summary>Camera-correct canal reflections, rendered at half resolution before water.</summary>
[Title( "Lowtide Water Reflections" ), Category( "Map" )]
public sealed class LowtideWaterReflections : Component, Component.DontExecuteOnServer, Component.ExecuteInEditor
{
    [Property] public float WaterHeight { get; set; } = -137;
    [Property, Range( 256, 1280 )] public int MaximumWidth { get; set; } = 960;
    // World XY extent of the flat canal surface in lowtide_map.water_model.
    // Harbour water and bank pools use cubemaps at their own elevations.
    [Property] public Vector2 ChannelMinimum { get; set; } = new( -1500, -128 );
    [Property] public Vector2 ChannelMaximum { get; set; } = new( 3400, 128 );

    private sealed class View
    {
        public readonly CommandList Capture = new( "Lowtide planar reflection" );
        public readonly bool AddedExclusion;
        public readonly CameraComponent CommandCamera;

        public View( CameraComponent camera, CameraComponent commandCamera )
        {
            CommandCamera = commandCamera;
            AddedExclusion = !camera.RenderExcludeTags.Has( "water" );
            camera.RenderExcludeTags.Add( "water" );
            // Opaque depth is available here; later glass and particles still
            // blend over the water in the normal transparent pass.
            CommandCamera.AddCommandList( Capture, Stage.AfterSkybox, -200 );
        }

        public void Detach( CameraComponent camera )
        {
            if ( CommandCamera.IsValid() ) CommandCamera.RemoveCommandList( Capture );
            if ( camera.IsValid() )
            {
                // Also clears registrations retained across a hotload from the
                // version that always attached to the viewport camera.
                camera.RemoveCommandList( Capture );
                if ( AddedExclusion ) camera.RenderExcludeTags.Remove( "water" );
            }
            Capture.Reset();
        }
    }

    private readonly Dictionary<CameraComponent, View> views = new();
    private readonly HashSet<CameraComponent> activeViews = new();
    private readonly TagSet excluded = new();
    // Reused every frame. Made when first wanted, since a hotload leaves a new field null.
    private List<CameraComponent> cameras, stale;

    protected override void OnEnabled()
    {
        excluded.Add( "water" );
        excluded.Add( "viewer" );
        excluded.Add( "viewmodel" );
        excluded.Add( "optic_viewmodel" );
        excluded.Add( "hidden" );
    }

    protected override void OnPreRender() => PrepareViews();

    // Public for deterministic editor capture; normal play uses OnPreRender.
    public void PrepareViews()
    {
        var water = GetComponent<ModelRenderer>();
        if ( !water.IsValid() || !water.Active || water.Model is null || water.Model.IsError )
        {
            OnDisabled();
            return;
        }
        activeViews.Clear();
        var bounds = new BBox(
            new Vector3( ChannelMinimum.x - 16, ChannelMinimum.y - 16, WaterHeight - 1 ),
            new Vector3( ChannelMaximum.x + 16, ChannelMaximum.y + 16, WaterHeight + 1 ) );
        cameras ??= new();
        cameras.Clear();
        Scene.GetAll( cameras );
        // Editor viewport initialization copies Scene.Camera's render hooks.
        // Commands on the viewport camera itself are consequently never run.
        // Multiple editor views share that hook, so retain ordinary cubemap
        // water there instead of submitting a different mirror for each view.
        var editorCommandCamera = Scene.IsEditor ? Scene.Camera : null;
        var sharedEditorViews = false;
        if ( editorCommandCamera.IsValid() )
        {
            var perspective = 0;
            foreach ( var camera in cameras )
                if ( camera.Active && !camera.Orthographic ) perspective++;
            sharedEditorViews = perspective > 1;
        }
        foreach ( var camera in cameras )
        {
            if ( !camera.Active || camera.Orthographic || sharedEditorViews || camera.WorldPosition.z <= WaterHeight + 1 ) continue;
            // Respect a camera that intentionally hid water before we owned it.
            if ( !views.ContainsKey( camera ) && camera.RenderExcludeTags.Has( "water" ) ) continue;
            // Looking away from the canal must not render a second full view.
            // A small margin keeps transitions outside the visible water edge.
            if ( !camera.GetFrustum().IsInside( bounds, true ) ) continue;
            activeViews.Add( camera );
            var commandCamera = editorCommandCamera.IsValid() ? editorCommandCamera : camera;
            if ( views.TryGetValue( camera, out var previous ) && previous.CommandCamera != commandCamera )
            {
                previous.Detach( camera );
                views.Remove( camera );
            }
            if ( !views.TryGetValue( camera, out var view ) )
            {
                view = new View( camera, commandCamera );
                views.Add( camera, view );
            }
            var commands = view.Capture;
            commands.Reset();
            var size = camera.CustomSize ?? Screen.Size;
            var width = Math.Clamp( (int)size.x / 2, 256, Math.Clamp( MaximumWidth, 256, 1280 ) );
            var height = Math.Max( 1, (int)(width * size.y / Math.Max( size.x, 1 )) );
            // A short linear-HDR pyramid supplies roughness and minification filtering.
            var reflectionMips = 1;
            for ( var extent = Math.Min( width, height ); extent > 1 && reflectionMips < 7; extent >>= 1 )
                reflectionMips++;
            var target = commands.GetRenderTarget( "lowtide-reflection", width, height,
                ImageFormat.RGBA16161616F, ImageFormat.D24S8, MultisampleAmount.MultisampleNone, reflectionMips );
            commands.DrawReflection( camera, new Plane( new Vector3( 0, 0, WaterHeight ), Vector3.Up ), in target,
                new ReflectionSetup
                {
                    ClipOffset = .2f,
                    ViewSetup = new ViewSetup
                    {
                        ExcludeTags = excluded,
                        EnablePostprocessing = false,
                        EnableUI = false,
                        EnableDebugOverlays = false
                    }
                } );
            // Generate only after the reflected view is complete, before publishing its texture.
            // Box filtering preserves linear HDR radiance; the engine Gaussian path applies a display-space transform.
            if ( reflectionMips > 1 )
                commands.GenerateMipMaps( target, Sandbox.Graphics.DownsampleMethod.Box );
            // Published after the nested view completes. DrawReflection guards
            // child views against recursion, and water is excluded from capture.
            commands.Attributes.Set( "LowtideReflection", target.ColorTexture );
            commands.Attributes.Set( "LowtideReflectionEnabled", true );
            commands.Attributes.Set( "LowtideReflectionFlip", false );
            commands.Attributes.Set( "LowtideReflectionPlane", WaterHeight );
            // DrawRenderer honors the camera's water exclusion. DrawModel is
            // deliberate here: it submits only this surface with our attributes.
            commands.DrawModel( water.Model, water.WorldTransform );
            commands.Attributes.Set( "LowtideReflectionEnabled", false );
            commands.ReleaseRenderTarget( target );
        }
        stale ??= new();
        stale.Clear();
        foreach ( var camera in views.Keys )
            if ( !activeViews.Contains( camera ) ) stale.Add( camera );
        foreach ( var camera in stale )
        {
            views[camera].Detach( camera );
            views.Remove( camera );
        }
    }

    protected override void OnDisabled()
    {
        foreach ( var pair in views ) pair.Value.Detach( pair.Key );
        views.Clear();
        activeViews.Clear();
    }

    protected override void OnDestroy() => OnDisabled();
}
