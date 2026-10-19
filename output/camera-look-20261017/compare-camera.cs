var session = Editor.SceneEditorSession.Active;
if ( Game.IsPlaying || session?.Scene.Source?.ResourcePath != "scenes/maps/lowtide/lowtide.scene" )
    throw new Exception( "Expected the existing Lowtide edit session." );
var scene = session.Scene;
var wasDirty = session.HasUnsavedChanges;
var sourceObject = scene.Directory.FindByGuid( Guid.Parse( "f73e7b0c-7483-5702-8588-fa7166694cce" ) );
if ( !sourceObject.IsValid() ) throw new Exception( "The shared camera source was not found." );
var originalIds = scene.GetAllObjects( true ).Select( x => x.Id ).ToHashSet();
var folder = System.IO.Path.Combine( Project.Current.GetRootPath(), "output/camera-look-20261017" );
using var scope = scene.Push();
var review = new GameObject( false, "Temporary camera comparison" );
review.Flags = GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked | GameObjectFlags.Hidden;
T Copy<T>() where T : Component, new()
{
    var original = sourceObject.GetComponent<T>( true );
    if ( !original.IsValid() ) return null;
    var json = original.Serialize().AsObject();
    json.Remove( "__guid" );
    var copy = review.Components.Create<T>();
    copy.DeserializeImmediately( json );
    return copy;
}
try
{
    var camera = Copy<CameraComponent>();
    camera.IsMainCamera = false;
    camera.Priority = -100;
    camera.FieldOfView = 80;
    Copy<Bloom>();
    var tone = Copy<Tonemapping>();
    Copy<Sharpen>();
    Copy<AmbientOcclusion>();
    var color = Copy<ColorAdjustments>();
    Copy<Vignette>();
    review.WorldPosition = Vector3.Parse( "-1360.79956,-236.104324,180.333176" );
    review.WorldRotation = Rotation.From( Angles.Parse( "17.800478,-31.4998188,0" ) );
    review.Enabled = true;
    var system = scene.GetSystem<PostProcessSystem>();
    var update = typeof( PostProcessSystem ).GetMethod( "UpdateCamera", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic );
    if ( update is null ) throw new Exception( "Installed post-process update method was not found." );
    var results = new System.Collections.Generic.List<object>();
    foreach ( var look in new[] { "aces-neutral", "agx-current" } )
    {
        tone.Mode = look == "aces-neutral" ? Tonemapping.TonemappingMode.ACES : Tonemapping.TonemappingMode.AgX;
        color.Enabled = look == "agx-current";
        for ( var frame = 0; frame < 8; frame++ )
        {
            cancellationToken.ThrowIfCancellationRequested();
            update.Invoke( system, new object[] { camera } );
            using var bitmap = new Bitmap( 1280, 720 );
            camera.RenderToBitmap( bitmap, false );
            if ( frame == 7 )
            {
                var path = System.IO.Path.Combine( folder, "lowtide-camera-" + look + ".png" );
                System.IO.File.WriteAllBytes( path, bitmap.ToPng() );
                results.Add( new { look, path, mode = tone.Mode.ToString(), color.Enabled, color.Contrast, color.Saturation } );
            }
            await Task.Delay( 120, cancellationToken );
        }
    }
    return new { results, camera.EnablePostProcessing, wasDirty };
}
finally
{
    review.Destroy();
    if ( session.HasUnsavedChanges != wasDirty ) throw new Exception( "Unexpected change to the editor dirty state." );
    if ( !originalIds.SetEquals( scene.GetAllObjects( true ).Select( x => x.Id ) ) )
        throw new Exception( "Temporary camera cleanup did not preserve the original scene objects." );
}

