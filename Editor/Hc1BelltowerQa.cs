using Editor;
using Sandbox;
using Facepunch;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

public static class Hc1BelltowerQa
{
	// The scene's top-level objects that make the picture (`hc1_belltower_views`): everything else is gameplay.
	private static readonly HashSet<string> Visual = new( StringComparer.OrdinalIgnoreCase )
	{
		"Sun", "Sky", "Fog", "Town", "Trees and planting", "Lights", "Street Detail", "Ambient", "Reflections",
		"Indirect Light", "Look", "Volumetric Fog",
	};

	// ( name, eye, target, fov ), in plan ( east, north, up ): world is ( north, -east, up ).
	private static readonly (string Name, Vector3 Eye, Vector3 Target, float Fov)[] Views =
	{
		( "market", new( -1760, 1275, 64 ), new( 0, 1240, 170 ), 80 ),
		( "market_tower", new( -1150, 1170, 64 ), new( 0, 825, 640 ), 80 ),
		( "west_street", new( -1800, 125, 64 ), new( -400, 160, 130 ), 80 ),
		( "square", new( -560, -320, 64 ), new( 0, 700, 330 ), 85 ),
		( "road", new( -2075, -760, 64 ), new( -2075, 1700, 150 ), 80 ),
		( "gate", new( -1960, -330, 64 ), new( -2340, 0, 170 ), 80 ),
		( "alley", new( -1325, 380, 64 ), new( -1325, 1100, 130 ), 80 ),
		( "terrace", new( -1760, -950, 64 ), new( 0, -950, 110 ), 80 ),
		( "gardens", new( -1560, -1380, 16 ), new( 0, -1000, 120 ), 80 ),
		( "aerial", new( -2900, -2600, 1500 ), new( 0, 300, 0 ), 70 ),
		( "out_south", new( -1600, -1430, 40 ), new( -1600, -9000, -1400 ), 80 ),
	};

	private static (string Name, Vector3 Eye, Vector3 Target, float Fov)? _shot;

	private static Vector3 World( Vector3 plan ) => new( plan.y, -plan.x, plan.z );

	/// <summary>
	/// Belltower's views, offscreen, from the map's own scene file: its town, planting, lights, sun, sky, fog and look are
	/// copied into a scene of their own, so the editor's open scene isn't touched. The camera has the player camera's
	/// tonemapping and bloom at a fixed exposure. Writes output/belltower/views/&lt;view&gt;.png.
	/// </summary>
	[ConCmd( "hc1_belltower_views" )]
	public static async void RenderViews( string filter = "", float exposure = 1f )
	{
		if ( rendering ) return;
		rendering = true;
		var folder = Path.Combine( Folder, "views" );
		Directory.CreateDirectory( folder );
		var scene = new Scene();
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Belltower/belltower.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
			{
				var name = item["Name"]?.GetValue<string>();
				if ( name is not null && Visual.Contains( name ) ) objects.Add( item.DeepClone() );
			}
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				var holder = new GameObject( false, "QA Camera" );
				camera = holder.Components.Create<CameraComponent>();
				camera.ZNear = 4;
				camera.ZFar = 100000;
				var tonemap = holder.Components.Create<Tonemapping>();
				tonemap.Mode = Tonemapping.TonemappingMode.ACES;
				tonemap.AutoExposureEnabled = false;
				tonemap.ExposureCompensation = exposure;
				var bloom = holder.Components.Create<Bloom>();
				bloom.Mode = SceneCamera.BloomAccessor.BloomMode.Additive;
				bloom.Strength = 0.15f;
				bloom.Threshold = 1.33f;
				holder.Enabled = true;
				scene.EditorTick( .016f, .016f );
			}
			var views = _shot is { } one ? new[] { one } : Views;
			_shot = null;
			using var bitmap = new Bitmap( 1600, 900 );
			var first = true;
			foreach ( var view in views )
			{
				if ( !string.IsNullOrEmpty( filter ) && !view.Name.Contains( filter, StringComparison.OrdinalIgnoreCase ) ) continue;
				var eye = World( view.Eye );
				using ( scene.Push() )
				{
					camera.WorldPosition = eye;
					camera.WorldRotation = Rotation.LookAt( World( view.Target ) - eye );
					camera.FieldOfView = view.Fov;
					scene.EditorTick( .016f, .016f );
					camera.RenderToBitmap( bitmap );
				}
				// Textures stream in once they're seen: render again when they have.
				await Task.Delay( first ? 4000 : 1500 );
				first = false;
				using ( scene.Push() ) camera.RenderToBitmap( bitmap );
				File.WriteAllBytes( Path.Combine( folder, view.Name + ".png" ), bitmap.ToPng() );
			}
			Log.Info( $"Belltower views: {objects.Count} objects, written to {folder}" );
		}
		catch ( Exception e ) { Log.Warning( $"Belltower views failed: {e}" ); }
		finally { scene.Destroy(); rendering = false; }
	}

	/// <summary>One view: `hc1_belltower_shot name east north up east north up [fov] [exposure]`, eye then target in plan.</summary>
	[ConCmd( "hc1_belltower_shot" )]
	public static void RenderShot( string name, float ee, float en, float ez, float te, float tn, float tz, float fov = 80f, float exposure = 1f )
	{
		_shot = (name, new Vector3( ee, en, ez ), new Vector3( te, tn, tz ), fov);
		RenderViews( name, exposure );
	}

	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/belltower" );
	private static bool rendering;

	[ConCmd( "hc1_belltower_preview" )]
	public static async void Preview()
	{
		if ( rendering ) return;
		rendering = true;
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Belltower/belltower.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
				if ( new[] { "Town", "Trees and planting", "Sun", "Sky", "Fog", "Lights" }.Contains( item["Name"]?.GetValue<string>() ) ) objects.Add( item.DeepClone() );
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				camera = new GameObject( true, "QA Camera" ).Components.Create<CameraComponent>();
				camera.FieldOfView = 75; camera.ZNear = 1;
				scene.EditorTick( .016f, .016f );
			}
			await Task.Delay( 1000 );
			var views = new[] {
				("cart", new Vector3(140,1620,65), new Vector3(300,1620,28)),
				("barrels", new Vector3(0,1760,52), new Vector3(-55,1815,22)),
				("orchard", new Vector3(-1240,1110,25), new Vector3(-1370,1290,80)),
				("square", new Vector3(-450,650,70), new Vector3(350,0,85)) };
			using var bitmap = new Bitmap( 1600, 900 );
			foreach ( var (name, eye, target) in views )
			{
				using ( scene.Push() )
				{
					camera.WorldPosition = eye; camera.WorldRotation = Rotation.LookAt( target-eye );
					scene.EditorTick( 1f, .016f ); camera.RenderToBitmap( bitmap );
				}
				await Task.Delay( 150 );
				using ( scene.Push() ) camera.RenderToBitmap( bitmap );
				File.WriteAllBytes( Path.Combine( Folder, name+".png" ), bitmap.ToPng() );
			}
			Log.Info( $"Belltower preview: {Folder}" );
		}
		catch ( Exception e ) { Log.Warning( $"Belltower preview failed: {e}" ); }
		finally { scene.Destroy(); rendering = false; }
	}

	[ConCmd( "hc1_belltower_assets" )]
	public static void Assets()
	{
		Directory.CreateDirectory( Folder );
		var paths = new[] { "models/sbox_props/trees/oak/tree_oak_small_a.vmdl", "models/sbox_props/trees/oak/tree_oak_medium_a.vmdl",
			"models/sbox_props/shrubs/beech/beech_bush_small.vmdl", "models/sbox_props/shrubs/beech/beech_bush_medium_wall.vmdl" };
		var data = paths.Select( p => { var m = Model.Load( p ); return new { path = p, error = m.IsError,
			min = new[] { m.Bounds.Mins.x, m.Bounds.Mins.y, m.Bounds.Mins.z }, max = new[] { m.Bounds.Maxs.x, m.Bounds.Maxs.y, m.Bounds.Maxs.z } }; } );
		File.WriteAllText( Path.Combine( Folder, "assets.json" ), JsonSerializer.Serialize( data ) );
		var material = Material.Load( "materials/plaster/beige_wall_001.vmat" );
		File.WriteAllText( Path.Combine( Folder, "plaster.json" ), JsonSerializer.Serialize(
			new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "TextureColor", "TextureNormal" }
			.ToDictionary( x => x, x => material.GetTexture( x )?.ResourcePath ) ) );
	}

	[ConCmd( "hc1_belltower_penetration" )]
	public static void Penetration()
	{
		Directory.CreateDirectory( Folder );
		var results = new System.Collections.Generic.List<string>();
		var scene = new Scene();
		try
		{
			using ( scene.Push() )
			{
				foreach ( var test in new[] { ("default", 12f, false), ("brick", 12f, false), ("concrete", 24f, false),
					("wood", 1f, true), ("wood", 12f, false), ("glass", .25f, true), ("metal", 1f, false) } )
				{
					var wall = new GameObject( true, "Wall" );
					var collider = wall.Components.Create<BoxCollider>();
					collider.Center = new Vector3( 100, 0, 0 ); collider.Scale = new Vector3( test.Item2, 100, 100 );
					collider.Surface = Surface.FindByName( test.Item1 );
					var target = new GameObject( true, "Target" );
					var box = target.Components.Create<BoxCollider>(); box.Center = new Vector3( 150, 0, 0 ); box.Scale = new Vector3( 5, 30, 30 );
					scene.EditorTick( .016f, .016f );
					var all = scene.Trace.Ray( Vector3.Zero, new Vector3( 200, 0, 0 ) ).RunAll().ToArray();
					var hits = Shootable.ResolvePenetration( scene, all, 32f ).ToArray();
					var through = hits.Any( x => x.GameObject == target );
					results.Add( $"{(through == test.Item3 && hits.Length > 0 ? "PASS" : "FAIL")} {test.Item1} thickness={test.Item2} through={through} hits={hits.Length} surface={all.FirstOrDefault().Surface?.ResourceName}" );
					wall.Destroy(); target.Destroy(); scene.ProcessDeletes();
				}
			}
		}
		finally { scene.Destroy(); }
		File.WriteAllLines( Path.Combine( Folder, "penetration.txt" ), results );
	}
}
