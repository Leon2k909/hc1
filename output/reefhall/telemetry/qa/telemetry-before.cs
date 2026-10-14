var scene = Editor.SceneEditorSession.Active.Scene;
var folder = System.IO.Path.Combine( Project.Current.GetRootPath(), "output/reefhall/telemetry" );
System.IO.Directory.CreateDirectory( folder );
GameObject holder = null;
try
{
    using ( scene.Push() )
    {
        holder = scene.CreateObject( false );
        holder.Name = "__telemetry_review";
        holder.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.Hidden;
        holder.WorldPosition = new Vector3( 0, 2224, 58 );
        holder.WorldRotation = Rotation.LookAt( new Vector3( 0, 2193.5f, 54.5f ) - holder.WorldPosition );
        var camera = holder.Components.Create<CameraComponent>();
        camera.IsMainCamera = false;
        camera.ZNear = 1;
        camera.ZFar = 20000;
        camera.FieldOfView = 50;
        var tone = holder.Components.Create<Tonemapping>();
        tone.Mode = Tonemapping.TonemappingMode.ACES;
        tone.AutoExposureEnabled = false;
        tone.ExposureCompensation = 1;
        holder.Enabled = true;
        using var bitmap = new Bitmap( 1536, 1024 );
        camera.RenderToBitmap( bitmap );
        await Task.Delay( 1000, cancellationToken );
        camera.RenderToBitmap( bitmap );
        var path = System.IO.Path.Combine( folder, "before.png" );
        System.IO.File.WriteAllBytes( path, bitmap.ToPng() );
        return path;
    }
}
finally { holder?.Destroy(); }
