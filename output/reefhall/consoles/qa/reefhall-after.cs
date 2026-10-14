var scene = Editor.SceneEditorSession.All.First( s => s.Scene?.Name == "reefhall" ).Scene;
var folder = System.IO.Path.Combine( Project.Current.GetRootPath(), "output/reefhall/consoles" );
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
        var tone = holder.Components.Create<Tonemapping>();
        tone.Mode = Tonemapping.TonemappingMode.ACES;
        tone.AutoExposureEnabled = false;
        tone.ExposureCompensation = 1;
        holder.Enabled = true;
        Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
        var views = new (string name, Vector3 eye, Vector3 target, float fov)[] {
            ("after",new(2455,175,70),new(2600,420,39),72),
            ("console-overview",new(2440,80,76),new(2600,255,37),68),
            ("console-detail",new(2530,210,65),new(2600,260,48),66),
            ("console-back",new(2700,60,73),new(2600,260,40),72),
            ("room-overview",new(1930,-540,72),new(2630,0,75),82)
        };
        using var bitmap = new Bitmap( 1600, 1000 );
        foreach ( var view in views )
        {
            cancellationToken.ThrowIfCancellationRequested();
            camera.WorldPosition = World( view.eye );
            camera.WorldRotation = Rotation.LookAt( World( view.target ) - camera.WorldPosition );
            camera.FieldOfView = view.fov;
            camera.RenderToBitmap( bitmap );
            await Task.Delay( 700, cancellationToken );
            camera.RenderToBitmap( bitmap );
            System.IO.File.WriteAllBytes( System.IO.Path.Combine( folder, view.name + ".png" ), bitmap.ToPng() );
        }
    }
    return folder;
}
finally { holder?.Destroy(); }
