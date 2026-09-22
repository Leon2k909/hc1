using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

/// <summary>Inspect timing checks and isolated first-person previews; never edits the open scene.</summary>
public static class Hc1InspectQa
{
	[ConCmd( "hc1_inspect_check" )]
	public static void Check()
	{
		var output = Path.Combine( Path.GetTempPath(), "hc1-inspect-check.txt" );
		try
		{
			foreach ( var fps in new[] { 30, 60, 144 } )
			{
				var animation = new WeaponInspectAnimation();
				var delta = 1f / fps;
				animation.Update( true, true, delta );
				Require( !animation.IsActive, "Blocked input started an inspect" );
				animation.Update( true, false, delta );
				Require( animation.IsPlaying, "Inspect did not start" );
				for ( int i = 0; i < fps * 4; ++i ) animation.Update( false, false, delta );
				Require( !animation.IsActive && animation.Pose.Position.Length < 0.001f, "Inspect did not return to idle" );
				animation.Update( true, false, delta );
				for ( int i = 0; i < fps; ++i ) animation.Update( false, false, delta );
				animation.Update( false, true, delta );
				Require( !animation.IsPlaying, "Combat did not interrupt inspect" );
				for ( int i = 0; i < fps / 4; ++i ) animation.Update( false, true, delta );
				Require( !animation.IsActive && animation.Pose.Position.Length < 0.001f, "Cancel left a pose offset" );
				animation.Update( true, false, delta );
				Require( animation.IsPlaying, "Inspect could not restart after cancellation" );
				animation.Reset();
				Require( !animation.IsActive, "Holster reset failed" );
			}

			var left = WeaponInspectAnimation.Evaluate( 0.8f );
			var right = WeaponInspectAnimation.Evaluate( 2.2f );
			Require( left.Rotation.Yaw() < -20f && right.Rotation.Yaw() < -30f
				&& left.Rotation.Angles().roll < 0f && right.Rotation.Angles().roll > 10f, "Both inspection angles were not presented" );
			var pivot = new Vector3( 16f, -4f, -4f );
			var heldPivot = pivot + new Vector3( 6f, 2.5f, 2f );
			Require( (left.Position + left.Rotation * pivot - heldPivot).Length < 0.001f, "First turn moved the receiver pivot" );
			Require( (right.Position + right.Rotation * pivot - heldPivot).Length < 0.001f, "Second turn moved the receiver pivot" );
			File.WriteAllText( output, "PASS: start, blocking, automatic completion, combat cancellation, restart and holster reset at 30/60/144 FPS; both presentation angles and receiver pivot verified." );
		}
		catch ( Exception e ) { File.WriteAllText( output, e.ToString() ); }
	}

	private static void Require( bool value, string message )
	{
		if ( !value ) throw new Exception( message );
	}

	[ConCmd( "hc1_inspect_preview" )]
	public static async void Preview( string weapon = "m4a1" )
	{
		var folder = Path.Combine( Path.GetTempPath(), "hc1-inspect-preview" );
		Directory.CreateDirectory( folder );
		var scene = new Scene();
		try
		{
			GameObject root;
			SkinnedModelRenderer renderer;
			SkinnedModelRenderer[] renderers;
			CameraComponent camera;
			string[] names;
			using ( scene.Push() )
			{
				var path = $"weapons/{weapon}/vm_{weapon}.prefab";
				var prefab = ResourceLibrary.Get<PrefabFile>( path );
				Require( prefab is not null, $"Missing prefab: {path}" );
				root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
				var view = root.GetComponent<ViewModel>( true );
				Require( view.IsValid() && view.ModelRenderer.IsValid(), "Missing viewmodel renderer" );
				renderer = view.ModelRenderer;
				foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
					component.Enabled = component is ModelRenderer;
				renderers = root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ).ToArray();
				foreach ( var model in renderers )
				{
					model.RenderOptions.Game = true;
					model.RenderOptions.Overlay = false;
				}
				names = Enumerable.Range( 0, renderer.Model.AnimationCount ).Select( renderer.Model.GetAnimationName ).ToArray();
				renderer.UseAnimGraph = true;
				renderer.Set( "b_deploy_skip", true );
				renderer.Set( "b_grounded", true );
				renderer.Set( "b_twohanded", weapon != "usp" );
				renderer.Set( "holdtype", (int)(weapon == "usp" ? AnimationHelper.HoldTypes.Pistol : AnimationHelper.HoldTypes.Rifle) );
				root.Enabled = true;

				camera = new GameObject( true, "Inspect QA camera" ).Components.Create<CameraComponent>();
				camera.BackgroundColor = new Color( 0.12f, 0.15f, 0.18f );
				camera.FieldOfView = 90f;
				camera.ZNear = 0.1f;
				var light = new GameObject( true, "Inspect QA light" ).Components.Create<DirectionalLight>();
				light.WorldRotation = Rotation.From( 35f, 25f, 0f );
				light.LightColor = Color.White * 2f;
				light.SkyColor = Color.White * 0.65f;
				scene.EditorTick( 0.016f, 0.016f );
			}

			// Let the renderer finish bone updates between ticks, as it does in play.
			for ( int i = 0; i < 12; ++i )
			{
				using ( scene.Push() )
				{
					scene.EditorTick( 0.1f, 0.1f );
					renderer.SceneModel.Update( 0.1f );
				}
				await Task.Delay( 20 );
			}

			foreach ( var time in new[] { 0f, 0.25f, 0.8f, 1.6f, 2.2f, 2.95f, 3.2f } )
			{
				using ( scene.Push() )
				{
					root.WorldTransform = WeaponInspectAnimation.Evaluate( time );
					scene.EditorTick( 0.016f, 0.016f );
					foreach ( var model in renderers )
					{
						model.SceneModel.Transform = model.WorldTransform;
						model.SceneModel.Update( 0f );
					}
				}
				await Task.Delay( 80 );
				using ( scene.Push() )
				{
					foreach ( var model in renderers )
						if ( model != renderer && model.BoneMergeTarget == renderer )
							model.SceneModel.MergeBones( renderer.SceneModel );
					using var bitmap = new Bitmap( 1600, 900 );
					camera.RenderToBitmap( bitmap );
					File.WriteAllBytes( Path.Combine( folder, $"{weapon}-{time:0.00}.png" ), bitmap.ToPng() );
				}
			}
			File.WriteAllText( Path.Combine( folder, $"{weapon}.txt" ), $"PASS: rendered seven inspection poses using the weapon animation graph; available inspect clips: {string.Join( ", ", names.Where( x => x.Contains( "inspect", StringComparison.OrdinalIgnoreCase ) || x.Contains( "admire", StringComparison.OrdinalIgnoreCase ) ) )}" );
		}
		catch ( Exception e ) { File.WriteAllText( Path.Combine( folder, $"{weapon}.txt" ), e.ToString() ); }
		finally { scene.Destroy(); }
	}
}
