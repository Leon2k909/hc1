using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

/// <summary>
/// The combat bot's body holding each gun it's issued, carried and shouldered (LightweightCombatBot's own IK), in an
/// isolated scene: hc1_bot_grip_preview [gun] [dress] [headDrop] [buttToEye] [side] [pitch] [yaw] [speed] [crouch]
/// [reloadTime] [cant]. Writes output/bot-grip/&lt;gun&gt;.png: carried, then shouldered, each from the bot's left, front
/// and right, then two rows of close-ups round the shouldered head. Logs how far each hand ended up from its IK target,
/// where the butt sits against the right shoulder, and how much of the face is inside the gun. headDrop, buttToEye, side
/// (the gun that far right of the eye) and cant (the cheek weld's head roll) try out other shouldered poses than the
/// bot's, into &lt;gun&gt;_d.._b.._s.._k...png. Pitch, yaw, movement speed, crouch and reload time exercise the full
/// weapon correction in other poses. Never edits the open scene.
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
				if ( !gun.IsValid() || !gun.IkLeftHand.IsValid() || body.GetInt( "ik.hand_left.enabled" ) == 0 ) continue;
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

	private record struct Tuning( float HeadDrop, float ButtToEye, float Side, float Pitch = 0f, float Yaw = 0f, float Speed = 0f, bool Crouch = false, float ReloadTime = -1f, float Cant = LightweightCombatBot.ShoulderedHeadCant );

	[ConCmd( "hc1_bot_grip_preview" )]
	public static async void Preview( string only = "", bool dress = true, float headDrop = LightweightCombatBot.ShoulderedHeadDrop,
		float buttToEye = LightweightCombatBot.ButtToEye, float side = 0f, float pitch = 0f, float yaw = 0f, float speed = 0f, bool crouch = false, float reloadTime = -1f,
		float cant = LightweightCombatBot.ShoulderedHeadCant )
	{
		var tuning = new Tuning( headDrop, buttToEye, side, pitch, yaw, speed, crouch, reloadTime, cant );
		var suffix = tuning == new Tuning( LightweightCombatBot.ShoulderedHeadDrop, LightweightCombatBot.ButtToEye, 0f )
			? "" : $"_d{headDrop:0.#}_b{buttToEye:0.#}_s{side:0.#}_p{pitch:0.#}_y{yaw:0.#}_v{speed:0.#}_c{crouch}_r{reloadTime:0.##}_k{cant:0.#}";
		var folder = Path.Combine( Project.Current.GetRootPath(), "output", "bot-grip" );
		Directory.CreateDirectory( folder );
		foreach ( var weapon in LightweightCombatBot.WeaponPool().OrderBy( x => x.ResourceName ) )
		{
			if ( !string.IsNullOrEmpty( only ) && !weapon.ResourceName.Contains( only, StringComparison.OrdinalIgnoreCase ) )
				continue;

			try
			{
				using var sheet = new Bitmap( Tile * 3, Tile * 4 );
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
			var gripHand = new BotSupportHand( true );
			var weaponPose = new BotWeaponPose();
			var headCant = new BotHeadCant();
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
			var aim = Rotation.From( tuning.Pitch, tuning.Yaw, 0f ) * new Vector3( 1f, 0f, -0.04f ).Normal;
			var time = 0f;
			var ticks = 16 + (tuning.ReloadTime >= 0f ? (int)MathF.Ceiling( tuning.ReloadTime / .05f ) + 1 : 0);
			for ( var i = 0; i < ticks; i++ )
			{
				using ( scene.Push() )
				{
					var reloading = tuning.ReloadTime >= 0f && i >= 16;
					if ( reloading && i == 16 ) body.SetBool( "b_reload", true );
					Pose( body, gun, aim, shouldered, tuning, reloading );
					time += 0.05f;
					scene.EditorTick( time, 0.05f );
					foreach ( var renderer in body.GameObject.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
						renderer.SceneModel?.Update( 0.05f );
					Follow( body, gun, handToGun );
					var right = body.Model.Bones.GetBone( "hand_R" );
					if ( right is not null )
					{
						var wrist = body.SceneModel.GetBoneWorldTransform( right.Index );
						var shift = weaponPose.Fit( body, gun, supportHand, gripHand, wrist.Position, reloading ? 0f : 1f );
						gripHand.Apply( body, wrist.WithPosition( wrist.Position + shift ) );
						Follow( body, gun, handToGun );
					}
					// The cheek weld, as LightweightCombatBot.FinishWeaponPose cants it.
					if ( shouldered && !reloading && (body.GetAttachment( "eye_R_forward" ) ?? body.GetAttachment( "eyes" )) is { } eye )
						headCant.Apply( body, eye.Position, aim, tuning.Cant * tuning.HeadDrop / LightweightCombatBot.ShoulderedHeadDrop );
					if ( !reloading && LeftTarget( body, gun ) is { } target )
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
				var cameraDrop = tuning.Crouch && body.TryGetBoneTransform( "neck_0", out var neck ) ? Vector3.Up * (neck.Position.z - 57f) : Vector3.Zero;
				for ( var v = 0; v < views.Length; v++ )
				{
					camera.WorldPosition = views[v].Item1 + cameraDrop;
					camera.WorldRotation = Rotation.LookAt( views[v].Item2 - views[v].Item1 );
					scene.EditorTick( time, 0f );
					camera.RenderToBitmap( tile );
					sheet.DrawBitmap( tile, new Rect( v * Tile, row, Tile, Tile ) );
				}

				// Shouldered, two rows of close-ups round the head: from the left, from ahead and to the left, and from above,
				// then from the gun's side: from the right, from ahead and to the right, low, and from behind and above.
				if ( shouldered && body.GetAttachment( "eye_R_forward" ) is { } eye )
				{
					var close = new[]
					{
						(new Vector3( 2f, 20f, 1f ), new Vector3( -1f, 0f, -2f )),
						(new Vector3( 16f, 12f, 6f ), new Vector3( -2f, 0f, -2f )),
						(new Vector3( -4f, 3f, 20f ), new Vector3( -2f, 0f, -3f )),
						(new Vector3( 2f, -20f, 1f ), new Vector3( -1f, 0f, -2f )),
						(new Vector3( 12f, -12f, -3f ), new Vector3( -3f, 0f, -3f )),
						(new Vector3( -14f, -10f, 8f ), new Vector3( -3f, 0f, -2f )),
					};
					for ( var v = 0; v < close.Length; v++ )
					{
						camera.WorldPosition = eye.Position + close[v].Item1;
						camera.WorldRotation = Rotation.LookAt( eye.Position + close[v].Item2 - camera.WorldPosition );
						scene.EditorTick( time, 0f );
						camera.RenderToBitmap( tile );
						sheet.DrawBitmap( tile, new Rect( v % 3 * Tile, row + Tile * (1 + v / 3), Tile, Tile ) );
					}
				}
			}
		}
		finally
		{
			scene.Destroy();
		}
	}

	/// <summary> The bot's parameters for standing still aiming along <paramref name="aim"/> (LightweightCombatBot.UpdateAnimation). </summary>
	private static void Pose( SkinnedModelRenderer body, WorldModel gun, Vector3 aim, bool shouldered, Tuning tuning, bool reloading = false )
	{
		shouldered &= !reloading;
		body.Set( "holdtype", (int)AnimationHelper.HoldTypes.Rifle );
		body.Set( "holdtype_handedness", (int)AnimationHelper.Hand.Right );
		body.SetBool( "b_twohanded", true );
		body.SetBool( "b_grounded", true );
		body.Set( "move_speed", tuning.Speed );
		body.Set( "move_groundspeed", tuning.Speed );
		body.Set( "move_x", tuning.Speed );
		body.Set( "move_y", 0f );
		body.Set( "move_z", 0f );
		body.Set( "move_rate", 1f );
		body.Set( "speed_move", 1f );
		body.Set( "move_style", (int)AnimationHelper.MoveStyles.Run );
		body.Set( "move_direction", 0f );
		body.Set( "duck", tuning.Crouch ? 1f : 0f );
		body.SetLookDirection( "aim_eyes", aim, 1f );
		body.SetLookDirection( "aim_head", LightweightCombatBot.Lowered( aim, shouldered ? tuning.HeadDrop : 0f ), 1f );
		body.SetLookDirection( "aim_body", aim, shouldered ? 1f : 0.75f );

		var left = reloading ? null : LeftTarget( body, gun );
		body.SetBool( "ik.hand_left.enabled", left.HasValue );
		if ( left is { } l )
		{
			body.Set( "ik.hand_left.position", l.Position );
			body.Set( "ik.hand_left.rotation", l.Rotation );
		}

		var right = shouldered ? LightweightCombatBot.ShoulderedHandIk( body, gun, EyeOnGun( gun, tuning ), aim ) : null;
		body.SetBool( "ik.hand_right.enabled", right.HasValue );
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
		var left = tuning.ReloadTime >= 0f ? null : LeftTarget( body, gun );
		var leftError = left is { } l && body.TryGetBoneTransform( "hand_L", out var leftHand )
			? leftHand.Position.Distance( body.WorldTransform.PointToWorld( l.Position ) ) : -1f;
		var eyeOnGun = EyeOnGun( gun, tuning );
		var right = shouldered && tuning.ReloadTime < 0f ? LightweightCombatBot.ShoulderedHandIk( body, gun, eyeOnGun, aim ) : null;
		var rightError = right is { } r && body.TryGetBoneTransform( "hand_R", out var rightHand )
			? rightHand.Position.Distance( body.WorldTransform.PointToWorld( r.Position ) ) : -1f;
		var eye = body.GetAttachment( "eye_R_forward" );
		var sights = eye is { } e ? gun.WorldTransform.PointToLocal( e.Position ) : Vector3.Zero;
		var bounds = gun.ModelRenderer?.Model?.Bounds;
		var mountError = body.TryGetBoneTransform( "hand_R", out var mountHand )
			? gun.WorldPosition.Distance( mountHand.WithScale( 1f ).ToWorld( MilitaryUniform.WeaponHandOffset( body.Model ) ).Position ) : -1f;
		Log.Info( $"HC1_BOT_GRIP {weapon.ResourceName} {(shouldered ? "shouldered" : "carried")} leftError={leftError:0.00} rightIkError={rightError:0.00} rightMountError={mountError:0.00} eyeOnGun={eyeOnGun} eyeInGun={sights} bounds={bounds}" );
		if ( !shouldered || bounds is not { } b )
			return;

		// In the body's space (x forward, y left, z up): the butt (the back of the bounds, level with the bore) against
		// the right shoulder joint, and where the head and the eye ended up.
		var bore = gun.Muzzle.IsValid() ? gun.WorldTransform.PointToLocal( gun.Muzzle.WorldPosition ).z : eyeOnGun.z - 2.5f;
		var butt = body.WorldTransform.PointToLocal( gun.WorldTransform.PointToWorld( new Vector3( b.Mins.x, 0f, bore ) ) );
		string Bone( string name ) => body.TryGetBoneTransform( name, out var t ) ? Round( body.WorldTransform.PointToLocal( t.Position ) ) : "-";
		var shoulder = body.TryGetBoneTransform( "arm_upper_R", out var upperArm ) ? body.WorldTransform.PointToLocal( upperArm.Position ) : Vector3.Zero;
		Log.Info( $"HC1_BOT_GRIP {weapon.ResourceName} body butt={Round( butt )} butt-shoulder={Round( butt - shoulder )} shoulder={Round( shoulder )} clavicle={Bone( "clavicle_R" )} neck={Bone( "neck_0" )} head={Bone( "head" )} eye={(eye is { } eyeAt ? Round( body.WorldTransform.PointToLocal( eyeAt.Position ) ) : "-")}" );
		Face( weapon, body, gun, aim );
	}

	private const float Cell = 0.25f;
	private static readonly System.Collections.Generic.Dictionary<Model, System.Collections.Generic.Dictionary<(int, int), (float Min, float Max)>> Shells = new();

	/// <summary> The gun's mesh as columns over its (x, y) plane, each from the lowest to the highest surface in it. </summary>
	private static System.Collections.Generic.Dictionary<(int, int), (float Min, float Max)> Shell( Model model )
	{
		if ( Shells.TryGetValue( model, out var shell ) )
			return shell;

		shell = new();
		var vertices = model.GetVertices();
		var indices = model.GetIndices();
		var count = Math.Min( indices.Length, model.GetIndexCountForLod( 0 ) );
		for ( var t = 0; t + 2 < count; t += 3 )
		{
			var a = vertices[indices[t]].Position;
			var b = vertices[indices[t + 1]].Position;
			var c = vertices[indices[t + 2]].Position;
			var n = Math.Max( 1, (int)MathF.Ceiling( MathF.Max( a.Distance( b ), MathF.Max( b.Distance( c ), c.Distance( a ) ) ) / 0.2f ) );
			for ( var i = 0; i <= n; i++ )
			for ( var j = 0; i + j <= n; j++ )
			{
				var p = a + (b - a) * (i / (float)n) + (c - a) * (j / (float)n);
				var key = ((int)MathF.Floor( p.x / Cell ), (int)MathF.Floor( p.y / Cell ));
				shell[key] = shell.TryGetValue( key, out var r ) ? (MathF.Min( r.Min, p.z ), MathF.Max( r.Max, p.z )) : (p.z, p.z);
			}
		}

		Shells[model] = shell;
		return shell;
	}

	/// <summary>
	/// The head's vertices (its bind pose, moved rigidly with the head bone) inside the gun's mesh: how many, how deep,
	/// and how far the gun would have to come down for the face to clear it. Then the face's lowest points under the
	/// eye, in the aim's frame (x along the aim, y left), for each half inch ahead of and beside the eye.
	/// </summary>
	private static void Face( EquipmentResource weapon, SkinnedModelRenderer body, WorldModel gun, Vector3 aim )
	{
		var renderer = gun.ModelRenderer.IsValid() ? gun.ModelRenderer : gun.GetComponentInChildren<SkinnedModelRenderer>();
		var head = body.Model.Bones.GetBone( "head" );
		if ( renderer?.Model is not { } model || head is null || body.GetAttachment( "eye_R_forward" ) is not { } eye )
			return;

		var headBind = body.Model.GetBoneTransform( head.Index );
		var neckBind = body.Model.GetBoneTransform( body.Model.Bones.GetBone( "neck_0" ).Index );
		var headNow = body.SceneModel.GetBoneWorldTransform( head.Index );
		var shell = Shell( model );
		var aimFrame = new Transform( eye.Position, Rotation.LookAt( aim, Vector3.Up ) );
		var inside = 0;
		var deepest = 0f;
		var lift = 0f;
		var liftAt = Vector3.Zero;
		var profile = new System.Collections.Generic.Dictionary<(int, int), float>();
		var slices = new System.Collections.Generic.SortedDictionary<int, float>();
		foreach ( var vertex in body.Model.GetVertices() )
		{
			var bind = vertex.Position;
			if ( bind.z < neckBind.Position.z + 1f || (bind - headBind.Position).WithZ( 0f ).Length > 6f )
				continue;

			var world = headNow.PointToWorld( headBind.PointToLocal( bind ) );
			var local = renderer.WorldTransform.PointToLocal( world );
			if ( shell.TryGetValue( ((int)MathF.Floor( local.x / Cell ), (int)MathF.Floor( local.y / Cell )), out var column )
				&& local.z >= column.Min && local.z <= column.Max )
			{
				inside++;
				deepest = MathF.Max( deepest, MathF.Min( local.z - column.Min, column.Max - local.z ) );
				if ( column.Max - local.z > lift )
				{
					lift = column.Max - local.z;
					liftAt = aimFrame.PointToLocal( world );
				}

				var slice = (int)MathF.Floor( aimFrame.PointToLocal( world ).x );
				slices[slice] = MathF.Max( slices.TryGetValue( slice, out var previousLift ) ? previousLift : 0f, column.Max - local.z );
			}

			var a = aimFrame.PointToLocal( world );
			var cell = ((int)MathF.Floor( a.x / 0.5f ), (int)MathF.Floor( a.y / 0.5f ));
			profile[cell] = profile.TryGetValue( cell, out var low ) ? MathF.Min( low, a.z ) : a.z;
		}

		Log.Info( $"HC1_BOT_GRIP {weapon.ResourceName} face inside={inside} deepest={deepest:0.00} lift={lift:0.00} liftAt={Round( liftAt )} byInch={string.Join( " ", slices.Select( p => $"{p.Key}:{p.Value:0.00}" ) )}" );
		var rows = new System.Text.StringBuilder();
		for ( var x = -16; x <= 5; x++ )
		{
			rows.Append( $"\n x{x * 0.5f:+0.0;-0.0}:" );
			for ( var y = -4; y <= 8; y++ )
				rows.Append( profile.TryGetValue( (x, y), out var z ) ? $" {z,5:0.0}" : "     ." );
		}
		Log.Info( $"HC1_BOT_GRIP {weapon.ResourceName} face profile (lowest z under each half inch, y from -2.0 to +4.0):{rows}" );
	}

	private static string Round( Vector3 v ) => $"({v.x:0.0} {v.y:0.0} {v.z:0.0})";
}
