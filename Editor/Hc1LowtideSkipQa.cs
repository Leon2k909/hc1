using Editor;
using Sandbox;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Render Lowtide's skip in an isolated scene, without changing the user's editor or match.</summary>
public static class Hc1LowtideSkipQa
{
	private static bool rendering;
	private static readonly HashSet<string> Visual = new( StringComparer.OrdinalIgnoreCase )
	{
		"Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes"
	};

	[ConCmd( "hc1_lowtide_skip_shot" )]
	public static async void Shot( string name = "skip", float ee = 660, float en = -620, float ez = 64,
		float te = 860, float tn = -560, float tz = 12, float fov = 48, float exposure = 0 )
	{
		if ( rendering ) return;
		rendering = true;
		var scene = new Scene();
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/skip-pass" );
		Directory.CreateDirectory( folder );
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Lowtide/lowtide.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
				if ( item["Name"] is { } label && Visual.Contains( label.GetValue<string>() ) ) objects.Add( item.DeepClone() );
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				var holder = new GameObject( false, "Lowtide Skip QA Camera" );
				camera = holder.Components.Create<CameraComponent>();
				camera.WorldPosition = World( new( ee, en, ez ) );
				camera.WorldRotation = Rotation.LookAt( World( new( te, tn, tz ) ) - camera.WorldPosition );
				camera.FieldOfView = fov;
				camera.ZNear = 1;
				camera.ZFar = 100000;
				camera.EnablePostProcessing = true;
				var tonemap = holder.Components.Create<Tonemapping>();
				tonemap.Mode = Tonemapping.TonemappingMode.ACES;
				tonemap.AutoExposureEnabled = false;
				tonemap.ExposureCompensation = exposure;
				holder.Enabled = true;
			}
			using var bitmap = new Bitmap( 1672, 941 );
			float elapsed = 0;
			using ( scene.Push() )
			{
				scene.EditorTick( elapsed += .016f, .016f );
				camera.RenderToBitmap( bitmap );
			}
			await Task.Delay( 4500 );
			for ( int frame = 0; frame < 20; frame++ )
			{
				using ( scene.Push() )
				{
					scene.EditorTick( elapsed += .016f, .016f );
					camera.RenderToBitmap( bitmap );
				}
				await Task.Delay( 32 );
			}
			File.WriteAllBytes( Path.Combine( folder, name + ".png" ), bitmap.ToPng() );
			var report = new System.Text.StringBuilder();
			foreach ( var paint in new[] { "lt_skip", "lt_skip_end", "lt_skip_inner", "lt_skip_floor", "lt_skip_trim", "lt_skip_weld" } )
			{
				var material = Material.Load( "materials/lowtide/" + paint + ".vmat" );
				report.AppendLine( $"{paint}: error={material.IsError}, shader={material.ShaderName}, metalTexture={material.GetFeature( "F_METALNESS_TEXTURE" )}, colour={material.GetTexture( "g_tColor" )}, normal={material.GetTexture( "g_tNormal" )}, roughness={material.GetTexture( "g_tRoughness" )}" );
			}
			File.WriteAllText( Path.Combine( folder, "materials.txt" ), report.ToString() );
			Log.Info( $"Lowtide skip view written: {name}" );
		}
		catch ( Exception e ) { Log.Warning( $"Lowtide skip view failed: {e}" ); }
		finally { scene.Destroy(); rendering = false; }
	}

	[ConCmd( "hc1_lowtide_skip_collision_qa" )]
	public static void Collision( string name = "collision" )
	{
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/skip-pass" );
		Directory.CreateDirectory( folder );
		var scene = new Scene();
		var report = new System.Text.StringBuilder();
		var checks = 0;
		var failures = 0;
		void Check( string label, bool passed, SceneTraceResult trace )
		{
			checks++;
			if ( !passed ) failures++;
			report.AppendLine( $"{(passed ? "PASS" : "FAIL")} {label}: hit={trace.Hit}, solid={trace.StartedSolid}, end={trace.EndPosition}, normal={trace.Normal}" );
		}
		try
		{
			using ( scene.Push() )
			{
				foreach ( var side in new[] { "east", "west" } )
				{
					var model = Model.Load( $"models/maps/lowtide/lowtide_dress_{side}.vmdl" );
					if ( model.IsError ) throw new InvalidOperationException( $"{side} model failed to load" );
					var holder = new GameObject( false, side );
					var collider = holder.Components.Create<ModelCollider>();
					collider.Model = model;
					collider.Static = true;
					holder.Enabled = true;
				}
				scene.EditorTick( .016f, .016f );
				// Match the player's 32 x 32 x 64 movement box, with its origin at the feet.
				var player = new BBox( new Vector3( -16, -16, 0 ), new Vector3( 16, 16, 64 ) );
				foreach ( var side in new[] { -1, 1 } )
				{
					var origin = World( new( side * 860, -560, 0 ) );
					Vector3 At( float length, float width, float z ) => origin + new Vector3( length, -width, z );
					foreach ( var length in new[] { -24f, 0f, 24f } )
					foreach ( var width in new[] { -10f, 0f, 10f } )
					{
						var ray = scene.Trace.Ray( At( length, width, 80 ), At( length, width, -8 ) ).Run();
						Check( $"{side} floor {length},{width}", ray.Hit && MathF.Abs( ray.EndPosition.z - 4.4f ) < .2f, ray );
						var drop = scene.Trace.Ray( At( length, width, 80 ), At( length, width, -8 ) ).Size( player ).Run();
						Check( $"{side} player drop {length},{width}", drop.Hit && !drop.StartedSolid && MathF.Abs( drop.EndPosition.z - 4.4f ) < .2f && drop.Normal.z > .99f, drop );
					}
					foreach ( var rim in new[] { new Vector2( -72, 0 ), new Vector2( 72, 0 ), new Vector2( 0, -38 ), new Vector2( 0, 38 ) } )
					{
						var trace = scene.Trace.Ray( At( rim.x, rim.y, 80 ), At( rim.x, rim.y, 30 ) ).Run();
						Check( $"{side} rim {rim}", trace.Hit && MathF.Abs( trace.EndPosition.z - 39.95f ) < .2f, trace );
					}
					foreach ( var z in new[] { 12f, 28f } )
					foreach ( var sign in new[] { -1f, 1f } )
					foreach ( var end in new[] { false, true } )
					{
						var target = end ? At( sign * 90, 0, z ) : At( 0, sign * 50, z );
						var trace = scene.Trace.Ray( At( 0, 0, z ), target ).Run();
						var expected = end ? 52 + (z - 4) * 20 / 34 - .37f : 34 + (z - 4) * 4 / 34 - .35f;
						Check( $"{side} wall end={end} sign={sign} z={z}", trace.Hit && !trace.StartedSolid && MathF.Abs( trace.Distance - expected ) < .3f, trace );
					}
					var opening = scene.Trace.Ray( At( 0, 0, 6 ), At( 0, 0, 80 ) ).Size( player ).Run();
					Check( $"{side} player can leave opening", !opening.Hit && !opening.StartedSolid, opening );
				}
			}
			report.AppendLine( $"checks={checks}, failures={failures}" );
			Log.Info( $"Lowtide skip collision QA: {checks} checks, {failures} failures" );
		}
		catch ( Exception e ) { report.AppendLine( $"ERROR: {e}" ); Log.Warning( e ); }
		finally
		{
			scene.Destroy();
			File.WriteAllText( Path.Combine( folder, name + ".txt" ), report.ToString() );
		}
	}

	private static Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
}
