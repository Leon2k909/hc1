using Editor;
using Sandbox;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Isolated lantern daylight and lighting comparisons; never changes the map's atmosphere.</summary>
public static class Hc1LowtideLanternQa
{
	private static bool _rendering;
	private static readonly HashSet<string> Visual = new( StringComparer.OrdinalIgnoreCase )
	{
		"Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes"
	};
	private const string Prefix = "Bridge Lantern ";
	private static string Root => Project.Current.GetRootPath();

	[ConCmd( "hc1_lowtide_lantern_shot" )]
	public static async void Shot( string name = "day", float ee = 445, float en = 1325, float ez = 136,
		float te = 240, float tn = 1159, float tz = 135, float fov = 80, float exposure = 2,
		bool night = false, bool lightsOn = true )
	{
		if ( _rendering ) return;
		_rendering = true;
		var scene = new Scene();
		var folder = Path.Combine( Root, "output/lowtide/lanterns-pass" );
		Directory.CreateDirectory( folder );
		try
		{
			var root = ReadScene();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
			{
				if ( item["Name"] is not { } label || !Visual.Contains( label.GetValue<string>() ) ) continue;
				var copy = item.DeepClone();
				if ( label.GetValue<string>() == "Lights" )
					foreach ( var light in copy["Children"].AsArray() )
						if ( light["Name"].GetValue<string>().StartsWith( Prefix ) ) light["Enabled"] = lightsOn;
				if ( night && label.GetValue<string>() == "Sun" )
				{
					copy["Components"][0]["LightColor"] = "0,0,0,1";
					copy["Components"][0]["SkyColor"] = "0.008,0.012,0.022,1";
				}
				if ( night && label.GetValue<string>() == "Sky" ) copy["Components"][0]["Tint"] = "0.025,0.035,0.06,1";
				if ( night && label.GetValue<string>() == "Fog" ) copy["Enabled"] = false;
				objects.Add( copy );
			}
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				var holder = new GameObject( false, "Lowtide Lantern QA Camera" );
				camera = holder.Components.Create<CameraComponent>();
				camera.WorldPosition = World( new( ee, en, ez ) );
				camera.WorldRotation = Rotation.LookAt( World( new( te, tn, tz ) ) - camera.WorldPosition );
				camera.FieldOfView = fov;
				camera.ZNear = .25f;
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
			var report = new List<string> { $"view={name}, night={night}, lights-on={lightsOn}" };
			foreach ( var paint in new[] { "iron", "glass", "bulb", "brass" } )
			{
				var material = Material.Load( $"materials/lowtide/lanterns/lt_lantern_{paint}.vmat" );
				report.Add( $"material={paint}, error={material.IsError}, shader={material.ShaderName}" );
			}
			foreach ( var light in scene.GetAllComponents<PointLight>().Where( p => p.GameObject.Name.StartsWith( Prefix ) ) )
				report.Add( $"light={light.GameObject.Name}, enabled={light.Enabled}, position={light.WorldPosition}, color={light.LightColor}, radius={light.Radius}, shadows={light.Shadows}" );
			File.WriteAllLines( Path.Combine( folder, name + ".txt" ), report );
			Log.Info( $"Lowtide lantern capture finished: {name}" );
		}
		catch ( Exception e ) { File.WriteAllText( Path.Combine( folder, name + ".error.txt" ), e.ToString() ); Log.Warning( e ); }
		finally { scene.Destroy(); _rendering = false; }
	}

	[ConCmd( "hc1_lowtide_lantern_apply_live" )]
	public static void ApplyLive()
	{
		var scene = Game.ActiveScene;
		if ( scene is null || !scene.GetAllComponents<ModelRenderer>().Any( r => r.Model?.ResourcePath == "models/maps/lowtide/lowtide_fleet.vmdl" ) ) return;
		var root = ReadScene();
		var lights = root["GameObjects"].AsArray().First( g => g["Name"]?.GetValue<string>() == "Lights" )["Children"].AsArray();
		using ( scene.Push() )
		{
			foreach ( var data in lights.Where( g => g["Name"].GetValue<string>().StartsWith( Prefix ) ) )
			{
				var name = data["Name"].GetValue<string>();
				var light = scene.GetAllComponents<PointLight>().FirstOrDefault( p => p.GameObject.Name == name );
				if ( light is null ) light = new GameObject( true, name ).Components.Create<PointLight>();
				var props = data["Components"][0];
				light.WorldPosition = Vector3.Parse( data["Position"].GetValue<string>() );
				light.LightColor = Color.Parse( props["LightColor"].GetValue<string>() ) ?? light.LightColor;
				light.Radius = props["Radius"].GetValue<float>();
				light.Attenuation = 1;
				light.Shadows = props["Shadows"].GetValue<bool>();
				light.FogStrength = .15f;
				light.Enabled = true;
			}
		}
		Log.Info( "Applied the four Lowtide bridge lantern lights to the current match" );
	}

	private static JsonObject ReadScene() => JsonNode.Parse( File.ReadAllText( Path.Combine( Root, "Assets/scenes/maps/Lowtide/lowtide.scene" ) ) ).AsObject();
	private static Vector3 World( Vector3 plan ) => new( plan.y, -plan.x, plan.z );
}
