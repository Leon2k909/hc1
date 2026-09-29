using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

public static class Hc1BelltowerQa
{
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
