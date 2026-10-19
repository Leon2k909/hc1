var session = Editor.SceneEditorSession.Active;
var config = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( exchangeDirectory, "capture.json" ) ) ).AsObject();
if ( Game.IsPlaying || session?.Scene.Source?.ResourcePath.ToLowerInvariant() != config["map"].GetValue<string>() )
    throw new Exception( "Expected the requested idle map editor." );
var scene = session.Scene;
var wasDirty = session.HasUnsavedChanges;
var originalIds = scene.GetAllObjects( true ).Where( x => x.IsValid() && !x.Flags.HasFlag( GameObjectFlags.NotSaved ) ).Select( x => x.Id ).ToHashSet();
var root = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( root, "output/map-daylight-20261017/captures" );
System.IO.Directory.CreateDirectory( folder );
var prefab = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText(
    System.IO.Path.Combine( root, "Assets/prefabs/player/cameras/default_player_camera.prefab" ) ) );
var sources = prefab["RootObject"]["Components"].AsArray();
using var scope = scene.Push();
var review = new GameObject( false, "Temporary daylight review" );
review.Flags = GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked | GameObjectFlags.Hidden;
T Copy<T>() where T : Component, new()
{
    var source = sources.FirstOrDefault( x => x["__type"]?.GetValue<string>() == "Sandbox." + typeof(T).Name );
    if ( source is null ) return null;
    var json = source.DeepClone().AsObject();
    json.Remove( "__guid" );
    var component = review.Components.Create<T>();
    component.DeserializeImmediately( json );
    return component;
}
try
{
    var camera = Copy<CameraComponent>();
    camera.IsMainCamera = false;
    camera.Priority = -100;
    Copy<Bloom>();
    var tone = Copy<Tonemapping>();
    Copy<Sharpen>();
    Copy<AmbientOcclusion>();
    Copy<ColorAdjustments>();
    Copy<Vignette>();
    var system = scene.GetSystem<PostProcessSystem>();
    var update = typeof( PostProcessSystem ).GetMethod( "UpdateCamera", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic );
    if ( update is null ) throw new Exception( "Installed post-process update method missing." );
    var results = new System.Collections.Generic.List<object>();
    foreach ( var item in config["views"].AsArray() )
    {
        cancellationToken.ThrowIfCancellationRequested();
        review.WorldPosition = Vector3.Parse( item["position"].GetValue<string>() );
        review.WorldRotation = Rotation.From( Angles.Parse( item["angles"].GetValue<string>() ) );
        camera.FieldOfView = item["fov"].GetValue<float>();
        review.Enabled = true;
        // Settle auto exposure and streaming before the retained frame.
        for ( var frame = 0; frame < 160; frame++ )
        {
            cancellationToken.ThrowIfCancellationRequested();
            if ( Game.IsPlaying || Editor.SceneEditorSession.Active != session )
                throw new Exception( "Editor state changed during capture." );
            update.Invoke( system, new object[] { camera } );
            using var warm = new Bitmap( 640, 360 );
            camera.RenderToBitmap( warm, false );
            await Task.Delay( 16, cancellationToken );
        }
        update.Invoke( system, new object[] { camera } );
        using var bitmap = new Bitmap( 1280, 720 );
        camera.RenderToBitmap( bitmap, false );
        var path = System.IO.Path.Combine( folder, config["slug"].GetValue<string>() + "-" +
            item["name"].GetValue<string>() + "-" + config["suffix"].GetValue<string>() + ".png" );
        System.IO.File.WriteAllBytes( path, bitmap.ToPng() );
        results.Add( new { path, Position = review.WorldPosition.ToString(), Rotation = review.WorldRotation.Angles().ToString(),
            camera.FieldOfView, camera.EnablePostProcessing, Tone = tone.Mode.ToString(), SettledFrames = 160 } );
    }
    return new { results, wasDirty };
}
finally
{
    review.Destroy();
    await Task.Delay( 50 );
    if ( session.HasUnsavedChanges != wasDirty )
        throw new Exception( "Temporary capture changed scene dirty state." );
    if ( !originalIds.SetEquals( scene.GetAllObjects( true ).Where( x => x.IsValid() && !x.Flags.HasFlag( GameObjectFlags.NotSaved ) ).Select( x => x.Id ) ) )
        throw new Exception( "Temporary camera cleanup changed scene objects." );
}

