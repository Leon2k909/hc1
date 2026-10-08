using Editor;
using Sandbox;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Railhead captures from an isolated copy of its visual scene. No editor or match state is changed.</summary>
public static class Hc1RailheadQa
{
	private static bool rendering;
	private static readonly HashSet<string> Visual = new( StringComparer.OrdinalIgnoreCase )
	{
		"Sun", "Sky", "Fog", "Look", "Station", "Trees", "Lights", "Reflection Probes"
	};
	private static (string Name, Vector3 Eye, Vector3 Target, float Fov)[] Views() => new (string, Vector3, Vector3, float)[]
	{
		( "buffer", new( -424, 590, 30 ), new( -424, 770, 14 ), 55 ),
		( "buffer_side", new( -495, 590, 34 ), new( -416, 795, 14 ), 65 ),
		( "concourse", new( -40, 1230, 64 ), new( 60, -1300, 230 ), 85 ),
		( "platform", new( 510, 475, 64 ), new( 460, -1300, 130 ), 80 )
	};
	private static Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
	private static (string Name, Vector3 Eye, Vector3 Target, float Fov)? shot;

	[ConCmd( "hc1_railhead_materials" )]
	public static void Materials()
	{
		var lines = new System.Text.StringBuilder();
		foreach ( var name in new[] { "rw_buffer_led", "rw_signal_red", "rw_buffer_contact", "rw_buffer_beam" } )
		{
			var material = Material.Load( "materials/railhead/" + name + ".vmat" );
			lines.AppendLine( $"{name}: path={material.ResourcePath}, error={material.IsError}, shader={material.ShaderName}, selfillum={material.GetFeature( "F_SELF_ILLUM" )}, metaltexture={material.GetFeature( "F_METALNESS_TEXTURE" )}, tint={material.GetVector4( "g_vSelfIllumTint" )}, colour={material.GetTexture( "g_tColor" )}, mask={material.GetTexture( "g_tSelfIllumMask" )}" );
		}
		foreach ( var material in Model.Load( "models/maps/railhead/railhead_dress_west.vmdl" ).Materials )
			if ( material.Name.Contains( "buffer" ) ) lines.AppendLine( $"Model material: {material.Name}, path={material.ResourcePath}, error={material.IsError}, selfillum={material.GetFeature( "F_SELF_ILLUM" )}" );
		Directory.CreateDirectory( Path.Combine( Project.Current.GetRootPath(), "output/railhead/buffer-pass" ) );
		File.WriteAllText( Path.Combine( Project.Current.GetRootPath(), "output/railhead/buffer-pass/materials.txt" ), lines.ToString() );
	}

	[ConCmd( "hc1_railhead_shot" )]
	public static void Shot( string name, float ee, float en, float ez, float te, float tn, float tz, float fov = 55f, float exposure = 1f )
	{
		shot = (name, new( ee, en, ez ), new( te, tn, tz ), fov);
		Render( name, exposure );
	}

	[ConCmd( "hc1_railhead_views" )]
	public static async void Render( string filter = "", float exposure = 1f )
	{
		if ( rendering ) return;
		rendering = true;
		var scene = new Scene();
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/railhead/buffer-pass" );
		Directory.CreateDirectory( folder );
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Railhead/railhead.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
				if ( item["Name"] is { } name && Visual.Contains( name.GetValue<string>() ) ) objects.Add( item.DeepClone() );
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				var holder = new GameObject( false, "Railhead QA Camera" );
				camera = holder.Components.Create<CameraComponent>();
				camera.ZNear = 1;
				camera.ZFar = 100000;
				camera.EnablePostProcessing = true;
				var tonemap = holder.Components.Create<Tonemapping>();
				tonemap.Mode = Tonemapping.TonemappingMode.ACES;
				tonemap.AutoExposureEnabled = false;
				tonemap.ExposureCompensation = exposure;
				var bloom = holder.Components.Create<Bloom>();
				bloom.Mode = SceneCamera.BloomAccessor.BloomMode.Additive;
				bloom.Strength = 0.08f;
				bloom.Threshold = 1.6f;
				holder.Enabled = true;
			}
			using var bitmap = new Bitmap( 1400, 1123 );
			float elapsed = 0;
			var views = shot is { } one ? new[] { one } : Views();
			shot = null;
			foreach ( var view in views )
			{
				if ( !string.IsNullOrEmpty( filter ) && !view.Name.Contains( filter, StringComparison.OrdinalIgnoreCase ) ) continue;
				using ( scene.Push() )
				{
					camera.WorldPosition = World( view.Eye );
					camera.WorldRotation = Rotation.LookAt( World( view.Target ) - camera.WorldPosition );
					camera.FieldOfView = view.Fov;
					scene.EditorTick( elapsed += .016f, .016f );
					camera.RenderToBitmap( bitmap );
				}
				await Task.Delay( 4500 );
				// Let dynamic reflections and temporal effects settle as they do in a live match.
				for ( int frame = 0; frame < 16; frame++ )
				{
					using ( scene.Push() )
					{
						scene.EditorTick( elapsed += .016f, .016f );
						camera.RenderToBitmap( bitmap );
					}
					await Task.Delay( 32 );
				}
				File.WriteAllBytes( Path.Combine( folder, view.Name + ".png" ), bitmap.ToPng() );
			}
			var diagnostics = new System.Text.StringBuilder();
			foreach ( var probe in scene.GetAllComponents<EnvmapProbe>() )
				diagnostics.AppendLine( $"{probe.GameObject.Name}: mode={probe.Mode}, range={probe.MaxDistance}, custom={probe.Texture}, baked={probe.BakedTexture}" );
			foreach ( var volume in scene.GetAllComponents<PostProcessVolume>() )
				diagnostics.AppendLine( $"{volume.GameObject.Name}: active={volume.Active}, infinite={volume.IsInfinite}, blend={volume.BlendWeight}" );
			File.WriteAllText( Path.Combine( folder, "lighting.txt" ), diagnostics.ToString() );
			Log.Info( $"Railhead views written to {folder}" );
		}
		catch ( Exception e ) { Log.Warning( $"Railhead views failed: {e}" ); }
		finally { scene.Destroy(); rendering = false; }
	}
}
