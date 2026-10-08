using Editor;
using Sandbox;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Isolated Lowtide skyline captures; leaves the current editor scene and match untouched.</summary>
public static class Hc1LowtideShipyardQa
{
	private static bool _rendering;
	private static readonly HashSet<string> Visual = new( StringComparer.OrdinalIgnoreCase )
	{
		"Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes"
	};

	[ConCmd( "hc1_lowtide_shipyard_shot" )]
	public static async void Shot( string name = "front", float ee = 0, float en = -1480, float ez = 64,
		float te = 0, float tn = -11000, float tz = 1050, float fov = 85, float exposure = 2 )
	{
		if ( _rendering ) return;
		_rendering = true;
		var scene = new Scene();
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/shipyard" );
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
				var holder = new GameObject( false, "Lowtide Shipyard QA Camera" );
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
			var elapsed = 0f;
			using ( scene.Push() )
			{
				scene.EditorTick( elapsed += .016f, .016f );
				camera.RenderToBitmap( bitmap );
			}
			await Task.Delay( 4500 );
			for ( var frame = 0; frame < 20; frame++ )
			{
				using ( scene.Push() )
				{
					scene.EditorTick( elapsed += .016f, .016f );
					camera.RenderToBitmap( bitmap );
				}
				await Task.Delay( 32 );
			}
			File.WriteAllBytes( Path.Combine( folder, name + ".png" ), bitmap.ToPng() );
			var material = Material.Load( "materials/lowtide/shipyard/lt_shipyard_panorama.vmat" );
			var texture = material.GetTexture( "g_tColor" );
			var report = new List<string>
			{
				$"view={name}, eye-plan={ee},{en},{ez}, target-plan={te},{tn},{tz}, fov={fov}, exposure={exposure}",
				$"material-error={material.IsError}, shader={material.ShaderName}, alpha-test={material.GetFeature( "F_ALPHA_TEST" )}, self-illum={material.GetFeature( "F_SELF_ILLUM" )}",
				$"colour-dimensions={texture?.Width}x{texture?.Height}, mips={texture?.Mips}",
				$"backdrop renderers={scene.GetAllComponents<ModelRenderer>().Count( x => x.Model?.ResourcePath == "models/maps/lowtide/lowtide_backdrop.vmdl" )}",
				$"backdrop colliders={scene.GetAllComponents<ModelCollider>().Count( x => x.Model?.ResourcePath == "models/maps/lowtide/lowtide_backdrop.vmdl" )}"
			};
			File.WriteAllLines( Path.Combine( folder, name + ".txt" ), report );
			Log.Info( $"Lowtide shipyard capture finished: {name}" );
		}
		catch ( Exception e ) { File.WriteAllText( Path.Combine( folder, name + "-error.txt" ), e.ToString() ); Log.Warning( e ); }
		finally { scene.Destroy(); _rendering = false; }
	}

	private static Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
}
