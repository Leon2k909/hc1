using Sandbox;
using Editor;
using System.IO;
using System.Linq;
using System.Text.Json;

/// <summary>Exports the current Ridgeback terrain for the river mesh builder without changing terrain data.</summary>
public static class RidgebackRiverTools
{
    [ConCmd( "ridgeback_river_validate" )]
    public static void Validate()
    {
        var scene = Game.ActiveScene;
        var models = scene.GetAllComponents<ModelRenderer>().Where( m => m.Model?.Name.Contains( "ridgeback/river/" ) == true ).ToArray();
        if ( models.Length != 21 || models.Any( m => m.Model.IsError ) )
            throw new System.Exception( $"Expected 21 valid river models; got {models.Length}" );
        if ( models.Any( m => m.GameObject.Components.Get<Collider>() is not null ) )
            throw new System.Exception( "Water must not block crossings" );
        // Also apply the scene's intended shadow option to the already running preview.
        foreach ( var model in models ) model.RenderType = ModelRenderer.ShadowRenderType.Off;
        var folder = Path.Combine( Project.Current.GetRootPath(), "output", "river" );
        using var report = JsonDocument.Parse( File.ReadAllText( Path.Combine( folder, "river-report.json" ) ) );
        var results = new System.Collections.Generic.List<object>();
        foreach ( var sample in report.RootElement.GetProperty( "samples" ).EnumerateArray() )
        {
            var x = sample.GetProperty( "x" ).GetSingle();
            var y = sample.GetProperty( "y" ).GetSingle();
            if ( System.Math.Abs( y ) > 30000 ) continue;
            var trace = scene.Trace.Ray( new Vector3( x, y, 14000 ), new Vector3( x, y, -3000 ) ).Run();
            if ( !trace.Hit ) throw new System.Exception( "Missing riverbed collision" );
            var ground = trace.EndPosition;
            var depth = sample.GetProperty( "water" ).GetSingle() - ground.z;
            results.Add( new { x, y, ground = ground.z, depth } );
            if ( depth < 10 || depth > 48 ) throw new System.Exception( $"Water depth {depth} at {x}, {y} is outside wading range" );
        }
        File.WriteAllText( Path.Combine( folder, "river-validation.json" ), JsonSerializer.Serialize( results, new JsonSerializerOptions { WriteIndented = true } ) );
        Log.Info( $"RIVER PASS: {models.Length} valid water meshes, {results.Count} riverbed collision/depth checks, no blocking water colliders." );
    }

    [ConCmd( "ridgeback_river_compile" )]
    public static void Compile()
    {
        var root = Project.Current.GetRootPath();
        AssetSystem.RegisterFile( Path.Combine( root, "Assets/materials/water/ridgeback_river.vmat" ) )?.Compile( true );
        var folder = Path.Combine( root, "Assets/models/maps/ridgeback/river" );
        foreach ( var file in Directory.GetFiles( folder ).Where( f => f.EndsWith( ".obj" ) || f.EndsWith( ".mtl" ) ) )
            AssetSystem.RegisterFile( file );
        foreach ( var file in Directory.GetFiles( folder, "*.vmdl" ) )
            AssetSystem.RegisterFile( file )?.Compile( true );
        AssetSystem.RegisterFile( Path.Combine( root, "Assets/scenes/maps/Ridgeback/ridgeback.scene" ) )?.Compile( true );
        Log.Info( "RIVER: requested compilation of river models and Ridgeback scene" );
    }

    [ConCmd( "ridgeback_river_export" )]
    public static void Export()
    {
        var terrain = Game.ActiveScene.GetAllComponents<Terrain>().First();
        var storage = terrain.Storage;
        if ( !storage.ResourcePath.EndsWith( "ridgeback.terrain", System.StringComparison.OrdinalIgnoreCase ) )
            throw new System.Exception( "Load Ridgeback before exporting its riverbed" );
        var folder = Path.Combine( Project.Current.GetRootPath(), "output", "river" );
        Directory.CreateDirectory( folder );
        using ( var writer = new BinaryWriter( File.Create( Path.Combine( folder, "terrain-heights.bin" ) ) ) )
            foreach ( var height in storage.HeightMap ) writer.Write( height );
        File.WriteAllText( Path.Combine( folder, "terrain-info.json" ), System.Text.Json.JsonSerializer.Serialize( new
        {
            resolution = storage.Resolution, size = storage.TerrainSize, height = storage.TerrainHeight,
            x = terrain.WorldPosition.x, y = terrain.WorldPosition.y, z = terrain.WorldPosition.z
        } ) );
        Log.Info( $"RIVER: exported {storage.HeightMap.Length} terrain samples to {folder}" );
    }

    [ConCmd( "ridgeback_river_capture" )]
    public static void Capture( float x = -4000, float y = 8000, float z = 7500, float tx = 6000, float ty = 0, float tz = 0, string name = "river-aerial" )
    {
        var scene = Game.ActiveScene;
        using var scope = scene.Push();
        var obj = scene.CreateObject();
        try
        {
            obj.Name = "River preview camera";
            obj.WorldPosition = new Vector3( x, y, z );
            obj.WorldRotation = Rotation.LookAt( new Vector3( tx, ty, tz ) - obj.WorldPosition );
            var camera = obj.AddComponent<CameraComponent>();
            camera.ZFar = 90000;
            camera.FieldOfView = 75;
            using var bitmap = new Bitmap( 1600, 900 );
            camera.RenderToBitmap( bitmap, false );
            var folder = Path.Combine( Project.Current.GetRootPath(), "output", "river" );
            Directory.CreateDirectory( folder );
            File.WriteAllBytes( Path.Combine( folder, name + ".png" ), bitmap.ToPng() );
            Log.Info( $"RIVER: captured {name}" );
        }
        finally { obj.Destroy(); }
    }
}
