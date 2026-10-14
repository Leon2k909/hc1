var scene = Editor.SceneEditorSession.Active.Scene;
var folder = System.IO.Path.Combine( Project.Current.GetRootPath(), "output/reefhall/telemetry" );
var material = Material.Load( "materials/reefhall/rh_screen_data.vmat" );
material.GetTexture( "g_tColor" )?.MarkUsed( 4096 );
await Task.Delay( 2000, cancellationToken );
Vector3 World( float e, float n, float z ) => new( n, -e, z );
var results = new System.Collections.Generic.List<string>();
foreach ( var view in new[] {
    ( Name: "office-west", Eye: World( 1960, 815, 263 ), Target: World( 1960, 772, 251.5f ), Fov: 50f ),
    ( Name: "office-east", Eye: World( 2150, 823, 263 ), Target: World( 2150, 868, 251.5f ), Fov: 50f )
} )
{
    cancellationToken.ThrowIfCancellationRequested();
    GameObject holder = null;
    try
    {
        using ( scene.Push() )
        {
            holder = scene.CreateObject( false );
            holder.Name = "__telemetry_review";
            holder.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.Hidden;
            holder.WorldPosition = view.Eye;
            holder.WorldRotation = Rotation.LookAt( view.Target - view.Eye );
            var camera = holder.Components.Create<CameraComponent>();
            camera.IsMainCamera = false;
            camera.ZNear = 1;
            camera.ZFar = 20000;
            camera.FieldOfView = view.Fov;
            var tone = holder.Components.Create<Tonemapping>();
            tone.Mode = Tonemapping.TonemappingMode.ACES;
            tone.AutoExposureEnabled = false;
            tone.ExposureCompensation = 1;
            holder.Enabled = true;
            using var bitmap = new Bitmap( 1440, 960 );
            camera.RenderToBitmap( bitmap );
            await Task.Delay( 500, cancellationToken );
            camera.RenderToBitmap( bitmap );
            var path = System.IO.Path.Combine( folder, view.Name + ".png" );
            System.IO.File.WriteAllBytes( path, bitmap.ToPng() );
            results.Add( path );
        }
    }
    finally { holder?.Destroy(); }
}
return results;
