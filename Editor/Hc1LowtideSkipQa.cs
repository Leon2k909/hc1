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

	private static Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
}
