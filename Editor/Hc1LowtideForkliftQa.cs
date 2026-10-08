using Editor;
using Sandbox;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Inspect the forklift under Lowtide's lighting without changing the open scene or match.</summary>
public static class Hc1LowtideForkliftQa
{
	private static bool rendering;
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/lowtide/forklift" );
	private static readonly HashSet<string> Visual = new( StringComparer.OrdinalIgnoreCase )
	{ "Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes" };

	[ConCmd( "hc1_lowtide_forklift_compile" )]
	public static async void Compile()
	{
		Directory.CreateDirectory( Folder );
		var report = new StringBuilder();
		try
		{
			foreach ( var path in Directory.EnumerateFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/materials/lowtide/forklift" ), "*.vmat" ) )
			{
				var resource = "materials/lowtide/forklift/" + Path.GetFileName( path );
				var asset = AssetSystem.FindByPath( resource );
				report.AppendLine( $"{resource}: compile={asset?.Compile( true )}" );
			}
			foreach ( var resource in new[] { "models/props/lowtide/forklift.vmdl", "models/props/lowtide/forklift_raised.vmdl", "models/props/lowtide/forklift_ground.vmdl", "models/maps/lowtide/lowtide_dress_east.vmdl", "models/maps/lowtide/lowtide_dress_west.vmdl" } )
				report.AppendLine( $"{resource}: compile={AssetSystem.FindByPath( resource )?.Compile( true )}" );
			await Task.Delay( 3000 );
			File.WriteAllText( Path.Combine( Folder, "compile.txt" ), report.ToString() );
			Log.Info( "Lowtide forklift compilation requested" );
		}
		catch ( Exception e ) { File.WriteAllText( Path.Combine( Folder, "compile-error.txt" ), e.ToString() ); }
	}

	[ConCmd( "hc1_lowtide_forklift_shot" )]
	public static async void Shot( string name = "side", float ee = -285, float en = 19, float ez = 54,
		float te = 0, float tn = 19, float tz = 43, float fov = 35, float exposure = 1, bool map = false, bool raised = false )
	{
		if ( rendering ) return;
		rendering = true;
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Lowtide/lowtide.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
			{
				var label = item["Name"]?.GetValue<string>();
				if ( label is not null && (map ? Visual.Contains( label ) : label is "Sun" or "Sky" or "Look") ) objects.Add( item.DeepClone() );
			}
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				if ( !map )
				{
					new GameObject( true, "Forklift QA prop" ).Components.Create<ModelRenderer>().Model = Model.Load( raised ? "models/props/lowtide/forklift_raised.vmdl" : "models/props/lowtide/forklift.vmdl" );
					new GameObject( true, "Forklift QA paving" ).Components.Create<ModelRenderer>().Model = Model.Load( "models/props/lowtide/forklift_ground.vmdl" );
				}
				var holder = new GameObject( false, "Lowtide Forklift QA Camera" );
				camera = holder.Components.Create<CameraComponent>();
				camera.WorldPosition = World( new( ee, en, ez ) );
				camera.WorldRotation = Rotation.LookAt( World( new( te, tn, tz ) ) - camera.WorldPosition );
				camera.FieldOfView = fov;
				camera.ZNear = .2f;
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
			using ( scene.Push() ) { scene.EditorTick( elapsed += .016f, .016f ); camera.RenderToBitmap( bitmap ); }
			await Task.Delay( 4500 );
			for ( int i = 0; i < 20; i++ )
			{
				using ( scene.Push() ) { scene.EditorTick( elapsed += .016f, .016f ); camera.RenderToBitmap( bitmap ); }
				await Task.Delay( 32 );
			}
			File.WriteAllBytes( Path.Combine( Folder, name + ".png" ), bitmap.ToPng() );
			var report = new StringBuilder( $"view={name}; eye={ee},{en},{ez}; target={te},{tn},{tz}; fov={fov}; exposure={exposure}; map={map}; raised={raised}\n" );
			foreach ( var renderer in scene.GetAllComponents<ModelRenderer>().Where( r => r.Model?.ResourcePath is { } path && (path.Contains( "forklift" ) || path.Contains( "lowtide_dress" )) ) )
				report.AppendLine( $"{renderer.Model.ResourcePath}: error={renderer.Model.IsError}; bounds={renderer.Model.Bounds}" );
			foreach ( var paint in new[] { "yellow", "steel", "silver", "rubber", "vinyl", "chrome" } )
			{
				var material = Material.Load( $"materials/lowtide/forklift/lt_fl_{paint}.vmat" );
				report.AppendLine( $"{paint}: error={material.IsError}; shader={material.ShaderName}; metalTexture={material.GetFeature( "F_METALNESS_TEXTURE" )}; colour={material.GetTexture( "g_tColor" )}; normal={material.GetTexture( "g_tNormal" )}; roughness={material.GetTexture( "g_tRoughness" )}" );
			}
			File.WriteAllText( Path.Combine( Folder, name + ".txt" ), report.ToString() );
			Log.Info( $"Lowtide forklift capture finished: {name}" );
		}
		catch ( Exception e ) { File.WriteAllText( Path.Combine( Folder, name + "-error.txt" ), e.ToString() ); Log.Warning( e ); }
		finally { scene.Destroy(); rendering = false; }
	}

	private static Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
}
