using Editor;
using Sandbox;
using System;
using System.IO;
using System.Threading.Tasks;

/// <summary>
/// Reef Hall's views (Tools/reefhall_map.py VIEWS), rendered from the open editor scene through a camera with the
/// player camera's tonemapping and bloom (prefabs/player/cameras/default_player_camera.prefab), to compare with the
/// reference pictures. `hc1_reefhall_views [filter] [exposure]` writes output/reefhall/&lt;view&gt;.png.
/// </summary>
public static class Hc1ReefHallQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/reefhall" );
	private static bool rendering;

	// ( name, eye, target, fov ), in plan ( east, north, up ): world is ( north, -east, up ).
	private static readonly (string Name, Vector3 Eye, Vector3 Target, float Fov)[] Views =
	{
		( "lobby", new( -2860, -500, 64 ), new( -1800, 300, 260 ), 90 ),
		( "lobby_balcony", new( -1800, 900, 272 ), new( -2700, -300, 200 ), 90 ),
		( "west_gallery", new( -1690, 0, 64 ), new( -800, 0, 80 ), 80 ),
		( "rotunda", new( -780, -200, 64 ), new( 0, 0, 260 ), 90 ),
		( "rotunda_balcony", new( 700, -300, 272 ), new( -300, 300, 260 ), 90 ),
		( "filter", new( 0, 1140, 64 ), new( 0, 1800, 200 ), 90 ),
		( "filter_catwalk", new( -1000, 1760, 272 ), new( 900, 1300, 150 ), 90 ),
		( "tunnel", new( -1100, -1500, 24 ), new( 1100, -1500, 200 ), 90 ),
		( "control", new( 1900, -500, 64 ), new( 2900, 100, 220 ), 90 ),
	};

	private static Vector3 World( Vector3 plan ) => new( plan.y, -plan.x, plan.z );

	/// <summary>One view: `hc1_reefhall_shot name east north up east north up [fov]` (eye, then target, in plan).</summary>
	[ConCmd( "hc1_reefhall_shot" )]
	public static void Shot( string name, float ee, float en, float ez, float te, float tn, float tz, float fov = 80f )
	{
		_extra = (name, new Vector3( ee, en, ez ), new Vector3( te, tn, tz ), fov);
		Render( name );
	}

	private static (string Name, Vector3 Eye, Vector3 Target, float Fov)? _extra;

	[ConCmd( "hc1_reefhall_views" )]
	public static async void Render( string filter = "", float exposure = 1f )
	{
		if ( rendering ) return;
		var scene = SceneEditorSession.Active?.Scene;
		if ( scene is null ) { Log.Warning( "Reef Hall views: no open scene" ); return; }
		rendering = true;
		Directory.CreateDirectory( Folder );
		GameObject holder = null;
		try
		{
			CameraComponent camera;
			using ( scene.Push() )
			{
				holder = scene.CreateObject( false );
				holder.Name = "__reefhall_qa_camera";
				holder.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.Hidden;
				camera = holder.Components.Create<CameraComponent>();
				camera.IsMainCamera = false;
				camera.Priority = -100;
				camera.ZNear = 4;
				camera.ZFar = 20000;
				var tonemap = holder.Components.Create<Tonemapping>();
				tonemap.Mode = Tonemapping.TonemappingMode.ACES;
				tonemap.AutoExposureEnabled = false;
				tonemap.ExposureCompensation = exposure;
				var bloom = holder.Components.Create<Bloom>();
				bloom.Mode = SceneCamera.BloomAccessor.BloomMode.Additive;
				bloom.Strength = 0.15f;
				bloom.Threshold = 1.33f;
				holder.Enabled = true;
			}
			using var bitmap = new Bitmap( 1280, 720 );
			var views = _extra is { } one ? new[] { one } : Views;
			_extra = null;
			foreach ( var view in views )
			{
				if ( !string.IsNullOrEmpty( filter ) && !view.Name.Contains( filter, StringComparison.OrdinalIgnoreCase ) ) continue;
				var eye = World( view.Eye );
				using ( scene.Push() )
				{
					camera.WorldPosition = eye;
					camera.WorldRotation = Rotation.LookAt( World( view.Target ) - eye );
					camera.FieldOfView = view.Fov;
					camera.RenderToBitmap( bitmap, false );
				}
				// Textures stream in on first sight: render again once they have.
				await Task.Delay( 600 );
				using ( scene.Push() ) camera.RenderToBitmap( bitmap, false );
				File.WriteAllBytes( Path.Combine( Folder, view.Name + ".png" ), bitmap.ToPng() );
			}
			Log.Info( $"Reef Hall views: {Folder}" );
		}
		catch ( Exception e ) { Log.Warning( $"Reef Hall views failed: {e}" ); }
		finally
		{
			holder?.Destroy();
			rendering = false;
		}
	}
}
