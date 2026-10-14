var scene = Editor.SceneEditorSession.All.First( s => s.Scene?.Name == "reefhall" ).Scene;
var folder = System.IO.Path.Combine( Project.Current.GetRootPath(), "output/reefhall/consoles" );
System.IO.Directory.CreateDirectory( folder );
GameObject holder = null;
try
{
    using ( scene.Push() )
    {
        holder = scene.CreateObject( false );
        holder.Name = "__console_review";
        holder.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.Hidden;
        var camera = holder.Components.Create<CameraComponent>();
        camera.IsMainCamera = false;
        camera.ZNear = 2;
        camera.ZFar = 20000;
        camera.FieldOfView = 72;
        var tone = holder.Components.Create<Tonemapping>();
        tone.Mode = Tonemapping.TonemappingMode.ACES;
        tone.AutoExposureEnabled = false;
        tone.ExposureCompensation = 1;
        holder.Enabled = true;
        Vector3 World( float e, float n, float z ) => new( n, -e, z );
        using var bitmap = new Bitmap( 1600, 1000 );
        camera.WorldPosition = World( 2455, 175, 70 );
        camera.WorldRotation = Rotation.LookAt( World( 2600, 420, 39 ) - camera.WorldPosition );
        camera.RenderToBitmap( bitmap );
        await Task.Delay( 1200, cancellationToken );
        camera.RenderToBitmap( bitmap );
        System.IO.File.WriteAllBytes( System.IO.Path.Combine( folder, "before.png" ), bitmap.ToPng() );
    }
    return folder;
}
finally { holder?.Destroy(); }
