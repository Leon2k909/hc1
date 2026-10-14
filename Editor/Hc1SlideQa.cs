using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

/// <summary>Render entry, hold and recovery poses in an isolated scene: hc1_slide_preview.</summary>
public static class Hc1SlideQa
{
	[ConCmd( "hc1_slide_preview" )]
	public static async void Run()
	{
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/slide-validation" );
		Directory.CreateDirectory( folder );
		var scene = new Scene();
		try
		{
			SkinnedModelRenderer body;
			CameraComponent camera;
			WorldModel gun;
			GameObject handObject;
			using ( scene.Push() )
			{
				body = new GameObject( true, "Slide preview" ).AddComponent<SkinnedModelRenderer>();
				MilitaryUniform.SetModel( body, Model.Load( MilitaryUniform.HumanModelPath ) );
				handObject = body.GetBoneObject( "hand_R" );
				var weapon = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
				var weaponObject = weapon.WorldModelPrefab.Clone( new CloneConfig { Parent = handObject, StartEnabled = false,
					Transform = MilitaryUniform.WeaponHandOffset( body.Model ) } );
				foreach ( var component in weaponObject.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
					component.Enabled = component is ModelRenderer || component is WeaponModel;
				weaponObject.Enabled = true;
				gun = weaponObject.GetComponentInChildren<WorldModel>();
				var helper = body.GameObject.AddComponent<AnimationHelper>();
				helper.Target = body;
				helper.IkLeftHand = gun.IkLeftHand;
				camera = new GameObject( true, "Slide preview camera" ).AddComponent<CameraComponent>();
				camera.BackgroundColor = new Color( .10f, .12f, .15f );
				camera.FieldOfView = 48f;
				camera.ZNear = 1f;
				var light = new GameObject( true, "Slide preview light" ).AddComponent<DirectionalLight>();
				light.WorldRotation = Rotation.From( 40f, 150f, 0f );
				light.LightColor = Color.White * 2f;
				light.SkyColor = Color.White * .6f;
			}
			var time = 0f;
			for ( var tick = 0; tick < 24; tick++ )
			{
				using ( scene.Push() )
				{
					body.Set( "holdtype", (int)AnimationHelper.HoldTypes.Rifle );
					body.SetBool( "b_grounded", true );
					body.Set( "duck", .75f );
					body.SetLookDirection( "aim_body", Vector3.Forward );
					time += .05f;
					scene.EditorTick( time, .05f );
					foreach ( var renderer in body.GetComponentsInChildren<SkinnedModelRenderer>() ) renderer.SceneModel?.Update( .05f );
					body.SceneModel?.Update( .05f );
				}
				await Task.Delay( 30 );
			}
			using ( scene.Push() )
			{
				var poses = new[] { 0f, .33f, .66f, 1f, .66f, .33f, 0f };
				var slide = new ThirdPersonSlidePose();
				using var sheet = new Bitmap( 480 * poses.Length, 480 * 2 );
				using var tile = new Bitmap( 480, 480 );
				var report = new System.Text.StringBuilder();
				for ( var p = 0; p < poses.Length; p++ )
				{
					for ( var side = 0; side < 2; side++ )
					{
						camera.WorldPosition = side == 0 ? new Vector3( 8f, 100f, 36f ) : new Vector3( 70f, -80f, 38f );
						camera.WorldRotation = Rotation.LookAt( new Vector3( 7f, 0f, 28f ) - camera.WorldPosition );
						scene.EditorTick( time, 0f );
						body.SceneModel.Update( .001f );
						foreach ( var renderer in body.GetComponentsInChildren<SkinnedModelRenderer>() ) renderer.SceneModel?.Update( .001f );
						slide.Apply( body, poses[p] );
						// In this isolated scene the explicit animation update happens after EditorTick's merge.
						// Repeat that merge for the unmodified baseline and recovery pose too.
						foreach ( var garment in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
							if ( garment != body && garment.BoneMergeTarget == body ) garment.SceneModel?.MergeBones( body.SceneModel );
						var hand = body.SceneModel.GetBoneWorldTransform( body.Model.Bones.GetBone( "hand_R" ).Index );
						if ( poses[p] == 0f ) handObject.WorldTransform = hand;
						var mountError = gun.WorldPosition.Distance( hand.ToWorld( MilitaryUniform.WeaponHandOffset( body.Model ) ).Position );
						if ( mountError > .01f ) throw new Exception( $"Weapon missed its hand by {mountError} at blend {poses[p]}" );
						camera.RenderToBitmap( tile );
						sheet.DrawBitmap( tile, new Rect( p * 480, side * 480, 480, 480 ) );
						if ( side == 0 )
						{
							report.AppendLine( $"blend {poses[p]} weapon mount error: {mountError:F4}" );
							Vector3 At( string name ) => body.SceneModel.GetBoneWorldTransform( body.Model.Bones.GetBone( name ).Index ).Position;
							foreach ( var leg in new[] { "L", "R" } )
								report.AppendLine( $"blend {poses[p]} {leg}: hip={At( "leg_upper_" + leg )} knee={At( "leg_lower_" + leg )} ankle={At( "ankle_" + leg )} thigh={At( "leg_upper_" + leg ).Distance( At( "leg_lower_" + leg ) ):F3} shin={At( "leg_lower_" + leg ).Distance( At( "ankle_" + leg ) ):F3}" );
						}
					}
				}
				File.WriteAllBytes( Path.Combine( folder, "slide-preview.png" ), sheet.ToPng() );
				File.WriteAllText( Path.Combine( folder, "slide-preview.txt" ), report.ToString() );
				Log.Info( "SLIDE_PREVIEW done: " + folder );
			}
		}
		catch ( Exception error )
		{
			File.WriteAllText( Path.Combine( folder, "slide-preview-error.txt" ), error.ToString() );
			Log.Error( "SLIDE_PREVIEW " + error );
		}
		finally { scene.Destroy(); }
	}
}
