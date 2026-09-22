using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

public static class Hc1CasingQa
{
	[ConCmd( "hc1_casing_check" )]
	public static async void Check()
	{
		var folder = Path.Combine( Path.GetTempPath(), "hc1-casing-qa" );
		Directory.CreateDirectory( folder );
		var report = new StringBuilder();
		var scene = new Scene();
		try
		{
			ViewModel view;
			GameObject root;
			CameraComponent camera;
			GameObject casingPrefab;
			using ( scene.Push() )
			{
				root = SceneUtility.GetPrefabScene( ResourceLibrary.Get<PrefabFile>( "weapons/m4a1/vm_m4a1.prefab" ) )
					.Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
				view = root.GetComponent<ViewModel>( true );
				foreach ( var c in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) ) c.Enabled = c is ModelRenderer;
				foreach ( var r in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				{
					r.RenderOptions.Game = true;
					r.RenderOptions.Overlay = false;
				}
				view.ModelRenderer.Set( "b_deploy_skip", true );
				view.ModelRenderer.Set( "b_grounded", true );
				view.ModelRenderer.Set( "b_twohanded", true );
				root.Enabled = true;
				camera = new GameObject( true, "Casing QA camera" ).Components.Create<CameraComponent>();
				camera.BackgroundColor = new Color( 0.12f, 0.15f, 0.18f );
				camera.FieldOfView = 90f;
				camera.ZNear = 0.1f;
				var light = new GameObject( true, "Casing QA light" ).Components.Create<DirectionalLight>();
				light.WorldRotation = Rotation.From( 35f, 25f, 0f );
				light.LightColor = Color.White * 2f;
				light.SkyColor = Color.White * 0.65f;
				casingPrefab = SceneUtility.GetPrefabScene( ResourceLibrary.Get<PrefabFile>( "prefabs/weapon_effects/556_spent_casing.prefab" ) );
				var floor = new GameObject( true, "Casing QA floor" ).Components.Create<BoxCollider>();
				floor.Center = new Vector3( 0, 0, -70 );
				floor.Scale = new Vector3( 1000, 1000, 10 );
			}

			for ( int i = 0; i < 12; i++ )
			{
				using ( scene.Push() )
				{
					scene.EditorTick( 0.1f, 0.1f );
					view.ModelRenderer.SceneModel.Update( 0.1f );
				}
				await Task.Delay( 20 );
			}

			GameObject brass;
			SpentCasing casing;
			using ( scene.Push() )
			{
				report.AppendLine( $"Animated port bone: {view.ModelRenderer.SceneModel.GetBoneWorldTransform( view.EjectionPort.Name )}" );
				brass = view.EjectCasing( casingPrefab );
				report.AppendLine( $"Spawn={brass?.Name}, parent={brass?.Parent?.Name}, parentType={brass?.Parent?.GetType().Name}" );
				Require( brass.IsValid() && brass.Parent != view.EjectionPort && brass.Parent != root, "Case must be detached from the weapon" );
				var screen = camera.PointToScreenNormal( brass.WorldPosition );
				Require( brass.WorldPosition.x > 2f && screen.x > 0f && screen.x < 1f && screen.y > 0f && screen.y < 1f,
					"Case did not spawn at the visible animated receiver" );
				casing = brass.GetComponent<SpentCasing>();
				casing.Enabled = false;
				Require( casing.Velocity.Dot( view.WorldRotation.Right ) > 80, "Case did not eject to the right" );
				Require( casing.Velocity.Dot( view.WorldRotation.Up ) > 50, "Case did not arc upward" );
				var renderer = brass.GetComponent<ModelRenderer>();
				Require( renderer.Model is not null && !renderer.Model.IsError, "Brass model failed to load" );
				report.AppendLine( $"Model={renderer.Model.Name}, bounds={renderer.Model.Bounds}, bodygroups={renderer.BodyGroups}" );
				report.AppendLine( $"Ejection port={view.EjectionPort.WorldPosition}, velocity={casing.Velocity}" );
				foreach ( var property in typeof(Model).GetProperties().Where( p => p.Name.Contains( "Body" ) ) )
					report.AppendLine( $"Model property {property.Name}: {property.GetValue( renderer.Model )}" );
			}

			float elapsed = 0;
			foreach ( var time in new[] { 0f, 0.033f, 0.067f, 0.1f, 0.167f } )
			{
				using ( scene.Push() )
				{
					Advance( casing, time - elapsed );
					elapsed = time;
					scene.EditorTick( 0.001f, 0.001f );
					foreach ( var r in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
					{
						r.SceneModel.Transform = r.WorldTransform;
						if ( r != view.ModelRenderer && r.BoneMergeTarget == view.ModelRenderer ) r.SceneModel.MergeBones( view.ModelRenderer.SceneModel );
					}
					brass.GetComponent<ModelRenderer>().SceneObject.Transform = brass.WorldTransform;
				}
				await Task.Delay( 50 );
				using ( scene.Push() )
				{
					using var bitmap = new Bitmap( 1600, 900 );
					camera.RenderToBitmap( bitmap );
					File.WriteAllBytes( Path.Combine( folder, $"eject-{time:0.000}.png" ), bitmap.ToPng() );
					report.AppendLine( $"t={time}: position={brass.WorldPosition}, screen={camera.PointToScreenNormal( brass.WorldPosition )}" );
				}
			}

			using ( scene.Push() )
			{
				camera.WorldPosition = brass.WorldPosition + new Vector3( -5f, -5f, 3f );
				camera.WorldRotation = Rotation.LookAt( brass.WorldPosition - camera.WorldPosition );
				using var closeup = new Bitmap( 800, 800 );
				camera.RenderToBitmap( closeup );
				File.WriteAllBytes( Path.Combine( folder, "casing-closeup.png" ), closeup.ToPng() );
				var position = brass.WorldPosition;
				root.WorldPosition += Vector3.Forward * 100;
				Require( brass.WorldPosition.Distance( position ) < 0.001f, "Brass moved with the gun" );
				for ( int i = 0; i < 300; i++ ) Advance( casing, 1f / 60f );
				Require( casing.HasSettled && brass.WorldPosition.z > -65f, "Case did not settle on the floor" );
				Advance( casing, 9f );
			}
			// Destroy is queued until the engine finishes the frame.
			await Task.Delay( 100 );
			using ( scene.Push() )
			{
				Require( brass.IsDestroyed, "Expired casing was not cleaned up" );
				for ( int i = 0; i < 110; i++ ) view.EjectCasing( casingPrefab );
			}
			await Task.Delay( 100 );
			using ( scene.Push() )
			{
				Require( scene.GetAllComponents<SpentCasing>().Count( c => c.IsValid() ) <= SpentCasing.MaxActiveCasings, "Brass budget exceeded" );
				report.AppendLine( "PASS: detached case per ejection; rightward/upward flight; world collision and settling; expiry; bounded casing count." );
			}
		}
		catch ( Exception ex ) { report.AppendLine( $"FAIL: {ex}" ); }
		finally
		{
			scene.Destroy();
			File.WriteAllText( Path.Combine( folder, "result.txt" ), report.ToString() );
		}
	}

	private static void Advance( SpentCasing casing, float time ) => typeof(SpentCasing).GetMethod( "Advance", BindingFlags.Instance | BindingFlags.NonPublic ).Invoke( casing, new object[] { time } );
	private static void Require( bool value, string message ) { if ( !value ) throw new Exception( message ); }
}
