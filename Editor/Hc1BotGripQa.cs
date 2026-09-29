using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

/// <summary>
/// The combat bot's body holding each gun it's issued, carried and shouldered (LightweightCombatBot's own IK), from
/// its left, its front and its right, in an isolated scene: hc1_bot_grip_preview [gun] [dress] [headDrop] [buttToEye]
/// [side]. Writes output/bot-grip/&lt;gun&gt;.png (top row carried, bottom shouldered) and logs how far each hand ended
/// up from its IK target and where the butt sits against the right shoulder. headDrop, buttToEye and side (the gun
/// that far right of the eye) try out other shouldered poses than the bot's, into &lt;gun&gt;_d.._b.._s...png. Never
/// edits the open scene.
/// </summary>
public static class Hc1BotGripQa
{
	private const int Tile = 600;

	[ConCmd( "hc1_bot_grip_sample" )]
	public static async void Sample( string label = "motion" )
	{
		var scene = Game.ActiveScene;
		var errors = new System.Collections.Generic.List<float>();
		var rightErrors = new System.Collections.Generic.List<float>();
		var returning = 0;
		var worst = "";
		var worstError = 0f;
		for ( var frame = 0; frame < 180 && scene.IsValid(); frame++ )
		{
			await Task.Delay( 16 );
			foreach ( var bot in scene.GetAllComponents<LightweightCombatBot>() )
			{
				var body = bot.Renderer;
				if ( !bot.IsAlive || !body.IsValid() || body.SceneModel is null ) continue;
				var gun = bot.GetComponentInChildren<WorldModel>();
				if ( !gun.IsValid() || !gun.IkLeftHand.IsValid() || !body.GetBool( "ik.hand_left.enabled" ) ) continue;
				var left = body.Model.Bones.GetBone( "hand_L" ) ?? body.Model.Bones.GetBone( "l_hand" );
				var right = body.Model.Bones.GetBone( "hand_R" ) ?? body.Model.Bones.GetBone( "r_hand" );
				if ( left is null || right is null ) continue;
				var error = body.SceneModel.GetBoneWorldTransform( left.Index ).Position.Distance( gun.IkLeftHand.WorldPosition );
				var weight = (float?)typeof( LightweightCombatBot ).GetField( "_supportGripWeight", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance )?.GetValue( bot ) ?? 0f;
				if ( weight < 1f ) { returning++; continue; }
				errors.Add( error );
				if ( error > worstError )
				{
					worstError = error;
					var lower = left.Parent; var upper = lower.Parent;
					var u = body.SceneModel.GetBoneWorldTransform( upper.Index ).Position;
					var l = body.SceneModel.GetBoneWorldTransform( lower.Index ).Position;
					var h = body.SceneModel.GetBoneWorldTransform( left.Index ).Position;
					worst = $"{bot.WeaponResource?.Name}: weight={weight} chain={upper.Name}/{lower.Name}/{left.Name} reach={u.Distance(l)+l.Distance(h):0.00} target={u.Distance(gun.IkLeftHand.WorldPosition):0.00} aiming={bot.IsAimingIn} aim={bot.AimDirection} body={body.WorldRotation} gunInBody={body.WorldTransform.ToLocal(gun.WorldTransform)}";
				}
				var expectedGun = body.SceneModel.GetBoneWorldTransform( right.Index ).WithScale( 1f ).ToWorld( MilitaryUniform.WeaponHandOffset( body.Model ) );
				rightErrors.Add( gun.WorldPosition.Distance( expectedGun.Position ) );
			}
		}
		var folder = Path.Combine( Project.Current.GetRootPath(), "output/bot-grip" );
		Directory.CreateDirectory( folder );
		string Stats( System.Collections.Generic.List<float> values )
		{
			values.Sort();
			return values.Count == 0 ? "no active bots sampled" : $"samples={values.Count} average={values.Average():0.000} p95={values[(int)((values.Count - 1) * .95f)]:0.000} max={values[^1]:0.000}";
		}
		File.WriteAllText( Path.Combine( folder, $"motion-{System.IO.Path.GetFileName( label )}.txt" ), $"Left: {Stats( errors )}\nRight mount: {Stats( rightErrors )}\nReturning from reload/spawn: {returning}\nWorst: {worst}" );
	}

	private record struct Tuning( float HeadDrop, float ButtToEye, float Side );

	[ConCmd( "hc1_bot_grip_preview" )]
	public static async void Preview( string only = "", bool dress = true, float headDrop = LightweightCombatBot.ShoulderedHeadDrop,
		float buttToEye = LightweightCombatBot.ButtToEye, float side = 0f )
	{
		var tuning = new Tuning( headDrop, buttToEye, side );
		var suffix = tuning == new Tuning( LightweightCombatBot.ShoulderedHeadDrop, LightweightCombatBot.ButtToEye, 0f )
			? "" : $"_d{headDrop:0.#}_b{buttToEye:0.#}_s{side:0.#}";
		var folder = Path.Combine( Project.Current.GetRootPath(), "output", "bot-grip" );
		Directory.CreateDirectory( folder );
		foreach ( var weapon in LightweightCombatBot.WeaponPool().OrderBy( x => x.ResourceName ) )
		{
			if ( !string.IsNullOrEmpty( only ) && !weapon.ResourceName.Contains( only, StringComparison.OrdinalIgnoreCase ) )
				continue;

			try
			{
				using var sheet = new Bitmap( Tile * 3, Tile * 2 );
				sheet.Clear( Color.Black );
				await Render( weapon, false, dress, tuning, sheet, 0 );
				await Render( weapon, true, dress, tuning, sheet, Tile );
				File.WriteAllBytes( Path.Combine( folder, $"{weapon.ResourceName}{suffix}.png" ), sheet.ToPng() );
			}
			catch ( Exception e )
			{
				Log.Warning( $"HC1_BOT_GRIP {weapon.ResourceName} failed: {e}" );
			}
		}

		Log.Info( $"HC1_BOT_GRIP done: {folder} ({tuning})" );
	}

	private static async Task Render( EquipmentResource weapon, bool shouldered, bool dress, Tuning tuning, Bitmap sheet, int row )
	{
		var scene = new Scene();
		try
		{
			SkinnedModelRenderer body;
			WorldModel gun;
			Transform handToGun;
			var supportHand = new BotSupportHand();
			CameraComponent camera;
			using ( scene.Push() )
			{
				body = new GameObject( true, "Bot" ).Components.Create<SkinnedModelRenderer>();
				body.Model = Model.Load( MilitaryUniform.HumanModelPath );
				if ( dress )
					MilitaryUniform.SetModel( body, body.Model, MilitaryUniformStyle.Standard );

				var gunObject = weapon.WorldModelPrefab.Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
				foreach ( var component in gunObject.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
					component.Enabled = component is ModelRenderer || component is WeaponModel;
				gunObject.Enabled = true;
				gun = gunObject.Components.Get<WorldModel>( FindMode.EverythingInSelfAndDescendants );
				if ( gun is null )
					throw new Exception( "no WorldModel" );
				if ( gun.ModelRenderer.IsValid() )
				{
					gun.ModelRenderer.SetBodyGroup( "sight", 0 );
					gun.ModelRenderer.SetBodyGroup( "muzzle", 0 );
				}

				handToGun = MilitaryUniform.WeaponHandOffset( body.Model );
				camera = new GameObject( true, "Grip QA camera" ).Components.Create<CameraComponent>();
				camera.BackgroundColor = new Color( 0.10f, 0.12f, 0.15f );
				camera.FieldOfView = 40f;
				camera.ZNear = 1f;
				var light = new GameObject( true, "Grip QA light" ).Components.Create<DirectionalLight>();
				light.WorldRotation = Rotation.From( 40f, 150f, 0f );
				light.LightColor = Color.White * 2f;
				light.SkyColor = Color.White * 0.6f;
				scene.EditorTick( 0.016f, 0.016f );
			}

			// 0.8 s: past the IK's 0.35 s blend, short of the rifle pose's long idle (1.1 s stood still).
			var aim = new Vector3( 1f, 0f, -0.04f ).Normal;
			var time = 0f;
			for ( var i = 0; i < 16; i++ )
			{
				using ( scene.Push() )
				{
					Pose( body, gun, aim, shouldered, tuning );
					time += 0.05f;
					scene.EditorTick( time, 0.05f );
					foreach ( var renderer in body.GameObject.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
						renderer.SceneModel?.Update( 0.05f );
					Follow( body, gun, handToGun );
					if ( LeftTarget( body, gun ) is { } target )
						supportHand.Apply( body, body.WorldTransform.ToWorld( target ) );
				}

				await Task.Delay( 20 );
			}

			using ( scene.Push() )
			{
				Report( weapon, body, gun, aim, shouldered, tuning );
				using var tile = new Bitmap( Tile, Tile );
				var views = new[]
				{
					(new Vector3( 4f, 62f, 56f ), new Vector3( 4f, 0f, 52f )),
					(new Vector3( 62f, -34f, 60f ), new Vector3( 4f, 0f, 53f )),
					(new Vector3( 4f, -62f, 58f ), new Vector3( 4f, 0f, 54f )),
				};
				for ( var v = 0; v < views.Length; v++ )
				{
					camera.WorldPosition = views[v].Item1;
					camera.WorldRotation = Rotation.LookAt( views[v].Item2 - views[v].Item1 );
					scene.EditorTick( time, 0f );
					camera.RenderToBitmap( tile );
					sheet.DrawBitmap( tile, new Rect( v * Tile, row, Tile, Tile ) );
				}
			}
		}
		finally
		{
			scene.Destroy();
		}
	}

	/// <summary> The bot's parameters for standing still aiming along <paramref name="aim"/> (LightweightCombatBot.UpdateAnimation). </summary>
	private static void Pose( SkinnedModelRenderer body, WorldModel gun, Vector3 aim, bool shouldered, Tuning tuning )
	{
		body.Set( "holdtype", (int)AnimationHelper.HoldTypes.Rifle );
		body.Set( "holdtype_handedness", (int)AnimationHelper.Hand.Right );
		body.Set( "b_grounded", true );
		body.Set( "move_speed", 0f );
		body.Set( "move_groundspeed", 0f );
		body.Set( "move_x", 0f );
		body.Set( "move_y", 0f );
		body.Set( "move_z", 0f );
		body.Set( "duck", 0f );
		body.SetLookDirection( "aim_eyes", aim, 1f );
		body.SetLookDirection( "aim_head", LightweightCombatBot.Lowered( aim, shouldered ? tuning.HeadDrop : 0f ), 1f );
		body.SetLookDirection( "aim_body", aim, shouldered ? 1f : 0.75f );

		var left = LeftTarget( body, gun );
		body.Set( "ik.hand_left.enabled", left.HasValue );
		if ( left is { } l )
		{
			body.Set( "ik.hand_left.position", l.Position );
			body.Set( "ik.hand_left.rotation", l.Rotation );
		}

		var right = shouldered ? LightweightCombatBot.ShoulderedHandIk( body, gun, EyeOnGun( gun, tuning ), aim ) : null;
		body.Set( "ik.hand_right.enabled", right.HasValue );
		if ( right is { } r )
		{
			body.Set( "ik.hand_right.position", r.Position );
			body.Set( "ik.hand_right.rotation", r.Rotation );
		}
	}

	/// <summary> The bot's eye on the gun, <see cref="Tuning.Side"/> left of the gun's line: the gun that far right of the eye. </summary>
	private static Vector3 EyeOnGun( WorldModel gun, Tuning tuning )
	{
		return LightweightCombatBot.EyeOnGun( gun, tuning.ButtToEye ) + Vector3.Left * tuning.Side;
	}

	private static Transform? LeftTarget( SkinnedModelRenderer body, WorldModel gun )
	{
		if ( !gun.IkLeftHand.IsValid() )
			return null;

		var hand = body.WorldTransform.ToLocal( gun.IkLeftHand.WorldTransform );
		return MilitaryUniform.HandIkTransform( body.Model, "hand_left", hand );
	}

	/// <summary> The gun in the right hand as this frame's animation has it (LightweightCombatBot.FollowHand). </summary>
	private static void Follow( SkinnedModelRenderer body, WorldModel gun, Transform handToGun )
	{
		if ( !body.TryGetBoneTransform( "hand_R", out var hand ) )
			return;

		gun.WorldTransform = hand.WithScale( 1f ).ToWorld( handToGun );
		foreach ( var renderer in gun.GameObject.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			if ( renderer.SceneModel is null ) continue;
			renderer.SceneModel.Transform = renderer.WorldTransform;
			renderer.SceneModel.Update( 0f );
		}
	}

	private static void Report( EquipmentResource weapon, SkinnedModelRenderer body, WorldModel gun, Vector3 aim, bool shouldered, Tuning tuning )
	{
		var left = LeftTarget( body, gun );
		var leftError = left is { } l && body.TryGetBoneTransform( "hand_L", out var leftHand )
			? leftHand.Position.Distance( body.WorldTransform.PointToWorld( l.Position ) ) : -1f;
		var eyeOnGun = EyeOnGun( gun, tuning );
		var right = shouldered ? LightweightCombatBot.ShoulderedHandIk( body, gun, eyeOnGun, aim ) : null;
		var rightError = right is { } r && body.TryGetBoneTransform( "hand_R", out var rightHand )
			? rightHand.Position.Distance( body.WorldTransform.PointToWorld( r.Position ) ) : -1f;
		var eye = body.GetAttachment( "eye_R_forward" );
		var sights = eye is { } e ? gun.WorldTransform.PointToLocal( e.Position ) : Vector3.Zero;
		var bounds = gun.ModelRenderer?.Model?.Bounds;
		Log.Info( $"HC1_BOT_GRIP {weapon.ResourceName} {(shouldered ? "shouldered" : "carried")} leftError={leftError:0.00} rightError={rightError:0.00} eyeOnGun={eyeOnGun} eyeInGun={sights} bounds={bounds}" );
		if ( !shouldered || bounds is not { } b )
			return;

		// In the body's space (x forward, y left, z up): the butt (the back of the bounds, level with the bore) against
		// the right shoulder joint, and where the head and the eye ended up.
		var bore = gun.Muzzle.IsValid() ? gun.WorldTransform.PointToLocal( gun.Muzzle.WorldPosition ).z : eyeOnGun.z - 2.5f;
		var butt = body.WorldTransform.PointToLocal( gun.WorldTransform.PointToWorld( new Vector3( b.Mins.x, 0f, bore ) ) );
		string Bone( string name ) => body.TryGetBoneTransform( name, out var t ) ? Round( body.WorldTransform.PointToLocal( t.Position ) ) : "-";
		var shoulder = body.TryGetBoneTransform( "arm_upper_R", out var upperArm ) ? body.WorldTransform.PointToLocal( upperArm.Position ) : Vector3.Zero;
		Log.Info( $"HC1_BOT_GRIP {weapon.ResourceName} body butt={Round( butt )} butt-shoulder={Round( butt - shoulder )} shoulder={Round( shoulder )} clavicle={Bone( "clavicle_R" )} neck={Bone( "neck_0" )} head={Bone( "head" )} eye={(eye is { } eyeAt ? Round( body.WorldTransform.PointToLocal( eyeAt.Position ) ) : "-")}" );
	}

	private static string Round( Vector3 v ) => $"({v.x:0.0} {v.y:0.0} {v.z:0.0})";
}
